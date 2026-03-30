"""
ReviewGuard — Sheets Tool.
Provides Google Sheets API integration for reading and writing review data.

Expected sheet layout ("Feedback Queue"):
  A: Name | B: Email | C: Visit Date | D: Visit Time | E: Status | F: Sentiment | G: Category
"""

from __future__ import annotations

from typing import List

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import base64
import json
import os
import tempfile

from config import settings
from logger import logger
from state import FeedbackRow, FormResponseRow

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SHEET_NAME = "Feedback Queue"
READ_RANGE = f"{SHEET_NAME}!A2:G"

FORM_SHEET_NAME = "Feedback Responses"
FORM_READ_RANGE = f"{FORM_SHEET_NAME}!A2:E"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_sheets_service():
    """Build and return an authorised Google Sheets API service."""
    spreadsheet_id = settings.google_sheets_id

    if not spreadsheet_id:
        logger.error("GOOGLE_SHEETS_ID is not set in environment.")
        raise RuntimeError("GOOGLE_SHEETS_ID is not set. Please add it to your .env file.")

    try:
        # Option 1: Raw JSON string from env var (most reliable for Railway)
        json_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
        # Option 2: Base64-encoded credential from env var
        b64_creds = os.environ.get("GOOGLE_CREDENTIALS_B64", "")

        if json_creds:
            logger.info("Loading credentials from GOOGLE_CREDENTIALS_JSON env var.")
            creds_json = json.loads(json_creds)
            credentials = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        elif b64_creds:
            logger.info("Loading credentials from GOOGLE_CREDENTIALS_B64 env var.")
            creds_json = json.loads(base64.b64decode(b64_creds))
            credentials = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
        else:
            # Fallback to local file
            creds_path = settings.google_credentials_path
            logger.info(f"No env var credentials found. Falling back to file: {creds_path}")
            credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    except FileNotFoundError as exc:
        logger.error(f"Service account file missing")
        raise RuntimeError(f"Service-account credentials not found.") from exc
    except Exception as exc:
        logger.error(f"Failed to load service account credentials: {exc}")
        raise RuntimeError(f"Failed to load credentials: {exc}") from exc

    service = build("sheets", "v4", credentials=credentials)
    return service.spreadsheets()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_pending_feedback_rows() -> List[FeedbackRow]:
    """
    Read the *Feedback Queue* sheet and return rows whose Status column
    is empty (i.e. not yet processed).

    Returns
    -------
    list[FeedbackRow]
        One ``FeedbackRow`` per unprocessed row.
    """
    logger.info("Fetching pending feedback from Google Sheets...")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    try:
        result = sheets.values().get(spreadsheetId=spreadsheet_id, range=READ_RANGE).execute()
    except HttpError as exc:
        logger.error(f"HTTP Error reading Sheets: {exc}")
        raise RuntimeError(f"Could not read Google Sheet: {exc}") from exc

    rows = result.get("values", [])
    if not rows:
        logger.info("No rows found in sheet.")
        return []

    pending: List[FeedbackRow] = []
    for i, row in enumerate(rows):
        while len(row) < 5:
            row.append("")

        name, email, visit_date, visit_time, status = row[:5]

        if status.strip() == "":
            pending.append(
                FeedbackRow(
                    name=name.strip(),
                    email=email.strip(),
                    visit_date=visit_date.strip(),
                    visit_time=visit_time.strip(),
                    row_index=i + 1,  # 1-based data-row index
                )
            )

    logger.info(f"Found {len(pending)} pending feedback string(s).")
    return pending


def get_pending_form_responses() -> List[FormResponseRow]:
    """
    Read the *Feedback Responses* sheet and return rows whose Status column
    is empty or "Pending" (i.e. not yet processed).

    Returns
    -------
    list[FormResponseRow]
        One ``FormResponseRow`` per unprocessed row.
    """
    logger.info("Fetching pending form responses from Google Sheets...")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    try:
        result = sheets.values().get(spreadsheetId=spreadsheet_id, range=FORM_READ_RANGE).execute()
    except HttpError as exc:
        logger.error(f"HTTP Error reading Form Responses Sheets: {exc}")
        return []

    rows = result.get("values", [])
    if not rows:
        return []

    pending: List[FormResponseRow] = []
    for i, row in enumerate(rows):
        while len(row) < 5:
            row.append("")

        timestamp, name, email, feedback, status = row[:5]

        if status.strip() == "" or status.strip().lower() == "pending":
            pending.append(
                FormResponseRow(
                    timestamp=timestamp.strip(),
                    name=name.strip(),
                    email=email.strip(),
                    feedback=feedback.strip(),
                    row_index=i + 1,  # 1-based data-row index
                )
            )

    logger.info(f"Found {len(pending)} pending form response(s).")
    return pending


