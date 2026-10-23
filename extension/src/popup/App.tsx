import React, { useEffect, useState } from 'react';
import { SiteAnalysisResult, EvidenceFinding } from '@shared/types';
import { ScoreCard } from './components/ScoreCard';
import { GapList } from './components/GapList';
import { PolicyObservedMatrix } from './components/PolicyObservedMatrix';
import { DataFlowGraph } from './components/DataFlowGraph';
import { EvidenceModal } from './components/EvidenceModal';
import { Shield, RefreshCw, Radio, Layers, History, Activity, Globe, Compass, Download } from 'lucide-react';

export const App: React.FC = () => {
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'matrix' | 'graph' | 'timeline'>('overview');
  const [analysis, setAnalysis] = useState<SiteAnalysisResult | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<EvidenceFinding | null>(null);
  const [currentDomain, setCurrentDomain] = useState<string>('example.com');
  const [evalMode, setEvalMode] = useState<'backend' | 'edge'>('edge');
  const [isSystemPage, setIsSystemPage] = useState<boolean>(false);
  const [monitoringEnabled, setMonitoringEnabled] = useState<boolean>(false);
  const [policyFetchConsent, setPolicyFetchConsent] = useState<boolean>(false);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [systemPageUrl, setSystemPageUrl] = useState<string>('');

  const runAnalysis = async () => {
    setLoading(true);
    setIsSystemPage(false);

    try {
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        const state = await chrome.storage.local.get({ monitoringEnabled: false, policyFetchConsent: false });
        const enabled = state.monitoringEnabled === true;
        setPolicyFetchConsent(state.policyFetchConsent === true);
        setMonitoringEnabled(enabled);
        if (!enabled) {
          setAnalysis(null);
          setLoading(false);
          return;
        }
      }
      if (typeof chrome !== 'undefined' && chrome.tabs && chrome.tabs.query) {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tab && tab.id) {
          const tabUrl = tab.url || '';

          // Check if user is on an internal browser page (edge://, chrome://, about:)
          const isInternal = !tabUrl ||
            tabUrl.startsWith('edge://') ||
            tabUrl.startsWith('chrome://') ||
            tabUrl.startsWith('chrome-extension://') ||
            tabUrl.startsWith('about:');

          if (isInternal) {
            setIsSystemPage(true);
            setSystemPageUrl(tabUrl || 'New Tab Page');
            setLoading(false);
            return;
          }

          const parsed = new URL(tabUrl);
          setCurrentDomain(parsed.hostname);

          chrome.runtime.sendMessage(
            { type: 'ANALYZE_ACTIVE_TAB', tabId: tab.id },
            (response) => {
              setBackendError(response?.error || null);
              if (response && response.analysis) {
                setAnalysis(response.analysis);
                setEvalMode(response.analysis.evaluationMode);
              } else {
                setAnalysis(null);
              }
              setLoading(false);
            }
          );
          return;
        }
      }
    } catch {
      // Standalone browser test mode
    }

    setAnalysis(null);
    setLoading(false);
  };

  const toggleMonitoring = async () => {
    if (typeof chrome === 'undefined' || !chrome.storage?.local) return;
    const next = !monitoringEnabled;
    await chrome.storage.local.set({ monitoringEnabled: next });
    setMonitoringEnabled(next);
    if (next) {
      await runAnalysis();
    } else {
      setAnalysis(null);
      setLoading(false);
    }
  };

  const togglePolicyFetchConsent = async () => {
    if (typeof chrome === 'undefined' || !chrome.storage?.local) return;
    const next = !policyFetchConsent;
    await chrome.storage.local.set({ policyFetchConsent: next });
    setPolicyFetchConsent(next);
  };

  const exportAuditReport = () => {
    if (!analysis) return;
    const dateStr = new Date(analysis.inspectedAt).toLocaleString();
    const md = `# 🛡️ PrivacyLens Audit Report — ${analysis.domain}

**Inspection Date:** ${dateStr}
**Heuristic risk indicator:** ${analysis.riskScore} / 100 (${analysis.riskTier})
**Evidence coverage estimate:** ${(analysis.evidenceCoverage * 100).toFixed(0)}%
**Discovered Policy URL:** ${analysis.policyUrl || 'None Identified'}

---

## 1. Executive Summary
${analysis.summary}

## 2. Policy vs Reality Gaps Detected (${analysis.findings.length})
${analysis.findings
  .map(
    (f, i) => `### ${i + 1}. [${f.severity.toUpperCase()}] ${f.title}
- **Rationale:** ${f.rationale}
- **Policy Citations:** ${
      f.evidence.policyQuotes.length > 0
        ? f.evidence.policyQuotes.map((q) => `\n  > "${q}"`).join('')
        : 'No disclosure found in published policy.'
    }
- **Observed Domains:** ${f.evidence.observedDomains.join(', ')}
`
  )
  .join('\n')}

## 3. Observed Third-Party Supply Chain (${analysis.dataFlow.thirdParties.length})
| Destination Domain | Category | Observed Requests | Disclosed in Policy |
| :--- | :--- | :---: | :---: |
${analysis.dataFlow.thirdParties
  .map(
    (tp) =>
      `| \`${tp.domain}\` | ${tp.category} | ${tp.requestCount} | ${
        tp.disclosedInPolicy ? 'Yes' : 'No'
      } |`
  )
  .join('\n')}

