# AI--Email---Agent
AI -Email - Agent 
  
# ai_email_agent  
 
`ai_email_agent` is a beginner-friendly Flask project that checks unread Gmail messages, sends email content to Gemini to generate a reply, saves the reply as a Gmail draft, stores logs in SQLite, and shows those logs in a small dashboard.

The project is designed to be built step by step. It does not auto-send emails. It creates drafts so you can review them safely in Gmail.

## 1. What This Project Does    
 
This app automates part of your email workflow:
 
1. reads unread emails from your Gmail inbox 
2. extracts sender, subject, and email body 
3. asks Gemini to write a professional reply
4. creates a Gmail draft reply in the same thread 
5. saves the result in a local SQLite database 
6. shows the logs in a Flask web page   

## 2. Folder Structure

Current project structure:

```text
ai_email_agent/
├── .env.example
├── app.py
├── db.py
├── gemini_service.py
├── gmail_service.py
├── scheduler.py
├── requirements.txt
├── README.md
└── templates/
    └── logs.html
```

What each file does:

- `app.py`: Flask app, dashboard routes, and background scheduler startup
- `db.py`: SQLite database setup and log helper functions
- `gemini_service.py`: Gemini API client and reply generation
- `gmail_service.py`: Gmail OAuth, inbox reading, and draft creation
- `scheduler.py`: main automation logic that connects Gmail, Gemini, and SQLite
- `requirements.txt`: Python dependencies
- `.env.example`: sample environment settings
- `templates/logs.html`: dashboard page for viewing logs

## 3. Installation Steps

Make sure Python 3.11 or newer is installed.

Then:

1. open a terminal in the project folder
2. create a virtual environment
3. activate it
4. install the requirements
5. create a `.env` file from `.env.example`
6. add your Gmail and Gemini settings
7. run the Flask app

## 4. Create And Activate A Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate again:

