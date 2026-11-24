# 01 – Build the server

```text
Build an MCP server named gmail-calendar in the current folder, in Python with FastMCP,
running over stdio and managed with uv (pyproject.toml + uv.lock).

Expose exactly 6 tools:
- search_emails(query, max_results): Gmail search syntax; return id, from, subject, date, snippet.
- read_email(message_id): headers and the full plain-text body (convert HTML-only mail to text).
- create_draft(to, subject, body, reply_to_message_id optional): create a DRAFT only; thread it
  as a reply when reply_to_message_id is given.
- list_events(start, end): events on the primary calendar in the range.
- check_availability(start, end): free/busy for the primary calendar.
- create_event(summary, start, end, location optional, description optional): no invitations sent.

Times are ISO 8601; times without an offset are Asia/Jerusalem.
Do NOT add any tool that sends email.

Secrets: read client_secret*.json and token.json from the folder in the environment variable
GOOGLE_PRIVATE_DIR. Never copy them into this project. If there is no valid token, run the
browser OAuth flow and save the token back to GOOGLE_PRIVATE_DIR.

Log only to stderr (stdout is the MCP protocol). Add a .gitignore that excludes token.json,
client_secret*.json, .env and .venv. Add a small read-only smoke test (test_server.py) that
starts the server, lists the tools and calls list_events.
```

**Why:** To turn the fixed L05 script into a tool menu the agent can choose from on its own.

**What happened:** The agent produced `server.py` with 6 tools, `test_server.py`, `pyproject.toml`/`uv.lock` and `.gitignore`; no send tool.
