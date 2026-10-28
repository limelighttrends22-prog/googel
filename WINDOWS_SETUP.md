# Windows setup (PowerShell)

These are executable setup instructions, not a claim that Windows was tested in
this Linux build environment. Use Python 3.12 (64-bit), Windows 10/11, outbound
HTTPS access, and an account allowed to install Python packages. Do not put
credentials in chat, Git, the ZIP, or customer-facing reports.

## 1. Extract and install

Extract the ZIP to `C:\GoogleAdsCommandCenter`, then enter the extracted
`google-ads-command-center` folder. Adjust the path below if needed.

```powershell
Set-Location C:\GoogleAdsCommandCenter\google-ads-command-center
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m pip check
Copy-Item .env.example .env
notepad .env
```

Activation is unnecessary; the full executable paths avoid PowerShell execution
policy changes. Existing environment variables override `.env`. Never overwrite
an existing `.env` with `Copy-Item` when updating. Install instructions require
internet access to PyPI; the ZIP is source-complete, not an offline wheelhouse.
Pinned dependencies were resolved on Python 3.12/Linux; platform wheel and Python
compatibility must still be checked on your Windows installation.

## 2. Configure Google Cloud API access

1. Select/create the Google Cloud project that will own the OAuth client.
2. Enable **Google Ads API** in that project. If using the Google Cloud CLI:

   ```powershell
   gcloud services enable googleads.googleapis.com --project=YOUR_PROJECT_ID
   ```

3. Open that project's Google Ads API Overview in Cloud Console. Confirm its
   access level permits your intended accounts. Test access cannot read real
   production advertisers; request the appropriate production access there.
4. Ensure the Google user has permission for the advertiser, directly or through
   a manager. Use the lowest practical Ads account role (read-only for this
   server). API project access and advertiser permission are separate gates.
5. Configure Google Auth Platform branding, audience/test users and data access.
   The server requests `openid`, userinfo email/profile, and
   `https://www.googleapis.com/auth/adwords`. Google Ads has no separate
   read-only OAuth scope; safety comes from account roles and the server's
   read-only tool implementation. External publishing may require Google's
   verification process; review Google policy for your actual distribution.

