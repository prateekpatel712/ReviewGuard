"""
ReviewGuard — Pipeline Test.
Tests both phases: email dispatch and guard pipeline.
"""

import os
from pprint import pprint

# Force DRY_RUN off for live testing
os.environ["DRY_RUN"] = "false"

from state import FeedbackRow, FormResponseRow
from main import run_guard_pipeline
from tools.gmail_tool import send_review_request
from config import settings


def test_phase1_email():
    """Test Phase 1: Sending a review request email."""
    print("====================================")
    print(" PHASE 1: REVIEW REQUEST EMAIL TEST")
    print("====================================")

    success = send_review_request(
        to_email=settings.owner_email,
        customer_name="Test Customer",
        google_review_link=settings.google_review_link,
    )

    print(f"Email sent: {'PASS' if success else 'FAIL'}")
    print()


def test_phase2_guard():
    """Test Phase 2: Guard pipeline for private feedback."""
    print("====================================")
    print(" PHASE 2: GUARD PIPELINE TEST")
    print("====================================")

    mock_form = FormResponseRow(
        timestamp="2026-03-29T10:00:00Z",
        name="Unhappy Customer",
        email=settings.owner_email,  # Send to yourself for testing
        feedback="The food was cold and the waiter was very rude. We waited 45 minutes for our order.",
        row_index=1,
    )

    state = run_guard_pipeline(mock_form)

    print("\n--- Validation Results ---")
    print(f"Sentiment: {state.get('sentiment')} (expected: negative)")
    print(f"Recovery email sent: {'PASS' if state.get('recovery_email_sent') else 'FAIL'}")
    print(f"Ops notified: {'PASS' if state.get('ops_notified') else 'FAIL'}")
    print(f"Recovery draft present: {'PASS' if state.get('recovery_email_draft') else 'FAIL'}")
    print(f"Ops note present: {'PASS' if state.get('internal_ops_note') else 'FAIL'}")
    print("--------------------------\n")


if __name__ == "__main__":
    test_phase1_email()
    test_phase2_guard()
