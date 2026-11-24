# gmail-calendar MCP server

A stdio MCP server (Python, FastMCP) with 6 tools:

| Tool | What it does |
|---|---|
| `search_emails(query, max_results)` | Gmail search → id, from, subject, date, snippet |
| `read_email(message_id)` | Headers + full plain-text body |
| `create_draft(to, subject, body, reply_to_message_id?)` | Creates a **draft only** — nothing is ever sent |
| `list_events(start, end)` | Primary-calendar events in a range |
| `check_availability(start, end)` | Free/busy for the primary calendar |
| `create_event(summary, start, end, location?, description?)` | Creates a calendar event |

There is no send-email tool. Times are ISO 8601; times without an offset are
treated as `Asia/Jerusalem`.

## Secrets

`client_secret*.json` and `token.json` are read from `$GOOGLE_PRIVATE_DIR`
(default `~/my-private`). A refreshed token is written back there. Nothing
secret is stored in this folder. If there is no valid token, the first tool
call opens a browser for Google sign-in.

Scopes: `gmail.modify`, `calendar`.

## Register in Claude Code

```bash
claude mcp add gmail-calendar \
  -e GOOGLE_PRIVATE_DIR="$HOME/my-private" \
  -- uv run --directory /Users/guyyaari/AI-Course/L06 server.py
```

Check with `claude mcp list`, or `/mcp` inside Claude Code.
