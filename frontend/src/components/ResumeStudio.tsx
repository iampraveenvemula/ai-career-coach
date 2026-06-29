/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Sparkles, AlertCircle, Download, Loader2,
  RotateCcw, Pencil, Check, X, TrendingUp, TrendingDown, Minus,
  RefreshCw, ChevronDown, ChevronRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE_URL } from "@/lib/config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface ScoreState {
  score: number;
  matched: string[];
  missing: string[];
}

interface InlineEdit {
  lineText: string;
  lineIndex: string;
  prompt: string;
}

interface ResumeSection {
  header: string;
  lines: string[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const KNOWN_HEADERS = new Set([
  "PROFESSIONAL SUMMARY", "SUMMARY",
  "WORK EXPERIENCE", "EXPERIENCE", "EMPLOYMENT",
  "PROJECTS", "PROJECT EXPERIENCE",
  "EDUCATION",
  "SKILLS", "TECHNICAL SKILLS",
  "CERTIFICATIONS", "AWARDS", "PUBLICATIONS", "VOLUNTEERING",
]);

const SECTION_ICONS: Record<string, string> = {
  "PROFESSIONAL SUMMARY": "🎯",
  "SUMMARY": "🎯",
  "SKILLS": "⚡",
  "TECHNICAL SKILLS": "⚡",
  "WORK EXPERIENCE": "💼",
  "EXPERIENCE": "💼",
  "EMPLOYMENT": "💼",
  "EDUCATION": "🎓",
  "PROJECTS": "🔧",
  "PROJECT EXPERIENCE": "🔧",
  "CERTIFICATIONS": "📜",
};

// ---------------------------------------------------------------------------
// Parse plain-text resume into sections
// ---------------------------------------------------------------------------
function parseResume(text: string): ResumeSection[] {
  const sections: ResumeSection[] = [];
  let current: ResumeSection | null = null;
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const upper = line.trim().toUpperCase();
    const isHeader =
      KNOWN_HEADERS.has(upper) ||
      [...KNOWN_HEADERS].some((h) => upper.startsWith(h));
    if (isHeader && line.trim().length > 0) {
      if (current) sections.push(current);
      current = { header: upper, lines: [] };
    } else if (current) {
      current.lines.push(line);
    } else if (line.trim()) {
      sections.push({ header: "__HEADER__", lines: [line] });
    }
  }
  if (current) sections.push(current);
  return sections;
}

// ---------------------------------------------------------------------------
// ATS Score Ring
// ---------------------------------------------------------------------------
function ATSRing({
  score,
  isLoading,
}: {
  score: number | null;
  isLoading: boolean;
}) {
  const radius = 36;
  const circumference = 2 * Math.PI * radius;
  const fill = score !== null ? (score / 100) * circumference : 0;

  const color =
    score === null ? "#e2e8f0" :
    score >= 75 ? "#10b981" :
    score >= 50 ? "#f59e0b" :
    "#ef4444";

  const label =
    score === null ? "—" :
    score >= 75 ? "Strong" :
    score >= 50 ? "Fair" :
    "Weak";

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
          <circle cx="44" cy="44" r={radius} fill="none" stroke="#f1f5f9" strokeWidth="7" />
          {!isLoading && (
            <motion.circle
              cx="44" cy="44" r={radius}
              fill="none"
              stroke={color}
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset: circumference - fill }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          )}
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {isLoading ? (
            <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />
          ) : (
            <>
              <span className="text-2xl font-black text-slate-800 tabular-nums leading-none">
                {score ?? "—"}
              </span>
              {score !== null && (
                <span className="text-[9px] font-bold text-slate-400 uppercase tracking-wide">ATS</span>
              )}
            </>
          )}
        </div>
      </div>
      {score !== null && !isLoading && (
        <span className="text-xs font-semibold" style={{ color }}>{label}</span>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Keyword Gap Panel (left column)
// ---------------------------------------------------------------------------
function KeywordPanel({
  score,
  isLoading,
  activeKeyword,
  onKeywordClick,
  previousScore,
}: {
  score: ScoreState | null;
  isLoading: boolean;
  activeKeyword: string | null;
  onKeywordClick: (kw: string) => void;
  previousScore: number | null;
}) {
  const delta = score && previousScore !== null ? score.score - previousScore : null;

  return (
    <div className="flex flex-col gap-4 h-full overflow-y-auto pr-1">
      {/* Score ring */}
      <div className="flex flex-col items-center pt-2">
        <ATSRing score={score?.score ?? null} isLoading={isLoading} />
        {delta !== null && !isLoading && (
          <div className={`flex items-center gap-1 text-xs font-bold mt-1 px-2 py-0.5 rounded-full ${
            delta > 0 ? "bg-emerald-50 text-emerald-600" :
            delta < 0 ? "bg-red-50 text-red-500" :
            "bg-slate-100 text-slate-500"
          }`}>
            {delta > 0 ? <TrendingUp className="w-3 h-3" /> :
             delta < 0 ? <TrendingDown className="w-3 h-3" /> :
             <Minus className="w-3 h-3" />}
            {delta > 0 ? `+${delta}` : delta === 0 ? "No change" : delta}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex flex-col gap-1 px-1">
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-200 shrink-0" /> Matched in resume
        </div>
        <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
          <span className="w-2.5 h-2.5 rounded-sm bg-red-200 shrink-0" /> Missing — click to find
        </div>
      </div>

      {/* Matched keywords */}
      {score && score.matched.length > 0 && (
        <div>
          <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-wider mb-1.5 px-1">
            ✓ Matched ({score.matched.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {score.matched.slice(0, 15).map((kw) => (
              <button
                key={kw}
                onClick={() => onKeywordClick(kw)}
                className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-all border ${
                  activeKeyword === kw
                    ? "bg-emerald-500 text-white border-emerald-500"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100"
                }`}
              >
                {kw}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Missing keywords */}
      {score && score.missing.length > 0 && (
        <div>
          <p className="text-[10px] font-bold text-red-500 uppercase tracking-wider mb-1.5 px-1">
            ✗ Missing ({score.missing.length})
          </p>
          <div className="flex flex-wrap gap-1">
            {score.missing.slice(0, 15).map((kw) => (
              <button
                key={kw}
                onClick={() => onKeywordClick(kw)}
                className={`text-[10px] px-2 py-0.5 rounded-full font-medium transition-all border ${
                  activeKeyword === kw
                    ? "bg-red-500 text-white border-red-500"
                    : "bg-red-50 text-red-700 border-red-200 hover:bg-red-100"
                }`}
              >
                {kw}
              </button>
            ))}
          </div>
        </div>
      )}

      {!score && !isLoading && (
        <p className="text-[11px] text-slate-400 text-center px-2 pt-4">
          Keywords will appear after tailoring completes.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable line — hover to show inline refine prompt
// ---------------------------------------------------------------------------
function EditableLine({
  lineKey, lineText, onRefine, isRefining, activeKey, children, className = "",
}: {
  lineKey: string;
  lineText: string;
  onRefine: (e: InlineEdit) => void;
  isRefining: boolean;
  activeKey: string | null;
  children: React.ReactNode;
  className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [prompt, setPrompt] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const isThis = isRefining && activeKey === lineKey;

  const open = () => { setEditing(true); setTimeout(() => inputRef.current?.focus(), 40); };
  const cancel = () => { setEditing(false); setPrompt(""); };
  const submit = () => {
    if (!prompt.trim()) return;
    onRefine({ lineText, lineIndex: lineKey, prompt: prompt.trim() });
    setEditing(false); setPrompt("");
  };

  return (
    <div className={`group relative ${className}`}>
      <div className={`relative pr-7 transition-colors rounded ${
        isThis ? "opacity-40" : "hover:bg-indigo-50/60"
      }`}>
        {children}
        {!editing && !isRefining && (
          <button
            onClick={open}
            className="absolute right-0 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-full bg-white border border-slate-200 shadow-sm hover:border-indigo-400"
            title="Refine this line with AI"
          >
            <Pencil className="w-2.5 h-2.5 text-slate-400 hover:text-indigo-600" />
          </button>
        )}
        {isThis && (
          <span className="absolute right-1 top-1/2 -translate-y-1/2">
            <Loader2 className="w-3 h-3 text-indigo-500 animate-spin" />
          </span>
        )}
      </div>
      <AnimatePresence>
        {editing && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.12 }}
            className="mt-1 flex items-center gap-2 bg-white border border-indigo-300 rounded-xl shadow-lg px-3 py-2 z-30"
          >
            <Sparkles className="w-3 h-3 text-indigo-500 shrink-0" />
            <input
              ref={inputRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") { e.preventDefault(); submit(); }
                if (e.key === "Escape") cancel();
              }}
              placeholder="How should I change this?"
              className="flex-1 text-xs text-slate-800 placeholder:text-slate-400 outline-none bg-transparent"
            />
            <button
              onClick={submit}
              disabled={!prompt.trim()}
              className="p-1 rounded-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40"
            >
              <Check className="w-2.5 h-2.5 text-white" />
            </button>
            <button onClick={cancel} className="p-1 rounded-full hover:bg-slate-100">
              <X className="w-2.5 h-2.5 text-slate-400" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Highlight text — mark active keyword
// ---------------------------------------------------------------------------
function Highlighted({
  text,
  matchedSet,
  missingSet,
  activeKeyword,
}: {
  text: string;
  matchedSet: Set<string>;
  missingSet: Set<string>;
  activeKeyword: string | null;
}) {
  const words = text.split(/(\s+)/);
  return (
    <>
      {words.map((w, i) => {
        const clean = w.toLowerCase().replace(/[^a-z0-9+#]/g, "");
        const isActive = activeKeyword && clean === activeKeyword.toLowerCase();
        if (isActive)
          return <mark key={i} className="bg-yellow-300 text-yellow-900 rounded px-0.5 not-italic font-semibold">{w}</mark>;
        if (matchedSet.has(clean))
          return <mark key={i} className="bg-emerald-100 text-emerald-800 rounded px-0.5 not-italic font-medium">{w}</mark>;
        if (missingSet.has(clean))
          return <mark key={i} className="bg-red-100 text-red-700 rounded px-0.5 not-italic">{w}</mark>;
        return <span key={i}>{w}</span>;
      })}
    </>
  );
}

// ---------------------------------------------------------------------------
// Resume renderer — structured sections
// ---------------------------------------------------------------------------
function ResumeRenderer({
  text, onRefine, isRefining, activeKey, matchedKeywords, missingKeywords, activeKeyword,
}: {
  text: string;
  onRefine: (e: InlineEdit) => void;
  isRefining: boolean;
  activeKey: string | null;
  matchedKeywords: string[];
  missingKeywords: string[];
  activeKeyword: string | null;
}) {
  const sections = parseResume(text);
  const matchedSet = new Set(matchedKeywords.map((k) => k.toLowerCase()));
  const missingSet = new Set(missingKeywords.map((k) => k.toLowerCase()));

  return (
    <div className="font-sans text-sm leading-relaxed space-y-5">
      {sections.map((section, si) => {
        // Candidate name / contact header
        if (section.header === "__HEADER__") {
          return (
            <div key={si} className="space-y-0.5 pb-2 border-b border-slate-100">
              {section.lines.map((l, li) => {
                const key = `h-${si}-${li}`;
                const isName = li === 0;
                return (
                  <EditableLine key={key} lineKey={key} lineText={l.trim()}
                    onRefine={onRefine} isRefining={isRefining} activeKey={activeKey}>
                    <p className={isName
                      ? "text-2xl font-black text-slate-900 tracking-tight"
                      : "text-slate-500 text-xs"
                    }>
                      {l.trim()}
                    </p>
                  </EditableLine>
                );
              })}
            </div>
          );
        }

        const icon = SECTION_ICONS[section.header] ?? "";

        return (
          <div key={si}>
            {/* Section header */}
            <div className="flex items-center gap-2 mb-2.5">
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-1">
                {icon && <span>{icon}</span>}
                {section.header}
              </span>
              <div className="flex-1 h-px bg-slate-200" />
            </div>

            <div className="space-y-1 pl-0.5">
              {section.lines.map((line, li) => {
                const trimmed = line.trim();
                if (!trimmed) return <div key={li} className="h-2" />;
                const key = `${si}-${li}`;

                // Bullet point
                if (trimmed.startsWith("•") || trimmed.startsWith("-") || trimmed.startsWith("*")) {
                  const content = trimmed.replace(/^[•\-\*]\s*/, "");
                  return (
                    <EditableLine key={key} lineKey={key} lineText={content}
                      onRefine={onRefine} isRefining={isRefining} activeKey={activeKey}
                      className="pl-3">
                      <div className="flex gap-2 items-start py-0.5">
                        <span className="text-slate-300 mt-1 shrink-0 text-xs">▸</span>
                        <span className="text-slate-700">
                          <Highlighted text={content} matchedSet={matchedSet} missingSet={missingSet} activeKeyword={activeKeyword} />
                        </span>
                      </div>
                    </EditableLine>
                  );
                }

                // Company | Title | Date
                if (trimmed.includes("|")) {
                  const parts = trimmed.split("|").map((p) => p.trim());
                  return (
                    <EditableLine key={key} lineKey={key} lineText={trimmed}
                      onRefine={onRefine} isRefining={isRefining} activeKey={activeKey}
                      className="mt-4 first:mt-0">
                      <div className="py-0.5">
                        <div className="flex flex-wrap items-baseline gap-1.5">
                          <span className="font-bold text-slate-900 text-[13px]">{parts[0]}</span>
                          {parts[1] && (
                            <span className="text-slate-600 text-xs font-medium">· {parts[1]}</span>
                          )}
                          {parts[2] && (
                            <span className="text-slate-400 text-xs ml-auto">{parts[2]}</span>
                          )}
                        </div>
                      </div>
                    </EditableLine>
                  );
                }

                // Project / bold line with em-dash
                if (trimmed.includes("—") || trimmed.includes("–")) {
                  return (
                    <EditableLine key={key} lineKey={key} lineText={trimmed}
                      onRefine={onRefine} isRefining={isRefining} activeKey={activeKey}
                      className="mt-3 first:mt-0">
                      <p className="font-semibold text-slate-800 py-0.5">
                        <Highlighted text={trimmed} matchedSet={matchedSet} missingSet={missingSet} activeKeyword={activeKeyword} />
                      </p>
                    </EditableLine>
                  );
                }

                // Default body (summary text, skill lines, etc.)
                return (
                  <EditableLine key={key} lineKey={key} lineText={trimmed}
                    onRefine={onRefine} isRefining={isRefining} activeKey={activeKey}>
                    <p className="text-slate-700 py-0.5 leading-snug">
                      <Highlighted text={trimmed} matchedSet={matchedSet} missingSet={missingSet} activeKeyword={activeKeyword} />
                    </p>
                  </EditableLine>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// JD Panel — right column, highlights keywords
// ---------------------------------------------------------------------------
function JDPanel({
  text, missing, matched, activeKeyword,
}: {
  text: string;
  missing: string[];
  matched: string[];
  activeKeyword: string | null;
}) {
  const missingSet = new Set(missing.map((k) => k.toLowerCase()));
  const matchedSet = new Set(matched.map((k) => k.toLowerCase()));

  if (!text) return <p className="text-slate-400 text-sm">No job description available.</p>;

  const words = text.split(/(\s+)/);
  return (
    <p className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-wrap">
      {words.map((w, i) => {
        const clean = w.toLowerCase().replace(/[^a-z0-9+#]/g, "");
        const isActive = activeKeyword && clean === activeKeyword.toLowerCase();
        if (isActive)
          return <mark key={i} className="bg-yellow-300 text-yellow-900 rounded px-0.5 not-italic font-semibold">{w}</mark>;
        if (missingSet.has(clean))
          return <mark key={i} className="bg-red-100 text-red-700 rounded px-0.5 not-italic">{w}</mark>;
        if (matchedSet.has(clean))
          return <mark key={i} className="bg-emerald-100 text-emerald-700 rounded px-0.5 not-italic">{w}</mark>;
        return <span key={i}>{w}</span>;
      })}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Main ResumeStudio component
// ---------------------------------------------------------------------------
export function ResumeStudio({ job, onClose }: { job: any; onClose: () => void }) {
  const [phase, setPhase] = useState<"idle" | "generating" | "editor" | "exporting">("idle");
  const [noResume, setNoResume] = useState(false);
  const [resumeText, setResumeText] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [scoreHistory, setScoreHistory] = useState<ScoreState[]>([]);
  const [atsScore, setAtsScore] = useState<ScoreState | null>(null);
  const [isScoringLoading, setIsScoringLoading] = useState(false);
  const [isRefining, setIsRefining] = useState(false);
  const [activeKey, setActiveKey] = useState<string | null>(null);
  const [refineError, setRefineError] = useState<string | null>(null);
  const [activeKeyword, setActiveKeyword] = useState<string | null>(null);

  // Fetch ATS score against JD
  const fetchScore = useCallback(async (text: string) => {
    setIsScoringLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/resume/quick-score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ resume_text: text, job_description: job.description_text }),
      });
      const data = await res.json();
      if (res.ok) {
        const s: ScoreState = { score: data.score, matched: data.matched, missing: data.missing };
        setAtsScore(s);
        setScoreHistory((prev) => [...prev, s]);
      }
    } catch { /* silent */ } finally {
      setIsScoringLoading(false);
    }
  }, [job.description_text]);

  const previousScore = scoreHistory.length >= 2
    ? scoreHistory[scoreHistory.length - 2].score
    : null;

  // Generate / regenerate
  const handleGenerate = async () => {
    const rawResume = localStorage.getItem("resume_text");
    if (!rawResume) { setNoResume(true); return; }
    setNoResume(false);
    setPhase("generating");
    setActiveKeyword(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/generate/tailored-text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: rawResume,
          job_description: job.description_text,
          job_title: job.title,
          company: job.company,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Generation failed");
      setResumeText(data.resume_text);
      setHistory([data.resume_text]);
      setScoreHistory([]);
      setAtsScore(null);
      setPhase("editor");
      fetchScore(data.resume_text);
    } catch (err: any) {
      console.error(err);
      setRefineError(err.message || "Generation failed. Please try again.");
      setPhase("idle");
    }
  };

  // Inline refinement
  const handleInlineRefine = useCallback(async ({ lineText, lineIndex, prompt }: InlineEdit) => {
    setIsRefining(true);
    setActiveKey(lineIndex);
    setRefineError(null);
    const instruction = `Find this exact line in the resume:\n"${lineText}"\n\nInstruction: ${prompt}\n\nUpdate only that line. Keep everything else exactly the same.`;
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/generate/refine-resume`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_resume: resumeText, instruction }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Refinement failed");
      setHistory((prev) => [...prev, data.resume_text]);
      setResumeText(data.resume_text);
      fetchScore(data.resume_text);
    } catch (err: any) {
      setRefineError(err.message || "Refinement failed. Please try again.");
    } finally {
      setIsRefining(false);
      setActiveKey(null);
    }
  }, [resumeText, fetchScore]);

  // Undo
  const handleUndo = () => {
    if (history.length < 2) return;
    const prev = history[history.length - 2];
    setHistory((h) => h.slice(0, -1));
    setScoreHistory((s) => s.slice(0, -1));
    setResumeText(prev);
    if (scoreHistory.length >= 2) {
      setAtsScore(scoreHistory[scoreHistory.length - 2]);
    }
  };

  // Download DOCX
  const handleDownload = async () => {
    setPhase("exporting");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/generate/tailored-docx`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          resume_text: resumeText,
          candidate_name: localStorage.getItem("candidate_name") || "",
          job_title: job.title || "",
          company: job.company || "",
        }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail); }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") || "";
      const filenameMatch = disposition.match(/filename="([^"]+)"/);
      const filename = filenameMatch?.[1] || `Resume_${job.company}.docx`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setRefineError("Download failed: " + err.message);
    } finally {
      setPhase("editor");
    }
  };

  const handleKeywordClick = (kw: string) => {
    setActiveKeyword((prev) => (prev === kw ? null : kw));
  };

  // ===== PHASE: idle =====
  if (phase === "idle") {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-6 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg">
          <Sparkles className="w-8 h-8 text-white" />
        </div>
        <div className="space-y-2">
          <p className="text-lg text-slate-700 font-semibold max-w-sm">
            Tailor your resume for <span className="font-bold text-slate-900">{job.title}</span> at{" "}
            <span className="font-bold text-slate-900">{job.company}</span>
          </p>
          <p className="text-sm text-slate-500 max-w-xs mx-auto">
            AI restructures your resume into a clean 1-page format with Professional Summary,
            Skills, Experience, and Education — then aligns it to the job description keywords.
          </p>
        </div>
        {noResume && (
          <div className="flex items-center gap-2 text-sm font-bold text-red-600 bg-red-50 px-4 py-2 rounded-lg border border-red-200">
            <AlertCircle className="w-4 h-4" /> Upload your resume in the Resume tab first.
          </div>
        )}
        <Button
          id="tailor-now-btn"
          onClick={handleGenerate}
          className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white rounded-full px-10 h-12 text-base font-bold shadow-lg shadow-indigo-200 transition-all"
        >
          <Sparkles className="w-4 h-4 mr-2" />
          Tailor Now
        </Button>
      </div>
    );
  }

  // ===== PHASE: generating =====
  if (phase === "generating") {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-5 text-center">
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg animate-pulse" />
          <Loader2 className="w-7 h-7 text-white animate-spin absolute inset-0 m-auto" />
        </div>
        <p className="text-base font-semibold text-slate-700">
          Building your tailored resume for <span className="font-bold">{job.title}</span>…
        </p>
        <p className="text-sm text-slate-400 max-w-xs">
          Restructuring into Professional Summary → Skills → Experience → Education.
          This takes 30–90 seconds.
        </p>
      </div>
    );
  }

  // ===== PHASE: editor =====
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col"
      style={{ height: "84vh" }}
    >
      {/* ── Top bar ── */}
      <div className="flex items-center justify-between px-5 py-2.5 border-b border-slate-200 bg-white shrink-0 gap-3">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <span className="text-xs font-black text-slate-800">{job.title}</span>
            <span className="text-[10px] text-slate-400">{job.company}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {/* Regenerate */}
          <Button
            id="regenerate-btn"
            variant="ghost" size="sm"
            onClick={handleGenerate}
            disabled={isRefining || phase === "exporting"}
            className="text-slate-400 hover:text-indigo-600 rounded-full text-xs gap-1.5"
          >
            <RefreshCw className="w-3 h-3" /> Regenerate
          </Button>

          {history.length > 1 && (
            <Button variant="ghost" size="sm" onClick={handleUndo} disabled={isRefining}
              className="text-slate-400 hover:text-slate-700 rounded-full text-xs gap-1">
              <RotateCcw className="w-3 h-3" /> Undo
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onClose}
            className="text-slate-400 hover:text-slate-700 rounded-full text-xs">
            Close
          </Button>
          <Button
            id="download-docx-btn"
            onClick={handleDownload}
            disabled={phase === "exporting" || isRefining}
            size="sm"
            className="bg-slate-900 hover:bg-slate-700 text-white rounded-full px-4 text-xs font-bold gap-1.5 shadow-sm"
          >
            {phase === "exporting"
              ? <><Loader2 className="w-3 h-3 animate-spin" /> Generating…</>
              : <><Download className="w-3 h-3" /> Download DOCX</>}
          </Button>
        </div>
      </div>

      {/* Error banner */}
      {refineError && (
        <div className="flex items-center gap-2 px-5 py-2 text-xs text-red-600 bg-red-50 border-b border-red-100 shrink-0">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" /> {refineError}
          <button onClick={() => setRefineError(null)} className="ml-auto">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Active keyword banner */}
      {activeKeyword && (
        <div className="flex items-center gap-2 px-5 py-1.5 text-xs text-yellow-800 bg-yellow-50 border-b border-yellow-100 shrink-0">
          <span className="font-semibold">Highlighting:</span>
          <span className="bg-yellow-300 px-1.5 py-0.5 rounded font-mono">{activeKeyword}</span>
          <button onClick={() => setActiveKeyword(null)} className="ml-auto text-yellow-600 hover:text-yellow-800">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* ── 3-column layout ── */}
      <div className="flex flex-1 overflow-hidden">

        {/* LEFT — Keyword Gap Panel */}
        <div className="w-[200px] shrink-0 border-r border-slate-200 bg-slate-50/50 overflow-hidden flex flex-col px-3 py-4">
          <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-3">
            ATS Analysis
          </p>
          <KeywordPanel
            score={atsScore}
            isLoading={isScoringLoading}
            activeKeyword={activeKeyword}
            onKeywordClick={handleKeywordClick}
            previousScore={previousScore}
          />
        </div>

        {/* CENTRE — Tailored Resume */}
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          <div className="px-6 py-2.5 border-b border-slate-100 bg-white shrink-0 flex items-center justify-between">
            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400 flex items-center gap-1.5">
              <Pencil className="w-3 h-3" /> Tailored Resume — hover any line to refine
            </p>
            {history.length > 1 && (
              <span className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full font-semibold">
                {history.length - 1} edit{history.length !== 2 ? "s" : ""}
              </span>
            )}
          </div>

          <div className="flex-1 overflow-y-auto px-8 py-7 relative">
            {/* Refining overlay */}
            {isRefining && (
              <div className="absolute inset-0 bg-white/70 z-10 flex items-center justify-center pointer-events-none">
                <div className="bg-white border border-slate-200 rounded-2xl shadow-xl px-5 py-3 flex items-center gap-3">
                  <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
                  <span className="text-sm font-semibold text-slate-700">Applying refinement…</span>
                </div>
              </div>
            )}

            <AnimatePresence mode="wait">
              <motion.div
                key={resumeText.slice(0, 80)}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <ResumeRenderer
                  text={resumeText}
                  onRefine={handleInlineRefine}
                  isRefining={isRefining}
                  activeKey={activeKey}
                  matchedKeywords={atsScore?.matched ?? []}
                  missingKeywords={atsScore?.missing ?? []}
                  activeKeyword={activeKeyword}
                />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* RIGHT — Job Description */}
        <div className="w-[260px] shrink-0 border-l border-slate-200 flex flex-col overflow-hidden">
          <div className="px-4 py-2.5 border-b border-slate-100 bg-slate-50 shrink-0">
            <p className="text-[9px] font-black uppercase tracking-widest text-slate-400">
              Job Description
            </p>
          </div>

          {atsScore && (atsScore.missing.length > 0 || atsScore.matched.length > 0) && (
            <div className="px-4 py-2 border-b border-slate-100 bg-white shrink-0">
              <div className="flex gap-3 text-[10px] text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-sm bg-red-200" /> Missing
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block w-2 h-2 rounded-sm bg-emerald-200" /> Matched
                </span>
                {activeKeyword && (
                  <span className="flex items-center gap-1">
                    <span className="inline-block w-2 h-2 rounded-sm bg-yellow-300" /> Active
                  </span>
                )}
              </div>
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 py-4">
            <JDPanel
              text={job.description_text}
              missing={atsScore?.missing ?? []}
              matched={atsScore?.matched ?? []}
              activeKeyword={activeKeyword}
            />
          </div>
        </div>
      </div>
    </motion.div>
  );
}
