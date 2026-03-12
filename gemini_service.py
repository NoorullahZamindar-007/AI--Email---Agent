import os

from dotenv import load_dotenv
from google import genai


load_dotenv()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite").strip()


def get_gemini_client() -> genai.Client:
    """
    Create and return a Gemini API client.
    """
    if not GEMINI_API_KEY:
        raise ValueError("Missing GEMINI_API_KEY environment variable.")

    return genai.Client(api_key=GEMINI_API_KEY)


def generate_reply(sender: str, subject: str, body: str) -> str:
    """
    Generate a professional email reply from the incoming message details.

    Returns only the email body text. Raises a ValueError if Gemini returns
    no usable content.
    """
    client = get_gemini_client()

    prompt = (
        "You are an email assistant.\n"
        "Write a professional and concise email reply.\n"
        "Do not hallucinate facts, promises, dates, or actions that were not stated.\n"
        "If the message is unclear or missing important information, politely ask for clarification.\n"
        "Return only the email body text.\n"
        "Do not include a subject line.\n\n"
        f"Sender: {sender or 'Unknown'}\n"
        f"Subject: {subject or 'No subject'}\n\n"
        "Original email:\n"
        f"{body or ''}"
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
    except Exception as exc:
        raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    text = getattr(response, "text", None)
    if text and str(text).strip():
        return str(text).strip()

    raise ValueError("Gemini API returned an empty reply.")
