"""
ReviewGuard — Gmail Tool.
Provides Gmail API integration for sending emails:
  • Review-request emails  (positive flow)
  • Recovery emails        (negative flow)
  • Ops-notification emails (internal alerts)
  • Weekly summary emails  (reporting flow)
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import settings
from logger import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
TOKEN_PATH = Path(__file__).resolve().parent.parent / "token.json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_gmail_service():
    """
    Build and return an authorised Gmail API service.
    Supports both local file-based credentials and base64-encoded env vars
    for cloud deployment (Railway, Render, etc.).
    """
    creds: Credentials | None = None

    # Try loading token from env var first (cloud), then file (local)
    # Option 1: Raw JSON string (most reliable for Railway)
    token_json = os.environ.get("GMAIL_TOKEN_JSON", "")
    # Option 2: Base64-encoded token
    token_b64 = os.environ.get("GMAIL_TOKEN_B64", "")

    if token_json:
        logger.info("Loading Gmail token from GMAIL_TOKEN_JSON env var.")
        token_data = json.loads(token_json)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif token_b64:
        logger.info("Loading Gmail token from GMAIL_TOKEN_B64 env var.")
        token_data = json.loads(base64.b64decode(token_b64))
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save refreshed token back to file if running locally
                if not token_b64 and not token_json:
                    TOKEN_PATH.write_text(creds.to_json())
            except Exception as exc:
                logger.error(f"Failed to refresh Gmail token: {exc}")
                raise RuntimeError(f"Failed to refresh Gmail OAuth token: {exc}") from exc
        else:
            # Local-only: trigger OAuth browser flow
            creds_path = settings.gmail_credentials_path
            if not Path(creds_path).exists():
                logger.error(f"Missing Gmail credentials at {creds_path}")
                raise RuntimeError(f"Gmail OAuth credentials file not found at: {creds_path}.")
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            TOKEN_PATH.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _build_html_email(
    to_email: str,
    subject: str,
    html_body: str,
    from_name: str | None = None,
) -> dict:
    """
    Construct a base64url-encoded MIME message ready for the Gmail API.

    Parameters
    ----------
    to_email : str
        Recipient address.
    subject : str
        Email subject line.
    html_body : str
        Full HTML body content.
    from_name : str | None
        Display name for the sender (optional).

    Returns
    -------
    dict
        ``{"raw": "<base64url string>"}`` payload for Gmail's Send endpoint.
    """
    message = MIMEMultipart("alternative")
    message["To"] = to_email
    message["Subject"] = subject
    if from_name:
        message["From"] = from_name

    message.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    return {"raw": raw}


def _send(to_email: str, subject: str, html_body: str) -> bool:
    """
    Low-level send helper. Returns ``True`` on success, ``False`` on failure.
    """
    from_name = (
        f"{settings.owner_name} @ {settings.restaurant_name}"
        if settings.owner_name and settings.restaurant_name
        else None
    )

    if settings.dry_run:
        logger.info(f"[DRY RUN] Simulating email to {to_email} | Subject: {subject}")
        return True

    try:
        service = _get_gmail_service()
        payload = _build_html_email(to_email, subject, html_body, from_name)
        service.users().messages().send(userId="me", body=payload).execute()
        logger.info(f"Email sent successfully to {to_email}")
        return True
    except HttpError as exc:
        logger.error(f"HTTP error sending email to {to_email}: {exc.resp.status} — {exc.reason}")
        return False
    except Exception as exc:
        logger.error(f"Unexpected error sending email to {to_email}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_review_request(
    to_email: str,
    customer_name: str,
    google_review_link: str,
) -> bool:
    """
    Send a warm, short email asking the customer for a Google review.

    Parameters
    ----------
    to_email : str
        Customer email address.
    customer_name : str
        Customer's first/full name.
    google_review_link : str
        Direct link to the Google review page.

    Returns
    -------
    bool
        ``True`` if the email was sent successfully.
    """
    logger.info(f"Preparing review request email for {to_email}...")
    restaurant = settings.restaurant_name or "our restaurant"
    owner = settings.owner_name or "The Team"
    
    encoded_name = urllib.parse.quote(customer_name)
    encoded_email = urllib.parse.quote(to_email)
    private_feedback_link = f"{settings.form_url}?name={encoded_name}&email={encoded_email}"

    subject = f"How was your visit, {customer_name}? 🌟"

    html_body = f"""\
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto; padding: 24px; color: #333;">
        <p>Hi {customer_name},</p>
        <p>Thank you so much for dining with us at <strong>{restaurant}</strong>! We hope you had a wonderful experience.</p>
        <p>If you have a moment, we'd love to hear your thoughts — it helps other food-lovers discover us too.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{google_review_link}" style="background-color: #4CAF50; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; margin-bottom: 16px; width: 80%; max-width: 300px;">
                ⭐ Leave a Review
            </a>
            <br>
            <a href="{private_feedback_link}" style="background-color: #f1f3f4; color: #5f6368; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: 500; display: inline-block; width: 80%; max-width: 300px; font-size: 14px;">
                Share Private Feedback
            </a>
        </div>
        <p>Warm regards,<br><strong>{owner}</strong><br><em>{restaurant}</em></p>
    </div>
    """
    return _send(to_email, subject, html_body)


def send_recovery_email(to_email: str, draft_body: str) -> bool:
    """
    Send the AI-drafted recovery email to a dissatisfied customer.

    Parameters
    ----------
    to_email : str
        Customer email address.
    draft_body : str
        Complete email body already written by the AI agent.

    Returns
    -------
    bool
        ``True`` if the email was sent successfully.
    """
    logger.info(f"Preparing recovery email for {to_email}...")
    restaurant = settings.restaurant_name or "our restaurant"
    owner = settings.owner_name or "The Team"

    subject = f"We'd love to make it right, from {restaurant} 💛"

    html_body = f"""\
    <div style="font-family: Arial, sans-serif; max-width: 520px; margin: auto; padding: 24px; color: #333; line-height: 1.6;">
        {draft_body}
        <br><br>
        <p>Sincerely,<br><strong>{owner}</strong><br><em>{restaurant}</em></p>
    </div>
    """
    return _send(to_email, subject, html_body)


def send_ops_notification(
    owner_email: str,
    ops_note: str,
    category: str,
    customer_name: str,
) -> bool:
    """
    Send an internal alert email to the restaurant owner.

    Parameters
    ----------
    owner_email : str
        Owner / ops-team email address.
    ops_note : str
        Detailed operational note generated by the AI agent.
    category : str
        Feedback category (e.g. "Food Quality", "Service Speed").
    customer_name : str
        Name of the customer who left the feedback.

    Returns
    -------
    bool
        ``True`` if the email was sent successfully.
    """
    logger.info(f"Preparing ops notification for owner ({owner_email})...")
    subject = f"⚠️ Feedback Alert: {category} issue — {customer_name}"

    html_body = f"""\
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; color: #333; line-height: 1.6;">
        <h2 style="color: #d32f2f;">⚠️ Negative Feedback Alert</h2>
        <p><strong>Customer:</strong> {customer_name}<br><strong>Category:</strong> {category}</p>
        <h3>Operational Note</h3>
        <div style="background: #fff8e1; border-left: 4px solid #ffc107; padding: 12px 16px; margin-bottom: 16px;">
            {ops_note}
        </div>
        <p style="font-size: 0.9em; color: #777;">A recovery email has been automatically drafted and sent.</p>
    </div>
    """
    return _send(owner_email, subject, html_body)


def send_weekly_summary_email(
    to_email: str,
    stats: dict,
    summary_html: str
) -> bool:
    """
    Sends the generated weekly summary report to the owner.

    Parameters
    ----------
    to_email : str
        The address to receive the summary (usually the owner).
    stats : dict
        Metrics mapping for display.
    summary_html : str
        The LLM-generated HTML list block mapping insights.

    Returns
    -------
    bool
        ``True`` if the email was sent successfully.
    """
    logger.info(f"Preparing weekly summary report for {to_email}...")
    subject = f"📊 Weekly ReviewGuard Insight Summary"

    html_body = f"""\
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; color: #333; line-height: 1.6;">
        <h2 style="color: #4A90E2;">Weekly Performance Insights</h2>
        <div style="display: flex; gap: 20px; margin-bottom: 20px;">
            <div style="background: #f4f4f4; padding: 10px 20px; border-radius: 5px;">
                <strong>Processed:</strong> {stats.get('total', 0)}
            </div>
            <div style="background: #e8f5e9; padding: 10px 20px; border-radius: 5px;">
                <strong>Positive:</strong> {stats.get('positive', 0)}
            </div>
            <div style="background: #ffebee; padding: 10px 20px; border-radius: 5px;">
                <strong>Negative:</strong> {stats.get('negative', 0)}
            </div>
        </div>
        
        <h3>AI Executive Summary</h3>
        <div style="background: #fff; border: 1px solid #eee; padding: 20px; border-radius: 8px;">
            {summary_html}
        </div>
        
        <p style="font-size: 0.9em; color: #777; margin-top: 30px;">
            Generated automatically by <strong>ReviewGuard</strong> using OpenAI.
        </p>
    </div>
    """
    return _send(to_email, subject, html_body)
