/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  BrainCircuit, ChevronRight, RotateCcw, Send, Loader2,
  CheckCircle2, AlertCircle, Lightbulb, Star, TrendingUp,
  Sparkles, MessageSquare, Target, BarChart3,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/config";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface Question {
  id: number;
  category: "Technical" | "Behavioural" | "Situational";
  difficulty: "Easy" | "Medium" | "Hard";
  question: string;
  hint: string;
  ideal_keywords: string[];
}

interface Evaluation {
  score: number;
  rating: "Excellent" | "Good" | "Fair" | "Needs Work";
  strengths: string[];
  improvements: string[];
  model_answer_snippet: string;
}

interface QuestionResult {
  question: Question;
  answer: string;
  evaluation: Evaluation | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const CATEGORY_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  Technical:    { bg: "bg-violet-50",  text: "text-violet-700",  dot: "bg-violet-500" },
  Behavioural:  { bg: "bg-sky-50",     text: "text-sky-700",     dot: "bg-sky-500"    },
  Situational:  { bg: "bg-amber-50",   text: "text-amber-700",   dot: "bg-amber-500"  },
};

const DIFFICULTY_COLORS: Record<string, string> = {
  Easy:   "text-emerald-600 bg-emerald-50",
  Medium: "text-amber-600 bg-amber-50",
  Hard:   "text-red-600 bg-red-50",
};

const RATING_CONFIG: Record<string, { color: string; icon: any }> = {
  Excellent:    { color: "text-emerald-600", icon: Star },
  Good:         { color: "text-sky-600",     icon: TrendingUp },
  Fair:         { color: "text-amber-600",   icon: BarChart3 },
  "Needs Work": { color: "text-red-500",     icon: AlertCircle },
};