---
*Report generated automatically by PrivacyLens Browser Security Extension.*
`;

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${analysis.domain.replace(/[^a-z0-9]/gi, '_')}_privacy_audit.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const deleteStoredData = async () => {
    if (!currentDomain || !window.confirm(`Delete all stored PrivacyLens data for ${currentDomain}? This cannot be undone.`)) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/sites/${encodeURIComponent(currentDomain)}`, { method: 'DELETE' });
      if (!response.ok) throw new Error(`Deletion failed (${response.status})`);
      setAnalysis(null);
    } catch {
      window.alert('PrivacyLens could not delete the stored site data. The local API may be unavailable.');
    }
  };

  useEffect(() => {
    runAnalysis();
  }, []);

  return (
    <div className="flex flex-col min-h-[580px] bg-[#090d16] text-slate-100 p-3.5 space-y-3 font-sans">
      {/* Top Console Bar */}
      <header className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-blue-500/10 border border-blue-500/30 text-blue-400">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white flex items-center gap-1.5 font-mono">
              PrivacyLens
              {!isSystemPage && (
                <span className={`text-[10px] font-normal px-1.5 py-0.2 rounded border ${
                  evalMode === 'backend'
                    ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                    : 'text-sky-400 bg-sky-500/10 border-sky-500/20'
                }`}>
                  {evalMode === 'backend' ? 'Backend Live' : 'Edge Mode'}
                </span>
              )}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={toggleMonitoring}
            className={`px-2 py-1 rounded border text-[10px] font-mono ${monitoringEnabled ? 'border-amber-500/40 text-amber-300 bg-amber-500/10' : 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'}`}
            title={monitoringEnabled ? 'Pause local browser monitoring' : 'Enable local browser monitoring'}
          >
            {monitoringEnabled ? 'Pause' : 'Enable'}
          </button>
          <button
            onClick={togglePolicyFetchConsent}
            className={`px-2 py-1 rounded border text-[10px] font-mono ${policyFetchConsent ? 'border-blue-500/40 text-blue-300 bg-blue-500/10' : 'border-slate-600 text-slate-300 bg-slate-800/50'}`}
            title="Allow fetching and local storage of public policy text"
          >
            Policy {policyFetchConsent ? 'On' : 'Off'}
          </button>
          <button
          onClick={runAnalysis}
          disabled={loading || !monitoringEnabled}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Refresh runtime signals"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-blue-400' : ''}`} />
          </button>
          <button
            onClick={deleteStoredData}
            className="px-2 py-1 rounded border border-rose-500/40 text-rose-300 bg-rose-500/10 text-[10px] font-mono"
            title="Delete stored data for this site"
          >
            Delete data
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex-1 flex flex-col items-center justify-center p-8 space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
          <p className="text-xs font-mono text-slate-400 tracking-wide text-center">
            Correlating declared policy with runtime telemetry for {currentDomain}...
          </p>
        </div>
      ) : !monitoringEnabled ? (
        <div className="flex-1 flex flex-col justify-center rounded-2xl p-5 space-y-3 my-auto border border-slate-700 bg-slate-900/70">
          <h2 className="text-sm font-semibold text-white">Monitoring is paused</h2>
          <p className="text-xs text-slate-300 leading-relaxed">Enable monitoring to collect the current page’s destination origins, request methods and times, plus counts of local and session storage items. PrivacyLens does not read storage keys, storage values, cookies, or request bodies.</p>
          <p className="text-[11px] text-slate-400">Monitoring and policy fetching are separate choices. If enabled, a public policy page may be fetched and its cleaned text and extracted claims stored locally. If Gemini is explicitly configured, policy text is sent to Google. Pausing monitoring does not delete stored data; use the site delete control when available.</p>
          <button onClick={toggleMonitoring} className="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold">Enable local monitoring</button>
        </div>
      ) : isSystemPage ? (
        <div className="flex-1 flex flex-col justify-center glass-panel rounded-2xl p-5 space-y-4 my-auto border border-blue-500/20">
          <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center mx-auto text-blue-400 shadow-lg shadow-blue-500/10">
            <Compass className="w-6 h-6 text-sky-400" />
          </div>

          <div className="text-center space-y-1.5">
            <h3 className="text-sm font-bold text-white tracking-tight">
              Browser System Page Detected
            </h3>
            <div className="text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2 py-1 rounded inline-block border border-slate-800">
              {systemPageUrl}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed pt-1">
              Chromium security policy strictly restricts browser extensions from inspecting internal system and start pages.
            </p>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-2 text-xs">
            <div className="font-semibold text-slate-200 flex items-center gap-1.5 text-[11px]">
              <Globe className="w-3.5 h-3.5 text-sky-400" />
              How to inspect with PrivacyLens:
            </div>
            <ol className="list-decimal list-inside text-slate-400 space-y-1 text-[11px] leading-relaxed">
              <li>Type any live URL in your address bar (e.g. <span className="text-sky-300 font-mono">msn.com</span>, <span className="text-sky-300 font-mono">wikipedia.org</span>, or <span className="text-sky-300 font-mono">nytimes.com</span>).</li>
              <li>Wait for the page to finish loading.</li>
              <li>Click the PrivacyLens extension icon to view its real-time tracking footprint and policy correlation.</li>
            </ol>
          </div>
        </div>
      ) : backendError ? (
        <div className="flex-1 flex flex-col justify-center gap-2 p-6">
          <p className="text-sm font-semibold text-rose-300">Backend analysis failed</p>
          <p className="text-xs text-slate-400">{backendError}</p>
          <p className="text-[11px] text-slate-500">The observed scan was not silently replaced with a partial backend result. You can retry or continue with local monitoring.</p>
        </div>
      ) : analysis ? (
        <div className="space-y-3">
          {/* Executive Score Card */}
          <ScoreCard
            score={analysis.riskScore}
            tier={analysis.riskTier}
            evidenceCoverage={analysis.evidenceCoverage}
            riskFactors={analysis.riskFactors}
            riskWeights={analysis.riskWeights}
            domain={analysis.domain || currentDomain}
          />

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800/80 text-[11px] font-mono">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1 ${
                activeTab === 'overview'
                  ? 'bg-blue-600 text-white font-medium shadow-md shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Radio className="w-3 h-3" />
              Gaps ({analysis.findings.length})
            </button>
            <button
              onClick={() => setActiveTab('matrix')}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1 ${
                activeTab === 'matrix'
                  ? 'bg-blue-600 text-white font-medium shadow-md shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Matrix
            </button>
            <button
              onClick={() => setActiveTab('graph')}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1 ${
                activeTab === 'graph'
                  ? 'bg-blue-600 text-white font-medium shadow-md shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3 h-3" />
              Data Flow
            </button>
            <button
              onClick={() => setActiveTab('timeline')}
              className={`flex-1 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1 ${
                activeTab === 'timeline'
                  ? 'bg-blue-600 text-white font-medium shadow-md shadow-blue-600/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <History className="w-3 h-3" />
              History
            </button>
          </div>

          {/* Tab Views */}
          {activeTab === 'overview' && (
            <GapList
              findings={analysis.findings}
              onSelectFinding={(f) => setSelectedFinding(f)}
            />
          )}

          {activeTab === 'matrix' && (
            <PolicyObservedMatrix
              rows={(['advertising', 'analytics', 'social'] as const).map((category) => {
                const observed = analysis.dataFlow.thirdParties.filter((p) => p.category === category);
                return {
                  category: category[0].toUpperCase() + category.slice(1),
                  declared: false,
                  declarationSummary: 'Policy claims are not available in this view',
                  observedCount: observed.length,
                  observedDetail: `${observed.length} observed destination(s)`,
                  status: 'unverified' as const
                };
              })}
            />
          )}

          {activeTab === 'graph' && (
            <DataFlowGraph
              firstParty={analysis.domain || currentDomain}
              thirdParties={analysis.dataFlow.thirdParties}
            />
          )}

          {activeTab === 'timeline' && (
            <div className="glass-panel rounded-xl p-3.5 space-y-2.5">
              <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400">
                <span>Current Scan</span>
                <span className="text-sky-400 text-[10px]">Session only</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-slate-200">Heuristic risk indicator</div>
                  <div className="text-[10px] text-slate-400 font-mono">No historical baseline available</div>
                </div>
                <div className="text-right">
                  <span className="font-mono font-bold text-sky-400">{analysis.riskScore}</span>
                  <span className="text-[10px] text-slate-400"> / 100</span>
                </div>
              </div>
              <div className="p-2 rounded bg-slate-800/50 border border-slate-700/50 text-[11px] text-slate-300 flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                <span>Observed {analysis.observedThirdPartiesCount} third-party destination(s) in this scan session.</span>
              </div>
            </div>
          )}

          {/* Export Report Action */}
          <div className="pt-2 border-t border-slate-800/80">
            <button
              onClick={exportAuditReport}
              className="w-full py-2 px-3 rounded-xl bg-slate-900 hover:bg-slate-850 hover:border-sky-500/40 border border-slate-800 text-sky-400 hover:text-sky-300 font-mono text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm group"
            >
              <Download className="w-3.5 h-3.5 text-sky-400 group-hover:translate-y-0.5 transition-transform" />
              Export Evidence Audit Report (.md)
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-2">
          <Activity className="w-7 h-7 text-slate-500" />
          <h2 className="text-sm font-semibold text-slate-200">No scan evidence available</h2>
          <p className="text-xs text-slate-400">Enable monitoring and refresh to inspect the current browser session. The extension uses the local API when available; otherwise it shows local network heuristics only. No sample results are shown as live findings.</p>
        </div>
      )}

      {/* Evidentiary Audit Modal */}
      <EvidenceModal
        finding={selectedFinding}
        onClose={() => setSelectedFinding(null)}
      />
    </div>
  );
};
