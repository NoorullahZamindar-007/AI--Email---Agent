from email.utils import parseaddr
from typing import Dict, List

from db import already_processed, init_db, save_log
from gmail_service import (
    create_reply_draft,
    extract_plain_text_body,
    get_gmail_service,
    get_message,
    list_unread_inbox_messages,
    parse_headers,
)
from gemini_service import generate_reply


def process_inbox(max_results: int = 10) -> List[Dict]:
    """
    Process unread inbox messages from Gmail and create AI-generated reply drafts.

    Flow:
    1. Connect to Gmail
    2. List unread inbox messages
    3. Skip messages already stored in SQLite
    4. Read the full message
    5. Extract the fields needed for reply generation
    6. Send the email body to Gemini
    7. Create a Gmail draft reply in the same thread
    8. Save the result in SQLite

    Returns a simple results list so the caller can inspect what happened.
    """
    init_db()
    service = get_gmail_service()
    message_refs = list_unread_inbox_messages(service, max_results=max_results)

    results: List[Dict] = []

    for message_ref in message_refs:
        gmail_message_id = message_ref.get("id", "")

        # Skip messages we have already handled in a previous scheduler run.
        if not gmail_message_id or already_processed(gmail_message_id):
            continue

        try:
            full_message = get_message(service, gmail_message_id)
            headers = parse_headers(full_message)
            body = extract_plain_text_body(full_message)

            thread_id = full_message.get("threadId", "")
            sender = headers.get("from", "")
            sender_email = _extract_email_address(sender)
            subject = headers.get("subject", "")

            # This is the RFC email Message-ID header used for proper replies.
            reply_message_id = headers.get("message_id", "")

            # References keeps the email conversation chain. If the header is
            # missing, using the original message ID is a safe fallback.
            references = _get_header_value(full_message, "references") or reply_message_id

            ai_reply = generate_reply(
                sender=sender,
                subject=subject,
                body=body,
            )

            draft = create_reply_draft(
                service=service,
                to_email=sender_email,
                subject=subject,
                reply_text=ai_reply,
                thread_id=thread_id,
                message_id=reply_message_id,
                references=references,
            )

            draft_id = draft.get("id", "")

            save_log(
                gmail_message_id=gmail_message_id,
                thread_id=thread_id,
                sender=sender,
                subject=subject,
                original_body=body,
                ai_reply=ai_reply,
                draft_id=draft_id,
                status="draft_created",
            )

            results.append(
                {
                    "gmail_message_id": gmail_message_id,
                    "thread_id": thread_id,
                    "sender": sender,
                    "subject": subject,
                    "draft_id": draft_id,
                    "status": "draft_created",
                }
            )
        except Exception as exc:
            # Save failed attempts too, so the dashboard can show errors and
            # the message is not silently ignored.
            save_log(
                gmail_message_id=gmail_message_id,
                thread_id=full_message.get("threadId", "") if "full_message" in locals() else None,
                sender=headers.get("from", "") if "headers" in locals() else None,
                subject=headers.get("subject", "") if "headers" in locals() else None,
                original_body=body if "body" in locals() else None,
                ai_reply=None,
                draft_id=None,
                status=f"error: {exc}",
            )

            results.append(
                {
                    "gmail_message_id": gmail_message_id,
                    "status": f"error: {exc}",
                }
            )

    return results


def _extract_email_address(sender: str) -> str:
    """
    Convert a From header like 'Jane Doe <jane@example.com>' into
    'jane@example.com'.
    """
    _, email_address = parseaddr(sender or "")
    return email_address or sender


def _get_header_value(message: Dict, header_name: str) -> str:
    """
    Read one header value from the Gmail message payload.
    """
    headers = message.get("payload", {}).get("headers", [])
    target_name = header_name.lower()

    for header in headers:
        if header.get("name", "").lower() == target_name:
            return header.get("value", "")

    return ""
