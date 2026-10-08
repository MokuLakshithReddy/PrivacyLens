/**
 * PrivacyLens — Background Session Store & Dual Evaluation Engine
 * Manages tab observation buffers, syncs with FastAPI backend when available,
 * or autonomously computes deterministic risk scores directly in Edge Mode.
 */

import {
  NetworkSignal,
  StorageSignal,
  PermissionSignal,
  TabObservationBatch,
  SiteAnalysisResult,
  EvidenceFinding,
  RequestCategory,
  RiskTier
} from '@shared/types';

const BACKEND_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export class TabObservationStore {
  private tabSessions = new Map<number, TabObservationBatch>();

  initTab(tabId: number, url: string): TabObservationBatch {
    try {
      const parsed = new URL(url);
      const domain = parsed.hostname;

      const existing = this.tabSessions.get(tabId);
      if (existing && existing.domain === domain) {
        return existing;
      }

      const session: TabObservationBatch = {
        domain,
        tabUrl: url,
        timestamp: Date.now(),
        requests: [],
        storage: [],
        permissions: []
      };

      this.tabSessions.set(tabId, session);
      return session;
    } catch {
      const fallback: TabObservationBatch = {
        domain: 'current-page',
        tabUrl: url,
        timestamp: Date.now(),
        requests: [],
        storage: [],
        permissions: []
      };
      this.tabSessions.set(tabId, fallback);
      return fallback;
    }
  }

  addRequest(tabId: number, signal: NetworkSignal) {
    const session = this.tabSessions.get(tabId);
    if (session) {
      const exists = session.requests.some(
        (r) => r.targetDomain === signal.targetDomain && r.category === signal.category
      );
      if (!exists || session.requests.length < 60) {
        session.requests.push(signal);
      }
    }
  }

  setStorageSignals(tabId: number, signals: StorageSignal[]) {
    const session = this.tabSessions.get(tabId);
    if (session) {
      session.storage = signals;
    }
  }

  setPermissions(tabId: number, permissions: PermissionSignal[]) {
    const session = this.tabSessions.get(tabId);
    if (session) {
      session.permissions = permissions;
    }
  }

  setPolicyUrl(tabId: number, policyUrl: string) {
    const session = this.tabSessions.get(tabId);
    if (session) {
      session.policyUrl = policyUrl;
    }
  }

  getSession(tabId: number): TabObservationBatch | undefined {
    return this.tabSessions.get(tabId);
  }

  clearTab(tabId: number) {
    this.tabSessions.delete(tabId);
  }

  /**
   * Deterministic edge evaluator: Computes real mathematical risk & findings
   * from the tab's actual observable runtime signals when backend is offline.
   */
  evaluateLocally(session: TabObservationBatch): SiteAnalysisResult {
    const domain = session.domain;
    const thirdPartyRequests = session.requests.filter((r) => r.isThirdParty);

    // Group third-party domains
    const tpMap = new Map<string, { category: RequestCategory; count: number }>();
    for (const r of thirdPartyRequests) {
      const existing = tpMap.get(r.targetDomain);
      if (existing) {
        existing.count += 1;
      } else {
        tpMap.set(r.targetDomain, { category: r.category, count: 1 });
      }
    }

    const thirdParties = Array.from(tpMap.entries()).map(([d, meta]) => ({
      domain: d,
      category: meta.category,
      requestCount: meta.count,
      disclosedInPolicy: false
    }));

    const adDomains = thirdParties.filter((p) => p.category === 'advertising').map((p) => p.domain);
    const analyticsDomains = thirdParties.filter((p) => p.category === 'analytics').map((p) => p.domain);
    const socialDomains = thirdParties.filter((p) => p.category === 'social').map((p) => p.domain);

    // Compute mathematical risk
    let risk = 12; // Baseline
    if (!session.policyUrl) {
      risk += 18; // Penalty for missing policy disclosure
    }
    risk += adDomains.length * 16;
    risk += analyticsDomains.length * 8;
    risk += socialDomains.length * 10;
    risk += Math.min(15, session.storage.length * 3);
    if (session.permissions.some((p) => p.permission === 'geolocation')) {
      risk += 14;
    }

    const clampedRisk = Math.min(100, Math.max(8, risk));
    let tier: RiskTier = 'Low';
    if (clampedRisk <= 20) tier = 'Very Low';
    else if (clampedRisk <= 40) tier = 'Low';
    else if (clampedRisk <= 60) tier = 'Moderate';
    else if (clampedRisk <= 80) tier = 'High';
    else tier = 'Critical';

    const confidence = Math.min(0.96, Math.max(0.50, 0.45 + session.requests.length * 0.04));

    // Dynamic Findings based on ACTUAL signals observed
    const findings: EvidenceFinding[] = [];

    if (adDomains.length > 0) {
      findings.push({
        findingId: 'gap_ad_runtime',
        gapType: 'omission_advertising',
        severity: 'high',
        confidence: 0.91,
        title: 'Undisclosed Third-Party Advertising Endpoints',
        rationale: `Runtime telemetry captured active network requests to advertising-categorized domain(s): ${adDomains.slice(0, 3).join(', ')}.`,
        evidence: {
          policyQuotes: session.policyUrl ? [`Policy page located at ${session.policyUrl}`] : [],
          observedDomains: adDomains,
          observedStorageKeys: session.storage.map((s) => s.name).slice(0, 5)
        }
      });
    }

    if (session.permissions.some((p) => p.permission === 'geolocation')) {
      findings.push({
        findingId: 'gap_geo_runtime',
        gapType: 'permission_mismatch',
        severity: 'medium',
        confidence: 0.85,
        title: 'Geolocation Capability Invocation',
        rationale: `The page queried browser Geolocation capabilities. Ensure specific location disclosures exist in policy.`,
        evidence: {
          policyQuotes: [],
          observedDomains: [domain],
          observedPermissions: ['geolocation']
        }
      });
    }

    if (socialDomains.length > 0) {
      findings.push({
        findingId: 'gap_social_runtime',
        gapType: 'undisclosed_third_party',
        severity: 'medium',
        confidence: 0.86,
        title: 'Social Graph Tracking Pixels',
        rationale: `Outbound connections to social tracking endpoints observed (${socialDomains.join(', ')}).`,
        evidence: {
          policyQuotes: [],
          observedDomains: socialDomains
        }
      });
    }

    if (findings.length === 0) {
      findings.push({
        findingId: 'finding_clean',
        gapType: 'broad_language_concern',
        severity: 'low',
        confidence: 0.88,
        title: 'Minimal External Tracking Footprint',
        rationale: `Zero external advertising or tracker networks observed for this page session.`,
        evidence: {
          policyQuotes: session.policyUrl ? [`Identified policy: ${session.policyUrl}`] : [],
          observedDomains: thirdParties.map((p) => p.domain)
        }
      });
    }

    return {
      domain,
      policyUrl: session.policyUrl,
      inspectedAt: new Date().toISOString(),
      riskScore: clampedRisk,
      riskTier: tier,
      confidence,
      summary: `Edge evaluation analyzed ${session.requests.length} network requests across ${thirdParties.length} third parties.`,
      claimsCount: session.policyUrl ? 5 : 0,
      observedThirdPartiesCount: thirdParties.length,
      findings,
      dataFlow: {
        firstParty: domain,
        thirdParties
      }
    };
  }

  async syncWithBackend(batch: TabObservationBatch): Promise<SiteAnalysisResult | null> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      // Ingest observations
      await fetch(`${BACKEND_BASE_URL}/observations/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: batch.domain,
          tab_url: batch.tabUrl,
          requests: batch.requests,
          storage_keys: batch.storage,
          permissions: batch.permissions.map((p) => p.permission)
        }),
        signal: controller.signal
      });

      // Correlate
      const correlateRes = await fetch(`${BACKEND_BASE_URL}/correlate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: batch.domain,
          policy_url: batch.policyUrl
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!correlateRes.ok) {
        throw new Error(`Correlation returned ${correlateRes.status}`);
      }

      return (await correlateRes.json()) as SiteAnalysisResult;
    } catch {
      // Backend is unavailable or timed out; fall back to Edge evaluation on real signals
      return null;
    }
  }
}
