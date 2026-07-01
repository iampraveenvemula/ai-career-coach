/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, RefreshCw, ExternalLink, Briefcase, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { API_BASE_URL } from "@/lib/config";
import { ResumeStudio } from "@/components/ResumeStudio";

const SOURCE_COLORS: Record<string, string> = {
  Seed: "bg-slate-100 text-slate-600 border-slate-200",
  Remotive: "bg-purple-50 text-purple-700 border-purple-200",
  LinkedIn: "bg-blue-50 text-blue-700 border-blue-200",
  Google: "bg-amber-50 text-amber-700 border-amber-200",
};

export function JobSearch() {
  const [query, setQuery] = useState("");
  const [jobs, setJobs] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isScraping, setIsScraping] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState("");
  const [selectedJob, setSelectedJob] = useState<any | null>(null);

  const fetchJobs = async (searchQuery: string) => {
    setIsSearching(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/search?query=${encodeURIComponent(searchQuery)}`);
      const data = await response.json();
      const results = data.results || [];
      setJobs(results);
    } catch (error) {
      console.error("Error fetching jobs:", error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleScrape = async () => {
    const searchTerm = query || "AI Engineer";
    setIsScraping(true);
    setScrapeMsg("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/scrape?query=${encodeURIComponent(searchTerm)}`, { method: "POST" });
      const data = await response.json();
      setScrapeMsg(data.message);
      // Refresh results after scraping
      await fetchJobs(query);
    } catch (error) {
      setScrapeMsg("Scrape failed.");
    } finally {
      setIsScraping(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Are you sure you want to clear all jobs from the database and vector index?")) return;
    setIsClearing(true);
    setScrapeMsg("");
    try {
      await fetch(`${API_BASE_URL}/api/v1/jobs/clear`, { method: "POST" });
      setScrapeMsg("Database cleared.");
      setJobs([]);
      setSelectedJob(null);
    } catch (error) {
      setScrapeMsg("Clear failed.");
    } finally {
      setIsClearing(false);
    }
  };

  useEffect(() => {
    fetchJobs("");
  }, []);

  // Auto-select the first job on initial load or search update
  useEffect(() => {
    if (jobs.length > 0) {
      // Keep existing selection if it still exists in the new list, otherwise select the first one
      const exists = jobs.find((j) => j.id === selectedJob?.id);
      if (!exists) {
        setSelectedJob(jobs[0]);
      }
    } else {
      setSelectedJob(null);
    }
  }, [jobs]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs(query);
  };

  return (
    <div className="w-full flex gap-5" style={{ height: "82vh" }}>
      {/* LEFT PANEL — Job Listings List */}
      <div className="w-[30%] min-w-[290px] max-w-[350px] shrink-0 h-full flex flex-col overflow-hidden border-r border-slate-200 pr-4">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex gap-2 mb-3 shrink-0">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <Input 
              type="text" 
              placeholder="Search roles or skills..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="pl-9 pr-3 bg-white border-slate-200 text-slate-900 h-10 text-xs font-semibold rounded-full focus-visible:ring-1 focus-visible:ring-indigo-500 shadow-sm"
            />
          </div>
          <Button type="submit" disabled={isSearching} className="h-10 px-4 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-xs font-bold shrink-0">
            {isSearching ? "..." : "Search"}
          </Button>
        </form>

        {/* Scrape Controls */}
        <div className="flex flex-col gap-2 mb-4 shrink-0">
          <div className="flex gap-2">
            <Button
              onClick={handleScrape}
              disabled={isScraping || isClearing}
              variant="outline"
              className="flex-1 h-8 rounded-full text-[10px] font-bold border-slate-300 text-slate-700 hover:border-slate-500 hover:bg-slate-50"
            >
              <RefreshCw className={`w-3 h-3 mr-1 ${isScraping ? "animate-spin" : ""}`} />
              {isScraping ? "Fetching..." : "Fetch Jobs"}
            </Button>
            <Button
              onClick={handleClear}
              disabled={isScraping || isClearing}
              variant="destructive"
              className="h-8 px-3 rounded-full text-[10px] font-bold bg-red-50 text-red-600 hover:bg-red-100 hover:text-red-750 border border-red-200"
            >
              Clear DB
            </Button>
          </div>
          {scrapeMsg && (
            <span className="text-[10px] font-semibold text-slate-500 truncate text-center">{scrapeMsg}</span>
          )}
        </div>

        {/* Vertical Scrollable Jobs List */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 content-start">
          {jobs.map((job, idx) => {
            const isSelected = selectedJob?.id === job.id;
            return (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: Math.min(idx * 0.02, 0.2), duration: 0.2 }}
                onClick={() => setSelectedJob(job)}
                className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                  isSelected
                    ? "border-indigo-500 bg-indigo-50/20 shadow-sm ring-1 ring-indigo-500"
                    : "border-slate-200 bg-white hover:bg-slate-50/70"
                }`}
              >
                <div className="flex items-start justify-between gap-1.5 mb-1.5">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest truncate max-w-[120px]">
                    {job.company}
                  </p>
                  <span className={`text-[8px] font-black uppercase tracking-widest px-1.5 py-0.5 rounded border shrink-0 ${SOURCE_COLORS[job.source] || SOURCE_COLORS.Seed}`}>
                    {job.source}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-slate-900 leading-snug line-clamp-1 mb-2">
                  {job.title}
                </h3>
                <div className="flex items-baseline justify-between gap-1 text-[11px] text-slate-500 font-semibold mb-2">
                  <span className="truncate">{job.location}</span>
                  {job.posted_at && (
                    <span className="text-[9px] text-slate-400 font-normal shrink-0">
                      {new Date(job.posted_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    </span>
                  )}
                </div>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100">
                  <span className="text-xs font-bold text-slate-800">{job.salary_range}</span>
                  {job.url && (
                    <a
                      href={job.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-600 hover:text-indigo-800 transition-colors bg-indigo-50/80 hover:bg-indigo-100 px-2 py-0.5 rounded border border-indigo-100"
                    >
                      Apply <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  )}
                </div>
              </motion.div>
            );
          })}

          {jobs.length === 0 && !isSearching && (
            <div className="text-center py-16 text-slate-400">
              <Briefcase className="w-8 h-8 mx-auto mb-2 text-slate-300" />
              <p className="text-xs font-semibold">No positions found.</p>
            </div>
          )}
        </div>
      </div>

      {/* RIGHT PANEL — Resume Studio Workspace */}
      <div className="flex-1 h-full bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm flex flex-col">
        <AnimatePresence mode="wait">
          {selectedJob ? (
            <motion.div
              key={selectedJob.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
              className="flex-1 h-full overflow-hidden"
            >
              <ResumeStudio job={selectedJob} onClose={() => setSelectedJob(null)} />
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex-1 flex flex-col items-center justify-center text-center p-12 space-y-4"
            >
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 shadow-inner">
                <Sparkles className="w-6 h-6 animate-pulse" />
              </div>
              <div className="space-y-1 max-w-sm">
                <p className="text-sm font-black text-slate-800 uppercase tracking-widest">
                  Resume Studio Workspace
                </p>
                <p className="text-xs text-slate-400">
                  Select a job card from the left panel to tailor your resume, track application status, and draft matching cover letters.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
