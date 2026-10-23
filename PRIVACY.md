# PrivacyLens data handling

**Last reviewed:** 2026-10-23

PrivacyLens is a local browser extension and local API. Its default monitoring state is **off**. You must enable monitoring in the extension before it begins retaining new observations in its active tab sessions. Policy discovery and analysis are separately disabled until **policy-fetch consent** is enabled. This project is an experimental heuristic tool; it does not determine legal compliance or prove that a site transmitted personal data.

## Data handled when monitoring is enabled

The extension can observe destination hostnames, top-level initiator hostnames, request category, HTTP method, and event time for browser network requests. It stores request URLs as origins and does not collect URL paths, query strings, request or response bodies, or headers. In the page context it counts localStorage and sessionStorage entries; it does not enumerate keys or read values. It does not inspect cookies. Although permission-related code exists, permissions are not currently ingested into the backend or used to create findings.

The extension sends network observations to `http://127.0.0.1:8000` when that local API is available. The API stores observations and scan sessions in SQLite on the same device. When policy-fetch consent is enabled, the background service may discover a public policy URL, fetch it through the local API, and store cleaned policy text and extracted claims locally. If consent is disabled, it does not automatically discover or analyze a policy, but local network observation remains available. A configurable `PRIVACYLENS_RETENTION_DAYS` setting (90 days by default) removes stale site records during API startup, and the popup's Delete data control removes all records for the current site immediately. Pausing monitoring clears active in-memory tab sessions; it does not delete records already written by the API.

## AI provider behavior

The API defaults to local rule-based extraction and makes no AI provider request. If an operator explicitly sets `PRIVACYLENS_AI_PROVIDER=gemini` and supplies `GEMINI_API_KEY`, policy text that the user allowed the extension to fetch is sent to Google's Gemini service for extraction. Do not enable this mode unless that transfer is acceptable. A backend HTTP error is shown as an analysis error; only an unavailable or timed-out local API uses the local heuristic fallback.

## Deployment boundaries

The API is restricted to loopback and local deployment. Hosted mode fails closed because authentication, user-level authorization, and quotas are not implemented. Do not expose this API to a network. Browser monitoring requires broad site access to observe requests, but collection starts only after the user enables it. SQLite backups, browser profile backups, and operating-system logs are outside the deletion endpoint's control; users must remove those copies separately, and the application avoids logging policy text or browsing payloads.

## What conclusions mean

Tracker categories and risk values are heuristic indicators. A potential disclosure gap means the current rules observed a category of network destination and did not find an explicit matching disclosure among extracted policy claims. It does not establish what data was sent, whether processing was lawful, or whether a site is safe. Absence of a finding is not evidence of compliance.
