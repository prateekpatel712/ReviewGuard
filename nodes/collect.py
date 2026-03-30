"""
ReviewGuard — Support Node.
Handles the initial ingestion event into the LangGraph pipeline.
"""

from logger import logger
from state import ReviewGuardState


def collect_node(state: ReviewGuardState) -> dict:
    """
    Initialises the pipeline by transitioning the state to 'routing'.

    Parameters
    ----------
    state : ReviewGuardState
        The current pipeline state containing raw feedback.

    Returns
    -------
    dict
        State updates mapping the next stage.
    """
    customer = state.get('customer_name', 'Unknown Customer')
    logger.info(f"Node [collect]: Initialising pipeline for {customer}")
    return {"stage": "routing"}
