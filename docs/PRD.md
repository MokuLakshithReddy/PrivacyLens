# PrivacyLens — Product Requirements Document (PRD)

**Version:** 1.0.0  
**Status:** Approved Specification  
**System Thesis:** Evidence-driven browser privacy intelligence comparing declared privacy claims with real-time observable browser signals.

---

## 1. Executive Summary & Problem Statement

Current automated privacy analysis tools (such as Hercule) rely on a unidirectional pipeline:
$$\text{Privacy Policy URL} \longrightarrow \text{Text Scraper} \longrightarrow \text{LLM Evaluation} \longrightarrow \text{0–100 Score}$$

While effective at identifying textual red flags and reading lengthy legal disclosures, this approach suffers from fundamental limitations:
1. **Blind Trust in Policy Statements:** A website with a thoroughly drafted, compliant privacy policy can receive a stellar privacy score even if its real-time runtime behavior emits dozens of unlisted third-party tracking beacons and device fingerprints.
2. **False Legal Accusations:** Naive LLM summarizers frequently hallucinate legal non-compliance without verifiable evidence or evidentiary tracing.
3. **Black-Box Scoring:** Scores are generated through opaque LLM completions without deterministic mathematical backing or clear separation of **Risk** vs. **Confidence**.
4. **Static Snapshot Mentality:** Privacy postures change dynamically across revisions and site updates without temporal tracking.

### The PrivacyLens Solution
PrivacyLens shifts the paradigm from **"Policy Summarization"** to **"Multi-Layer Evidence Correlation (Policy vs. Reality)"**. The policy is treated merely as one source of evidence, which is cross-referenced against observable browser runtime behaviors (network requests, third-party origins, cookie/storage persistence metadata, and permission triggers).

```
                 ┌────────────────────────────────────────────────────────┐
                 │                        WEBSITE                         │
                 └───────┬───────────────────┬────────────────────┬───────┘
                         │                   │                    │
                         ▼                   ▼                    ▼
                ┌─────────────────┐ ┌─────────────────┐  ┌─────────────────┐
                │ Privacy Policy  │ │ Browser Signals │  │  Permissions    │
                └────────┬────────┘ └────────┬────────┘  └────────┬────────┘
                         │                   │                    │
                         ▼                   ▼                    ▼
                ┌─────────────────┐ ┌─────────────────┐  ┌─────────────────┐
                │ Policy Claims   │ │ Trackers/Origins│  │ Requested APIs  │
                │ (Structured)    │ │ Storage Meta    │  │ (Geo, Mic, etc) │
                └────────┬────────┘ └────────┬────────┘  └────────┬────────┘
                         └───────────────────┼────────────────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │   Evidence Engine    │
                                  └──────────┬───────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │Privacy KnowledgeGraph│
                                  └──────────┬───────────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │ Deterministic Risk & │
                                  │   AI Reasoner        │
                                  └──────────┬───────────┘
                                             │
                         ┌───────────────────┴────────────────────┐
                         ▼                                        ▼
               ┌───────────────────┐                    ┌───────────────────┐
               │ Policy vs Reality │                    │ Temporal Diff &   │
               │ Gaps + Evidence   │                    │ Audit Timeline    │
               └───────────────────┘                    └───────────────────┘
```

---

## 2. Core Personas & Use Cases

1. **Privacy-Conscious End User:** Wants to know immediately if a website's observed tracking footprint aligns with its claims, without wading through pages of legal legalese or trusting arbitrary scorecards.
2. **Security & Privacy Researcher / Auditor:** Requires reproducible, evidence-backed privacy claims linked to specific policy text spans and observable network telemetry.
3. **Developer / Compliance Engineer:** Needs an objective diff between what their product declares in its privacy policy and what third-party SDKs actually emit in the browser.

---

## 3. Product Principles

1. **Evidence-First, Not Accusatory:** PrivacyLens never states "This site violates GDPR/CCPA." It states "Candidate Gap Detected: Third-party advertising endpoints observed without matching specific disclosure (Confidence: 84%)."
2. **Strict Metadata Only (Zero Private Payload Extraction):** No cookie values, query parameter values with PII, form inputs, or response bodies are collected.
3. **Separation of Risk and Confidence:** A finding can carry High Risk with Low Confidence (an unknown external beacon), or Moderate Risk with High Confidence (explicitly declared ad-tech sharing).
4. **Deterministic Foundation, Explanatory AI:** Mathematical formulas compute risk baselines; LLMs reason across structured graph entities to generate human-readable explanations and auditable citations.
5. **Untrusted Page Content Guardrail:** All webpage inputs are treated as untrusted text within hard delimitations to prevent prompt injection attacks.
6. **Read-Only Browser Posture:** The initial system observes, analyzes, and explains; it does not block, modify DOM, or alter network traffic.

---

## 4. The 5 Evidence Layers

