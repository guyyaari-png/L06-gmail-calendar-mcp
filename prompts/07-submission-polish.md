# 07 – Submission polish

```text
Improve this repo for submission. Make each numbered task a separate commit with a meaningful message, and push after each one (git push origin main).

1. Create prompts/ with numbered files, one per real prompt used in this assignment, each with the prompt text in a code block, a one-line "why" and a one-line "what happened". [...list of the 7 prompts...] Add prompts/README.md with a table of all prompts.
2. server.py: catch google.auth.exceptions.RefreshError when refreshing the token and fall back to the browser OAuth flow; create the private folder if missing before saving the token. Run the existing smoke test afterwards (read-only).
3. test_server.py: respect an existing GOOGLE_PRIVATE_DIR env var, default ~/my-private.
4. README.md: rewrite in Hebrew with English technical terms: what the project is, the 6 tools table (and that there is no send tool, by design), prerequisites (uv, Google Cloud OAuth Desktop client, secrets in ~/my-private), setup (uv sync), registration command using "$(pwd)" instead of a hardcoded personal path, example prompts, how secrets are kept out of git, link to reflection.md and prompts/, and a screenshots section embedding docs/screenshots/01-mcp-connected.png, 02-draft.png, 03-event.png.
5. Final check: grep the whole repo and git history for GOCSPX, ghp_, refresh_token values and personal paths like /Users/; confirm .gitignore covers secrets; show me git log --oneline.

Never print or copy anything from ~/my-private. Never send email.
```

**Why:** To make the repo submission-ready: documented prompts, a more robust auth flow and a clear Hebrew README.

**What happened:** The agent made one commit per task and pushed after each: this `prompts/` folder, the RefreshError fallback, the env-aware smoke test, the Hebrew README and a final secrets scan.
