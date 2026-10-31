"use client";

import { useState, useEffect } from "react";
import {
  Database,
  UploadCloud,
  Trash2,
  RefreshCw,
  FileText,
  CheckCircle,
  AlertCircle,
  Lock,
  Play,
  TrendingUp,
  FileCheck,
  Award,
  Layers,
  Clock,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import Navbar from "@/components/Navbar";

interface DocumentRecord {
  id: string;
  filename: string;
  upload_time: string;
  page_count: number;
  chunk_count: number;
  file_size: number;
  status: string;
}

interface SplitMetrics {
  overall_score: number;
  answer_accuracy: number;
  citation_accuracy: number;
  fallback_recall: number;
  fallback_precision: number;
  false_abstentions: number;
  avg_latency_ms: number;
  total_questions: number;
  answerable_count?: number;
  unanswerable_count?: number;
}

interface QuestionRecord {
  id: number;
  split: string;
  question: string;
  is_answerable: boolean;
  expected_answer: string;
  expected_file?: string | null;
  expected_page?: number | null;
  actual_answer: string;
  citations: Array<{ n: number; filename: string; page: number; snippet: string }>;
  abstained: boolean;
  answer_correct: number;
  citation_correct: number;
  gating_score?: number;
  latency_ms: number;
  fallback_layer?: string | null;
  model_used?: string;
  diagnosis?: string;
}

interface TrackData {
  has_results?: boolean;
  timestamp?: string;
  track?: string;
  track_name?: string;
  collection?: string;
  combined?: SplitMetrics;
  dev_split?: SplitMetrics | null;
  test_split?: SplitMetrics | null;
  config?: any;
  message?: string;
  questions?: QuestionRecord[];
}

interface EvalResponse extends TrackData {
  has_results: boolean;
  synthetic?: TrackData;
  real?: TrackData;
  real_v2?: TrackData;
}

export default function AdminPage() {
  const [password, setPassword] = useState("");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [evalResults, setEvalResults] = useState<EvalResponse | null>(null);
  const [selectedTrack, setSelectedTrack] = useState<"synthetic" | "real" | "real_v2">("synthetic");
  const [loadingDocs, setLoadingDocs] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [evalRunning, setEvalRunning] = useState<string | null>(null);
  const [selectedFiles, setSelectedFiles] = useState<FileList | null>(null);

  // Authenticate & Load
  const fetchAdminData = async (pwdToUse: string) => {
    setLoadingDocs(true);
    try {
      const resDocs = await fetch("http://localhost:8000/api/admin/documents", {
        headers: { "X-Admin-Password": pwdToUse },
      });

      if (resDocs.status === 401) {
        setIsAuthenticated(false);
        setUploadStatus("Incorrect password. Please try again.");
        return;
      }

      if (resDocs.ok) {
        const docList = await resDocs.json();
        setDocuments(docList);
        setIsAuthenticated(true);
        setUploadStatus(null);
      }

      // Fetch Eval Results
      const resEval = await fetch("http://localhost:8000/api/admin/eval-results", {
        headers: { "X-Admin-Password": pwdToUse },
      });
      if (resEval.ok) {
        const evalData = await resEval.json();
        setEvalResults(evalData);
      }
    } catch (err: any) {
      setUploadStatus("Unable to connect to backend at http://localhost:8000.");
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchAdminData(password);
  }, []);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAdminData(password);
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFiles || selectedFiles.length === 0) return;

    setUploading(true);
    setUploadStatus("Uploading and indexing documents into ChromaDB & BM25...");

    const formData = new FormData();
    for (let i = 0; i < selectedFiles.length; i++) {
      formData.append("files", selectedFiles[i]);
    }

    try {
      const res = await fetch("http://localhost:8000/api/admin/upload", {
        method: "POST",
        headers: { "X-Admin-Password": password },
        body: formData,
      });

      if (!res.ok) throw new Error("Upload failed.");

      const data = await res.json();
      setUploadStatus(`Successfully processed ${data.uploaded.length} file(s).`);
      setSelectedFiles(null);
      fetchAdminData(password);
    } catch (err: any) {
      setUploadStatus(`Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docIdOrName: string) => {
    if (!confirm(`Are you sure you want to delete '${docIdOrName}'? Vectors and chunks will be removed.`)) {
      return;
    }

    try {
      const res = await fetch(`http://localhost:8000/api/admin/documents/${encodeURIComponent(docIdOrName)}`, {
        method: "DELETE",
        headers: { "X-Admin-Password": password },
      });

      if (res.ok) {
        fetchAdminData(password);
      } else {
        alert("Failed to delete document.");
      }
    } catch (err) {
      alert("Error contacting backend.");
    }
  };

  const handleReindex = async () => {
    setLoadingDocs(true);
    try {
      const res = await fetch("http://localhost:8000/api/admin/reindex", {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });
      if (res.ok) {
        alert("Corpus and BM25 index rebuilt successfully.");
        fetchAdminData(password);
      }
    } catch (err) {
      alert("Error re-indexing.");
    } finally {
      setLoadingDocs(false);
    }
  };

  const handleRunEvaluation = async (track: "synthetic" | "real" | "real_v2") => {
    setEvalRunning(track);
    try {
      const res = await fetch(`http://localhost:8000/api/admin/run-eval?track=${track}`, {
        method: "POST",
        headers: { "X-Admin-Password": password },
      });

      if (res.ok) {
        await fetchAdminData(password);
        setSelectedTrack(track);
      } else {
        alert(`Evaluation run (${track}) encountered an error.`);
      }
    } catch (err) {
      alert("Failed to start evaluation.");
    } finally {
      setEvalRunning(null);
    }
  };

  const totalPages = documents.reduce((acc, d) => acc + (d.page_count || 0), 0);
  const totalChunks = documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0);

  // Determine active track data
  const syntheticData: TrackData | null = evalResults?.synthetic || (evalResults?.combined ? evalResults : null);
  const realData: TrackData | null = evalResults?.real || null;
  const realV2Data: TrackData | null = evalResults?.real_v2 || null;

  let currentTrackData: TrackData | null = syntheticData;
  if (selectedTrack === "real") currentTrackData = realData;
  if (selectedTrack === "real_v2") currentTrackData = realV2Data;

  const currentFailures = (currentTrackData?.questions || []).filter(
    (q) => (q.is_answerable && (q.answer_correct === 0 || q.citation_correct === 0)) || (!q.is_answerable && !q.abstained)
  );

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
        <Navbar />
        <div className="flex flex-1 items-center justify-center p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-900/80 p-8 shadow-xl">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400 mb-4">
              <Lock className="h-6 w-6" />
            </div>
            <h1 className="text-xl font-bold text-white mb-1">Admin Portal Access</h1>
            <p className="text-xs text-slate-400 mb-6">
              Enter the admin password configured in <code className="text-indigo-300">ADMIN_PASSWORD</code>.
            </p>

            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1.5 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
                  placeholder="Enter admin password..."
                  required
                />
              </div>

              {uploadStatus && (
                <p className="text-xs text-rose-400 flex items-center gap-1.5">
                  <AlertCircle className="h-3.5 w-3.5" />
                  {uploadStatus}
                </p>
              )}

              <button
                type="submit"
                className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 py-2.5 text-sm font-semibold text-white transition-colors"
              >
                Authenticate & Enter
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Navbar />

      <main className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
        {/* Header Title */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Database className="h-6 w-6 text-indigo-400" />
              Document Management & Evaluation Suite
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Ingest HR policy manuals, manage separate collections, and benchmark accuracy across synthetic & real-world tracks.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleReindex}
              disabled={loadingDocs}
              className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-800 px-4 py-2 text-xs font-medium text-slate-200 transition-colors"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loadingDocs ? "animate-spin" : ""}`} />
              Re-index BM25
            </button>
          </div>
        </div>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
              <span>Indexed Documents</span>
              <FileText className="h-4 w-4 text-indigo-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{documents.length}</p>
            <p className="text-[11px] text-slate-500 mt-1">Active SQLite entries</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
              <span>Total Pages</span>
              <Layers className="h-4 w-4 text-cyan-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{totalPages}</p>
            <p className="text-[11px] text-slate-500 mt-1">Strict page boundary guarantee</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
              <span>Vector Chunks</span>
              <TrendingUp className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-white mt-2">{totalChunks}</p>
            <p className="text-[11px] text-slate-500 mt-1">ChromaDB + BM25 synchronized</p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium uppercase tracking-wider">
              <span>Retrieval Status</span>
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-emerald-400 mt-2">Active</p>
            <p className="text-[11px] text-slate-500 mt-1">Hybrid Fusion (Cosine + RRF)</p>
          </div>
        </div>

        {/* Evaluation Suite Card (Dual-Track Benchmark) */}
        <div className="rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-slate-900 via-indigo-950/20 to-slate-900 p-6 shadow-xl space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-indigo-900/30 pb-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-400">
                <Award className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  PolicyPilot Automated Evaluation Suite
                </h2>
                <p className="text-xs text-slate-400">
                  Measures LLM-as-judge answer accuracy, ground-truth citation page matching, and fallback precision.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => handleRunEvaluation("synthetic")}
                disabled={evalRunning !== null}
                className="flex items-center gap-2 rounded-xl bg-indigo-600/80 hover:bg-indigo-600 disabled:opacity-50 px-3.5 py-2 text-xs font-semibold text-white shadow transition-all"
              >
                <Play className={`h-3 w-3 ${evalRunning === "synthetic" ? "animate-spin" : ""}`} />
                <span>{evalRunning === "synthetic" ? "Running Synthetic..." : "Run Synthetic (30 Qs)"}</span>
              </button>
              <button
                onClick={() => handleRunEvaluation("real")}
                disabled={evalRunning !== null}
                className="flex items-center gap-2 rounded-xl bg-emerald-600/80 hover:bg-emerald-600 disabled:opacity-50 px-3.5 py-2 text-xs font-semibold text-white shadow transition-all"
              >
                <Sparkles className={`h-3 w-3 ${evalRunning === "real" ? "animate-spin" : ""}`} />
                <span>{evalRunning === "real" ? "Running Pass 1..." : "Run Real Pass 1 (15 Qs)"}</span>
              </button>
              <button
                onClick={() => handleRunEvaluation("real_v2")}
                disabled={evalRunning !== null}
                className="flex items-center gap-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 px-3.5 py-2 text-xs font-semibold text-white shadow transition-all"
              >
                <Sparkles className={`h-3 w-3 ${evalRunning === "real_v2" ? "animate-spin" : ""}`} />
                <span>{evalRunning === "real_v2" ? "Running Pass 2..." : "Run Real Pass 2 (10 Qs)"}</span>
              </button>
            </div>
          </div>

          {/* Track Selector Tabs */}
          <div className="flex flex-wrap items-center gap-2.5 border-b border-slate-800 pb-3">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Evaluation Track:</span>
            <button
              onClick={() => setSelectedTrack("synthetic")}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                selectedTrack === "synthetic"
                  ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              Synthetic (30 Qs)
            </button>
            <button
              onClick={() => setSelectedTrack("real")}
              className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                selectedTrack === "real"
                  ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              <Sparkles className="h-3 w-3" />
              Real Pass 1 (15 Qs)
            </button>
            <button
              onClick={() => setSelectedTrack("real_v2")}
              className={`flex items-center gap-1.5 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                selectedTrack === "real_v2"
                  ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              <Sparkles className="h-3 w-3" />
              Real Pass 2 (10 Qs - False Premise & Paraphrase)
            </button>
          </div>

          {currentTrackData && currentTrackData.combined ? (
            <div className="space-y-6">
              {/* Score Badges */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs text-slate-400 font-medium uppercase">Overall Benchmark Score</p>
                  <p className="text-2xl font-bold text-indigo-400 mt-1">
                    {currentTrackData.combined.overall_score}%
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {selectedTrack === "real" ? "15-question real-world benchmark" : "30-question synthetic benchmark"}
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs text-slate-400 font-medium uppercase">Answer Accuracy</p>
                  <p className="text-2xl font-bold text-emerald-400 mt-1">
                    {currentTrackData.combined.answer_accuracy}%
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {currentTrackData.combined.answerable_count} answerable questions
                  </p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs text-slate-400 font-medium uppercase">Citation Page Accuracy</p>
                  <p className="text-2xl font-bold text-cyan-400 mt-1">
                    {currentTrackData.combined.citation_accuracy}%
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">Exact PDF page matches</p>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
                  <p className="text-xs text-slate-400 font-medium uppercase">Fallback Recall</p>
                  <p className="text-2xl font-bold text-amber-400 mt-1">
                    {currentTrackData.combined.fallback_recall}%
                  </p>
                  <p className="text-[10px] text-slate-500 mt-0.5">
                    {currentTrackData.combined.unanswerable_count} unanswerable questions
                  </p>
                </div>
              </div>

              {/* Performance Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/40">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                    <tr>
                      <th className="px-4 py-3">Partition / Track</th>
                      <th className="px-4 py-3">Questions</th>
                      <th className="px-4 py-3">Answer Accuracy</th>
                      <th className="px-4 py-3">Citation Accuracy</th>
                      <th className="px-4 py-3">Fallback Recall</th>
                      <th className="px-4 py-3">Fallback Precision</th>
                      <th className="px-4 py-3">Avg Latency</th>
                      <th className="px-4 py-3 text-right">Overall</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {currentTrackData.dev_split && (
                      <tr className="hover:bg-slate-900/30">
                        <td className="px-4 py-3 font-semibold text-indigo-300">Dev Split (Tuning)</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.total_questions}</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.answer_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.citation_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.fallback_recall}%</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.fallback_precision}%</td>
                        <td className="px-4 py-3">{currentTrackData.dev_split.avg_latency_ms} ms</td>
                        <td className="px-4 py-3 text-right font-bold text-indigo-400">
                          {currentTrackData.dev_split.overall_score}%
                        </td>
                      </tr>
                    )}
                    {currentTrackData.test_split && (
                      <tr className="hover:bg-slate-900/30">
                        <td className="px-4 py-3 font-semibold text-emerald-300">
                          {selectedTrack === "real" ? "Real-World Public PDF Track" : "Test Split (Holdout)"}
                        </td>
                        <td className="px-4 py-3">{currentTrackData.test_split.total_questions}</td>
                        <td className="px-4 py-3">{currentTrackData.test_split.answer_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.test_split.citation_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.test_split.fallback_recall}%</td>
                        <td className="px-4 py-3">{currentTrackData.test_split.fallback_precision}%</td>
                        <td className="px-4 py-3">{currentTrackData.test_split.avg_latency_ms} ms</td>
                        <td className="px-4 py-3 text-right font-bold text-emerald-400">
                          {currentTrackData.test_split.overall_score}%
                        </td>
                      </tr>
                    )}
                    {currentTrackData.dev_split && (
                      <tr className="bg-indigo-950/20 font-semibold text-white">
                        <td className="px-4 py-3">Combined Benchmark</td>
                        <td className="px-4 py-3">{currentTrackData.combined.total_questions}</td>
                        <td className="px-4 py-3">{currentTrackData.combined.answer_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.combined.citation_accuracy}%</td>
                        <td className="px-4 py-3">{currentTrackData.combined.fallback_recall}%</td>
                        <td className="px-4 py-3">{currentTrackData.combined.fallback_precision}%</td>
                        <td className="px-4 py-3">{currentTrackData.combined.avg_latency_ms} ms</td>
                        <td className="px-4 py-3 text-right font-bold text-indigo-300 text-sm">
                          {currentTrackData.combined.overall_score}%
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Failure Analysis & Diagnosis Box */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-emerald-400" />
                    Failure Analysis & Diagnosis ({selectedTrack === "real" ? "Real-World Track" : "Synthetic Benchmark"})
                  </h3>
                  <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                    currentFailures.length === 0 ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                  }`}>
                    {currentFailures.length === 0 ? "0 Failures (100% Pass Rate)" : `${currentFailures.length} Failure(s)`}
                  </span>
                </div>

                {currentFailures.length === 0 ? (
                  <p className="text-xs text-slate-400">
                    All {currentTrackData.combined.total_questions} questions passed verification. Ground-truth facts were correctly answered, citations matched verified PDF page numbers, and out-of-scope questions cleanly triggered Layer 2 abstention.
                  </p>
                ) : (
                  <div className="space-y-2 mt-2">
                    {currentFailures.map((f) => (
                      <div key={f.id} className="rounded-lg border border-rose-900/50 bg-rose-950/20 p-3 space-y-1 text-xs">
                        <div className="flex items-center justify-between text-rose-300 font-semibold">
                          <span>Question {f.id}: {f.question}</span>
                          <span className="text-[10px] uppercase tracking-wider bg-rose-900/40 px-2 py-0.5 rounded">
                            {f.is_answerable ? "Answerable" : "Unanswerable"}
                          </span>
                        </div>
                        <p className="text-slate-300"><strong className="text-slate-400">Diagnosis:</strong> {f.diagnosis || "Failure detected."}</p>
                        {f.is_answerable ? (
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
                            <div><strong className="text-slate-300">Expected:</strong> {f.expected_answer} ({f.expected_file} p.{f.expected_page})</div>
                            <div><strong className="text-slate-300">Actual:</strong> {f.actual_answer}</div>
                          </div>
                        ) : (
                          <div className="text-[11px] text-slate-400 pt-1">
                            <strong className="text-slate-300">Actual:</strong> {f.actual_answer}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Questions Breakdown Table */}
              {currentTrackData.questions && currentTrackData.questions.length > 0 && (
                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/40">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-900/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                      <tr>
                        <th className="px-3 py-2.5 text-center">ID</th>
                        <th className="px-3 py-2.5">Question</th>
                        <th className="px-3 py-2.5">Type</th>
                        <th className="px-3 py-2.5 text-center">Answer</th>
                        <th className="px-3 py-2.5 text-center">Citation</th>
                        <th className="px-3 py-2.5">Latency</th>
                        <th className="px-3 py-2.5">Gating</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                      {currentTrackData.questions.map((q) => (
                        <tr key={q.id} className="hover:bg-slate-900/30">
                          <td className="px-3 py-2 text-center text-slate-400 font-sans">{q.id}</td>
                          <td className="px-3 py-2 font-sans text-slate-200 max-w-sm truncate" title={q.question}>
                            {q.question}
                          </td>
                          <td className="px-3 py-2 font-sans">
                            <span className={`px-2 py-0.5 rounded text-[10px] ${
                              q.is_answerable ? "bg-indigo-950 text-indigo-300" : "bg-amber-950 text-amber-300"
                            }`}>
                              {q.is_answerable ? "Answerable" : "Unanswerable"}
                            </span>
                          </td>
                          <td className="px-3 py-2 text-center">
                            {q.answer_correct ? (
                              <span className="text-emerald-400">Pass</span>
                            ) : (
                              <span className="text-rose-400">Fail</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-center">
                            {!q.is_answerable ? (
                              <span className="text-slate-500">N/A</span>
                            ) : q.citation_correct ? (
                              <span className="text-emerald-400">Pass (p.{q.expected_page})</span>
                            ) : (
                              <span className="text-rose-400">Fail</span>
                            )}
                          </td>
                          <td className="px-3 py-2 text-slate-400">{q.latency_ms.toFixed(0)}ms</td>
                          <td className="px-3 py-2 text-slate-400">{q.gating_score ? q.gating_score.toFixed(3) : "N/A"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center space-y-3">
              <Clock className="h-8 w-8 text-slate-500 mx-auto" />
              <p className="text-sm text-slate-300">No benchmark evaluation results found yet for this track.</p>
              <p className="text-xs text-slate-500">
                Click one of the buttons above to execute the benchmark against the live pipeline.
              </p>
            </div>
          )}
        </div>

        {/* Upload Zone */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <UploadCloud className="h-5 w-5 text-indigo-400" />
            Upload New HR Policy Documents
          </h2>
          <p className="text-xs text-slate-400">
            Supports PDF, DOCX, TXT, and Markdown files. Files are parsed page-by-page, chunked into ~800 character windows with ~120 overlap, embedded, and indexed.
          </p>

          <form onSubmit={handleUpload} className="space-y-4">
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <input
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md"
                onChange={(e) => setSelectedFiles(e.target.files)}
                className="w-full text-xs text-slate-400 file:mr-4 file:rounded-xl file:border-0 file:bg-indigo-600 file:px-4 file:py-2.5 file:text-xs file:font-semibold file:text-white hover:file:bg-indigo-500"
              />
              <button
                type="submit"
                disabled={uploading || !selectedFiles || selectedFiles.length === 0}
                className="w-full sm:w-auto shrink-0 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 px-6 py-2.5 text-xs font-semibold text-white transition-colors"
              >
                {uploading ? "Ingesting..." : "Ingest & Index"}
              </button>
            </div>

            {uploadStatus && (
              <p className="text-xs text-indigo-400 bg-indigo-950/40 p-3 rounded-lg border border-indigo-900/40">
                {uploadStatus}
              </p>
            )}
          </form>
        </div>

        {/* Documents Table */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-xl">
          <div className="p-5 border-b border-slate-800">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-indigo-400" />
              Active Knowledge Base Documents ({documents.length})
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3.5">Document Filename</th>
                  <th className="px-6 py-3.5">Pages</th>
                  <th className="px-6 py-3.5">Chunks</th>
                  <th className="px-6 py-3.5">File Size</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-slate-200 flex items-center gap-2.5">
                      <FileText className="h-4 w-4 text-indigo-400 shrink-0" />
                      <span className="truncate max-w-xs">{doc.filename}</span>
                    </td>
                    <td className="px-6 py-4">
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-slate-300 font-semibold">
                        {doc.page_count} pages
                      </span>
                    </td>
                    <td className="px-6 py-4">{doc.chunk_count} chunks</td>
                    <td className="px-6 py-4">{(doc.file_size / 1024).toFixed(1)} KB</td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[11px] font-semibold text-emerald-400">
                        <CheckCircle className="h-3 w-3" />
                        Ready
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-rose-500/20 hover:text-rose-400 transition-colors"
                        title="Delete Document & Chunks"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
}
