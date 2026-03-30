"""
ReviewGuard — Router Edge.
Evaluates agent output directly and selects the downstream edge organically.
"""

from logger import logger
from state import ReviewGuardState


def route_feedback(state: ReviewGuardState) -> str:
    """
    Evaluates the feedback sentiment to route to the correct branch.

    Parameters
    ----------
    state : ReviewGuardState
        The current pipeline state post-analysis.

    Returns
    -------
    str
        The name of the next node to trigger ('boost' or 'guard').
    """
    sentiment = state.get("sentiment")
    logger.info(f"Routing edge evaluating sentiment: {sentiment}")
    
    if sentiment == "positive":
        return "boost"
    if sentiment in ["negative", "neutral"]:
        return "guard"
        
    logger.warning(f"Routing edge encountered unknown sentiment '{sentiment}'; defaulting to guard.")
    return "guard"