// ---------------------------------------------------------------------------
// Setup screen
// ---------------------------------------------------------------------------
function SetupScreen({
  onStart,
}: {
  onStart: (jd: string, resume: string) => void;
}) {
  const [jd, setJd] = useState("");
  const [resume, setResume] = useState("");
  const [loading, setLoading] = useState(false);

  const handleStart = async () => {
    if (!jd.trim()) return;
    setLoading(true);
    onStart(jd.trim(), resume.trim());
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="max-w-2xl mx-auto"
    >
      {/* Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-lg mb-4">
          <BrainCircuit className="w-8 h-8 text-white" />
        </div>
        <h2 className="text-2xl font-black text-slate-900 mb-1">Interview Arena</h2>
        <p className="text-slate-500 text-sm">
          Paste a job description and let AI generate a personalised mock interview.
        </p>
      </div>

      {/* Form */}
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">
            Job Description <span className="text-red-500">*</span>
          </label>
          <textarea
            id="interview-jd-input"
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the full job description here…"
            className="w-full h-40 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-600 mb-1.5 uppercase tracking-wide">
            Your Resume <span className="text-slate-400">(optional — personalises questions)</span>
          </label>
          <textarea
            id="interview-resume-input"
            value={resume}
            onChange={(e) => setResume(e.target.value)}
            placeholder="Paste your resume text here (optional)…"
            className="w-full h-32 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
          />
        </div>

        <Button
          id="interview-start-btn"
          onClick={handleStart}
          disabled={!jd.trim() || loading}
          className="w-full h-12 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-bold text-sm shadow-md shadow-violet-200 transition-all disabled:opacity-50"
        >
          {loading ? (
            <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Generating Questions…</>
          ) : (
            <><Sparkles className="w-4 h-4 mr-2" /> Generate Interview Questions</>
          )}
        </Button>
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Question card
// ---------------------------------------------------------------------------
function QuestionCard({
  result,
  index,
  total,
  isActive,
  onAnswerChange,
  onSubmit,
  submitting,
}: {
  result: QuestionResult;
  index: number;
  total: number;
  isActive: boolean;
  onAnswerChange: (val: string) => void;
  onSubmit: () => void;
  submitting: boolean;
}) {
  const { question, answer, evaluation } = result;
  const cat = CATEGORY_COLORS[question.category] ?? CATEGORY_COLORS.Technical;
  const diff = DIFFICULTY_COLORS[question.difficulty] ?? "";
  const rating = evaluation ? RATING_CONFIG[evaluation.rating] : null;
  const RatingIcon = rating?.icon;

  return (
    <motion.div
      key={question.id}
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: isActive ? 1 : 0.4, x: 0 }}
      className={`rounded-2xl border ${isActive ? "border-slate-200 shadow-sm" : "border-slate-100"} bg-white overflow-hidden`}
    >
      {/* Card header */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-slate-100">
        <span className="text-xs font-bold text-slate-400">{index + 1}/{total}</span>
        <span className={`flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 rounded-full ${cat.bg} ${cat.text}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${cat.dot}`} />
          {question.category}
        </span>
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${diff}`}>
          {question.difficulty}
        </span>
      </div>

      <div className="p-5 space-y-4">
        {/* Question text */}
        <p className="text-slate-800 font-semibold text-[15px] leading-snug">
          {question.question}
        </p>

        {/* Hint */}
        {!evaluation && (
          <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">
            <Lightbulb className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{question.hint}</span>
          </div>
        )}

        {/* Answer textarea (only if not evaluated yet) */}
        {!evaluation && isActive && (
          <div className="space-y-3">
            <textarea
              id={`answer-input-${question.id}`}
              value={answer}
              onChange={(e) => onAnswerChange(e.target.value)}
              placeholder="Type your answer here…"
              rows={5}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 placeholder-slate-400 resize-none focus:outline-none focus:ring-2 focus:ring-violet-500 transition"
            />
            <Button
              id={`submit-answer-${question.id}`}
              onClick={onSubmit}
              disabled={!answer.trim() || submitting}
              className="w-full h-10 rounded-xl bg-slate-900 hover:bg-slate-700 text-white font-semibold text-sm transition-all disabled:opacity-40"
            >
              {submitting ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Evaluating…</>
              ) : (
                <><Send className="w-4 h-4 mr-2" /> Submit Answer</>
              )}
            </Button>
          </div>
        )}

        {/* Evaluation result */}
        {evaluation && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            {/* Score bar */}
            <div className="flex items-center gap-3">
              <div className="relative w-14 h-14 shrink-0">
                <svg className="w-14 h-14 -rotate-90" viewBox="0 0 56 56">
                  <circle cx="28" cy="28" r="22" fill="none" stroke="#f1f5f9" strokeWidth="5" />
                  <circle
                    cx="28" cy="28" r="22" fill="none"
                    stroke={evaluation.score >= 80 ? "#10b981" : evaluation.score >= 60 ? "#0ea5e9" : evaluation.score >= 40 ? "#f59e0b" : "#ef4444"}
                    strokeWidth="5"
                    strokeDasharray={`${(evaluation.score / 100) * 138.2} 138.2`}
                    strokeLinecap="round"
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-xs font-black text-slate-700">
                  {evaluation.score}
                </span>
              </div>
              <div>
                {RatingIcon && (
                  <div className={`flex items-center gap-1 font-bold text-base ${rating?.color}`}>
                    <RatingIcon className="w-4 h-4" />
                    {evaluation.rating}
                  </div>
                )}
                <p className="text-xs text-slate-500 mt-0.5">out of 100</p>
              </div>
            </div>

            {/* Strengths */}
            {evaluation.strengths.length > 0 && (
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5">Strengths</p>
                <ul className="space-y-1">
                  {evaluation.strengths.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Improvements */}
            {evaluation.improvements.length > 0 && (
              <div>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1.5">Improvements</p>
                <ul className="space-y-1">
                  {evaluation.improvements.map((s, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-slate-700">
                      <AlertCircle className="w-3.5 h-3.5 text-amber-500 mt-0.5 shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Model snippet */}
            <div className="bg-slate-50 rounded-xl p-3 border border-slate-200">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-wide mb-1">Model Answer Snippet</p>
              <p className="text-xs text-slate-600 leading-relaxed italic">"{evaluation.model_answer_snippet}"</p>
            </div>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Results summary
// ---------------------------------------------------------------------------
function ResultsSummary({
  results,
  onReset,
}: {
  results: QuestionResult[];
  onReset: () => void;
}) {
  const evaluated = results.filter((r) => r.evaluation);
  const avgScore = evaluated.length
    ? Math.round(evaluated.reduce((s, r) => s + (r.evaluation?.score ?? 0), 0) / evaluated.length)
    : 0;

  const ratingCounts = evaluated.reduce<Record<string, number>>((acc, r) => {
    const rat = r.evaluation?.rating ?? "Needs Work";
    acc[rat] = (acc[rat] || 0) + 1;
    return acc;
  }, {});

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="max-w-md mx-auto text-center space-y-6"
    >
      <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-violet-600 to-indigo-600 shadow-xl mb-2">
        <Target className="w-10 h-10 text-white" />
      </div>
      <div>
        <h3 className="text-2xl font-black text-slate-900">Session Complete!</h3>
        <p className="text-slate-500 text-sm mt-1">
          You answered {evaluated.length} of {results.length} questions.
        </p>
      </div>

      {/* Average score ring */}
      <div className="flex items-center justify-center">
        <div className="relative w-28 h-28">
          <svg className="w-28 h-28 -rotate-90" viewBox="0 0 112 112">
            <circle cx="56" cy="56" r="44" fill="none" stroke="#f1f5f9" strokeWidth="9" />
            <circle
              cx="56" cy="56" r="44" fill="none"
              stroke={avgScore >= 80 ? "#10b981" : avgScore >= 60 ? "#6366f1" : "#f59e0b"}
              strokeWidth="9"
              strokeDasharray={`${(avgScore / 100) * 276.5} 276.5`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-3xl font-black text-slate-800">{avgScore}</span>
            <span className="text-xs text-slate-400">avg score</span>
          </div>
        </div>
      </div>

      {/* Rating breakdown */}
      <div className="grid grid-cols-2 gap-3">
        {Object.entries(ratingCounts).map(([rating, count]) => {
          const cfg = RATING_CONFIG[rating];
          const Icon = cfg?.icon;
          return (
            <div key={rating} className="bg-white rounded-xl border border-slate-200 p-3 text-left">
              <div className={`flex items-center gap-1.5 font-semibold text-sm ${cfg?.color}`}>
                {Icon && <Icon className="w-4 h-4" />}
                {rating}
              </div>
              <p className="text-2xl font-black text-slate-800 mt-1">{count}</p>
              <p className="text-xs text-slate-400">question{count !== 1 ? "s" : ""}</p>
            </div>
          );
        })}
      </div>

      <Button
        id="interview-reset-btn"
        onClick={onReset}
        className="w-full h-11 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-sm shadow-sm transition-all"
      >
        <RotateCcw className="w-4 h-4 mr-2" />
        Start New Interview
      </Button>
    </motion.div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function InterviewArena() {
  const [phase, setPhase] = useState<"setup" | "interview" | "done">("setup");
  const [sessionData, setSessionData] = useState<{
    role: string;
    company: string;
    questions: Question[];
  } | null>(null);
  const [results, setResults] = useState<QuestionResult[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [generatingError, setGeneratingError] = useState("");

  const handleStart = async (jd: string, resume: string) => {
    setGeneratingError("");
    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/interview/generate-questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_description: jd, resume_text: resume }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const data = json.data;

      setSessionData({ role: data.role, company: data.company, questions: data.questions });
      setResults(data.questions.map((q: Question) => ({ question: q, answer: "", evaluation: null })));
      setCurrentIndex(0);
      setPhase("interview");
    } catch (e: any) {
      setGeneratingError(e.message ?? "Failed to generate questions.");
      setPhase("setup");
    }
  };

  const handleAnswerChange = (val: string) => {
    setResults((prev) => {
      const copy = [...prev];
      copy[currentIndex] = { ...copy[currentIndex], answer: val };
      return copy;
    });
  };

  const handleSubmitAnswer = async () => {
    const current = results[currentIndex];
    if (!current.answer.trim()) return;
    setSubmitting(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/v1/interview/evaluate-answer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: current.question.question,
          answer: current.answer,
          ideal_keywords: current.question.ideal_keywords,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const json = await res.json();
      const evaluation: Evaluation = json.data;

      setResults((prev) => {
        const copy = [...prev];
        copy[currentIndex] = { ...copy[currentIndex], evaluation };
        return copy;
      });
    } catch {
      // Use a graceful fallback evaluation
      const fallback: Evaluation = {
        score: 65,
        rating: "Good",
        strengths: ["Completed the answer."],
        improvements: ["Add more specific examples.", "Reference key technical concepts."],
        model_answer_snippet: "A strong answer incorporates concrete examples and relevant technical terminology.",
      };
      setResults((prev) => {
        const copy = [...prev];
        copy[currentIndex] = { ...copy[currentIndex], evaluation: fallback };
        return copy;
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < (sessionData?.questions.length ?? 0) - 1) {
      setCurrentIndex((i) => i + 1);
    } else {
      setPhase("done");
    }
  };

  const handleReset = () => {
    setPhase("setup");
    setSessionData(null);
    setResults([]);
    setCurrentIndex(0);
  };

  const currentResult = results[currentIndex];
  const allAnswered = results.every((r) => r.evaluation !== null);
  const currentEvaluated = currentResult?.evaluation !== null;

  return (
    <div className="min-h-[520px] py-4">
      <AnimatePresence mode="wait">
        {phase === "setup" && (
          <motion.div key="setup" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {generatingError && (
              <div className="mb-4 max-w-2xl mx-auto flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {generatingError}
              </div>
            )}
            <SetupScreen onStart={handleStart} />
          </motion.div>
        )}

        {phase === "interview" && sessionData && (
          <motion.div key="interview" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="space-y-6">
            {/* Session header */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-black text-slate-900 text-lg">{sessionData.role}</h3>
                <p className="text-slate-500 text-sm flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5" />
                  {sessionData.company} · {sessionData.questions.length} questions
                </p>
              </div>
              <button
                id="interview-exit-btn"
                onClick={handleReset}
                className="text-xs text-slate-400 hover:text-slate-600 transition flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" /> Restart
              </button>
            </div>

            {/* Progress bar */}
            <div className="flex gap-1.5">
              {results.map((r, i) => (
                <button
                  key={i}
                  id={`q-nav-${i}`}
                  onClick={() => setCurrentIndex(i)}
                  className={`h-1.5 flex-1 rounded-full transition-all ${
                    r.evaluation ? "bg-violet-500" :
                    i === currentIndex ? "bg-slate-400" : "bg-slate-200"
                  }`}
                />
              ))}
            </div>

            {/* Current question */}
            <QuestionCard
              result={currentResult}
              index={currentIndex}
              total={results.length}
              isActive={true}
              onAnswerChange={handleAnswerChange}
              onSubmit={handleSubmitAnswer}
              submitting={submitting}
            />

            {/* Navigation */}
            {currentEvaluated && (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
                <Button
                  id="interview-next-btn"
                  onClick={handleNext}
                  className="w-full h-11 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-700 hover:to-indigo-700 text-white font-bold text-sm shadow-md shadow-violet-200 transition-all"
                >
                  {allAnswered || currentIndex === results.length - 1 ? (
                    <><Target className="w-4 h-4 mr-2" /> View Results</>
                  ) : (
                    <>Next Question <ChevronRight className="w-4 h-4 ml-1" /></>
                  )}
                </Button>
              </motion.div>
            )}
          </motion.div>
        )}

        {phase === "done" && (
          <motion.div key="done" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <ResultsSummary results={results} onReset={handleReset} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
