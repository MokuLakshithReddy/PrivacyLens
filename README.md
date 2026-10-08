# PrivacyLens

> **Evidence-Driven Browser Privacy Intelligence: Policy vs. Reality**

PrivacyLens is an evidence-driven browser security and privacy intelligence system. Unlike traditional privacy analyzers that simply feed privacy policy text into an LLM to generate an opaque score, PrivacyLens treats the privacy policy as just **one source of evidence** and cross-references it with **real-time observable browser signals** (network requests, third-party origins, cookie/storage persistence metadata, and browser capability permissions).

---

## The Core Thesis: Policy vs. Reality

| Traditional Policy Analyzers (e.g., Hercule) | PrivacyLens |
| :--- | :--- |
| **Input:** Privacy Policy Text only | **Input:** Privacy Policy + Real-time Browser Signals + Permission Invocations |
| **Engine:** Text Scraper $\rightarrow$ LLM $\rightarrow$ Score | **Engine:** Multi-Layer Evidence Engine $\rightarrow$ Knowledge Graph $\rightarrow$ Deterministic Risk Scorer $\rightarrow$ AI Reasoner |
| **Output:** 0–100 Black-Box LLM Score | **Output:** Deterministic Risk (0–100) + Evidentiary Confidence % + Auditable Gaps |
| **Claim Verification:** Blind trust in policy declarations | **Claim Verification:** Cross-correlation of declared claims vs. observed network traffic |
| **Temporal View:** Static one-off evaluation | **Temporal View:** Historical policy diffing & privacy posture change tracking |
| **Security Posture:** Vulnerable to policy prompt injection | **Security Posture:** Hardened prompt injection defense & deterministic risk invariance |

---

## The 5 Evidence Layers

```
                                  ┌───────────────────────┐
                                  │      Target Site      │
                                  └───────────┬───────────┘
                                              │
         ┌───────────────────┬────────────────┼───────────────────┬───────────────────┐
         ▼                   ▼                ▼                   ▼                   ▼
    [ Layer 1 ]         [ Layer 2 ]      [ Layer 3 ]         [ Layer 4 ]         [ Layer 5 ]
   Policy Intel       Network Traffic  Storage & Cookies     Permissions       Supply Chain
 • Declared Types   • First vs Third  • Cookie Meta Only  • Geolocation     • Third-party graph
 • Disclosed Uses   • Category (Ads,  • Storage Keys &    • Camera / Mic    • Identity resolver
 • Sharing Claims     Analytics, CDN)   Byte lengths      • Notifications   • Data flow supply
 • Retention Period • Domain Cadence  • Lifespan Flags    • Policy Check      chain mapping
         │                   │                │                   │                   │
         └───────────────────┴────────────────┼───────────────────┴───────────────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │   Evidence Engine   │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │  Knowledge Graph    │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │ Deterministic Risk  │
                                   │  & AI Explanation   │
                                   └──────────┬──────────┘
                                              ▼
                                   ┌─────────────────────┐
                                   │  Policy vs Reality  │
                                   │   Gaps & Audits     │
                                   └─────────────────────┘
```

---

## Foundation Documents

Before executing implementation, the project specifications are locked down in three comprehensive documents:

1. **[Product Requirements Document (PRD)](file:///c:/Users/nsrfl/OneDrive/Desktop/privacy_policy/docs/PRD.md)**  
   Defines problem statement, core personas, 5 evidence layers, signature features (Gap Engine, Evidence Graph, Temporal Diff), and MVP boundaries.

2. **[Technical Architecture](file:///c:/Users/nsrfl/OneDrive/Desktop/privacy_policy/docs/technical-architecture.md)**  
   Specifies the Manifest V3 extension, FastAPI service, abstracted `AIProvider` interface, SQLite Knowledge Graph schema, deterministic scoring formula, and API contracts.

3. **[Threat Model & Privacy Architecture](file:///c:/Users/nsrfl/OneDrive/Desktop/privacy_policy/docs/threat-and-privacy-model.md)**  
   Outlines data minimization guarantees (zero PII, zero cookie values, zero request bodies), trust zones, prompt injection defenses, least-privilege permissions, and read-only safety posture.

---

## Phased Implementation Roadmap

- [x] **Phase 1: Browser Foundation & Telemetry:** Chrome MV3 setup, tab detection, policy URL discovery, sanitized network observer.
- [x] **Phase 2: Policy Intelligence Engine:** Clean HTML normalization, heuristic section segmenter, structured claim extraction.
- [x] **Phase 3: Browser Evidence & Storage Inspector:** Key-level cookie/storage inspection, permission listener, metadata batching.
- [x] **Phase 4: Correlation & Gap Detection Engine:** Rules-based matcher for omission gaps, permission divergence, and broad language alerts.
- [x] **Phase 5: Deterministic Risk & Confidence Engine:** Mathematical risk score calculation and independent evidentiary confidence scoring.
- [x] **Phase 6: AI Reasoning & Evidence Auditing:** Abstracted `AIProvider` with prompt-injection defense emitting auditable rationales.
- [x] **Phase 7: Security Console UI:** React + Tailwind popup with risk badges, gap drilldowns, and evidence cards.
- [x] **Phase 8: Advanced Intelligence:** Directed supply-chain data-flow graph, policy versioning, and semantic diffs.
- [x] **Phase 9: Evaluation & Robustness Suite:** Benchmark policy test suite, adversarial injection tests, and precision/recall metrics.

---

## Quickstart Guide

### 1. Start Backend API
```bash
# Set PYTHONPATH and launch FastAPI with hot-reload
$env:PYTHONPATH="backend"
backend\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at: `http://127.0.0.1:8000/docs`

### 2. Run Test Suite & Adversarial Defense Suite
```bash
$env:PYTHONPATH="backend"
backend\.venv\Scripts\pytest.exe backend/tests
```

### 3. Build & Load Chrome Extension
```bash
cd extension
npm.cmd run build
```
1. Open Chrome and navigate to `chrome://extensions`.
2. Enable **Developer mode** (top right toggle).
3. Click **Load unpacked** and select the [`extension/dist`](file:///c:/Users/nsrfl/OneDrive/Desktop/privacy_policy/extension/dist) directory.
4. Pin PrivacyLens and click the extension icon on any active website to view real-time Policy vs. Reality correlation!

