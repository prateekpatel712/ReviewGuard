"""
ReviewGuard — Weekly Summariser Agent.
Uses OpenAI to ingest processed stats and generate a 3-bullet executive summary.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from config import settings
from logger import logger

def generate_weekly_summary(stats: dict) -> str:
    """
    Generates a high-level weekly summary using OpenAI based on feedback statistics.
    
    Parameters
    ----------
    stats : dict
        A dictionary containing keys: 'total', 'positive', 'negative', 'top_category'.

    Returns
    -------
    str
        A formatted 3-bullet HTML string summarizing the week's sentiment.
    """
    logger.info("Agent [weekly_summariser] started generating summary...")
    
    system_prompt = (
        f"You are the executive AI assistant for {settings.restaurant_name}. "
        "The owner needs a clear, encouraging but realistic 3-bullet point weekly summary of customer feedback. "
        "Write exactly 3 distinct bullet points in plain HTML (<ul><li>...</li></ul>). Keep it strictly under 100 words total."
    )
    
    user_prompt = (
        f"Here are the stats for this week:\n"
        f"Total processed: {stats.get('total')}\n"
        f"Positive reviews: {stats.get('positive')}\n"
        f"Negative reviews: {stats.get('negative')}\n"
        f"Most mentioned issue category: {stats.get('top_category')}"
    )

    try:
        logger.info("Calling ChatOpenAI (gpt-4o-mini) for weekly summary...")
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            api_key=settings.groq_api_key,
            temperature=0
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        summary = response.content.strip()
        logger.info("Agent [weekly_summariser] finished mapping summary.")
        return summary
    except Exception as exc:
        logger.error(f"Agent Error [weekly_summariser]: {exc}")
        return "<ul><li>System error generating automated summary. Please review sheets manually.</li></ul>"
