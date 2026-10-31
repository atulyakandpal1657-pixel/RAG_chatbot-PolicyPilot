"use client";

import { FileText, X, CheckCircle, ExternalLink, Bookmark } from "lucide-react";

export interface CitationData {
  n: number;
  filename: string;
  page: number;
  snippet: string;
}

interface CitationPanelProps {
  citation: CitationData | null;
  onClose: () => void;
}

export default function CitationPanel({ citation, onClose }: CitationPanelProps) {
  if (!citation) return null;

  return (
    <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col border-l border-slate-800 bg-slate-900/95 backdrop-blur-xl shadow-2xl transition-all animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/20 text-indigo-400">
            <Bookmark className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Citation Source #{citation.n}</h3>
            <p className="text-xs text-slate-400">Grounded HR policy verification</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          aria-label="Close panel"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Document Info Card */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 space-y-3">
          <div className="flex items-start gap-3">
            <div className="mt-0.5 rounded-lg bg-blue-500/10 p-2 text-blue-400">
              <FileText className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Document Name</p>
              <p className="text-sm font-semibold text-slate-100 truncate mt-0.5" title={citation.filename}>
                {citation.filename}
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-slate-800/80 pt-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Source Page:</span>
              <span className="inline-flex items-center rounded-md bg-indigo-500/20 px-2 py-0.5 text-xs font-bold text-indigo-300">
                Page {citation.page}
              </span>
            </div>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-400">
              <CheckCircle className="h-3 w-3" />
              Verified Excerpt
            </span>
          </div>
        </div>

        {/* Snippet Card */}
        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Exact Supporting Excerpt
          </label>
          <div className="rounded-xl border border-indigo-900/30 bg-indigo-950/20 p-4 text-sm leading-relaxed text-slate-200 shadow-inner">
            <blockquote className="border-l-2 border-indigo-500 pl-3 italic text-slate-300">
              "{citation.snippet}"
            </blockquote>
          </div>
        </div>

        {/* Verification Note */}
        <div className="rounded-lg bg-slate-800/40 p-3.5 border border-slate-800 text-xs text-slate-400 leading-normal">
          <p className="font-medium text-slate-300 mb-1">Grounding Guarantee:</p>
          PolicyPilot strictly extracts text on a per-page boundary without cross-page mixing. Every cited paragraph maps directly to the designated page number of this PDF.
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-slate-800 p-4 bg-slate-950/40">
        <button
          onClick={onClose}
          className="w-full rounded-lg bg-slate-800 hover:bg-slate-700 py-2.5 text-sm font-medium text-white transition-colors"
        >
          Close Citation
        </button>
      </div>
    </div>
  );
}
