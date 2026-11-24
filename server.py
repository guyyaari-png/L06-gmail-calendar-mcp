"""gmail-calendar MCP server.

Exposes Gmail search/read/draft and Google Calendar tools over stdio.
There is intentionally no tool that sends email.

Secrets (client_secret*.json, token.json) live in $GOOGLE_PRIVATE_DIR
(default ~/my-private) and are never copied into this project folder.
All logging goes to stderr; stdout is reserved for the MCP protocol.
"""

from __future__ import annotations

import base64
import contextlib
import html
import logging
import os
import re
import sys
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("gmail-calendar")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]
TIMEZONE = "Asia/Jerusalem"
TZ = ZoneInfo(TIMEZONE)

mcp = FastMCP("gmail-calendar")


# --------------------------------------------------------------------------- auth


def _private_dir() -> Path:
    return Path(os.environ.get("GOOGLE_PRIVATE_DIR", "~/my-private")).expanduser()


def _client_secret_file(private_dir: Path) -> Path:
    matches = sorted(private_dir.glob("client_secret*.json"))
    if not matches:
        raise FileNotFoundError(
            f"No client_secret*.json found in {private_dir} (set GOOGLE_PRIVATE_DIR)."
        )
    return matches[0]


def _save_token(creds: Credentials, token_path: Path) -> None:
    token_path.write_text(creds.to_json())
    os.chmod(token_path, 0o600)
    log.info("Saved refreshed token to GOOGLE_PRIVATE_DIR")


_creds: Credentials | None = None


def _credentials() -> Credentials:
    global _creds
    if _creds and _creds.valid:
        return _creds

    private_dir = _private_dir()
    token_path = private_dir / "token.json"
    creds = _creds
    if creds is None and token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        log.info("Refreshing Google access token")
        creds.refresh(Request())
        _save_token(creds, token_path)
    elif not creds or not creds.valid:
        log.info("No valid token; starting browser OAuth flow")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(_client_secret_file(private_dir)), SCOPES
        )
        # The OAuth helper prints to stdout, which would corrupt the stdio protocol.
        with contextlib.redirect_stdout(sys.stderr):
            creds = flow.run_local_server(port=0)
        _save_token(creds, token_path)

    _creds = creds
    return creds


def _gmail():
    return build("gmail", "v1", credentials=_credentials(), cache_discovery=False)


def _calendar():
    return build("calendar", "v3", credentials=_credentials(), cache_discovery=False)


# --------------------------------------------------------------------------- time helpers


def _parse_time(value: str) -> datetime | date:
    """Parse ISO 8601; naive datetimes are interpreted as Asia/Jerusalem.

    A bare date (YYYY-MM-DD) is returned as a date (used for all-day events).
    """
    value = value.strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return date.fromisoformat(value)
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return dt


def _to_rfc3339(value: str) -> str:
    parsed = _parse_time(value)
    if isinstance(parsed, datetime):
        return parsed.isoformat()
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=TZ).isoformat()


def _event_time(value: str) -> dict:
    parsed = _parse_time(value)
    if isinstance(parsed, datetime):
        return {"dateTime": parsed.isoformat(), "timeZone": TIMEZONE}
    return {"date": parsed.isoformat()}


def _format_event(ev: dict) -> dict:
    return {
        "id": ev.get("id"),
        "summary": ev.get("summary", "(no title)"),
        "start": ev.get("start", {}).get("dateTime") or ev.get("start", {}).get("date"),
        "end": ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date"),
        "location": ev.get("location"),
        "description": ev.get("description"),
        "status": ev.get("status"),
        "html_link": ev.get("htmlLink"),
    }


# --------------------------------------------------------------------------- gmail helpers


def _headers(payload: dict) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in payload.get("headers", [])}


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode()).decode("utf-8", errors="replace")


def _collect_bodies(part: dict, plain: list[str], htmls: list[str]) -> None:
    mime = part.get("mimeType", "")
    data = part.get("body", {}).get("data")
    if data and not part.get("filename"):
        if mime == "text/plain":
            plain.append(_decode(data))
        elif mime == "text/html":
            htmls.append(_decode(data))
    for sub in part.get("parts", []) or []:
        _collect_bodies(sub, plain, htmls)


def _html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    raw = html.unescape(raw)
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


# --------------------------------------------------------------------------- tools


