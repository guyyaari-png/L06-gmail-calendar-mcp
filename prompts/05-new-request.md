# 05 – A new, unplanned request

```text
Find my latest email from Foresight, summarize it in two lines, and tell me if I am free tomorrow between 10:00 and 12:00.
```

**Why:** To check that the agent can combine the tools for a request nobody coded for.

**What happened:** The agent chained `search_emails` → `read_email` → `check_availability`, summarized the email in two lines and answered that I am busy in that slot.
