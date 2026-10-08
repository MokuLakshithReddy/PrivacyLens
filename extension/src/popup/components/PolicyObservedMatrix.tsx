import React from 'react';
import { CheckCircle2, AlertCircle, HelpCircle } from 'lucide-react';

interface MatrixRow {
  category: string;
  declared: boolean;
  declarationSummary: string;
  observedCount: number;
  observedDetail: string;
  status: 'aligned' | 'gap' | 'unverified';
}

interface PolicyObservedMatrixProps {
  rows: MatrixRow[];
}

export const PolicyObservedMatrix: React.FC<PolicyObservedMatrixProps> = ({ rows }) => {
  return (
    <div className="glass-panel rounded-xl p-3.5 space-y-2.5">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400">
        <span>Policy vs Observed Matrix</span>
        <span className="text-[10px] text-slate-500">Cross-Verification</span>
      </div>

      <div className="divide-y divide-slate-800/80">
        {rows.map((row, idx) => (
          <div key={idx} className="py-2 first:pt-0 last:pb-0 flex items-center justify-between gap-3 text-xs">
            <div className="space-y-0.5">
              <div className="font-medium text-slate-200">{row.category}</div>
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <span className="font-mono text-slate-400">Declared: {row.declarationSummary}</span>
                <span>•</span>
                <span className="font-mono text-slate-400">Observed: {row.observedDetail}</span>
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0 font-mono text-[11px]">
              {row.status === 'aligned' ? (
                <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  Aligned
                </span>
              ) : row.status === 'gap' ? (
                <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                  <AlertCircle className="w-3 h-3" />
                  Gap
                </span>
              ) : (
                <span className="flex items-center gap-1 text-slate-400 bg-slate-800/50 px-2 py-0.5 rounded border border-slate-700/30">
                  <HelpCircle className="w-3 h-3" />
                  Unknown
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
