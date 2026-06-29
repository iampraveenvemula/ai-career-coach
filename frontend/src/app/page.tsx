import { ResumeUpload } from "@/components/ResumeUpload";
import { JobSearch } from "@/components/JobSearch";
import { InterviewArena } from "@/components/InterviewArena";
import { AnalyticsDashboard } from "@/components/AnalyticsDashboard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#FAFAFA] text-slate-800 flex flex-col items-center py-10 font-sans px-4">
      <div className="w-full max-w-5xl">
        <Tabs defaultValue="resume" className="w-full">
          {/* Tab bar */}
          <TabsList className="flex w-full bg-transparent border-b-2 border-slate-200 rounded-none mb-8 max-w-lg mx-auto h-auto p-0 gap-0">
            {[
              { value: "resume",    label: "Resume"    },
              { value: "jobs",      label: "Jobs"      },
              { value: "interview", label: "Interview" },
              { value: "analytics", label: "Analytics" },
            ].map((tab) => (
              <TabsTrigger
                key={tab.value}
                value={tab.value}
                className="flex-1 rounded-none border-b-2 border-transparent data-[state=active]:border-slate-900 data-[state=active]:bg-transparent data-[state=active]:text-slate-900 text-slate-400 font-bold py-3 px-1 text-sm transition-all"
              >
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="resume" className="mt-0 outline-none">
            <ResumeUpload />
          </TabsContent>

          <TabsContent value="jobs" className="mt-0 outline-none">
            <JobSearch />
          </TabsContent>

          <TabsContent value="interview" className="mt-0 outline-none">
            <InterviewArena />
          </TabsContent>

          <TabsContent value="analytics" className="mt-0 outline-none">
            <AnalyticsDashboard />
          </TabsContent>
        </Tabs>
      </div>
    </main>
  );
}
