import React from 'react';
import { RiskTier } from '@shared/types';
import { ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react';

interface ScoreCardProps {
  score: number;
  tier: RiskTier;
  confidence: number;
  domain: string;
}

export const ScoreCard: React.FC<ScoreCardProps> = ({ score, tier, confidence, domain }) => {
  const getTierColor = (t: RiskTier) => {
    switch (t) {
      case 'Very Low':
        return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
      case 'Low':
        return 'text-teal-400 border-teal-500/30 bg-teal-500/10';
      case 'Moderate':
        return 'text-amber-400 border-amber-500/30 bg-amber-500/10';
      case 'High':
        return 'text-orange-400 border-orange-500/30 bg-orange-500/10';
      case 'Critical':
        return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
      default:
        return 'text-blue-400 border-blue-500/30 bg-blue-500/10';
    }
  };

  const getIcon = () => {
    if (score >= 60) return <ShieldAlert className="w-5 h-5 text-rose-400" />;
    if (score >= 40) return <ShieldQuestion className="w-5 h-5 text-amber-400" />;
    return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
  };

  return (
    <div className="glass-panel rounded-xl p-4 relative overflow-hidden">
      {/* Background ambient glow */}
      <div 
        className="absolute -top-10 -right-10 w-28 h-28 rounded-full blur-3xl opacity-20"
        style={{
          background: score > 60 ? '#f43f5e' : score > 35 ? '#f59e0b' : '#10b981'
        }}
      />

      <div className="flex items-start justify-between">
        <div>
          <span className="text-[11px] font-mono tracking-wider uppercase text-slate-400 flex items-center gap-1.5">
            {getIcon()}
            Runtime Risk Assessment
          </span>
          <h2 className="text-lg font-bold text-white tracking-tight mt-0.5 max-w-[240px] truncate" title={domain}>
            {domain}
          </h2>
        </div>

        <div className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${getTierColor(tier)}`}>
          {tier} Risk
        </div>
      </div>

      <div className="mt-4 flex items-baseline justify-between border-t border-slate-800/80 pt-3">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-extrabold text-white font-mono tracking-tight">{score}</span>
          <span className="text-xs text-slate-400 font-mono">/ 100</span>
        </div>

        <div className="text-right">
          <div className="text-[11px] text-slate-400 uppercase font-mono">Evidentiary Confidence</div>
          <div className="text-xs font-semibold text-sky-400 font-mono mt-0.5">
            {(confidence * 100).toFixed(0)}% validated
          </div>
        </div>
      </div>

      {/* Confidence progress indicator */}
      <div className="w-full bg-slate-850 h-1.5 rounded-full overflow-hidden mt-3 bg-slate-800">
        <div 
          className="h-full bg-gradient-to-r from-blue-500 to-sky-400 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(100, confidence * 100)}%` }}
        />
      </div>
    </div>
  );
};
