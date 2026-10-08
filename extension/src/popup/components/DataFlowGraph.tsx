import React, { useState } from 'react';
import { RequestCategory } from '@shared/types';
import { ArrowRight, Globe, Layers, Server } from 'lucide-react';

interface ThirdPartyNode {
  domain: string;
  category: RequestCategory;
  requestCount: number;
  disclosedInPolicy: boolean;
}

interface DataFlowGraphProps {
  firstParty: string;
  thirdParties: ThirdPartyNode[];
}

export const DataFlowGraph: React.FC<DataFlowGraphProps> = ({ firstParty, thirdParties }) => {
  const [selectedNode, setSelectedNode] = useState<ThirdPartyNode | null>(null);

  const getCategoryColor = (cat: RequestCategory) => {
    switch (cat) {
      case 'advertising':
        return 'text-rose-400 border-rose-500/30 bg-rose-500/10';
      case 'analytics':
        return 'text-sky-400 border-sky-500/30 bg-sky-500/10';
      case 'social':
        return 'text-purple-400 border-purple-500/30 bg-purple-500/10';
      case 'cdn':
        return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10';
      default:
        return 'text-slate-400 border-slate-700 bg-slate-800/40';
    }
  };

  return (
    <div className="glass-panel rounded-xl p-3.5 space-y-3">
      <div className="flex items-center justify-between text-xs font-mono uppercase tracking-wider text-slate-400">
        <span className="flex items-center gap-1.5">
          <Layers className="w-3.5 h-3.5 text-blue-400" />
          Third-Party Data Flow Graph
        </span>
        <span className="text-[10px] text-slate-500">{thirdParties.length} Emitters</span>
      </div>

      {/* Visual node flow representation */}
      <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/70 space-y-3">
        {/* Origin Flow Bar */}
        <div className="flex items-center justify-center gap-2 text-xs font-mono">
          <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 flex items-center gap-1">
            <Globe className="w-3 h-3 text-sky-400" />
            Client Browser
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-slate-500" />
          <span className="px-2 py-1 rounded bg-blue-950/60 border border-blue-800 text-blue-300 font-semibold max-w-[140px] truncate">
            {firstParty}
          </span>
        </div>

        {/* Third Party Destination Nodes */}
        <div className="pt-2 border-t border-slate-800/60">
          <div className="text-[10px] font-mono uppercase text-slate-500 mb-1.5">Outbound Destinations</div>
          <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
            {thirdParties.length === 0 ? (
              <span className="text-xs text-slate-500 py-1">Zero external tracking endpoints observed.</span>
            ) : (
              thirdParties.map((node, i) => (
                <button
                  key={i}
                  onClick={() => setSelectedNode(node)}
                  className={`px-2 py-1 rounded text-[11px] font-mono border transition-all ${getCategoryColor(node.category)} hover:scale-105`}
                >
                  {node.domain}
                </button>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Drilldown inspection panel for selected node */}
      {selectedNode && (
        <div className="p-2.5 rounded-lg bg-slate-900 border border-blue-500/30 text-xs space-y-1 animate-fadeIn">
          <div className="flex items-center justify-between">
            <span className="font-semibold text-white font-mono flex items-center gap-1">
              <Server className="w-3 h-3 text-sky-400" />
              {selectedNode.domain}
            </span>
            <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${getCategoryColor(selectedNode.category)}`}>
              {selectedNode.category}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 font-mono">
            <span>Observed Requests: {selectedNode.requestCount}</span>
            <span>
              Policy Disclosed: {selectedNode.disclosedInPolicy ? (
                <strong className="text-emerald-400">Yes</strong>
              ) : (
                <strong className="text-rose-400">Not Disclosed</strong>
              )}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
