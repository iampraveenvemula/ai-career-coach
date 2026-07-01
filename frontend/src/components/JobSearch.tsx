/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Search, RefreshCw } from "lucide-react";
import { motion } from "framer-motion";
import { API_BASE_URL } from "@/lib/config";
import { Dialog, DialogContent, DialogTitle, DialogDescription, DialogHeader } from "@/components/ui/dialog";
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
      setJobs(data.results || []);
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
      setScrapeMsg("Scrape failed. Check backend logs.");
    } finally {
      setIsScraping(false);
    }
  };

  const handleClear = async () => {
    if (!window.confirm("Are you sure you want to clear all jobs from the database and vector index?")) return;
    setIsClearing(true);
    setScrapeMsg("");
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/jobs/clear`, { method: "POST" });
      const data = await response.json();
      setScrapeMsg("Database cleared.");
      setJobs([]);
    } catch (error) {
      setScrapeMsg("Clear failed.");
    } finally {
      setIsClearing(false);
    }
  };

  useEffect(() => {
    fetchJobs("");
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs(query);
  };

  return (
    <div className="w-full max-w-5xl mx-auto flex flex-col" style={{ maxHeight: "calc(100vh - 140px)" }}>
      <form onSubmit={handleSearch} className="flex gap-3 mb-3 shrink-0">
        <div className="relative flex-1">
          <Search strokeWidth={2.5} className="absolute left-4 top-3.5 h-5 w-5 text-slate-500" />
          <Input 
            type="text" 
            placeholder="Search roles, skills, or titles..." 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-12 bg-white border-slate-200 text-slate-900 h-12 text-base font-medium rounded-full focus-visible:ring-1 focus-visible:ring-slate-400 shadow-sm"
          />
        </div>
        <Button type="submit" disabled={isSearching} className="h-12 px-8 bg-slate-900 hover:bg-slate-800 text-white rounded-full text-base font-bold">
          {isSearching ? "..." : "Search"}
        </Button>
      </form>

      {/* Scrape controls */}
      <div className="flex items-center gap-3 mb-5 shrink-0">
        <Button
          onClick={handleScrape}
          disabled={isScraping || isClearing}
          variant="outline"
          className="h-9 px-5 rounded-full text-sm font-bold border-slate-300 text-slate-700 hover:border-slate-500 hover:bg-slate-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 mr-2 ${isScraping ? "animate-spin" : ""}`} />
          {isScraping ? "Fetching from Google, LinkedIn, Remotive..." : "Fetch external jobs"}
        </Button>
        <Button
          onClick={handleClear}
          disabled={isScraping || isClearing}
          variant="destructive"
          className="h-9 px-5 rounded-full text-sm font-bold bg-red-50 text-red-600 hover:bg-red-100 hover:text-red-700 border border-red-200"
        >
          {isClearing ? "Clearing..." : "Clear Database"}
        </Button>
        {scrapeMsg && (
          <span className="text-sm font-semibold text-slate-500">{scrapeMsg}</span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 content-start pr-1">
        {jobs.map((job, idx) => (
          <motion.div
            key={job.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.03, duration: 0.3 }}
            onClick={() => setSelectedJob(job)}
            className="bg-white border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 rounded-2xl p-6 cursor-pointer group"
          >
            <div className="flex items-start justify-between mb-2">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">{job.company}</p>
              <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${SOURCE_COLORS[job.source] || SOURCE_COLORS.Seed}`}>
                {job.source}
              </span>
            </div>
            <h3 className="text-lg font-bold text-slate-900 leading-snug mb-3 group-hover:text-slate-600 transition-colors">{job.title}</h3>
            <p className="text-sm text-slate-600 font-semibold mb-1">{job.location}</p>
            <p className="text-sm font-bold text-slate-800">{job.salary_range}</p>
            <p className="text-sm text-slate-500 font-medium line-clamp-2 mt-4 leading-relaxed">{job.description_text}</p>
          </motion.div>
        ))}

        {jobs.length === 0 && !isSearching && (
          <div className="col-span-full text-center py-16">
            <p className="text-slate-500 font-semibold text-base">No positions found.</p>
          </div>
        )}
      </div>

      <Dialog open={!!selectedJob} onOpenChange={(open) => !open && setSelectedJob(null)}>
        <DialogContent className="sm:max-w-2xl bg-white border-0 p-0 text-slate-900 rounded-2xl shadow-[0_20px_60px_rgb(0,0,0,0.1)] overflow-hidden">
           <DialogHeader className="sr-only">
             <DialogTitle>Tailor Resume</DialogTitle>
             <DialogDescription>Tailor your resume for the selected job</DialogDescription>
           </DialogHeader>
           {selectedJob && <ResumeStudio job={selectedJob} onClose={() => setSelectedJob(null)} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
