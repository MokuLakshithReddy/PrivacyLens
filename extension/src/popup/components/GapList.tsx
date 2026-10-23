import React from 'react';
import { EvidenceFinding, FindingSeverity } from '@shared/types';
import { AlertTriangle, ChevronRight, FileSearch } from 'lucide-react';

interface GapListProps {
  findings: EvidenceFinding[];
  onSelectFinding: (finding: EvidenceFinding) => void;
}

export const GapList: React.FC<GapListProps> = ({ findings, onSelectFinding }) => {
  const getSeverityBadge = (sev: FindingSeverity) => {
    switch (sev) {
      case 'critical':
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
      case 'high':
        return 'text-orange-400 bg-orange-500/10 border-orange-500/20';
      case 'medium':
        return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
      default:
        return 'text-blue-400 bg-blue-500/10 border-blue-500/20';
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400 px-1">
        <span className="flex items-center gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
          Detected Privacy Gaps ({findings.length})
        </span>
        <span className="text-[10px] text-slate-500">Policy vs Reality</span>
      </div>

      {findings.length === 0 ? (
        <div className="glass-panel rounded-xl p-4 text-center">
          <p className="text-xs text-slate-400">No candidate findings were produced from the current inputs. This does not establish that the site is safe or compliant.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {findings.map((f) => (
            <div
              key={f.findingId}
              onClick={() => onSelectFinding(f)}
              className="glass-panel hover:border-blue-500/40 cursor-pointer rounded-xl p-3 transition-all duration-200 group relative overflow-hidden"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-medium ${getSeverityBadge(f.severity)}`}>
                      {f.severity}
                    </span>
                  </div>
                  <h4 className="text-sm font-semibold text-white group-hover:text-sky-300 transition-colors">
                    {f.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {f.rationale}
                  </p>
                </div>

                <div className="flex items-center text-slate-500 group-hover:text-sky-400 transition-colors pt-1">
                  <ChevronRight className="w-4 h-4 transform group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>

              <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-400">
                <span className="flex items-center gap-1 text-slate-400 font-mono text-[10px]">
                  <FileSearch className="w-3 h-3 text-sky-400" />
                  {f.evidence.observedDomains.length} domains • {f.evidence.policyQuotes.length} policy quotes
                </span>
                <span className="text-sky-400 text-[11px] font-medium group-hover:underline">
                  Audit Evidence
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