**October 2026 correction:** Developer tokens were sunset September 9, 2026.
Access is associated with the Cloud project owning your OAuth credentials.
`GOOGLE_ADS_DEVELOPER_TOKEN` is an optional legacy compatibility header, not a
required onboarding step. Some older Google pages still mention tokens; use
[the migration guidance](https://developers.google.com/google-ads/api/docs/api-policy/developer-token)
and [current first-call guidance](https://developers.google.com/google-ads/api/docs/get-started/introduction).
A quota-project setting alone does not change the project that owns an OAuth
client. See also [Google OAuth](https://developers.google.com/google-ads/api/docs/oauth/overview).

## 3A. Local stdio evaluation

Use this for local MCP clients that launch executables. **ChatGPT web does not
launch this executable or connect directly to localhost.**

Install the Google Cloud CLI separately. Create a **Desktop app** OAuth client
in your approved project for this ADC flow. Download its JSON to a private
folder outside the source tree, for example `C:\PrivateAds\desktop-oauth.json`.
Do not use a Web application OAuth client's file for this desktop login flow.

```powershell
gcloud auth application-default login --client-id-file="C:\PrivateAds\desktop-oauth.json" --scopes="https://www.googleapis.com/auth/adwords,https://www.googleapis.com/auth/cloud-platform"
.\.venv\Scripts\ads-command-center.exe doctor
.\.venv\Scripts\ads-command-center.exe serve
```

Leave the two `GOOGLE_ADS_MCP_OAUTH_CLIENT_*` variables empty for local mode.
Keep the server running only when the local MCP client owns its stdio stream.
A terminal waiting silently is expected. `doctor` does not verify live access.
ADC credentials are stored by gcloud outside this project; secure the Windows
user account. Do not distribute those files. `gcloud auth login` alone does not
create ADC. Never share a local-stdio service across unrelated users.

Example local client configuration (for clients supporting this JSON format):

```json
{
  "mcpServers": {
    "google-ads-command-center": {
      "command": "C:\\GoogleAdsCommandCenter\\google-ads-command-center\\.venv\\Scripts\\ads-command-center.exe",
      "args": ["serve", "--env-file", "C:\\GoogleAdsCommandCenter\\google-ads-command-center\\.env"]
    }
  }
}
```

## 3B. Authenticated HTTP for ChatGPT

Create a separate **Web application** OAuth client in the approved Google Cloud
project. Plan a stable HTTPS origin, e.g. `https://ads.yourcompany.example`.
In Google, register this exact redirect URI:

```text
https://ads.yourcompany.example/auth/callback
```

Google redirects to the server's callback. Separately, the MCP client redirects
back to ChatGPT: copy ChatGPT's **exact production redirect URI** from the MCP
server management page into `GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS`. These are two
different allowlists. Do not substitute a guessed callback or a wildcard.
If the ChatGPT UI needs to create the connection before it displays the URI,
create the draft connection, copy its callback from management, update `.env`,
and restart before completing OAuth/tool scanning.

Generate local secrets using Python, and put the resulting values directly in
`.env` or your deployment secret manager (not in chat):

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set these `.env` values (replace placeholders privately):

```dotenv
GOOGLE_ADS_MCP_OAUTH_CLIENT_ID=YOUR_WEB_CLIENT_ID
GOOGLE_ADS_MCP_OAUTH_CLIENT_SECRET=YOUR_WEB_CLIENT_SECRET
GOOGLE_ADS_MCP_BASE_URL=https://ads.yourcompany.example
GOOGLE_ADS_MCP_JWT_SIGNING_KEY=YOUR_RANDOM_SIGNING_KEY
GOOGLE_ADS_MCP_STORAGE_TYPE=filetree
GOOGLE_ADS_MCP_STORAGE_PATH=C:/PrivateAds/oauth
GOOGLE_ADS_MCP_STORAGE_ENCRYPTION_KEY=YOUR_FERNET_KEY
GOOGLE_ADS_MCP_ALLOWED_REDIRECT_URIS=EXACT_HTTPS_REDIRECT_FROM_CHATGPT
GOOGLE_ADS_MCP_REPORT_DB=C:/PrivateAds/reports.sqlite3
GOOGLE_ADS_MCP_HOST=127.0.0.1
PORT=8080
```

Optionally set `GOOGLE_ADS_MCP_ALLOWED_CUSTOMERS` to comma-separated 10-digit
advertiser IDs to restrict this deployment; set `GOOGLE_ADS_LOGIN_CUSTOMER_ID`
only when manager routing is needed. The manager ID is not an advertiser data
allowlist entry.

```powershell
.\.venv\Scripts\ads-command-center.exe doctor
.\.venv\Scripts\ads-command-center.exe serve
```

Provide HTTPS through a properly configured reverse proxy/deployment, forwarding
to loopback port 8080. Route `/mcp`, `/auth/*`, and `/.well-known/*`; do not strip
OAuth query parameters. Never expose an unauthenticated ADC service. For a
container set `GOOGLE_ADS_MCP_HOST=0.0.0.0` only behind authenticated OAuth and
TLS ingress. See [deployment](DEPLOYMENT.md) and
[ChatGPT connection](CHATGPT_CONNECTION.md).

The supplied entrypoint chooses HTTP only when OAuth is fully configured.
Incomplete credentials, HTTP public origins, short signing keys, unencrypted or
nonpersistent OAuth storage and unrestricted redirect configuration fail closed.
GoogleProvider supplies authorization code/PKCE, issuer protection, token
validation and refresh; live end-to-end OAuth remains a deployment test.

## 4. First account check

1. Invoke `customers_list_accessible_customers`. It lists directly accessible
   customers; it does not recursively enumerate all manager descendants.
2. If needed, use `search_search` on `customer_client` under your manager to
   inspect authorized child IDs, then choose a non-manager advertiser.
3. Invoke `intelligence_audit_account` with explicit ISO start/end dates and
   correct manager routing. Use a mature period first.
4. Compare totals with the same date range, timezone, currency, columns and
   filters in Google Ads. Review privacy/attribution differences.

## 5. Run offline tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
.\.venv\Scripts\python.exe -m pytest -ra
.\.venv\Scripts\python.exe -m black --check -l 80 ads_mcp tests
.\.venv\Scripts\python.exe -m build
```

Redis and Firestore backends are optional extras and their integration tests are
skipped if their packages are absent. They are not deployment-validated here.
