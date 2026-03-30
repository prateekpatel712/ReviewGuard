"""
ReviewGuard — Boost Node.
Handles positive review pathways by firing Google Review prompt requests.
"""

from config import settings
from logger import logger
from state import ReviewGuardState
from tools.gmail_tool import send_review_request


def boost_node(state: ReviewGuardState) -> dict:
    """
    Triggers the positive review boost logic.
    Sends an email to the customer asking for a Google Review.

    Parameters
    ----------
    state : ReviewGuardState
        The active pipeline state.

    Returns
    -------
    dict
        State updates reflecting the boost email success/failure.
    """
    to_email = state.get("customer_email", "")
    customer_name = state.get("customer_name", "Valued Customer")
    google_review_link = settings.google_review_link

    logger.info(f"Node [boost]: Triggering review boost for {customer_name} ({to_email})")

    if not to_email or not google_review_link:
        logger.warning("Node [boost]: Missing email or GOOGLE_REVIEW_LINK. Skipping boost.")
        return {
            "review_boost_sent": False,
            "stage": "complete",
            "error": "Missing email or Google Review link."
        }

    try:
        success = send_review_request(
            to_email=to_email,
            customer_name=customer_name,
            google_review_link=google_review_link
        )
        logger.info(f"Node [boost]: Review request sent -> {success}")
        return {
            "review_boost_sent": success,
            "stage": "complete"
        }
    except Exception as exc:
        logger.error(f"Node [boost] encountered an error: {exc}")
        return {
            "review_boost_sent": False,
            "stage": "complete",
            "error": str(exc)
        }
