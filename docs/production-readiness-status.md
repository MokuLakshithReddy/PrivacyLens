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
- Added scan-session identifiers and event deduplication; correlations now use observations from one scan and the newest extracted policy version. The enabled extension flow discovers/analyzes a policy through the local API before correlation, and unchanged policy text reuses its stored version. Findings carry session, policy, rule, and event provenance.
- Removed unsupported synthetic edge findings and fabricated history/matrix values. Unavailable policy declarations are shown as unknown; no baseline is invented.
- Replaced confidence claims with heuristic risk factors and an explicitly estimated evidence-coverage value. The output is not a calibrated probability or compliance determination.
- Restricted API deployment to loopback; disabled hosted mode until authentication, authorization, and quotas exist. Tightened CORS, request size, schema validation, and provider defaults. Gemini is opt-in.
- Added bounded policy retrieval with public-address DNS checks, redirect revalidation, content-type and response-size limits, timeouts, and sanitized stored policy URLs.
- Added isolated test databases, Python and extension invariant checks, a pinned backend dependency set, CI build/test jobs, and dependency/secret scans.
- Rewrote `PRIVACY.md` to reflect current collection, storage, and provider behavior.

## Verification performed

- Backend Python compilation: passed.
- Backend test suite: 18 passed.
- Extension privacy invariant tests: 3 passed.
- Full extension TypeScript/Vite build: not run in this environment because the JavaScript dependencies are not installed and the available package-manager path cannot create its dependency links. CI is configured to run `npm ci` and `npm run build` on Ubuntu.
- Browser end-to-end tests: not present or run.

## Remaining release gates

1. Use a complete Public Suffix List implementation for registrable-domain and same-site boundaries. The current bundled suffix rules are partial and can misclassify uncommon suffixes.
2. Add retention limits and an API/UI deletion workflow for stored scans, policies, claims, and findings. Pause is not deletion.
3. Complete a real browser install/build and end-to-end review of permission prompts, monitoring toggle, lifecycle, navigation, and privacy controls.
4. Add an explicit policy-fetch consent step before enabling automatic policy discovery, plus clearer status when discovery or analysis fails; the current opt-in explains local storage and configured Gemini transfer.
5. Validate taxonomy, risk factors, thresholds, and disclosure-gap rules against a labelled evaluation corpus. Current coverage and risk values are estimates and heuristics only.
6. Replace additive SQLite migrations with a tested versioned migration strategy, including cleanup of legacy confidence columns and explicit handling of pre-existing data.
7. Add API authentication, per-user authorization, rate limits, and quotas before any hosted or multi-user deployment. Hosted mode is deliberately blocked.
8. Add request throttling/concurrency limits, operational logging/monitoring that avoids sensitive content, accessibility review, and a release security review.
9. Review the broad browser host permissions and store listing/privacy disclosures against current extension-store requirements before distribution.

Until these gates are addressed, describe PrivacyLens as a local research prototype and do not publish its heuristic score as a safety or legal-compliance rating.
