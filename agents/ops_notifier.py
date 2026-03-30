"""
ReviewGuard — Ops Notifier Agent.
Generates brief, actionable operational notes based on customer feedback.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from config import settings
from logger import logger
from state import ReviewGuardState

def generate_ops_note(state: ReviewGuardState) -> dict:
    """
    Generates an internal note for the restaurant manager based on negative feedback.

    Parameters
    ----------
    state : ReviewGuardState
        The active pipeline state containing the feedback and parsed category.

    Returns
    -------
    dict
        State updates mapping the 'internal_ops_note' field representing an actionable alert.
    """
    logger.info("Agent [ops_notifier]: Commencing alert note generation...")
    category = state.get("category", "General")
    raw_feedback = state.get("raw_feedback", "")

    system_prompt = (
        "You are an operations consultant. Based on customer feedback, write a single actionable "
        "internal note for the restaurant manager. Max 2 sentences. Be specific and direct."
    )
    user_prompt = f"Category: {category}. Feedback: {raw_feedback}"

    try:
        logger.info("Agent [ops_notifier]: Trimming alert insights via LLM...")
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
            temperature=0
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        note = response.content.strip()
        logger.info("Agent [ops_notifier]: Alert note generated.")
        
        return {
            "internal_ops_note": note
        }
    except Exception as exc:
        logger.error(f"Agent Error [ops_notifier]: {exc}")
        return {
            "internal_ops_note": f"Alert regarding {category}. Please review recent customer feedback.",
            "error": str(exc)
        }
