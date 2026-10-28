# Deployment and troubleshooting

## One-instance evaluation deployment

Use Python 3.12 and the runtime lock. Run the process as a non-admin service user.
Mount durable, access-restricted storage for encrypted OAuth state and report
SQLite files. Inject credentials/signing/encryption keys using your host's secret
manager. Do not bake `.env`, ADC or token state into the image.

Container build (Docker is not available for validation in this environment):

```shell
docker build -t google-ads-command-center:0.1.0 .
```

Run with the privately prepared environment file, an owned persistent volume for
`/data`, and an HTTPS ingress configured for the canonical public origin. The
container user is UID 10001; the volume must be writable by that user. Set
`GOOGLE_ADS_MCP_STORAGE_TYPE=filetree`; the Dockerfile defaults storage paths to
`/data/oauth` and `/data/reports.sqlite3`. OAuth mode still requires the client ID,
secret, public HTTPS origin, signing key and exact MCP callback allowlist. The
container never changes FastMCP authentication source or disables issuer checks.

HTTPS ingress must route `/mcp`, OAuth endpoints and discovery endpoints, preserve
streaming and relevant headers, and apply sensible request-body, connection and
rate limits. Disable query/body/access-token logging on the proxy. Configure
request duration above the bounded upstream API request time so the client can
receive results; use deployment resource limits suitable for up to 10,000 rows
per read. Application report execution may perform several sequential API reads.
The reader retries transient transport errors; it does not retry all API quota
or authorization failures.

No global rate limiter, billing quota, readiness orchestration, distributed job
queue or automatic retention worker is included. Use a single process/instance
for this SQLite evaluation. Redis/Firestore OAuth stores do not magically make
the report database distributed. Scaling requires a proper durable report
service, consistent authorization/tenancy, refresh concurrency validation and
operational controls.

## Troubleshooting

| Symptom | Check / next action |
|---|---|
| `doctor` rejects configuration | Set both OAuth client values or leave both empty for stdio; use HTTPS public origin, >=32-character random signing key, persistent storage and exact redirect allowlist |
| No custom MCP option in ChatGPT | Check plan/workspace permissions using current official documentation; uploading ZIP source does not create a connection |
| ChatGPT cannot reach endpoint | Check reachable HTTPS `/mcp`, TLS chain and all OAuth/discovery proxy routes; localhost is not directly reachable from ChatGPT web |
| Callback/redirect error | Distinguish Google's `YOUR_ORIGIN/auth/callback` from the exact ChatGPT MCP-client redirect; each belongs in its own allowlist |
| Authentication stops after expiry | Check Google offline consent/refresh, persistent encrypted OAuth state and unchanged signing/encryption keys; reauthorize if appropriate |
| `CLOUD_PROJECT_NOT_APPROVED_FOR_PRODUCTION` | Request production access for the Cloud project owning the OAuth client; test-only access cannot read production advertisers |
| `USER_PERMISSION_DENIED` / wrong customer | Verify the signed-in Google user's Ads access, advertiser ID and optional manager routing; discovery lists direct customers, not every descendant |
| No ADC found in local mode | Use `gcloud auth application-default login` with the correct approved-project Desktop OAuth client; normal gcloud login alone is different |
| Field compatibility error | Inspect v25 resource metadata; not all selectable fields can be combined in one query; live curated GAQL eligibility remains unverified until first authorized API test |
| Report reaches 10,000-row cap | Narrow dates or campaign IDs; curated reports intentionally refuse incomplete analysis |
| No conversions or undefined CPA | Review goals/tracking/lag and traffic relevance; null CPA means division by zero, not zero acquisition cost |
| No competitor domains returned by API | Expected: public auction-insight competitor fields are restricted; use an actual UI CSV export |
| CSV parser rejects header | Export English CSV, remove title/date preambles, keep the real header and `%` signs; retain bounds such as `<10%` |
| Old report missing | Check Google identity/OAuth audience, report deletion, DB path and current deployment customer allowlist |
| Windows permission/storage error | Ensure the service user can access private OAuth/report paths; configure Windows ACLs; do not alter global execution policy |
| SOCKS-proxy startup/network error | If your environment requires a SOCKS proxy, install the optional HTTP client's SOCKS support (`pip install "httpx2[socks]==2.16.0"`) and validate connectivity. Standard runtime does not require SOCKS |
| Old tool list after upgrade | Refresh/review the frozen tool snapshot in ChatGPT's connection/workspace management |

## Tests and release process

Run `python -m pytest -ra`, `python -m pip check`, `python -m black --check -l 80
ads_mcp tests`, and `python -m build`. The standard tests have no real credentials
and do not call Google Ads or an AI model. The HTTP test uses real local ASGI
requests with synthetic OAuth configuration. Test errors never justify disabling
authentication. Optional upstream LLM tests require a model service/key and are
excluded from the default suite.

GitHub Actions definitions provide Linux and Windows Python 3.12 checks but were
not executed here. The release workflow builds review artifacts on manual
invocation; it does not publish to a package registry. Check VALIDATION.md for
actual local results, not workflow intent.
