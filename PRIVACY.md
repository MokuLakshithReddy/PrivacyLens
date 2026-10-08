# PrivacyLens — Privacy Policy

**Effective Date:** October 8, 2026  
**Last Updated:** October 8, 2026  

PrivacyLens is developed with a strict **Zero-PII (Personally Identifiable Information) and Local-First Architecture**. This document outlines our data handling practices and privacy commitments.

---

## 1. Core Principle: We Cannot See Your Data

PrivacyLens does not collect, sell, monetize, or transmit your personal data, credentials, browsing history, or private communications. 

The extension is architected as an **observational security lens**, meaning it inspects privacy metadata locally on your device rather than sending your content to remote servers.

---

## 2. Information Handled by the Extension

### What PrivacyLens Inspects (Metadata Only):
- **Hostnames & Target Domains:** Passive identification of domain names contacted by web pages (e.g., `google-analytics.com`, `doubleclick.net`) to categorize trackers.
- **Cookie & Storage Key Names:** The *names* of cookie keys (e.g., `_ga`, `_fbp`) and approximate byte sizes to assess tracking persistence. **Cookie values, tokens, and payloads are NEVER read or extracted.**
- **Browser Capability Queries:** Detects whether a page queries hardware permissions (Geolocation, Camera, Microphone) to check against declared privacy disclosures.
- **Public Policy Text:** The publicly accessible text of website privacy policies, used to extract declared data handling terms.

### What PrivacyLens NEVER Collects:
- ❌ **No Cookie Values or Session Tokens**
- ❌ **No Request or Response Payloads (POST/PUT bodies)**
- ❌ **No Passwords, Form Inputs, or Keystrokes**
- ❌ **No Personal User Identifiers or Profile Tracking**
- ❌ **No Persistent Browsing History Logs**

---

## 3. Chrome Web Store Permissions Justification

In compliance with the Chrome Web Store Single-Purpose and Least-Privilege policies, PrivacyLens requests only the permissions strictly required for its core functionality:

| Permission | Technical Purpose |
| :--- | :--- |
| `webRequest` | Required for read-only observation of third-party network domain names to detect tracking beacons. PrivacyLens does not block or modify requests. |
| `tabs` | Required to read the host domain of the active tab and identify candidate privacy policy links. |
| `storage` | Used locally via `chrome.storage.session` to cache observations for the active tab during your browsing session. |
| `activeTab` | Grants temporary access to the active tab DOM to scan for privacy policy links when the extension is invoked. |
| `scripting` | Allows programmatic execution of read-only content scripts for policy text extraction. |

---

## 4. Local-First and Edge Processing

By default, PrivacyLens operates in **Autonomous Edge Mode**:
- Mathematical risk calculations and tracker categorizations occur directly inside your browser on your device.
- If you configure a self-hosted or local FastAPI backend (`http://localhost:8000`), observation metadata is processed exclusively through your own local instance.

---

## 5. Third-Party Sharing

PrivacyLens does not share, sell, or rent any information to data brokers, advertising networks, or commercial third parties.

---

## 6. Open Source & Auditability

PrivacyLens is fully open source. Our code, schemas, and processing algorithms are publicly auditable at:  
👉 **[https://github.com/MokuLakshithReddy/PrivacyLens](https://github.com/MokuLakshithReddy/PrivacyLens)**

---

## 7. Contact & Security Inquiries

If you have questions or security inquiries regarding this Privacy Policy:
- **Maintainer:** Moku Lakshith Reddy
- **Repository Issues:** [https://github.com/MokuLakshithReddy/PrivacyLens/issues](https://github.com/MokuLakshithReddy/PrivacyLens/issues)
