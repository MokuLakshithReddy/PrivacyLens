# Production readiness implementation status

This report compares the repository with the attached Production Readiness Implementation Plan and documents what is implemented in this working copy. The repository is still a local-use prototype; these changes do not make it ready for a public hosted service or browser-store release.

## Repository architecture

- `extension/`: Manifest V3 browser extension, React popup, background service worker, content scripts, passive request observation, and local fallback scoring.
- `backend/`: FastAPI service, SQLite storage, policy parsing/extraction, scan-scoped observation ingest, correlation, and deterministic heuristic scoring.
- `shared/`: TypeScript contracts shared by the extension layers.
- `docs/`: original product and design material. Some original architecture claims described planned features rather than working code.

## Work completed

- Made monitoring explicitly opt-in and gated extension observation and analysis on the setting.
- Reduced browser telemetry: request URLs are origins only; local/session storage is counted without key enumeration or value reads; cookie inspection was removed. Storage metadata is no longer sent to the API.
- Added scan-session identifiers and event deduplication; correlations use the exact policy version linked to each scan. The enabled extension flow discovers/analyzes a policy through the local API before correlation, and unchanged policy text reuses its stored version. Findings carry session, policy, rule, event, quote, and source-location provenance.
- Removed unsupported synthetic edge findings and fabricated history/matrix values. Unavailable policy declarations are shown as unknown; no baseline is invented.
- Replaced confidence claims with heuristic risk factors and an explicitly estimated evidence-coverage value. The output is not a calibrated probability or compliance determination.
- Restricted API deployment to loopback; disabled hosted mode until authentication, authorization, and quotas exist. Tightened CORS, request size, schema validation, and provider defaults. Gemini is opt-in.
- Added bounded policy retrieval with public-address DNS checks, redirect revalidation, content-type and response-size limits, timeouts, and sanitized stored policy URLs.
- Added isolated test databases, Python and extension invariant checks, a pinned backend dependency set, CI build/test jobs, and dependency/secret scans.
- Added explicit policy-fetch consent, startup-triggered retention cleanup, site deletion controls, maintained Public Suffix List classification, and explicit backend-error versus offline-fallback handling.
- Rewrote `PRIVACY.md` to reflect current collection, storage, and provider behavior.

## Verification performed

- Backend Python compilation: passed.
- Backend test suite: 23 passed.
- Extension TypeScript/Vite production build: passed.
- Extension privacy invariant tests: 7 passed.
- GitHub Actions run `40003937749` for commit `03eaad3` completed successfully; backend, extension, and security jobs passed.
- Browser end-to-end tests: not present or run.

## Remaining release gates

1. Complete a real browser install and end-to-end review of permission prompts, consent changes, monitoring lifecycle, navigation, backend errors, and deletion controls.
2. Validate taxonomy, risk factors, thresholds, and disclosure-gap rules against a labelled evaluation corpus. Current coverage and risk values are estimates and heuristics only.
3. Replace additive SQLite migrations with a tested versioned migration strategy, including cleanup of legacy confidence columns and explicit handling of pre-existing data.
4. Add API authentication, per-user authorization, rate limits, and quotas before any hosted or multi-user deployment. Hosted mode is deliberately blocked.
5. Add request throttling/concurrency limits, operational logging/monitoring that avoids sensitive content, accessibility review, and a release security review.
6. Review the broad browser host permissions and store listing/privacy disclosures against current extension-store requirements before distribution.

Until these gates are addressed, describe PrivacyLens as a local research prototype and do not publish its heuristic score as a safety or legal-compliance rating.
