"""
ReviewGuard — Guard Node.
Handles negative review pathways by drafting a recovery email and firing an internal ops alert.
"""

from agents.email_drafter import draft_recovery_email
from agents.ops_notifier import generate_ops_note
from config import settings
from logger import logger
from state import ReviewGuardState
from tools.gmail_tool import send_ops_notification, send_recovery_email


def guard_node(state: ReviewGuardState) -> dict:
    """
    Triggers the negative review recovery logic.
    Coordinates AI agents to draft apologies and map ops notes, then dispatches 
    both the customer recovery email and internal team alert.

    Parameters
    ----------
    state : ReviewGuardState
        The active pipeline state.

    Returns
    -------
    dict
        State updates merging the agent results and tracking markers.
    """
    customer_name = state.get("customer_name", "Valued Customer")
    logger.info(f"Node [guard]: Initiating damage control for {customer_name}")

    # 1. Run AI Agents
    try:
        logger.info("Node [guard]: Calling email_drafter agent...")
        draft_update = draft_recovery_email(state)
        
        logger.info("Node [guard]: Calling ops_notifier agent...")
        ops_update = generate_ops_note(state)
    except Exception as exc:
        logger.error(f"Node [guard]: AI Agent generation failed: {exc}")
        return {"stage": "complete", "error": f"Agent generation failed: {exc}"}

    draft_body = draft_update.get("recovery_email_draft", "")
    ops_note = ops_update.get("internal_ops_note", "")

    # 2. Fire Emails
    customer_email = state.get("customer_email", "")
    owner_email = settings.owner_email
    category = state.get("category", "General")

    recovery_sent = False
    ops_notified = False

    if customer_email and draft_body:
        logger.info("Node [guard]: Dispatching recovery email to customer...")
        recovery_sent = send_recovery_email(customer_email, draft_body)
    else:
        logger.warning("Node [guard]: Missing customer email or draft, skipping recovery send.")

    if owner_email and ops_note:
        logger.info("Node [guard]: Dispatching ops notification to owner...")
        ops_notified = send_ops_notification(owner_email, ops_note, category, customer_name)
    else:
        logger.warning("Node [guard]: Missing owner email or ops note, skipping internal alert.")

    # 3. Consolidate State
    return {
        "recovery_email_draft": draft_body,
        "internal_ops_note": ops_note,
        "recovery_email_sent": recovery_sent,
        "ops_notified": ops_notified,
        "stage": "complete"
    }
