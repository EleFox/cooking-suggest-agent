# Penpot MCP Integration Debugging

## Environment
- Penpot 2.16 self-hosted via Docker, compose file: `D:\dockerImages\penpot\docker-compose.yaml`
- MCP server: `penpot-penpot-mcp-1` (image `penpotapp/mcp:2.16`), ports `4401`(HTTP)/`4402`(WS), proxied through frontend nginx
- MCP access endpoint (Streamable HTTP): `http://localhost:9001/mcp/stream?userToken=<token>`
- Frontend browser access: `http://localhost:9001`
- Prerequisite: The browser must have a Penpot file open with the MCP plugin connected (`File → MCP Server → Connect`). If the plugin window is closed or the token mismatches, the server will report "No plugin instance connected for user token".

## opencode Configuration
- Global config: `C:\Users\ZYBai\.config\opencode\opencode.json`
- `instructions` points to the kit bundle: `C:\Users\ZYBai\.penpot-ai-kit\AGENTS.md` + `skills\penpot-router\SKILL.md`
- `mcp.penpot`: remote type, URL includes the actual `userToken`, `oauth:false`, `timeout:30000`
- Project config: `F:\ProjectHarness\penpot-mcp-test\opencode.jsonc` – `mcp.penpot` also contains the real token, and project-level overrides global settings
- Penpot AI Kit installed to `C:\Users\ZYBai\.penpot-ai-kit` (v0.3.0). New sessions automatically load `AGENTS.md` and `penpot-router` via global `instructions`.

## Token Mechanism
- Authentication is handled by the `userToken` query parameter, which is a Penpot Personal Access Token (PAT).
- The `userToken` in the opencode URL must exactly match the token used by the browser plugin; otherwise the server cannot locate the plugin instance for that token and will return an error.
- Troubleshooting steps:
  1. Verify that the two tokens are identical.
  2. Confirm the plugin window is open (`File → MCP Server → Connect`).