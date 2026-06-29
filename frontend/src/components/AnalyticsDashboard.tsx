"use client";

import { motion } from "framer-motion";
import {
  TrendingUp, FileText, Briefcase, Award,
  Clock, CheckCircle2, XCircle, BarChart3,
  ArrowUpRight, Target, Zap, Users,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Mock analytics data — realistic snapshot of a job search campaign
// ---------------------------------------------------------------------------
const SUMMARY_STATS = [
  {
    id: "stat-applications",
    label: "Applications Sent",
    value: 24,
    delta: "+6 this week",
    positive: true,
    icon: FileText,
    color: "from-violet-500 to-indigo-500",
    bg: "bg-violet-50",
    text: "text-violet-600",
  },
  {
    id: "stat-avg-ats",
    label: "Average ATS Score",
    value: "78%",
    delta: "+12% from start",
    positive: true,
    icon: Target,
    color: "from-emerald-500 to-teal-500",
    bg: "bg-emerald-50",
    text: "text-emerald-600",
  },
  {
    id: "stat-interviews",
    label: "Interviews Scheduled",
    value: 5,
    delta: "2 this week",
    positive: true,
    icon: Users,
    color: "from-sky-500 to-cyan-500",
    bg: "bg-sky-50",
    text: "text-sky-600",
  },
  {
    id: "stat-response-rate",
    label: "Response Rate",
    value: "21%",
    delta: "+4% from avg",
    positive: true,
    icon: Zap,
    color: "from-amber-500 to-orange-500",
    bg: "bg-amber-50",
    text: "text-amber-600",
  },
];

const ATS_HISTORY = [
  { week: "W1", score: 52 },
  { week: "W2", score: 61 },
  { week: "W3", score: 65 },
  { week: "W4", score: 71 },
  { week: "W5", score: 75 },
  { week: "W6", score: 78 },
  { week: "W7", score: 84 },
  { week: "W8", score: 82 },
];

const STATUS_BREAKDOWN = [
  { status: "Offer",       count: 1,  color: "bg-emerald-500", light: "bg-emerald-50", text: "text-emerald-700", icon: Award },
  { status: "Interviewing", count: 5,  color: "bg-sky-500",     light: "bg-sky-50",     text: "text-sky-700",     icon: Users },
  { status: "Applied",     count: 11, color: "bg-violet-500",  light: "bg-violet-50",  text: "text-violet-700",  icon: CheckCircle2 },
  { status: "Saved",       count: 5,  color: "bg-slate-400",   light: "bg-slate-50",   text: "text-slate-600",   icon: Briefcase },
  { status: "Rejected",    count: 2,  color: "bg-red-400",     light: "bg-red-50",     text: "text-red-600",     icon: XCircle },
];

const RECENT_APPLICATIONS = [
  { company: "Anthropic",      role: "GenAI Platform Engineer", ats: 91, status: "Interviewing", daysAgo: 2 },
  { company: "OpenAI",         role: "Senior AI Engineer",      ats: 86, status: "Applied",      daysAgo: 4 },
  { company: "Google DeepMind", role: "ML Engineer",            ats: 82, status: "Interviewing", daysAgo: 5 },
  { company: "Cohere",         role: "NLP Engineer",            ats: 78, status: "Applied",      daysAgo: 7 },
  { company: "Spotify",        role: "Data Scientist",          ats: 74, status: "Applied",      daysAgo: 9 },
  { company: "Meta",           role: "Applied AI Scientist",    ats: 70, status: "Rejected",     daysAgo: 12 },
];

const SKILL_GAPS = [
  { skill: "Kubernetes",      coverage: 40 },
  { skill: "Rust",            coverage: 15 },
  { skill: "MLOps (Kubeflow)", coverage: 55 },
  { skill: "JAX",             coverage: 30 },
  { skill: "Terraform",       coverage: 60 },
];

// ---------------------------------------------------------------------------
// Inline bar chart for ATS history
// ---------------------------------------------------------------------------
function ATSChart() {
  const maxScore = Math.max(...ATS_HISTORY.map((d) => d.score));

  return (
    <div className="flex items-end gap-2 h-24 mt-4">
      {ATS_HISTORY.map((d, i) => {
        const height = (d.score / maxScore) * 100;
        const isLast = i === ATS_HISTORY.length - 1;
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
  const cfg = STATUS_BREAKDOWN.find((s) => s.status === status);
  if (!cfg) return <span className="text-xs text-slate-400">{status}</span>;
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.light} ${cfg.text}`}>
      {status}
    </span>
  );
}

// ---------------------------------------------------------------------------
// ATS score color
// ---------------------------------------------------------------------------
function atsColor(score: number) {
  if (score >= 80) return "text-emerald-600";
  if (score >= 65) return "text-sky-600";
  if (score >= 50) return "text-amber-600";
  return "text-red-500";
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export function AnalyticsDashboard() {
  const total = STATUS_BREAKDOWN.reduce((a, s) => a + s.count, 0);

  return (
    <div className="space-y-6 pb-6">
      {/* ── Summary stats ────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {SUMMARY_STATS.map((stat, i) => {
          const Icon = stat.icon;
          return (
            <motion.div
              key={stat.id}
              id={stat.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07 }}
              className="bg-white rounded-2xl border border-slate-200 p-4 shadow-sm"
            >
              <div className={`inline-flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br ${stat.color} mb-3`}>
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
              +30pts
            </div>
          </div>
          <ATSChart />
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
            {STATUS_BREAKDOWN.map((s) => {
              const Icon = s.icon;
              const pct = Math.round((s.count / total) * 100);
              return (
                <div key={s.status} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <Icon className={`w-3.5 h-3.5 ${s.text}`} />
                      <span className="font-medium text-slate-600">{s.status}</span>
                    </div>
                    <span className="font-bold text-slate-700">{s.count}</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${pct}%` }}
                      transition={{ duration: 0.7, ease: "easeOut", delay: 0.4 }}
                      className={`h-full rounded-full ${s.color}`}
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
            {RECENT_APPLICATIONS.map((app, i) => (
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
                    <span>{app.daysAgo}d ago</span>
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
          </div>
        </motion.div>

        {/* Skill gap radar */}
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
            {SKILL_GAPS.map((s, i) => (
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
