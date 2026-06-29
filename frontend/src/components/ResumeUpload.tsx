/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { UploadCloud, Check } from "lucide-react";
import { motion } from "framer-motion";
import { API_BASE_URL } from "@/lib/config";

export function ResumeUpload() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [parsedData, setParsedData] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/resume/parse`, {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setParsedData(data);

      // Persist the raw text so the Jobs tab can use it for tailoring
      if (data.raw_text_preview) {
        localStorage.setItem("resume_text", data.raw_text_preview);
      }
    } catch (error) {
      console.error("Upload failed", error);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="w-full max-w-xl mx-auto">
      <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {!parsedData ? (
          <div className="bg-white border border-slate-200 shadow-sm rounded-2xl p-12 flex flex-col items-center text-center space-y-6">
            <UploadCloud strokeWidth={2} className="w-12 h-12 text-slate-400" />
            <p className="text-lg text-slate-600 font-medium">Upload your resume to extract skills and attributes.</p>
            <Label htmlFor="resume-upload" className="cursor-pointer">
              <span className="bg-slate-900 hover:bg-slate-800 text-white px-8 py-3 rounded-full text-base font-bold transition-all inline-block">
                Browse Files
              </span>
              <Input id="resume-upload" type="file" className="hidden" accept=".pdf,.docx,.doc" onChange={handleFileChange} />
            </Label>
            {file && (
              <>
                <p className="text-base text-slate-800 font-bold">{file.name}</p>
                <Button onClick={handleUpload} disabled={isUploading} className="bg-slate-900 hover:bg-slate-800 text-white rounded-full px-10 h-12 text-base font-bold">
                  {isUploading ? "Processing..." : "Analyze"}
                </Button>
              </>
            )}
          </div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white border border-slate-200 shadow-sm rounded-2xl p-10 space-y-8">
            <div className="flex items-center gap-3 pb-5 border-b border-slate-200">
              <Check strokeWidth={2.5} className="text-slate-900 w-6 h-6" />
              <span className="text-lg font-bold text-slate-900">Analysis complete</span>
            </div>
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-4">Skills</p>
              <div className="flex flex-wrap gap-2">
                {parsedData.parsed_data?.skills.map((skill: string, i: number) => (
                  <span key={i} className="px-4 py-2 bg-slate-100 text-slate-800 rounded-full text-sm font-bold border border-slate-200">
                    {skill}
                  </span>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-2">Experience</p>
                <p className="text-xl font-bold text-slate-900">{parsedData.parsed_data?.years_experience} yrs</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mb-2">Education</p>
                <p className="text-xl font-bold text-slate-900">{parsedData.parsed_data?.education}</p>
              </div>
            </div>
            <button onClick={() => { setParsedData(null); localStorage.removeItem("resume_text"); }} className="text-sm text-slate-500 font-bold hover:text-slate-900 transition-colors">
              Reset
            </button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
}
