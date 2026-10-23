# PrivacyLens

PrivacyLens is a local research prototype for observing browser network metadata and comparing it with extracted privacy-policy claims. The extension monitoring toggle defaults to off. Its categories, risk indicator, and disclosure-gap candidates are heuristic; they do not establish what data was transmitted, whether a site is safe, or legal compliance.

See [Production Readiness Status](docs/production-readiness-status.md) for the repository analysis, completed work, verification, and release gates. See [Privacy and Data Handling](PRIVACY.md) for what the extension and local API collect, store, and send.

## Current capabilities

- Manifest V3 extension observes request destination origins, initiator hostnames, methods, categories, and timestamps while monitoring is enabled.
- Extension counts localStorage and sessionStorage entries without enumerating keys or reading values. It does not inspect cookies. Counts are not sent to the backend.
- Local FastAPI service ingests bounded, scan-scoped network metadata and stores it in SQLite.
- Policy fetching is a separate popup consent choice. When enabled, the policy API can discover and fetch public policy pages through an SSRF-aware bounded fetcher, parse text, and extract tentative claims using local rules by default. Gemini use requires explicit server configuration and sends policy text to Google.
- Scan sessions are bound to the policy version selected for that scan. Findings include relevant policy excerpts and source offsets where available.
- Stored site data can be deleted from the popup or `DELETE /api/v1/sites/{domain}`. Retention cleanup runs at API startup using `PRIVACYLENS_RETENTION_DAYS` (90 days by default); it is not a continuous scheduler.
- Correlation is limited and conservative. Risk weights are visible, but have not been validated against a labelled corpus. Evidence coverage is an input-presence estimate, not confidence.
- The API only supports local loopback use. Hosted mode is disabled until authentication, authorization, and quotas exist.

Not currently implemented in the active analysis flow: permission-query correlation, storage and cookie persistence analysis, calibrated scoring, comprehensive temporal comparisons, continuous background retention scheduling, and a full browser end-to-end test suite.

## Architecture

- `extension/` — browser extension, popup, service worker, content scripts, and privacy invariant checks.
- `backend/` — FastAPI endpoints, SQLite schema, policy parsing, AI provider boundary, risk and correlation rules.
- `shared/` — shared TypeScript contracts.
- `docs/production-readiness-status.md` — implementation findings and outstanding release gates.

## Local development

Use Python 3.11 or later and Node.js 22. From the repository root, create a Python environment, install dependencies, and run the local API:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r backend\requirements.lock
$env:PYTHONPATH = "backend"
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Build the extension from `extension/`:

```powershell
npm ci
npm test
npm run build
```

Load the resulting extension bundle in Chromium's developer extension page. Review its requested site access and keep monitoring disabled until you choose to enable it.

Monitoring and policy fetching are independent controls. Enabling monitoring does not authorize policy discovery, policy retrieval, local policy storage, or external AI processing. Pausing monitoring does not delete stored data; use the Delete data action for the current site.

The API defaults to local rule-based extraction. To explicitly use Gemini, set `PRIVACYLENS_AI_PROVIDER=gemini` and `GEMINI_API_KEY` in the API environment. This sends analyzed policy text to Google's Gemini service. Do not expose the API beyond loopback; setting `PRIVACYLENS_MODE` to a hosted mode or binding to a non-loopback address causes startup validation to fail.

## Verification

The backend test suite and extension privacy invariant tests are run in CI. See the [implementation status report](docs/production-readiness-status.md) for the checks run in this workspace and what still requires a full browser or release environment.

## License

MIT. See [LICENSE](LICENSE).