def get_processed_feedback_rows() -> List[dict]:
    """
    Reads the *Feedback Queue* sheet and returns all rows formatted as dicts
    where the Status column equals "Processed".
    
    Returns
    -------
    list[dict]
        A list of processed feedback dictionaries containing sentiment and category.
    """
    logger.info("Fetching all processed feedback for weekly summary...")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    try:
        result = sheets.values().get(spreadsheetId=spreadsheet_id, range=READ_RANGE).execute()
    except Exception as exc:
        logger.error(f"Error fetching processed rows: {exc}")
        return []

    rows = result.get("values", [])
    processed = []

    for row in rows:
        while len(row) < 7:
            row.append("")
        
        name, email, visit_date, visit_time, status, sentiment, category = row[:7]

        if status.strip().lower() == "processed":
            processed.append({
                "name": name,
                "sentiment": sentiment.strip(),
                "category": category.strip()
            })

    logger.info(f"Fetched {len(processed)} historical processed rows.")
    return processed


def mark_row_sent(row_index: int) -> None:
    """
    Set the Status column to ``"Sent"`` — indicating the review request
    email has been dispatched to this customer.

    Parameters
    ----------
    row_index : int
        **1-based** data-row index.
    """
    logger.info(f"Marking row {row_index} as Sent.")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    sheet_row = row_index + 1
    cell_range = f"{SHEET_NAME}!E{sheet_row}"

    try:
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [["Sent"]]},
        ).execute()
        logger.info(f"Successfully marked row {row_index} as Sent.")
    except Exception as exc:
        logger.error(f"Failed to mark row {row_index} as sent: {exc}")
        raise RuntimeError(f"Unexpected error updating row {row_index}: {exc}") from exc


def mark_row_processed(row_index: int, sentiment: str = "", category: str = "") -> None:
    """
    Set the Status column to ``"Processed"`` and record the sentiment and category.

    Parameters
    ----------
    row_index : int
        **1-based** data-row index.
    sentiment : str
        The extracted sentiment from analysis, e.g. "positive".
    category : str
        The extracted category, e.g. "Food Quality".
    """
    logger.info(f"Marking row {row_index} as Processed (Sentiment: {sentiment}, Category: {category}).")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    sheet_row = row_index + 1
    # We update E, F, G (Status, Sentiment, Category)
    cell_range = f"{SHEET_NAME}!E{sheet_row}:G{sheet_row}"

    try:
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [["Processed", sentiment, category]]},
        ).execute()
        logger.info(f"Successfully updated row {row_index} in Sheets.")
    except Exception as exc:
        logger.error(f"Failed to mark row {row_index} as processed: {exc}")
        raise RuntimeError(f"Unexpected error updating row {row_index}: {exc}") from exc


def mark_form_row_processed(row_index: int) -> None:
    """
    Set the Status column to ``"Processed"`` in the Feedback Responses tab.

    Parameters
    ----------
    row_index : int
        **1-based** data-row index.
    """
    logger.info(f"Marking form response row {row_index} as Processed.")
    sheets = _get_sheets_service()
    spreadsheet_id = settings.google_sheets_id

    sheet_row = row_index + 1
    # We update E (Status)
    cell_range = f"{FORM_SHEET_NAME}!E{sheet_row}"

    try:
        sheets.values().update(
            spreadsheetId=spreadsheet_id,
            range=cell_range,
            valueInputOption="RAW",
            body={"values": [["Processed"]]},
        ).execute()
        logger.info(f"Successfully updated form response row {row_index} in Sheets.")
    except Exception as exc:
        logger.error(f"Failed to mark form row {row_index} as processed: {exc}")
        raise RuntimeError(f"Unexpected error updating form row {row_index}: {exc}") from exc
