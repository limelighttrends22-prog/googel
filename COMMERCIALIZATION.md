# Commercial evaluation notes

This is an engineering foundation for a differentiated product, not a complete
hosted SaaS or a guarantee of business results. The demonstrable value is
traceable recommendations, conversion-lag/sample safeguards, honest competitor
access boundaries, explicit scenario math, scoped snapshots and read-only
execution limits. The client AI model can explain results in plain language;
the backend does not contain a proprietary predictive model.

## Licensing and distribution

The supplied upstream source is Apache License 2.0. Its full LICENSE, original
source notices, author attribution and a NOTICE describing modifications are
retained. The package was renamed `google-ads-ai-command-center` version 0.1.0
to identify this modified distribution; original CLI aliases are retained.
Do not imply Google endorsement or ownership of Google's trademarks.

`THIRD_PARTY_NOTICES.md` inventories the exact runtime packages and their
installed license metadata; `THIRD_PARTY_LICENSES/` preserves the installed
license/notice files made available by those distributions. Metadata is an
inventory, not a complete legal review. Before selling or redistributing,
review all applicable license conditions, required notices, Google Ads API
policies/OAuth publishing requirements, OpenAI plugin policies and your own
customer/data agreements. This build has no paid/commercial subscription license
system or enforcement. The license inventory does not include an entitlement
to resell third-party services or use vendor marks.

## Operational costs

Plan for hosting/containers, HTTPS/domain, persistent database/disk, secret
management, optional Redis/Firestore, monitoring/log retention, backups and
support. Google Ads API project access levels and quotas apply; review current
terms rather than assuming unrestricted free operations. Advertising spend
continues to be billed by Google. ChatGPT/model access and any independent
model service can carry separate plan/usage charges. This backend makes no
standalone model API calls and does not require a model API key for core tests.
No zero-cost operation claim is made.

## Required before an agency/public SaaS launch

- Real-account API/OAuth/refresh/ChatGPT acceptance testing, field compatibility,
  numerical reconciliation, Windows and container deployment validation.
- A proper organization/client tenancy model, roles/delegation and account-level
  access policy; current saved-report isolation is per Google identity + audience.
- A central database, audited retention/export/deletion policies, durable jobs,
  ingress rate limits, quotas, metering and billing integration.
- Independently reviewed authentication, secrets/key rotation, data protection,
  threat modelling, incident response and operational monitoring.
- Measured recommendation quality, advertiser feedback and controlled experiments;
  current priorities/thresholds are transparent heuristics, not validated uplift.
- API version/sunset maintenance, dependency security/license review and a verified
  release/update process. Pinned dependencies are reproducible, not perpetually safe.
- Clear customer consent and retention terms for potentially sensitive search
  queries and conversion metadata.

## Deliberately incomplete

No automatic live mutations, authenticated approval/execution workflow, CRM/offline
sales integration, verified qualified-lead scoring, true agency RBAC, subscriptions,
background alerts, causal forecasting, bid-simulator integration, complete PMax
asset intelligence, keyword intent model, or unrestricted live competitor data.
The campaign-status preview supports exact manual review only. A future write
implementation needs approvals bound to exact state/diff with expiry, stale-state
checks, idempotency, least privilege, API validation, audited results and read-back
verification before it can claim safe execution.
