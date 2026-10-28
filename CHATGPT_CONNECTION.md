# Connect to ChatGPT

Connection instructions checked against official OpenAI documentation on
October 28, 2026. Plan availability and workspace controls can change; the
current official page is authoritative:

- [Connect custom MCP servers](https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt)
- [MCP authentication](https://developers.openai.com/plugins/build/auth)
- [FastMCP Google OAuth](https://gofastmcp.com/integrations/google)

This project is an MCP backend; you do **not** paste the ZIP into ChatGPT to
activate a connection. Uploading source files is not installing a server.

## Supported route

1. Install and configure the authenticated server using
   [Windows setup](WINDOWS_SETUP.md), then deploy it behind HTTPS at your own
   stable hostname. MCP URL: `https://YOUR_HOST/mcp`.
2. In ChatGPT web open **Plugins**, select **+**, then **Add custom MCP server**.
   Account/workspace permission is required. Current documentation explicitly
   covers full support for Business and Enterprise/Edu; Pro has read/fetch
   support. Do not assume a Plus subscription guarantees custom MCP access.
3. Enter the name **Google Ads AI Command Center**, a description, and your
   HTTPS MCP URL. Choose OAuth; retain GoogleProvider authentication.
4. Copy the exact production redirect URI shown in the connection's management
   page to the server's `GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS`, then restart the
   server before completing OAuth. OpenAI can use a callback-specific redirect
   or a stable redirect depending on issuer support and connection history.
   Copy what the page shows; do not hardcode an assumed callback.
5. Review the risk warning, select its acknowledgement and **Create as a
   plugin**. Complete Google authorization with the intended Google user.
   Review the discovered tools; expect 20 with the default configuration.
6. Install the resulting plugin; open a new chat, type **@**, select it and ask:
   “List the Google Ads customers I can access.” Then select an advertiser and
   ask for an audit with explicit dates. Example:
   “Audit advertiser 1234567890 for September 1–30, 2026. Prioritize measurement
   problems and explain each recommendation.” The ID/dates here are illustrative.
7. Confirm account currency/timezone and compare reported totals with Google
   Ads before using recommendations for business decisions.

Legacy UI: use Settings → Apps → Advanced settings → Developer mode if your
account presents that workflow; then Apps → Create, select OAuth, **Scan Tools**,
and create the draft. Workspace admins control creation, review and publishing.
Refresh/review the tool snapshot after future server schema changes.

ChatGPT web does not directly reach `localhost` or launch stdio servers. An
OpenAI Secure MCP Tunnel can connect private servers where available; its
provider setup and OAuth origin routing must be verified separately. This
build documents/tests local stdio and the OAuth HTTP application, and does not
implement or validate a Secure MCP Tunnel deployment. A public marketplace
submission needs a stable reachable HTTPS deployment and its own review.

## What the connection can do

The client model turns natural-language questions into these tools. Google Ads
reads do not require approval for a live change because no live change method
exists. Explicit save/delete tools change server-local report storage only and
are marked as state-changing. The preview tool produces a manual review sheet,
not an approval token. Saying “optimize everything” cannot activate ad changes.

Local snapshots contain advertising data. Google identity and OAuth audience
are validated by GoogleProvider; their hash scopes stored reports and remains
stable across token refresh. A different identity cannot list/read/delete them.
This is user isolation in one deployment, not agency organization/RBAC support.

## Verify the deployed connection

Check anonymous `/mcp` returns 401 and advertises protected-resource metadata;
check OAuth metadata, PKCE, callback URI matching, refresh after token expiry,
user identity isolation, manager routing and denial for unauthorized advertisers.
The local test suite verifies anonymous/invalid-token denial and discovery with
synthetic configuration. Real Google consent, refresh and ChatGPT tool invocation
require your deployment and were **not** tested in this build.
