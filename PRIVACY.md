# PrivacyLens data handling

**Last reviewed:** 2026-10-23

PrivacyLens is a local browser extension and local API. Its default monitoring state is **off**. You must enable monitoring in the extension before it begins retaining new observations in its active tab sessions. This project is an experimental heuristic tool; it does not determine legal compliance or prove that a site transmitted personal data.

## Data handled when monitoring is enabled

The extension can observe destination hostnames, top-level initiator hostnames, request category, HTTP method, and event time for browser network requests. It stores request URLs as origins and does not collect URL paths, query strings, request or response bodies, or headers. In the page context it counts localStorage and sessionStorage entries; it does not enumerate keys or read values. It does not inspect cookies. Although permission-related code exists, permissions are not currently ingested into the backend or used to create findings.

The extension sends network observations to `http://127.0.0.1:8000` when that local API is available. The API stores observations and scan sessions in SQLite on the same device. Policy analysis can store cleaned policy text and extracted claims in that database. These records currently have no automatic expiry or user-facing delete control. Pausing monitoring clears active in-memory tab sessions; it does not delete records already written by the API.

## AI provider behavior

The API defaults to local rule-based extraction and makes no AI provider request. If an operator explicitly sets `PRIVACYLENS_AI_PROVIDER=gemini` and supplies `GEMINI_API_KEY`, analyzed policy text is sent to Google's Gemini service for extraction. Do not enable this mode unless that transfer is acceptable. The browser extension does not currently invoke policy discovery or analysis automatically.

## Deployment boundaries

The API is restricted to loopback and local deployment. Hosted mode fails closed because authentication, user-level authorization, quotas, and retention controls are not implemented. Do not expose this API to a network. Browser monitoring requires broad site access to observe requests, but collection starts only after the user enables it.

## What conclusions mean

Tracker categories and risk values are heuristic indicators. A potential disclosure gap means the current rules observed a category of network destination and did not find an explicit matching disclosure among extracted policy claims. It does not establish what data was sent, whether processing was lawful, or whether a site is safe. Absence of a finding is not evidence of compliance.
