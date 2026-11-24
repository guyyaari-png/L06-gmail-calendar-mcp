# 02 – Fix the secrets path

```text
The secrets folder is ~/my-private (not C:\my-private). It now contains client_secret_desk.json; there is no token.json yet. Update test_server.py and any default in the server to use ~/my-private, then run the test again.
```

**Why:** The course slides use Windows paths, which do not exist on a Mac.

**What happened:** Defaults were switched to `~/my-private`, the test opened the browser OAuth flow, created `token.json` there and listed the 6 tools.
