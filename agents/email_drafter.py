"""
ReviewGuard — Email Drafter Agent.
Drafts personal recovery emails for dissatisfied customers.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from config import settings
from logger import logger
from state import ReviewGuardState

def draft_recovery_email(state: ReviewGuardState) -> dict:
    """
    Drafts a recovery email tailored to the customer's negative feedback.

    Parameters
    ----------
    state : ReviewGuardState
        The active pipeline state.

    Returns
    -------
    dict
        State updates containing the 'recovery_email_draft' string mapping.
    """
    logger.info("Agent [email_drafter]: Commencing apology draft generation...")
    owner_name = settings.owner_name or "The Owner"
    restaurant_name = settings.restaurant_name or "our restaurant"
    
    customer_name = state.get("customer_name", "Valued Customer")
    category = state.get("category", "General")
    raw_feedback = state.get("raw_feedback", "")

    system_prompt = (
        f"You are {owner_name}, owner of {restaurant_name}. Write a warm, genuine personal "
        "recovery email to a customer who had a disappointing experience. Be specific to their issue ONLY if they provided details. "
        "Sound human, not corporate. Max 150 words. "
        "CRITICAL RULE: DO NOT invent, hallucinate, or assume ANY complaints or details not explicitly stated by the customer. "
        "If the customer feedback is vague (e.g., 'bad', 'okay', 'no comment'), simply apologize that their experience fell short of expectations and invite them to share more details."
    )
    user_prompt = (
        f"Customer name: {customer_name}. Issue category: {category}. "
        f"Their feedback: {raw_feedback}. Write the recovery email body only, no subject line."
    )

    try:
        logger.info("Agent [email_drafter]: Invoking GPT mapping...")
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
            temperature=0
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        draft = response.content.strip()
        logger.info("Agent [email_drafter]: Draft successfully written.")
        
        return {
            "recovery_email_draft": draft
        }
    except Exception as exc:
        logger.error(f"Agent Error [email_drafter]: {exc}")
        return {
            "recovery_email_draft": "We sincerely apologize for your experience and would love to make it right. Please reply to this email so we can discuss further.",
            "error": str(exc)
        }
