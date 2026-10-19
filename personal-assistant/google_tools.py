"""Google connection: Gmail (read and draft only - never sends) and Google Calendar."""

import base64
import os
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from anthropic import beta_tool
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

HERE = Path(__file__).parent
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",  # used only to create drafts
    "https://www.googleapis.com/auth/calendar.events",
]
_services = {}


def _tz():
    return os.environ.get("TIME_ZONE", "Europe/London")


def _creds():
    """Log in to Google once; afterwards the login is kept in token.json."""
    token = HERE / "token.json"
    creds = Credentials.from_authorized_user_file(token, SCOPES) if token.exists() else None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(HERE / "credentials.json", SCOPES)
        creds = flow.run_local_server(port=0)
    token.write_text(creds.to_json())
    return creds


def _service(name, version):
    if name not in _services:
        _services[name] = build(name, version, credentials=_creds())
    return _services[name]


def _gmail():
    return _service("gmail", "v1")


def _calendar():
    return _service("calendar", "v3")


# ---------- Gmail ----------

@beta_tool
def search_email(query: str, max_results: int = 10) -> str:
    """Search the user's Gmail. Returns sender, subject, date and a short preview for each email.

    Args:
        query: Gmail search, e.g. "from:dentist", "is:unread newer_than:3d", "theatre tickets".
        max_results: How many emails to return (up to 25).
    """
    gmail = _gmail()
    found = gmail.users().messages().list(userId="me", q=query, maxResults=min(max_results, 25)).execute()
    lines = []
    for m in found.get("messages", []):
        msg = gmail.users().messages().get(
            userId="me", id=m["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        h = {x["name"]: x["value"] for x in msg["payload"].get("headers", [])}
        lines.append(
            f"- id {m['id']} | {h.get('Date', '')} | From: {h.get('From', '')} | "
            f"Subject: {h.get('Subject', '(none)')}\n    {msg.get('snippet', '')}"
        )
    return "\n".join(lines) or "No emails found."


def _plain_text(payload):
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []):
        text = _plain_text(part)
        if text:
            return text
    return ""


@beta_tool
def read_email(email_id: str) -> str:
    """Read the full text of one email found with search_email.

    Args:
        email_id: The id shown in search_email results.
    """
    msg = _gmail().users().messages().get(userId="me", id=email_id, format="full").execute()
    h = {x["name"]: x["value"] for x in msg["payload"].get("headers", [])}
    body = _plain_text(msg["payload"]) or msg.get("snippet", "")
    return f"From: {h.get('From')}\nTo: {h.get('To')}\nDate: {h.get('Date')}\nSubject: {h.get('Subject')}\n\n{body[:8000]}"


@beta_tool
def draft_email(to: str, subject: str, body: str) -> str:
    """Save an email as a DRAFT in Gmail. This never sends. The user reviews and sends it themselves.

    Args:
        to: Recipient email address.
        subject: Subject line.
        body: The email text.
    """
    msg = EmailMessage()
    msg["To"], msg["Subject"] = to, subject
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    _gmail().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return f"Draft saved in Gmail (not sent): '{subject}' to {to}. Open Gmail > Drafts to check and send it."


# ---------- Calendar ----------

@beta_tool
def list_events(days_ahead: int = 7, search: str = "") -> str:
    """List events in the user's main Google Calendar from now onwards.

    Args:
        days_ahead: How many days ahead to look (1 = today only).
        search: Optional word to look for in event titles, e.g. "theatre".
    """
    now = datetime.now(ZoneInfo(_tz()))
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    params = dict(
        calendarId="primary",
        timeMin=start.isoformat(),
        timeMax=(start + timedelta(days=max(days_ahead, 1))).isoformat(),
        singleEvents=True,
        orderBy="startTime",
        maxResults=100,
    )
    if search:
        params["q"] = search
    events = _calendar().events().list(**params).execute().get("items", [])
    lines = []
    for e in events:
        when = e["start"].get("dateTime", e["start"].get("date"))
        where = f" @ {e['location']}" if e.get("location") else ""
        lines.append(f"- {when}: {e.get('summary', '(no title)')}{where} (id {e['id']})")
    return "\n".join(lines) or "Nothing in the calendar for that period."


@beta_tool
def add_event(title: str, start: str, end: str = "", location: str = "", notes: str = "", all_day: bool = False) -> str:
    """Add an event to the user's Google Calendar. Only call this after the user has said yes to the details.

    Args:
        title: Event name, e.g. "Theatre - Hamilton".
        start: Start as ISO date-time, e.g. "2026-11-02T19:30", or a date "2026-11-02" for all-day.
        end: Optional end in the same format. Defaults to one hour after start (or same day if all-day).
        location: Optional place.
        notes: Optional description.
        all_day: True for an all-day event.
    """
    tz = _tz()
    if all_day:
        day = datetime.fromisoformat(start[:10]).date()
        last = datetime.fromisoformat(end[:10]).date() if end else day
        times = {"start": {"date": day.isoformat()}, "end": {"date": (last + timedelta(days=1)).isoformat()}}
    else:
        s = datetime.fromisoformat(start)
        e = datetime.fromisoformat(end) if end else s + timedelta(hours=1)
        times = {
            "start": {"dateTime": s.replace(tzinfo=None).isoformat(), "timeZone": tz},
            "end": {"dateTime": e.replace(tzinfo=None).isoformat(), "timeZone": tz},
        }
    event = {"summary": title, **times}
    if location:
        event["location"] = location
    if notes:
        event["description"] = notes
    created = _calendar().events().insert(calendarId="primary", body=event).execute()
    return f"Added to Google Calendar: {title}. Link: {created.get('htmlLink')}"


TOOLS = [search_email, read_email, draft_email, list_events, add_event]