### Layer 1: Policy Intelligence (Declared Practices)
Transforms unstructured policy text into typed, verifiable claims:
- **Data Categories Collected:** Email, IP address, Device ID, Geolocation, Biometrics, Financial info, Usage logs.
- **Purposes of Processing:** Core service, Analytics, Targeted advertising, Security/fraud prevention, Service enhancement.
- **Third-Party Disclosures:** Affiliates, Service providers, Advertising networks, Data brokers.
- **Retention & Rights:** Explicit retention period declared (true/false), deletion mechanisms, opt-out mechanisms, cross-border transfers.
- **Source Grounding:** Every extracted claim must reference a verified text span, heading section, and policy URL.

### Layer 2: Network Traffic Telemetry (Observable Communications)
Observes HTTP request metadata initiated by the tab:
- Origin vs. Target domain categorization (First-party vs. Third-party).
- Domain classification (Analytics, Advertising, Social Tracker, CDN, Identity Provider, Unknown).
- Volume, cadence, and timing of outbound telemetry.

### Layer 3: Storage & Cookie Intelligence (Observable Persistence)
Monitors browser state storage without inspecting private value payloads:
- Cookie classification: First-party vs. Third-party, Session vs. Persistent, Security flags (Secure, HttpOnly, SameSite).
- Storage footprint: LocalStorage / SessionStorage / IndexedDB key namespaces (e.g., `_ga`, `_fbp`, `amplitude_id`).

### Layer 4: Permission & Device API Intelligence (Observable Hardware Access)
Detects browser capability queries:
- Requested APIs: Geolocation, Camera, Microphone, Notifications, Clipboard, MIDI.
- Correlation check: Does the policy disclose collection of data corresponding to the requested hardware/browser capabilities?

### Layer 5: Third-Party Ecosystem Mapping (Observable Supply Chain)
Constructs a directed data flow:
$$\text{User} \longrightarrow \text{Current Site} \longrightarrow \{\text{Analytics Domain}, \text{Ad-Exchange Domain}, \text{Social Graph}\}$$
Maps external entities to their parent organization (e.g., `doubleclick.net` $\rightarrow$ Google LLC).

---

## 5. Signature Features

### 5.1. Policy vs. Reality Gap Engine
Cross-evaluates Layer 1 against Layers 2–5 to flag four distinct gap archetypes:
1. **Omission Gap:** Third-party tracking or advertising endpoints active at runtime with zero identifiable disclosure in the policy.
2. **Breadth / Ambiguity Gap:** Policy uses vague terms ("may collect standard data for improvement") while observing intense tracking ecosystems (fingerprinting scripts, multiple ad networks).
3. **Retention & Transfer Divergence:** Observed servers operate in foreign jurisdictions without international transfer disclosure.
4. **Permission Disconnect:** Geolocation or Notification API requested without corresponding policy disclosure.

### 5.2. Auditable Evidence Graph & Drilldown
Every finding displayed in the UI maps directly to an Evidence Card containing:
- Specific policy citation (clause, section, exact quote).
- Observable network/storage events (timestamp, target domain, classification).
- Rationale for alignment/misalignment.
- Confidence score (0–100%) and Severity rating (Low, Medium, High, Critical).

### 5.3. Temporal Privacy Posture & Semantic Diff
- Retains timestamped snapshots of site policies and observed behaviors.
- Calculates **Semantic Diff**: Not just text changes, but shifts in claimed rights (e.g., addition of "advertising partners", removal of opt-out links) correlated with changes in observed tracker count.
- Timeline of Privacy Posture score over time.

---

## 6. Scope & Roadmap Phases

### Phase 1: MVP (In Scope for v1)
- **Extension (MV3):** Tab URL detection, policy link discovery, policy text extraction, network metadata capture (initiator, target domain, third-party flag), storage key metadata capture, permission tracking.
- **Backend (FastAPI):**
  - Section classifier & structured claim extractor (Gemini / abstract provider).
  - Observation ingest & normalized storage (SQLite).
  - Deterministic Risk Engine + Confidence scorer.
  - Correlation Engine (Policy vs. Reality Gaps).
  - Evidence API & findings generator.
- **UI (Extension Popup):**
  - Executive score card (Risk level + Confidence %).
  - Gap candidate list with evidence drilldown.
  - Policy vs. Observed summary table.

### Phase 2: Enhanced Ecosystem & Visualizations (v2)
- Interactive Directed Data-Flow Graph (User $\rightarrow$ Site $\rightarrow$ Third Parties).
- Domain identity resolution (parent organization mapping).
- Semantic Policy Diff & Temporal Privacy Timeline.

### Phase 3: Privacy & Deployment Maturity (v3+)
- Hybrid AI / Local LLM inference (WebGPU or on-device model for local text extraction).
- Cross-site tracker correlation (trackers following user across sessions).
- Automated regression test suite against benchmark policy datasets.

### Non-Goals (Explicitly Out of Scope)
- Automatic ad-blocking or tracker blocking (Must remain strictly an observational, auditable lens).
- Automated legal compliance certifications (GDPR/CCPA legal certification).
- Deep inspection of encrypted request bodies or user session variables.
- Multi-tenant enterprise SaaS infrastructure, billing, or accounts in initial stages.
