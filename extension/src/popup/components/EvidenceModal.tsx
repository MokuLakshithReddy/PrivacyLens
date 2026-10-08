import React from 'react';
import { EvidenceFinding } from '@shared/types';
import { X, Quote, Network, Key, ShieldAlert } from 'lucide-react';

interface EvidenceModalProps {
  finding: EvidenceFinding | null;
  onClose: () => void;
}

export const EvidenceModal: React.FC<EvidenceModalProps> = ({ finding, onClose }) => {
  if (!finding) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[#0f172a] border border-slate-700/80 rounded-2xl w-full max-h-[90vh] overflow-y-auto p-4 space-y-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-slate-800 pb-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30 font-semibold">
                {finding.severity} Severity
              </span>
              <span className="text-[11px] font-mono text-sky-400">
                Confidence: {(finding.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <h3 className="text-sm font-bold text-white tracking-tight">{finding.title}</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* AI Rationale */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
            Correlation Rationale
          </div>
          <p className="text-xs text-slate-300 bg-slate-900/80 p-3 rounded-xl border border-slate-800 leading-relaxed font-sans">
            {finding.rationale}
          </p>
        </div>

        {/* Policy Citations */}
        <div className="space-y-2">
          <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
            <Quote className="w-3.5 h-3.5 text-sky-400" />
            Declared Policy Citations ({finding.evidence.policyQuotes.length})
          </div>
          {finding.evidence.policyQuotes.length === 0 ? (
            <div className="text-xs text-slate-500 italic p-2.5 rounded-lg bg-slate-900 border border-slate-800/80">
              No matching disclosure clause identified in published policy.
            </div>
          ) : (
            finding.evidence.policyQuotes.map((quote, idx) => (
              <blockquote
                key={idx}
                className="text-xs text-slate-300 italic p-3 rounded-xl bg-slate-900/90 border-l-2 border-sky-400 leading-relaxed"
              >
                "{quote}"
              </blockquote>
            ))
          )}
        </div>

        {/* Observable Signals */}
        <div className="space-y-2">
          <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
            <Network className="w-3.5 h-3.5 text-emerald-400" />
            Runtime Observable Endpoints ({finding.evidence.observedDomains.length})
          </div>
          <div className="flex flex-wrap gap-1.5">
            {finding.evidence.observedDomains.map((dom, idx) => (
              <span
                key={idx}
                className="text-[11px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300"
              >
                {dom}
              </span>
            ))}
          </div>
        </div>

        {/* Storage Keys if applicable */}
        {finding.evidence.observedStorageKeys && finding.evidence.observedStorageKeys.length > 0 && (
          <div className="space-y-2">
            <div className="text-[11px] font-mono uppercase text-slate-400 flex items-center gap-1.5">
              <Key className="w-3.5 h-3.5 text-purple-400" />
              Observable Storage Namespaces
            </div>
            <div className="flex flex-wrap gap-1.5">
              {finding.evidence.observedStorageKeys.map((k, idx) => (
                <span
                  key={idx}
                  className="text-[11px] font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800 text-purple-300"
                >
                  {k}
                </span>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={onClose}
          className="w-full py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-blue-500/20"
        >
          Close Evidence Drilldown
        </button>
      </div>
    </div>
  );
};
