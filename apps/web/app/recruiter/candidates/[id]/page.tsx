'use client';

import React, { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { candidateService } from '../../../../services/candidate-service';
import { resumeService } from '../../../../services/resume-service';
import { recruiterService } from '../../../../services/recruiter-service';
import { interviewService } from '../../../../services/interview-service';
import { LoadingState } from '../../../../components/LoadingState';
import { ErrorBanner } from '../../../../components/ErrorBanner';
import { HiringDecisionStatus } from '../../../../types';
import { User, FileText, Upload, Sparkles, History, CheckCircle, ShieldCheck } from 'lucide-react';

export default function CandidateDetailPage() {
  const params = useParams();
  const candidateId = params.id as string;
  const queryClient = useQueryClient();

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadStatusMsg, setUploadStatusMsg] = useState('');
  const [decisionStatus, setDecisionStatus] = useState<HiringDecisionStatus>('SHORTLISTED');
  const [rationaleText, setRationaleText] = useState('');

  // Fetch Candidate Profile
  const { data: cand, isLoading: isCandLoading, error: candError } = useQuery({
    queryKey: ['candidate', candidateId],
    queryFn: () => candidateService.getCandidate(candidateId),
  });

  // Fetch Timeline
  const { data: timeline } = useQuery({
    queryKey: ['candidateTimeline', candidateId],
    queryFn: () => recruiterService.getCandidateTimeline(candidateId),
  });

  // Fetch Interviews
  const { data: interviews } = useQuery({
    queryKey: ['candidateInterviews', candidateId],
    queryFn: () => interviewService.listInterviews(candidateId),
  });

  // Resume Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => resumeService.uploadResume(candidateId, file),
    onSuccess: (data) => {
      setUploadStatusMsg(`Resume uploaded! Current status: ${data.processing_status}`);
      setSelectedFile(null);
      queryClient.invalidateQueries({ queryKey: ['candidate', candidateId] });
    },
  });

  // Decision Mutation
  const decisionMutation = useMutation({
    mutationFn: ({ interviewId, status, text }: { interviewId: string; status: HiringDecisionStatus; text?: string }) =>
      recruiterService.recordHiringDecision(interviewId, status, text),
    onSuccess: () => {
      alert('Human hiring decision recorded successfully!');
      queryClient.invalidateQueries({ queryKey: ['candidatePipeline'] });
      queryClient.invalidateQueries({ queryKey: ['candidateTimeline', candidateId] });
    },
  });

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    uploadMutation.mutate(selectedFile);
  };

  const latestInterview = interviews && interviews.length > 0 ? interviews[0] : null;

  if (isCandLoading) return <LoadingState message="Loading candidate profile..." />;
  if (candError) return <ErrorBanner message={(candError as Error).message} />;
  if (!cand) return <ErrorBanner message="Candidate profile not found." />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header Profile Section */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center space-x-4">
          <div className="w-14 h-14 bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 font-bold text-xl rounded-full flex items-center justify-center shadow-lg">
            {cand.first_name[0]}
            {cand.last_name[0]}
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-white">
              {cand.first_name} {cand.last_name}
            </h1>
            <p className="text-sm text-slate-300">{cand.headline || 'Software Engineer Candidate'}</p>
            <p className="text-xs text-slate-400 mt-1">{cand.email}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Skills & Experience */}
        <div className="lg:col-span-2 space-y-6">
          {/* Skills Breakdown */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <span>Extracted & Manual Skills</span>
            </h2>

            <div className="flex flex-wrap gap-2">
              {(cand.skills || []).map((sk) => (
                <span
                  key={sk.id}
                  className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border ${
                    sk.source === 'RESUME_AI' ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' : 'bg-slate-800 text-slate-300 border-slate-700/60'
                  }`}
                >
                  <span>{sk.skill_name}</span>
                  <span className="text-[10px] uppercase tracking-wider font-bold opacity-75">({sk.source})</span>
                </span>
              ))}
              {(cand.skills || []).length === 0 && <p className="text-sm text-slate-400 py-2">No skills recorded yet.</p>}
            </div>
          </div>

          {/* Resume Upload & Processing Status */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <FileText className="w-5 h-5 text-indigo-400" />
              <span>Resume Upload & AI Parsing</span>
            </h2>

            {uploadStatusMsg && <div className="p-3 bg-indigo-500/20 border border-indigo-500/40 text-indigo-300 rounded-lg text-xs">{uploadStatusMsg}</div>}

            <form onSubmit={handleFileUpload} className="flex items-center space-x-3">
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
                className="text-xs text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer"
              />
              <button
                type="submit"
                disabled={!selectedFile || uploadMutation.isPending}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 flex items-center space-x-1.5 shadow-lg shadow-indigo-600/30"
              >
                <Upload className="w-4 h-4" />
                <span>Upload</span>
              </button>
            </form>
          </div>

          {/* Candidate Timeline Event Stream */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <History className="w-5 h-5 text-indigo-400" />
              <span>Candidate Timeline</span>
            </h2>

            <div className="space-y-3">
              {(timeline || []).map((evt, idx) => (
                <div key={idx} className="border-l-2 border-indigo-500/60 pl-4 py-1 text-xs space-y-1">
                  <div className="font-bold text-white">{evt.event_type}</div>
                  <div className="text-slate-300">{evt.description}</div>
                  <div className="text-slate-400">{new Date(evt.timestamp).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Human Decision Management */}
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>Record Human Hiring Decision</span>
            </h2>

            <p className="text-xs text-slate-400">
              AI hiring signals are strictly decision support. Human recruiters must record final hiring authority decisions.
            </p>

            {latestInterview ? (
              <div className="space-y-4 pt-2">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Decision Status</label>
                  <select
                    value={decisionStatus}
                    onChange={(e) => setDecisionStatus(e.target.value as HiringDecisionStatus)}
                    className="w-full px-3 py-2 border border-slate-800 rounded-lg text-xs bg-slate-950 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="SHORTLISTED" className="bg-slate-900 text-slate-200">Shortlisted</option>
                    <option value="HIRED" className="bg-slate-900 text-slate-200">Hired</option>
                    <option value="REJECTED" className="bg-slate-900 text-slate-200">Rejected</option>
                    <option value="ON_HOLD" className="bg-slate-900 text-slate-200">On Hold</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Recruiter Rationale</label>
                  <textarea
                    rows={3}
                    value={rationaleText}
                    onChange={(e) => setRationaleText(e.target.value)}
                    placeholder="Enter explicit recruiter evaluation notes..."
                    className="w-full p-2.5 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <button
                  onClick={() =>
                    decisionMutation.mutate({
                      interviewId: latestInterview.id,
                      status: decisionStatus,
                      text: rationaleText,
                    })
                  }
                  disabled={decisionMutation.isPending}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 shadow-lg shadow-emerald-600/30"
                >
                  Save Human Decision
                </button>
              </div>
            ) : (
              <p className="text-xs text-amber-300 bg-amber-500/20 border border-amber-500/30 p-3 rounded-lg">
                No active interview session found for this candidate. Create an interview first to record hiring decisions.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
