"""
ReviewGuard — Feedback Analyser Agent.
Analyses raw customer feedback for sentiment and category using LangGraph tools.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from config import settings
from logger import logger
from state import ReviewGuardState
from tools.mcp_client import get_gmail_tools, get_sheets_tools

def analyse_feedback(state: ReviewGuardState) -> dict:
    """
    Analyses the given customer feedback and extracts sentiment and category.

    Parameters
    ----------
    state : ReviewGuardState
        The active pipeline state containing the user's raw feedback.

    Returns
    -------
    dict
        State updates for the extracted 'sentiment' and 'category'.
        Returns default values if the LLM invocation fails.
    """
    logger.info("Agent [feedback_analyser]: Commencing sentiment extraction...")
    restaurant_name = settings.restaurant_name or "the restaurant"
    raw_feedback = state.get("raw_feedback", "")

    system_prompt = (
        f"You are a customer experience analyst for {restaurant_name}. Analyse the customer "
        "feedback and return ONLY this exact format with no extra text:\n"
        "SENTIMENT: positive|negative|neutral\n"
        "CATEGORY: Food Quality|Service Speed|Staff Attitude|Value for Money|Ambience|Other"
    )
    user_prompt = f"Customer feedback: {raw_feedback}"

    try:
        # Load MCP Tools dynamically
        mcp_tools = get_gmail_tools() + get_sheets_tools()

        logger.info("Agent [feedback_analyser]: Setting up LLM capabilities...")
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
            temperature=0
        )
        
        # Build tool-calling agent
        agent = create_react_agent(llm, tools=mcp_tools)
        
        # Invoke agent
        response = agent.invoke({
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
        })
        
        # The AI's final response is the content of the last message
        content = response["messages"][-1].content.strip()
        
        # Parse the output
        sentiment = "neutral"
        category = "Other"
        
        for line in content.split('\n'):
            line = line.strip()
            if line.upper().startswith("SENTIMENT:"):
                raw_sentiment = line.split(":", 1)[1].strip().lower()
                if "|" in raw_sentiment or raw_sentiment not in ["positive", "negative", "neutral"]:
                    sentiment = "neutral"
                else:
                    sentiment = raw_sentiment
            elif line.upper().startswith("CATEGORY:"):
                category = line.split(":", 1)[1].strip()
                
        logger.info(f"Agent [feedback_analyser]: Output parsed -> {sentiment.upper()} | {category}")
        return {
            "sentiment": sentiment,
            "category": category
        }
    except Exception as exc:
        logger.error(f"Agent Error [feedback_analyser]: HTTP/LLM execution failed: {exc}")
        return {
            "sentiment": "neutral",
            "category": "Other",
            "error": str(exc)
        }
