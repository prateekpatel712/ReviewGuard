"""
ReviewGuard — State module.
Defines the graph state schema used across LangGraph nodes.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic model — represents one row read from Google Sheets
# ---------------------------------------------------------------------------

class FeedbackRow(BaseModel):
    """A single customer-feedback row ingested from Google Sheets."""

    name: str = Field(..., description="Customer's full name")
    email: str = Field(..., description="Customer's email address")
    visit_date: str = Field(..., description="Date of the visit (YYYY-MM-DD)")
    visit_time: str = Field(..., description="Time of the visit (HH:MM)")
    row_index: int = Field(-1, description="1-based data row index in Google Sheets")

class FormResponseRow(BaseModel):
    """A single private feedback submission from the web form."""

    timestamp: str = Field(..., description="ISO form submission timestamp")
    name: str = Field(..., description="Customer's full name")
    email: str = Field(..., description="Customer's email address")
    feedback: str = Field(..., description="The raw private feedback text")
    row_index: int = Field(-1, description="1-based data row index in Google Sheets (Feedback Responses tab)")


# ---------------------------------------------------------------------------
# LangGraph state — flows through every node in the pipeline
# ---------------------------------------------------------------------------

class ReviewGuardState(TypedDict):
    """Central state object that every LangGraph node reads / writes."""

    # ── Customer info ──────────────────────────────────────────────────
    customer_name: str
    customer_email: str
    visit_date: Optional[str]

    # ── Feedback & analysis ────────────────────────────────────────────
    raw_feedback: str
    sentiment: Optional[Literal["positive", "negative", "neutral"]]
    category: str  # e.g. "Food Quality", "Service Speed", "Staff Attitude",
                   #      "Value for Money", "Ambience", "Other"

    # ── Agent outputs ──────────────────────────────────────────────────
    recovery_email_draft: str
    internal_ops_note: str

    # ── Status flags ───────────────────────────────────────────────────
    review_boost_sent: bool
    recovery_email_sent: bool
    ops_notified: bool

    # ── Pipeline meta ──────────────────────────────────────────────────
    error: Optional[str]
    stage: str  # tracks the current pipeline stage