```powershell
.venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

## 5. Install Requirements

With the virtual environment activated:

```powershell
pip install -r requirements.txt
```

## 6. Create The `.env` File From `.env.example`

Copy the example file:

```powershell
Copy-Item .env.example .env
```

Then open `.env` and update the values you need.

Important variables:

- `SECRET_KEY`: Flask secret key
- `DATABASE_FILE`: SQLite file path, default is `email_agent.db`
- `CHECK_INTERVAL_MINUTES`: how often the inbox checker runs
- `GOOGLE_CLIENT_SECRETS_FILE`: path to your Google OAuth client file
- `GOOGLE_TOKEN_FILE`: path where the Gmail login token will be saved
- `GEMINI_API_KEY`: your Gemini API key
- `GEMINI_MODEL`: model name used to generate replies

## 7. Enable Gmail API In Google Cloud

To use Gmail securely, you must create Google OAuth credentials.

Steps:

1. go to Google Cloud Console
2. create a new project or select an existing one
3. search for `Gmail API`
4. open the Gmail API page
5. click `Enable`
6. go to `APIs & Services` > `OAuth consent screen`
7. configure the consent screen
8. add yourself as a test user if Google asks for it
9. go to `APIs & Services` > `Credentials`
10. click `Create Credentials`
11. choose `OAuth client ID`
12. select `Desktop app`
13. create the credential

## 8. Download `credentials.json`

After creating the OAuth client:

1. download the JSON file from Google Cloud
2. rename it to `credentials.json` if needed
3. place it in the project root

By default, this project expects:

```text
ai_email_agent/credentials.json
```

If you store it somewhere else, update this in `.env`:

```env
GOOGLE_CLIENT_SECRETS_FILE=path/to/credentials.json
```

## 9. How First-Time Gmail OAuth Works

The first time the app tries to access Gmail:

1. `gmail_service.py` looks for `token.json`
2. if `token.json` does not exist, it starts the OAuth login flow
3. a browser window opens
4. you log in to your Google account
5. Google asks you to approve Gmail access
6. after approval, the app receives a token
7. the app saves that token into `token.json`

On later runs:

- the app reuses `token.json`
- if the access token expires, Google can refresh it automatically

You normally do not need to log in every time.

## 10. How To Get A Gemini API Key

1. go to Google AI Studio
2. create an API key
3. copy the key into your `.env` file

Example:

```env
GEMINI_API_KEY=your-real-api-key
GEMINI_MODEL=gemini-2.0-flash-lite
```

## 11. How To Run The Flask App

Before running:

- make sure `.env` exists
- make sure `credentials.json` exists
- make sure your virtual environment is activated

Run:

```powershell
python app.py
```

Then open:

```text
http://127.0.0.1:5000/
```

What happens on startup:

- Flask starts
- SQLite table is created if needed
- APScheduler starts in the background
- the scheduler calls `process_inbox()` every few minutes

## 12. How To Test The `/run-now` Route

Once the Flask app is running, open:

```text
http://127.0.0.1:5000/run-now
```

That route:

1. immediately runs the inbox processor
2. checks unread inbox emails
3. generates reply drafts
4. stores logs in SQLite
5. redirects back to the dashboard

You can also test it from PowerShell:

```powershell
Invoke-WebRequest http://127.0.0.1:5000/run-now
```

After that, refresh the dashboard at `/` and inspect the new log rows.

## 13. Where SQLite Logs Are Stored

By default, logs are stored in:

```text
email_agent.db
```

This file is created in the project root unless you change `DATABASE_FILE` in `.env`.

The table name is:

```text
processed_email_logs
```

It stores fields like:

- Gmail message ID
- thread ID
- sender
- subject
- original email body
- AI reply
- draft ID
- status
- created timestamp

## 14. Common Errors And Fixes

### `python` command does not work

Fix:

- make sure Python is installed
- check with `python --version`
- if needed, install Python and reopen the terminal

### Virtual environment activation is blocked

Fix in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### `Missing GEMINI_API_KEY environment variable`

Cause:

- `.env` is missing or the Gemini key is empty

Fix:

- add a valid `GEMINI_API_KEY` to `.env`

### `Missing OAuth credentials file`

Cause:

- `credentials.json` is missing
- the path in `.env` is wrong

Fix:

- download the OAuth client JSON from Google Cloud
- place it in the correct path
- update `GOOGLE_CLIENT_SECRETS_FILE` if needed

### Browser login does not open on first Gmail run

Cause:

- local OAuth flow failed
- firewall or browser restrictions

Fix:

- try running the app again
- make sure your browser can open local auth pages
- confirm the Google OAuth client type is `Desktop app`

### Gmail API says access denied

Cause:

- Gmail API is not enabled
- OAuth consent screen is incomplete
- your Google account is not added as a test user

Fix:

- enable Gmail API in Google Cloud
- finish the consent screen setup
- add your Gmail address as a test user if required

### Drafts are not created in the expected thread

Cause:

- missing or incorrect email reply headers
- wrong message ID used for reply metadata

Fix:

- make sure the original message has a valid `Message-ID` header
- make sure the app is using `threadId`, `In-Reply-To`, and `References`

### No email body is extracted

Cause:

- email is HTML-only
- unusual multipart structure
- body content is empty in the payload

Fix:

- the app already tries plain text, then HTML, then snippet
- if a specific email still fails, inspect that Gmail message payload

### Database shows duplicate message errors

Cause:

- the same Gmail message was processed again

Fix:

- this usually means duplicate protection worked
- check `already_processed()` logic and existing log rows

## Practical Notes

- Start with drafts only. Do not auto-send emails while testing.
- Use a test Gmail account first.
- Keep `credentials.json`, `token.json`, and `.env` out of version control.
- Review draft replies in Gmail before trusting the automation.

## Current Run Command

For the current version of this project, use:

```powershell
python app.py
```
