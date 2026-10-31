"use client";

import { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  AlertTriangle,
  RotateCcw,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  HelpCircle,
  FileCheck2,
  ExternalLink,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import CitationPanel, { CitationData } from "@/components/CitationPanel";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: CitationData[];
  answerable?: boolean;
  confidence?: number;
  gatingScore?: number;
}

const STARTER_QUESTIONS = [
  {
    title: "Paid Vacation & Accrual",
    query: "How many days of paid leave do new employees get?",
  },
  {
    title: "401(k) Retirement Match",
    query: "What percentage does Northwind Labs match on employee 401(k) contributions?",
  },
  {
    title: "Remote Work & Core Hours",
    query: "What are the core collaboration hours and remote work policy?",
  },
  {
    title: "IT Security Incident SLA",
    query: "Within how many hours must a suspected security incident be reported?",
  },
  {
    title: "Out-of-Scope Fallback Test",
    query: "What is Northwind Labs' stock ticker symbol on NASDAQ?",
  },
];

const FALLBACK_PHRASE = "I couldn't find this in the uploaded documents";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState<CitationData | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend?: string) => {
    const query = (textToSend || input).trim();
    if (!query || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: query,
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInput("");
    setLoading(true);

    // Format previous turns for backend query rewriter
    const payloadHistory = messages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: query,
          history: payloadHistory,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();

      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        citations: data.citations || [],
        answerable: data.answerable,
        confidence: data.confidence,
        gatingScore: data.gating_score,
      };

      setMessages([...newHistory, assistantMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Unable to connect to the PolicyPilot backend. Please ensure the backend server is running at http://localhost:8000.",
        answerable: false,
      };
      setMessages([...newHistory, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
    setActiveCitation(null);
  };

  const renderFormattedAnswer = (text: string, citations: CitationData[] = []) => {
    // Replace citation markers [1], [2] with interactive badges
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const match = part.match(/\[(\d+)\]/);
      if (match) {
        const n = parseInt(match[1]);
        const citationObj = citations.find((c) => c.n === n);
        return (
          <button
            key={i}
            onClick={() => citationObj && setActiveCitation(citationObj)}
            className="inline-flex items-center mx-1 px-1.5 py-0.5 rounded bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 font-bold text-xs ring-1 ring-inset ring-indigo-500/30 transition-colors"
            title={citationObj ? `${citationObj.filename} (Page ${citationObj.page})` : `Citation ${n}`}
          >
            [{n}]
          </button>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <Navbar />

      <main className="flex-1 flex flex-col mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
        {/* Top Controls */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-900 mb-4">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="flex h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Northwind Labs HR Corpus Active (3 Ingested Documents)</span>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors py-1 px-2.5 rounded-lg hover:bg-slate-900"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Reset Conversation</span>
            </button>
          )}
        </div>

        {/* Chat Stream / Welcome */}
        <div className="flex-1 space-y-6 overflow-y-auto pb-6">
          {messages.length === 0 ? (
            <div className="my-auto flex flex-col items-center justify-center text-center py-12 px-4 space-y-6">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-tr from-indigo-500 to-cyan-500 shadow-xl shadow-indigo-500/10 ring-1 ring-white/20">
                <ShieldCheck className="h-9 w-9 text-white" />
              </div>

              <div className="max-w-md space-y-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Welcome to PolicyPilot
                </h1>
                <p className="text-sm text-slate-400 leading-relaxed">
                  Ask any question about Northwind Labs HR policies, benefits, leave, and IT security. Every answer is grounded with verifiable source document page citations.
                </p>
              </div>

              {/* Starter Question Cards */}
              <div className="w-full max-w-2xl space-y-2.5 pt-4">
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 text-left px-1">
                  Try asking about:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {STARTER_QUESTIONS.map((q, idx) => (
                    <button
                      key={idx}
                      onClick={() => handleSend(q.query)}
                      className="group flex flex-col items-start p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/40 hover:bg-slate-900 hover:border-indigo-500/50 text-left transition-all"
                    >
                      <span className="text-xs font-semibold text-indigo-400 group-hover:text-indigo-300">
                        {q.title}
                      </span>
                      <span className="text-xs text-slate-300 mt-1 line-clamp-2">
                        {q.query}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            messages.map((m) => {
              const isUser = m.role === "user";
              const isFallback =
                !m.answerable ||
                (m.content && m.content.includes(FALLBACK_PHRASE));

              return (
                <div
                  key={m.id}
                  className={`flex gap-3.5 ${
                    isUser ? "justify-end" : "justify-start"
                  }`}
                >
                  {!isUser && (
                    <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs shadow-md shadow-indigo-600/30">
                      PP
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-5 py-4 ${
                      isUser
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : isFallback
                        ? "border border-amber-500/30 bg-amber-950/20 text-amber-200 shadow-sm"
                        : "border border-slate-800 bg-slate-900/80 text-slate-100 shadow-sm"
                    }`}
                  >
                    {/* Fallback Banner Styling */}
                    {isFallback ? (
                      <div className="space-y-3">
                        <div className="flex items-center gap-2 text-amber-400 font-semibold text-xs tracking-wide uppercase">
                          <AlertTriangle className="h-4 w-4" />
                          <span>No Grounded Answer in Documents</span>
                        </div>
                        <p className="text-sm leading-relaxed text-amber-100 font-medium">
                          {m.content}
                        </p>
                        <div className="pt-2 text-[11px] text-amber-300/70 border-t border-amber-500/20 flex items-center gap-1.5">
                          <HelpCircle className="h-3.5 w-3.5" />
                          <span>Out-of-domain query safely abstained to prevent hallucinations.</span>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {/* Normal Grounded Answer */}
                        <div className="text-sm leading-relaxed whitespace-pre-wrap">
                          {isUser
                            ? m.content
                            : renderFormattedAnswer(m.content, m.citations || [])}
                        </div>

                        {/* Citations Row */}
                        {!isUser && m.citations && m.citations.length > 0 && (
                          <div className="pt-3 border-t border-slate-800/80 space-y-2">
                            <div className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                              <BookOpen className="h-3 w-3 text-indigo-400" />
                              <span>Verified Source Citations:</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {m.citations.map((c) => (
                                <button
                                  key={c.n}
                                  onClick={() => setActiveCitation(c)}
                                  className="group flex items-center gap-1.5 rounded-lg border border-indigo-900/50 bg-indigo-950/30 hover:bg-indigo-900/40 px-3 py-1.5 text-xs text-indigo-200 transition-all hover:scale-[1.02]"
                                >
                                  <span className="flex h-4 w-4 items-center justify-center rounded bg-indigo-500/20 text-[10px] font-bold text-indigo-300">
                                    {c.n}
                                  </span>
                                  <span className="font-medium text-slate-300 group-hover:text-white truncate max-w-[180px]">
                                    {c.filename}
                                  </span>
                                  <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] text-indigo-300 font-semibold">
                                    p.{c.page}
                                  </span>
                                  <ExternalLink className="h-3 w-3 text-slate-400 group-hover:text-indigo-300" />
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Loading indicator */}
          {loading && (
            <div className="flex gap-3.5 justify-start items-center">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-xs shadow-md">
                PP
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 text-slate-400 text-xs flex items-center gap-2">
                <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-ping" />
                <span>Searching policies & verifying citations...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Area */}
        <div className="sticky bottom-0 pt-2 pb-4 bg-slate-950">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="relative flex items-center rounded-2xl border border-slate-800 bg-slate-900/80 shadow-lg shadow-black/40 focus-within:border-indigo-500/60 focus-within:ring-1 focus-within:ring-indigo-500/50 transition-all"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask an HR policy question (e.g. vacation days, 401k match, remote work)..."
              disabled={loading}
              className="w-full bg-transparent px-5 py-4 text-sm text-slate-100 placeholder-slate-500 focus:outline-none disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="mr-3 flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-30 disabled:hover:bg-indigo-600 transition-colors shadow-sm"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
          <p className="mt-2 text-center text-[11px] text-slate-400">
            PolicyPilot answers are strictly grounded in uploaded company policy documents with page citations.
          </p>
        </div>
      </main>

      {/* Side Panel for Citations */}
      <CitationPanel
        citation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />
    </div>
  );
}
