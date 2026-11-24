# 03 – List the tools

```text
What tools does the gmail-calendar server give you?
```

**Why:** To confirm the agent actually sees the registered MCP server, not just that `claude mcp list` says connected.

**What happened:** The first attempt failed because MCP tools load only at session start; after restarting the agent it listed all 6 tools.
