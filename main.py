"""
ReviewGuard — Main entry point.
Orchestrates the two-phase pipeline:

  Phase 1 (Outbound):  Read new customers from "Feedback Queue" sheet
                        → Send review request email (two buttons)
                        → Mark as "Sent"

  Phase 2 (Inbound):   Read private feedback from "Feedback Responses" sheet
                        → Hardcode as negative
                        → Run AI guard pipeline (recovery email + ops alert)
                        → Mark as "Processed"
"""

import os
import sys
from collections import Counter
from typing import Any, Dict

# Debug: dump env var keys at startup
print(f"DEBUG ENV KEYS: {list(os.environ.keys())}", flush=True)

from langgraph.graph import START, END, StateGraph

from agents.email_drafter import draft_recovery_email
from agents.ops_notifier import generate_ops_note
from agents.weekly_summariser import generate_weekly_summary
from config import settings
from logger import logger
from nodes.guard import guard_node
from state import FeedbackRow, FormResponseRow, ReviewGuardState
from tools.gmail_tool import send_review_request, send_weekly_summary_email
from tools.sheets_tool import (
    get_pending_feedback_rows,
    get_pending_form_responses,
    get_processed_feedback_rows,
    mark_row_sent,
    mark_form_row_processed,
)

# ---------------------------------------------------------------------------
# Build the Inbound LangGraph (for private feedback processing)
# ---------------------------------------------------------------------------
from agents.feedback_analyser import analyse_feedback

builder = StateGraph(ReviewGuardState)
builder.add_node("analyzer", analyse_feedback)
builder.add_node("guard", guard_node)

builder.add_edge(START, "analyzer")

def route_inbound(state: ReviewGuardState):
    sentiment = state.get("sentiment", "negative")
    if sentiment == "positive":
        logger.info("Inbound route: positive feedback detected. Skipping guard.")
        return END
    return "guard"

builder.add_conditional_edges("analyzer", route_inbound)
builder.add_edge("guard", END)
guard_graph = builder.compile()


# ---------------------------------------------------------------------------
# Phase 1: Send Review Request Emails
# ---------------------------------------------------------------------------

def send_all_pending_emails():
    """
    Reads all new (unprocessed) rows from the 'Feedback Queue' sheet,
    sends each customer the two-button review request email, and marks
    the row as 'Sent'.

    No AI or sentiment analysis is involved in this phase.
    """
    logger.info("=" * 40)
    logger.info("PHASE 1: Sending review request emails...")
    logger.info("=" * 40)

    try:
        pending_rows = get_pending_feedback_rows()
    except Exception as exc:
        logger.error(f"Failed to fetch pending rows: {exc}")
        return

    if not pending_rows:
        logger.info("No new customers to email. ✅")
        return

    total = len(pending_rows)
    logger.info(f"Found {total} new customer(s) to email.")

    sent_count = 0
    error_count = 0

    for row in pending_rows:
        try:
            logger.info(f"[{row.name}] Sending review request to {row.email}...")
            success = send_review_request(
                to_email=row.email,
                customer_name=row.name,
                google_review_link=settings.google_review_link,
            )

            if success and row.row_index > 0:
                mark_row_sent(row.row_index)
                sent_count += 1
                logger.info(f"[{row.name}] ✅ Review request sent & marked.")
            elif not success:
                logger.warning(f"[{row.name}] ⚠️ Email send returned False.")
                error_count += 1

        except Exception as exc:
            logger.error(f"[{row.name}] ❌ Failed: {exc}")
            error_count += 1

    logger.info(f"Phase 1 complete: {sent_count}/{total} emails sent.")
    if error_count > 0:
        logger.error(f"Encountered errors on {error_count} row(s).")


# ---------------------------------------------------------------------------
# Phase 2: Process Private Feedback (Guard Pipeline)
# ---------------------------------------------------------------------------

def run_guard_pipeline(row: FormResponseRow) -> dict:
    """
    Initialises state from a FormResponseRow and runs through the
    negative-only guard pipeline (AI recovery email + ops alert).
    """
    logger.info(f"[{row.name}] ▶ Starting guard pipeline...")

    initial_state: ReviewGuardState = {
        "customer_name": row.name,
        "customer_email": row.email,
        "visit_date": None,

        "raw_feedback": row.feedback,
        "sentiment": "unknown",         # Will be determined by feedback_analyser
        "category": "Private Response",

        "recovery_email_draft": "",
        "internal_ops_note": "",

        "review_boost_sent": False,
        "recovery_email_sent": False,
        "ops_notified": False,

        "error": None,
        "stage": "starting",
    }

    final_state = guard_graph.invoke(initial_state)
    return final_state


def process_all_form_responses():
    """
    Reads all pending rows from the 'Feedback Responses' tab, pushes each
    through the guard pipeline, and marks as 'Processed'.
    """
    logger.info("=" * 40)
    logger.info("PHASE 2: Processing private feedback...")
    logger.info("=" * 40)

    try:
        pending_forms = get_pending_form_responses()
    except Exception as exc:
        logger.error(f"Failed to fetch form responses: {exc}")
        return

    if not pending_forms:
        logger.info("No pending form responses. ✅")
        return

    total = len(pending_forms)
    logger.info(f"Found {total} private feedback(s) to process.")

    processed_count = 0
    error_count = 0

    for row in pending_forms:
        try:
            final_state = run_guard_pipeline(row)

            if row.row_index > 0:
                mark_form_row_processed(row_index=row.row_index)

            processed_count += 1
            logger.info(f"[{row.name}] ✅ Guard pipeline complete.")

        except Exception as exc:
            logger.error(f"[{row.name}] ❌ Pipeline failed: {exc}")
            error_count += 1

    logger.info(f"Phase 2 complete: {processed_count}/{total} processed.")
    if error_count > 0:
        logger.error(f"Encountered errors on {error_count} row(s).")


# ---------------------------------------------------------------------------
# Weekly Summary (unchanged)
# ---------------------------------------------------------------------------

def weekly_summary():
    """
    Pulls processed rows, calculates stats, generates AI summary, and
    emails the management report.
    """
    logger.info("Starting Weekly Summary sweep...")
    rows = get_processed_feedback_rows()

    if not rows:
        logger.warning("No historical processed rows found. Skipping report.")
        return

    total = len(rows)
    positives = sum(1 for r in rows if r.get("sentiment") == "positive")
    negatives = sum(1 for r in rows if r.get("sentiment") in ["negative", "neutral"])

    categories = [r.get("category") for r in rows if r.get("category")]
    top_category = Counter(categories).most_common(1)[0][0] if categories else "Unknown"

    stats = {
        "total": total,
        "positive": positives,
        "negative": negatives,
        "top_category": top_category,
    }

    logger.info(f"Stats -> Total: {total} | Pos: {positives} | Neg: {negatives} | Top: {top_category}")

    summary_html = generate_weekly_summary(stats)
    success = send_weekly_summary_email(settings.owner_email, stats, summary_html)

    if success:
        logger.info("Weekly Summary successfully delivered.")
    else:
        logger.error("Failed to deliver Weekly Summary.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--weekly":
        weekly_summary()
    else:
        # Run both phases sequentially
        send_all_pending_emails()
        process_all_form_responses()
