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

export class BackendSyncError extends Error {
  readonly kind = 'backend_error';

  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = 'BackendSyncError';
  }
}

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
        scanSessionId: crypto.randomUUID(),
        tabUrl: parsed.origin,
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
        scanSessionId: crypto.randomUUID(),
        tabUrl: 'about:blank',
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
      const duplicateEvent = signal.requestId !== undefined &&
        session.requests.some((r) => r.requestId === signal.requestId);
      if (duplicateEvent) return;
      if (session.requests.length < 200) {
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

  clearAll() {
    this.tabSessions.clear();
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

    // Explainable local heuristic factors; no policy has been fetched or extracted here.
    const uniqueThirdPartyDomains = new Set(thirdPartyRequests.map((r) => r.targetDomain));
    const uniqueAdDomains = new Set(thirdPartyRequests.filter((r) => r.category === 'advertising').map((r) => r.targetDomain));
    const uniqueAnalyticsDomains = new Set(thirdPartyRequests.filter((r) => r.category === 'analytics').map((r) => r.targetDomain));
    const riskFactors = {
      collection: 0,
      sharing: 0,
      retention: 75,
      tracking: Math.min(100, uniqueThirdPartyDomains.size * 12 + uniqueAdDomains.size * 15 + uniqueAnalyticsDomains.size * 8),
      gap_candidates: 0,
      transparency: 80
    };
    const riskWeights = { collection: 0.15, sharing: 0.20, retention: 0.10, tracking: 0.25, gap_candidates: 0.25, transparency: 0.05 };
    const riskScore = Math.max(0, Math.min(100, Math.round(Object.entries(riskFactors).reduce((sum, [name, value]) => sum + value * riskWeights[name as keyof typeof riskWeights], 0))));
    const tier: RiskTier = riskScore <= 20 ? 'Very Low' : riskScore <= 40 ? 'Low' :
      riskScore <= 60 ? 'Moderate' : riskScore <= 80 ? 'High' : 'Critical';
    const knownCategories = new Set<RequestCategory>(['analytics', 'advertising', 'social', 'cdn', 'essential', 'telemetry']);
    const distinctDomains = new Set(session.requests.map((r) => r.targetDomain));
    const classifiedDomains = new Set(session.requests.filter((r) => knownCategories.has(r.category)).map((r) => r.targetDomain));
    const evidenceCoverage = Math.round((Math.min(1, session.requests.length / 15) * 0.35 +
      (distinctDomains.size ? classifiedDomains.size / distinctDomains.size : 0) * 0.25) * 100) / 100;
    const findings: EvidenceFinding[] = [];

    return {
      domain,
      policyUrl: session.policyUrl,
      inspectedAt: new Date().toISOString(),
      riskScore,
      riskTier: tier,
      evidenceCoverage,
      riskFactors,
      riskWeights,
      algorithmVersion: 'risk-v2',
      evaluationMode: 'edge',
      summary: `Local heuristic evaluation analyzed ${session.requests.length} observed requests across ${thirdParties.length} external destinations. Findings depend on browser coverage and domain rules; no finding is not a safety or compliance assessment.`,
      claimsCount: 0,
      observedThirdPartiesCount: thirdParties.length,
      findings,
      dataFlow: {
        firstParty: domain,
        thirdParties
      }
    };
  }

  async syncWithBackend(batch: TabObservationBatch): Promise<SiteAnalysisResult | null> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60_000);
    try {
      // Ingest observations
      const ingestRes = await fetch(`${BACKEND_BASE_URL}/observations/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: batch.domain,
          scan_session_id: batch.scanSessionId,
          requests: batch.requests
        }),
        signal: controller.signal
      });
      if (!ingestRes.ok) {
        throw new BackendSyncError(`Observation ingestion failed (${ingestRes.status})`, ingestRes.status);
      }

      const consent = await chrome.storage.local.get({ policyFetchConsent: false });
      const policyFetchAllowed = consent.policyFetchConsent === true;
      // Policy discovery and retrieval are separate from network monitoring consent.
      let policyUrl = batch.policyUrl;
      if (policyFetchAllowed && !policyUrl) {
        const discoveryRes = await fetch(`${BACKEND_BASE_URL}/policies/discover`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: `https://${batch.domain}` }),
          signal: controller.signal
        });
        if (discoveryRes.ok) {
          const discovery = await discoveryRes.json();
          if (discovery.discovered && typeof discovery.policy_url === 'string') policyUrl = discovery.policy_url;
        }
      }
      if (policyFetchAllowed && policyUrl) {
        const analysisRes = await fetch(`${BACKEND_BASE_URL}/policies/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            domain: batch.domain,
            policy_url: policyUrl,
            scan_session_id: batch.scanSessionId
          }),
          signal: controller.signal
        });
        if (!analysisRes.ok) throw new BackendSyncError(`Policy analysis returned ${analysisRes.status}`, analysisRes.status);
      }

      // Correlate this policy version with this scan session.
      const correlateRes = await fetch(`${BACKEND_BASE_URL}/correlate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: batch.domain,
          scan_session_id: batch.scanSessionId,
          policy_url: policyUrl ? new URL(policyUrl).origin : undefined
        }),
        signal: controller.signal
      });

      if (!correlateRes.ok) {
        throw new BackendSyncError(`Correlation returned ${correlateRes.status}`, correlateRes.status);
      }

      return (await correlateRes.json()) as SiteAnalysisResult;
    } catch (error) {
      if (error instanceof BackendSyncError) throw error;
      // Network and timeout failures mean the local evaluator can be used safely.
      return null;
    } finally {
      clearTimeout(timeoutId);
    }
  }
}
