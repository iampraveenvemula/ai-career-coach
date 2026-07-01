"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp, FileText, Briefcase, Award,
  Clock, CheckCircle2, XCircle, BarChart3,
  ArrowUpRight, Target, Zap, Users, Loader2,
} from "lucide-react";
import { API_BASE_URL } from "@/lib/config";

// ---------------------------------------------------------------------------
// Styling and Icon Configurations
// ---------------------------------------------------------------------------
const STAT_CONFIG: Record<string, { icon: any; color: string; bg: string; text: string }> = {
  "stat-applications":  { icon: FileText,   color: "from-violet-500 to-indigo-500", bg: "bg-violet-50",   text: "text-violet-600" },
  "stat-avg-ats":       { icon: Target,     color: "from-emerald-500 to-teal-500", bg: "bg-emerald-50",  text: "text-emerald-600" },
  "stat-interviews":    { icon: Users,      color: "from-sky-500 to-cyan-500",    bg: "bg-sky-50",      text: "text-sky-600" },
  "stat-response-rate": { icon: Zap,        color: "from-amber-500 to-orange-500", bg: "bg-amber-50",    text: "text-amber-600" },
};

const STATUS_CONFIG: Record<string, { color: string; light: string; text: string; icon: any }> = {
  Offer:          { color: "bg-emerald-500", light: "bg-emerald-50", text: "text-emerald-700", icon: Award },
  Interviewing:   { color: "bg-sky-500",     light: "bg-sky-50",     text: "text-sky-700",     icon: Users },
  Applied:        { color: "bg-violet-500",  light: "bg-violet-50",  text: "text-violet-700",  icon: CheckCircle2 },
  Saved:          { color: "bg-slate-400",   light: "bg-slate-50",   text: "text-slate-600",   icon: Briefcase },
  Rejected:       { color: "bg-red-400",     light: "bg-red-50",     text: "text-red-600",     icon: XCircle },
};

const DEFAULT_SKILL_GAPS = [
  { skill: "Kubernetes",      coverage: 40 },
  { skill: "Rust",            coverage: 15 },
  { skill: "MLOps (Kubeflow)", coverage: 55 },
  { skill: "JAX",             coverage: 30 },
  { skill: "Terraform",       coverage: 60 },
];

