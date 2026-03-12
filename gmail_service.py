import base64
import os
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


load_dotenv()


# Gmail scopes:
# - gmail.readonly lets the app read email messages and metadata
# - gmail.compose lets the app create and manage drafts
DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_FILE = Path(
    os.getenv("GOOGLE_CLIENT_SECRETS_FILE", str(BASE_DIR / "credentials.json"))
)
TOKEN_FILE = Path(os.getenv("GOOGLE_TOKEN_FILE", str(BASE_DIR / "token.json")))
SCOPES = [
    scope.strip()
    for scope in os.getenv("GMAIL_SCOPES", ",".join(DEFAULT_SCOPES)).split(",")
    if scope.strip()
]


def get_gmail_service():
    """
    Authenticate with Gmail using OAuth and return a Gmail API service object.

    On the first run, this opens a browser window so the user can sign in to
    Google and approve access. After that, the saved token is reused.
    """
    creds = None

    # Load an existing saved token if we already authenticated before.
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    # If there are no valid credentials, either refresh them or start a new
    # OAuth login flow in the browser.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"Missing OAuth credentials file: {CREDENTIALS_FILE}"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Save the token so the user does not need to log in every time.
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def list_unread_inbox_messages(service, max_results: int = 10) -> List[Dict]:
    """
    Return a list of unread inbox messages that are likely real incoming emails.

    The query excludes emails from yourself plus social and promotions
    categories to reduce noise for the agent.
    """
    query = os.getenv(
        "GMAIL_QUERY",
        "is:unread in:inbox -from:me -category:promotions -category:social",
    )

    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max(1, int(max_results)))
        .execute()
    )

    return response.get("messages", [])


def get_message(service, message_id: str) -> Dict:
    """
    Fetch and return a full Gmail message by its ID.

    Using format='full' includes headers, payload, MIME parts, and snippet.
    """
    return (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def parse_headers(message: Dict) -> Dict[str, str]:
    """
    Extract common email headers into a simpler dictionary.
    """
    header_map: Dict[str, str] = {}
    headers = message.get("payload", {}).get("headers", [])

    for header in headers:
        name = header.get("name", "")
        value = header.get("value", "")
        if name:
            header_map[name.lower()] = value

    return {
        "from": header_map.get("from", ""),
        "to": header_map.get("to", ""),
        "subject": header_map.get("subject", ""),
        "date": header_map.get("date", ""),
        "message_id": header_map.get("message-id", ""),
    }


def extract_plain_text_body(message: Dict) -> str:
    """
    Safely extract the plain text body from a Gmail message.

    Strategy:
    1. Prefer text/plain from multipart emails
    2. Fall back to the main payload body if it is plain text
    3. Fall back to Gmail's snippet if no body text is available
    """
    payload = message.get("payload", {})

    body_text = _extract_text_from_payload(payload, mime_type="text/plain")
    if body_text:
        return body_text.strip()

    # Some messages only include HTML. Strip tags very loosely as a fallback
    # before giving up and using the snippet.
    html_text = _extract_text_from_payload(payload, mime_type="text/html")
    if html_text:
        return _strip_html(html_text).strip()

    snippet = message.get("snippet", "")
    return snippet.strip()


def _extract_text_from_payload(payload: Dict, mime_type: str = "text/plain") -> str:
    """
    Walk through Gmail payload parts and return decoded text for the target
    MIME type. This handles nested multipart structures recursively.
    """
    current_mime_type = payload.get("mimeType", "")
    filename = payload.get("filename", "")

    # Skip attachments. They often have a MIME type but should not be treated
    # as the email body.
    if filename:
        return ""

    if current_mime_type == mime_type:
        data = payload.get("body", {}).get("data")
        return _decode_base64_url(data)

    for part in payload.get("parts", []):
        text = _extract_text_from_payload(part, mime_type=mime_type)
        if text:
            return text

    if not payload.get("parts") and current_mime_type == mime_type:
        data = payload.get("body", {}).get("data")
        return _decode_base64_url(data)

    return ""


def _decode_base64_url(data: Optional[str]) -> str:
    """
    Gmail encodes message bodies using URL-safe base64. Decode safely and
    return a UTF-8 string.
    """
    if not data:
        return ""

    try:
        padding = "=" * (-len(data) % 4)
        decoded_bytes = base64.urlsafe_b64decode((data + padding).encode("utf-8"))
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html(html: str) -> str:
    """
    Remove the most common HTML tags with a simple regex fallback.

    This is not a full HTML parser, but it is enough for a readable fallback
    when Gmail only provides a text/html part.
    """
    import re

    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return text


def create_reply_draft(
    service,
    to_email: str,
    subject: str,
    reply_text: str,
    thread_id: str,
    message_id: str,
    references: str = "",
) -> Dict:
    """
    Create a Gmail draft reply in the same thread as the original message.

    Gmail uses both the threadId and standard email reply headers so the
    draft is grouped correctly in the conversation view.
    """
    mime_message = MIMEText(reply_text, "plain", "utf-8")
    mime_message["To"] = to_email
    mime_message["Subject"] = _normalize_reply_subject(subject)
    mime_message["In-Reply-To"] = message_id

    if references:
        mime_message["References"] = references
    else:
        mime_message["References"] = message_id

    raw_message = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw_message,
            "threadId": thread_id,
        }
    }

    return service.users().drafts().create(userId="me", body=draft_body).execute()


def _normalize_reply_subject(subject: str) -> str:
    """
    Ensure the subject looks like a reply subject.
    """
    cleaned_subject = (subject or "").strip()
    if cleaned_subject.lower().startswith("re:"):
        return cleaned_subject
    return f"Re: {cleaned_subject}" if cleaned_subject else "Re:"
