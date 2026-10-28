# Release review

This modified distribution is `google-ads-ai-command-center` 0.1.0.
The provided GitHub workflow builds review artifacts only; it does not upload to
PyPI or inherit an upstream release authorization.

Before release, run the documented pytest, formatting, dependency and build
checks; review security advisories/license obligations and verify Google Ads API
version support. Test real OAuth, token refresh, manager routing and API totals
on an authorized test deployment. Refresh the ChatGPT connection's reviewed tool
snapshot when schemas change. Store secrets only in deployment configuration.
See COMMERCIALIZATION.md for remaining requirements; no marketplace/public
publication was performed as part of this build.