@mcp.tool()
def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail using Gmail search syntax (e.g. 'from:alice is:unread newer_than:7d').

    Returns up to max_results messages (1-100), each with id, from, subject, date and snippet.
    Use read_email with the returned id to get the full body.
    """
    max_results = max(1, min(int(max_results), 100))
    gmail = _gmail()
    resp = gmail.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    results = []
    for m in resp.get("messages", []):
        msg = (
            gmail.users()
            .messages()
            .get(
                userId="me",
                id=m["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            )
            .execute()
        )
        h = _headers(msg.get("payload", {}))
        results.append(
            {
                "id": msg["id"],
                "thread_id": msg.get("threadId"),
                "from": h.get("from", ""),
                "subject": h.get("subject", ""),
                "date": h.get("date", ""),
                "snippet": html.unescape(msg.get("snippet", "")),
            }
        )
    log.info("search_emails returned %d results", len(results))
    return results


@mcp.tool()
def read_email(message_id: str) -> dict:
    """Read one Gmail message by id: returns headers (from, to, cc, subject, date, ...)
    and the full plain-text body (HTML-only messages are converted to text)."""
    msg = _gmail().users().messages().get(userId="me", id=message_id, format="full").execute()
    payload = msg.get("payload", {})
    h = _headers(payload)
    plain: list[str] = []
    htmls: list[str] = []
    _collect_bodies(payload, plain, htmls)
    body = "\n".join(plain).strip() or _html_to_text("\n".join(htmls))
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId"),
        "labels": msg.get("labelIds", []),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "cc": h.get("cc", ""),
        "subject": h.get("subject", ""),
        "date": h.get("date", ""),
        "message_id_header": h.get("message-id", ""),
        "headers": h,
        "body": body,
    }


@mcp.tool()
def create_draft(
    to: str, subject: str, body: str, reply_to_message_id: str | None = None
) -> dict:
    """Create a Gmail DRAFT (it is NOT sent). The user must review and send it manually in Gmail.

    to: recipient address(es), comma-separated. body: plain text.
    reply_to_message_id: optional Gmail message id; if given, the draft is threaded
    as a reply to that message (In-Reply-To/References headers set).
    """
    gmail = _gmail()
    msg = EmailMessage()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    draft_message: dict = {}
    if reply_to_message_id:
        orig = (
            gmail.users()
            .messages()
            .get(
                userId="me",
                id=reply_to_message_id,
                format="metadata",
                metadataHeaders=["Message-ID", "References", "Subject"],
            )
            .execute()
        )
        oh = _headers(orig.get("payload", {}))
        orig_mid = oh.get("message-id")
        if orig_mid:
            msg["In-Reply-To"] = orig_mid
            msg["References"] = f"{oh.get('references', '')} {orig_mid}".strip()
        draft_message["threadId"] = orig.get("threadId")

    draft_message["raw"] = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = gmail.users().drafts().create(userId="me", body={"message": draft_message}).execute()
    log.info("Created draft %s", draft.get("id"))
    return {
        "draft_id": draft.get("id"),
        "message_id": draft.get("message", {}).get("id"),
        "thread_id": draft.get("message", {}).get("threadId"),
        "status": "Draft created (not sent).",
    }


@mcp.tool()
def list_events(start: str, end: str) -> list[dict]:
    """List events on the primary Google Calendar between start and end.

    start/end: ISO 8601 (e.g. '2026-11-25T09:00:00' or '2026-11-25').
    Times without an offset are interpreted in Asia/Jerusalem; results are in Asia/Jerusalem.
    """
    cal = _calendar()
    events: list[dict] = []
    page_token = None
    while True:
        resp = (
            cal.events()
            .list(
                calendarId="primary",
                timeMin=_to_rfc3339(start),
                timeMax=_to_rfc3339(end),
                singleEvents=True,
                orderBy="startTime",
                timeZone=TIMEZONE,
                pageToken=page_token,
            )
            .execute()
        )
        events.extend(_format_event(e) for e in resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return events


@mcp.tool()
def check_availability(start: str, end: str) -> dict:
    """Check free/busy on the primary Google Calendar between start and end.

    start/end: ISO 8601; times without an offset are interpreted in Asia/Jerusalem.
    Returns the busy intervals and whether the whole range is free.
    """
    resp = (
        _calendar()
        .freebusy()
        .query(
            body={
                "timeMin": _to_rfc3339(start),
                "timeMax": _to_rfc3339(end),
                "timeZone": TIMEZONE,
                "items": [{"id": "primary"}],
            }
        )
        .execute()
    )
    primary = resp.get("calendars", {}).get("primary", {})
    busy = [
        {
            "start": datetime.fromisoformat(b["start"].replace("Z", "+00:00")).astimezone(TZ).isoformat(),
            "end": datetime.fromisoformat(b["end"].replace("Z", "+00:00")).astimezone(TZ).isoformat(),
        }
        for b in primary.get("busy", [])
    ]
    return {
        "time_zone": TIMEZONE,
        "start": _to_rfc3339(start),
        "end": _to_rfc3339(end),
        "is_free": not busy,
        "busy": busy,
        "errors": primary.get("errors", []),
    }


@mcp.tool()
def create_event(
    summary: str,
    start: str,
    end: str,
    location: str | None = None,
    description: str | None = None,
) -> dict:
    """Create an event on the primary Google Calendar (no invitations are emailed).

    start/end: ISO 8601 date-times (e.g. '2026-11-25T14:00:00'), interpreted in
    Asia/Jerusalem when no offset is given. Bare dates (YYYY-MM-DD) create an all-day
    event (end date is exclusive).
    """
    body: dict = {"summary": summary, "start": _event_time(start), "end": _event_time(end)}
    if location:
        body["location"] = location
    if description:
        body["description"] = description
    ev = _calendar().events().insert(calendarId="primary", body=body, sendUpdates="none").execute()
    log.info("Created event %s", ev.get("id"))
    return _format_event(ev)


def main() -> None:
    log.info("Starting gmail-calendar MCP server (stdio)")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
