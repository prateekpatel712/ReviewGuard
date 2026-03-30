# ReviewGuard

A multi-agent review management system built with LangGraph and OpenAI.

## Project Structure

```
review-guard/
├── main.py                 # Entry point (Polling & Weekly Summaries)
├── config.py               # Configuration & Pydantic environment settings
├── logger.py               # Centralised logging initialisation
├── state.py                # LangGraph state schema
├── agents/
│   ├── feedback_analyser.py  # Sentiment analysis agent
│   ├── email_drafter.py      # Email response drafting agent
│   ├── ops_notifier.py       # Operational alerts agent
│   └── weekly_summariser.py  # Management report generating agent
├── nodes/
│   ├── collect.py            # Review collection node
│   ├── route.py              # Sentiment-based routing node
│   ├── boost.py              # Positive review engagement node
│   └── guard.py              # Negative review escalation node
├── tools/
│   ├── gmail_tool.py         # Gmail API integration
│   └── sheets_tool.py        # Google Sheets API integration
├── mcp_config.json           # Model Context Protocol servers
├── .env.example              # Environment variable template
└── requirements.txt          # Python dependencies
```

## Setup & Integrations

### 1. Google Sheets Setup
To capture reviews effectively, create a Google Sheet containing a tab exactly named **"Feedback Queue"**. The system relies on the following exact column setup starting from `A1`:
- **A**: `Name`
- **B**: `Email`
- **C**: `Visit Date`
- **D**: `Visit Time`
- **E**: `Status`
- **F**: `Sentiment` (Optional, ReviewGuard populates this)
- **G**: `Category` (Optional, ReviewGuard populates this)

Ensure the `Status` column for unprocessed feedback is completely empty.

### 2. Google API Credentials (Service Account)
To grant ReviewGuard access to Google Sheets without UI popups:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and enable the **Google Sheets API**.
3. Under **Credentials**, click **Create Credentials** > **Service Account**.
4. Create the account and download the JSON key.
5. Rename the file to `service_account.json` and save it closely securely.
6. Open your Google Sheet, click **Share**, and share the sheet specifically with the "client_email" found inside the JSON file, granting it `Editor` permissions.
7. Update your `.env` to map `GOOGLE_CREDENTIALS_PATH=service_account.json` and grab the `GOOGLE_SHEETS_ID` from your sheet's URL parameter.

### 3. Local Installation
Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

## Running ReviewGuard

ReviewGuard serves two primary functionalities: **Active Polling** and **Weekly Management Summaries**.
It automatically produces logs in the `./logs/review_guard.log` file.

**A. Process Pending Reviews**  
Standard execution runs the LangGraph engine. It fetches rows with a blank `Status`, handles sentiment routing, drafts apology emails, shoots notifications, and writes 'Processed' back to the sheet.
```bash
python main.py
```

**B. Generate & Email Weekly Summaries**  
Passing the `--weekly` flag triggers the weekly summary sweep. The system skips new rows, reads the historical "Processed" rows instead, calculates distribution metrics (Total, Positive vs Negative, Tops Categories), commands OpenAI to write a 3-bullet executive brief, and emails the snapshot to the owner.
```bash
python main.py --weekly
```

## Scheduling with Cron (Linux/macOS)
You can automate ReviewGuard to continuously poll for new reviews, and send a summary brief. Open your cron editor (`crontab -e`):

```bash
# Process new feedback every 30 minutes
*/30 * * * * cd /path/to/review-guard && /path/to/review-guard/venv/bin/python main.py >> /path/to/review-guard/logs/cron.log 2>&1

# Fire the Weekly Summary Report every Friday at 6:00 PM (18:00)
0 18 * * 5 cd /path/to/review-guard && /path/to/review-guard/venv/bin/python main.py --weekly >> /path/to/review-guard/logs/cron.log 2>&1
```

## Dependencies
- **LangGraph** — Multi-agent orchestration
- **LangChain + OpenAI** — LLM-powered agents
- **Google APIs** — Gmail and Sheets integration
- **Pydantic Settings** — Environment constraint checks
- **Model Context Protocol (MCP)** — Tool orchestration hooks