// ---------------------------------------------------------------------------
// Inline bar chart for ATS history
// ---------------------------------------------------------------------------
function ATSChart({ history }: { history: any[] }) {
  if (!history || history.length === 0) return null;
  const maxScore = Math.max(...history.map((d) => d.score), 1);

  return (
    <div className="flex items-end gap-2 h-24 mt-4">
      {history.map((d, i) => {
        const height = (d.score / maxScore) * 100;
        const isLast = i === history.length - 1;
        return (
          <div key={d.week} className="flex-1 flex flex-col items-center gap-1.5">
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: `${height}%` }}
              transition={{ duration: 0.6, delay: i * 0.06, ease: "easeOut" }}
              className={`w-full rounded-t-md ${
                isLast ? "bg-gradient-to-t from-violet-600 to-indigo-500" : "bg-slate-200"
              }`}
              style={{ minHeight: 4 }}
            />
            <span className={`text-[10px] font-semibold ${isLast ? "text-violet-600" : "text-slate-400"}`}>
              {d.week}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Status badge helper
// ---------------------------------------------------------------------------
function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status];
  if (!cfg) return <span className="text-xs text-slate-400">{status}</span>;
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.light} ${cfg.text}`}>
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// ATS score color helper
// ---------------------------------------------------------------------------
function atsColor(score: number) {
  if (score >= 80) return "text-emerald-600";
  if (score >= 65) return "text-sky-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-500";
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export function AnalyticsDashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/v1/analytics/dashboard`);
        const json = await res.json();
        setData(json);
      } catch (err) {
        console.error("Failed to load analytics", err);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-32 space-y-3">
        <Loader2 className="w-8 h-8 text-violet-600 animate-spin" />
        <p className="text-sm font-medium text-slate-500">Loading analytics dashboard...</p>
      </div>
    );
  }

  const pipelineBreakdown = data?.pipeline_breakdown || [];
  const total = pipelineBreakdown.reduce((a: number, s: any) => a + s.count, 0);

  if (total === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-md mx-auto text-center py-20 px-6 bg-white border border-slate-200 rounded-3xl shadow-sm space-y-6"
      >
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-violet-50 text-violet-600">
          <BarChart3 className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-slate-900">Your Dashboard is Empty</h3>
          <p className="text-slate-500 text-sm max-w-xs mx-auto">
            You haven't tracked any applications yet. Go to the Jobs tab, select a position, and click "Tailor Now" to save or mark it as applied!
          </p>
        </div>
      </motion.div>
    );
  }

  const summaryStats = data?.summary_stats || [];
  const recentApplications = data?.recent_applications || [];
  const atsHistory = data?.ats_history || [];

  return (
    <div className="space-y-6 pb-6">
      {/* ── Summary stats ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {summaryStats.map((stat: any, i: number) => {
          const config = STAT_CONFIG[stat.id] || { icon: FileText, color: "from-slate-500 to-slate-600", bg: "bg-slate-50", text: "text-slate-600" };
          const Icon = config.icon;
          return (
            <motion.div
              key={stat.id}
              id={stat.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm"
            >
              <div className={`inline-flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br ${config.color} mb-3`}>
                <Icon className="w-4 h-4 text-white" />
              </div>
              <p className="text-2xl font-black text-slate-900">{stat.value}</p>
              <p className="text-xs text-slate-500 mt-0.5">{stat.label}</p>
              <div className={`flex items-center gap-1 mt-1.5 text-xs font-semibold ${stat.positive ? "text-emerald-600" : "text-red-500"}`}>
                <ArrowUpRight className="w-3 h-3" />
                {stat.delta}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* ── Row 2: ATS Chart + Status Breakdown ──────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* ATS Score trend */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm"
        >
          <div className="flex items-center justify-between mb-1">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">ATS Score Trend</h4>
              <p className="text-xs text-slate-400">8-week campaign</p>
            </div>
            <div className="flex items-center gap-1 text-emerald-600 text-xs font-semibold bg-emerald-50 px-2 py-1 rounded-full">
              <TrendingUp className="w-3 h-3" />
              Progressive matches
            </div>
          </div>
          <ATSChart history={atsHistory} />
        </motion.div>

        {/* Status breakdown */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">Application Pipeline</h4>
              <p className="text-xs text-slate-400">{total} total applications</p>
            </div>
            <BarChart3 className="w-4 h-4 text-slate-400" />
          </div>

          <div className="space-y-3">
            {pipelineBreakdown.map((s: any) => {
              const config = STATUS_CONFIG[s.status] || STATUS_CONFIG.Saved;
              const Icon = config.icon;
              const pct = Math.round((s.count / total) * 100);
              return (
                <div key={s.status} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <Icon className={`w-3.5 h-3.5 ${config.text}`} />
                      <span className="font-medium text-slate-600">{s.status}</span>
                    </div>
                    <span className="font-bold text-slate-700">{s.count}</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.7, ease: "easeOut", delay: 0.4 }}
                      className={`h-full rounded-full ${config.color}`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </motion.div>
      </div>

      {/* ── Row 3: Recent Applications + Skill Gaps ──────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent applications table */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden"
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">Recent Applications</h4>
              <p className="text-xs text-slate-400">Sorted by recency</p>
            </div>
            <Briefcase className="w-4 h-4 text-slate-400" />
          </div>
          <div className="divide-y divide-slate-50">
            {recentApplications.map((app: any, i: number) => (
              <motion.div
                key={i}
                id={`app-row-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + i * 0.05 }}
                className="flex items-center justify-between px-5 py-3 hover:bg-slate-50 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-800 truncate">{app.role}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    <span>{app.company}</span>
                    <span className="text-slate-300">·</span>
                    <Clock className="w-3 h-3" />
                    <span>{app.daysAgo === 0 ? "Today" : `${app.daysAgo}d ago`}</span>
                  </p>
                </div>
                <div className="flex items-center gap-3 shrink-0 ml-3">
                  <span className={`text-sm font-black tabular-nums ${atsColor(app.ats)}`}>
                    {app.ats}%
                  </span>
                  <StatusBadge status={app.status} />
                </div>
              </motion.div>
            ))}

            {recentApplications.length === 0 && (
              <p className="text-sm text-slate-400 text-center py-8">No recent applications.</p>
            )}
          </div>
        </motion.div>

        {/* Skill gaps */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm"
        >
          <div className="flex items-center justify-between mb-4">
            <div>
              <h4 className="font-bold text-slate-800 text-sm">Skill Gaps</h4>
              <p className="text-xs text-slate-400">Top missing skills</p>
            </div>
            <Target className="w-4 h-4 text-slate-400" />
          </div>

          <div className="space-y-3.5">
            {DEFAULT_SKILL_GAPS.map((s, i) => (
              <div key={i} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-slate-600 truncate">{s.skill}</span>
                  <span className={`font-bold tabular-nums ${s.coverage < 40 ? "text-red-500" : s.coverage < 60 ? "text-amber-600" : "text-emerald-600"}`}>
                    {s.coverage}%
                  </span>
                </div>
                <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${s.coverage}%` }}
                    transition={{ duration: 0.8, ease: "easeOut", delay: 0.55 + i * 0.06 }}
                    className={`h-full rounded-full ${
                      s.coverage < 40 ? "bg-red-400" : s.coverage < 60 ? "bg-amber-400" : "bg-emerald-400"
                    }`}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 pt-4 border-t border-slate-100">
            <p className="text-xs text-slate-500 leading-relaxed">
              💡 <span className="font-medium text-slate-700">Focus on Kubernetes & JAX</span> — they appear in 72% of your target roles but score lowest in your resume.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
