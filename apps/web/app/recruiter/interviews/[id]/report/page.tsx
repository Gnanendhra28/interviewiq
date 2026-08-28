'use client';

import React, { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { reportService } from '../../../../../services/report-service';
import { recruiterService } from '../../../../../services/recruiter-service';
import { pdfExportService } from '../../../../../services/pdf-export-service';
import { LoadingState } from '../../../../../components/LoadingState';
import { ErrorBanner } from '../../../../../components/ErrorBanner';
import { HiringDecisionStatus } from '../../../../../types';
import { Award, ShieldCheck, RefreshCw, FileDown, Download } from 'lucide-react';

export default function InterviewReportPage() {
  const params = useParams();
  const interviewId = params.id as string;
  const queryClient = useQueryClient();

  const [decisionStatus, setDecisionStatus] = useState<HiringDecisionStatus>('SHORTLISTED');
  const [rationaleText, setRationaleText] = useState('');

  const { data: report, isLoading, error } = useQuery({
    queryKey: ['interviewReport', interviewId],
    queryFn: () => reportService.getLatestReport(interviewId),
  });

  const { data: exports } = useQuery({
    queryKey: ['pdfExports', interviewId, report?.id],
    queryFn: () => (report ? pdfExportService.listExports(interviewId, report.id) : Promise.resolve([])),
    enabled: !!report,
    refetchInterval: 3000,
  });

  const { data: decision } = useQuery({
    queryKey: ['hiringDecision', interviewId],
    queryFn: () => recruiterService.getHiringDecision(interviewId),
  });

  const { data: decisionHistory } = useQuery({
    queryKey: ['decisionHistory', interviewId],
    queryFn: () => recruiterService.getHiringDecisionHistory(interviewId),
  });

  const regenerateMutation = useMutation({
    mutationFn: () => reportService.regenerateReport(interviewId),
    onSuccess: (data) => {
      alert(`Report regeneration enqueued for target version ${data.target_version}`);
      queryClient.invalidateQueries({ queryKey: ['interviewReport', interviewId] });
    },
  });

  const pdfExportMutation = useMutation({
    mutationFn: () => {
      if (!report) throw new Error('Report missing');
      return pdfExportService.requestExport(interviewId, report.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pdfExports', interviewId, report?.id] });
    },
  });

  const decisionMutation = useMutation({
    mutationFn: () => recruiterService.recordHiringDecision(interviewId, decisionStatus, rationaleText),
    onSuccess: () => {
      alert('Human hiring decision recorded!');
      queryClient.invalidateQueries({ queryKey: ['hiringDecision', interviewId] });
      queryClient.invalidateQueries({ queryKey: ['decisionHistory', interviewId] });
    },
  });

  if (isLoading) return <LoadingState message="Loading interview report..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;
  if (!report) return <ErrorBanner message="Interview report not found." />;

  const readyExport = (exports || []).find((e) => e.status === 'READY');

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Report Header */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 text-xs font-bold rounded-full">Report v{report.report_version}</span>
            <span className="text-xs text-slate-400 font-mono">Scoring Engine: {report.scoring_version}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white mt-1">{report.seniority_assessment}</h1>
          <p className="text-xs text-slate-400 mt-1">{new Date(report.created_at).toLocaleString()}</p>
        </div>

        <div className="flex items-center space-x-3">
          {readyExport ? (
            <a
              href={pdfExportService.getDownloadUrl(readyExport.id)}
              download
              className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-600/30 transition"
            >
              <Download className="w-4 h-4" />
              <span>Download PDF</span>
            </a>
          ) : (
            <button
              onClick={() => pdfExportMutation.mutate()}
              disabled={pdfExportMutation.isPending}
              className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              <FileDown className="w-4 h-4" />
              <span>Export PDF</span>
            </button>
          )}

          <button
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending}
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-bold rounded-xl transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Scores Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="glass-panel p-4 rounded-xl border border-indigo-500/30 bg-indigo-600/10 text-center">
          <p className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">Overall Score</p>
          <p className="text-2xl font-extrabold text-indigo-300 mt-1">{report.overall_score.toFixed(1)}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 text-center">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Technical Accuracy</p>
          <p className="text-xl font-bold text-white mt-1">{report.technical_competency_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 text-center">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Reasoning</p>
          <p className="text-xl font-bold text-white mt-1">{report.reasoning_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 text-center">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Communication</p>
          <p className="text-xl font-bold text-white mt-1">{report.communication_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 text-center">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Completeness</p>
          <p className="text-xl font-bold text-white mt-1">{report.completeness_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="glass-panel p-4 rounded-xl border border-slate-800/80 text-center">
          <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">AI Signal</p>
          <span className="inline-block px-2.5 py-1 bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold text-xs rounded-full mt-2">
            {report.hiring_signal}
          </span>
        </div>
      </div>

      {/* Main Breakdown & Scorecards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Summary */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-3">
            <h2 className="font-bold text-white text-base">Executive Summary</h2>
            <p className="text-sm text-slate-300 leading-relaxed">{report.executive_summary}</p>
          </div>

          {/* Strengths & Growth Areas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass-panel p-5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 space-y-2">
              <h3 className="font-bold text-emerald-300 text-sm">Key Strengths</h3>
              <ul className="list-disc list-inside text-xs text-emerald-200 space-y-1">
                {(report.top_strengths?.strengths || []).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>

            <div className="glass-panel p-5 rounded-xl border border-amber-500/30 bg-amber-500/10 space-y-2">
              <h3 className="font-bold text-amber-300 text-sm">Growth Areas</h3>
              <ul className="list-disc list-inside text-xs text-amber-200 space-y-1">
                {(report.growth_areas?.growth_areas || []).map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Requirement Scorecards */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="font-bold text-white text-base">Job Requirement Scorecards</h2>
            <div className="space-y-3">
              {(report.requirement_scorecards_json?.scorecards || []).map((sc, idx) => (
                <div key={idx} className="p-4 bg-slate-900/90 rounded-lg border border-slate-800 flex justify-between items-center text-xs">
                  <div>
                    <span className="font-bold text-white text-sm block">{sc.requirement_skill}</span>
                    <span className="text-slate-400 mt-0.5 block">
                      Evidence Count: {sc.evidence_count} | Status: <strong className="text-slate-200">{sc.status}</strong>
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-extrabold text-indigo-300">{sc.average_score.toFixed(1)}</span>
                    <span className="text-slate-500 block text-[10px]">Weight: {sc.weight}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Human Decision Authority */}
        <div className="space-y-6">
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <span>Record Human Decision</span>
            </h2>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Human Decision Status</label>
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
                <label className="block text-xs font-semibold text-slate-400 mb-1">Recruiter Rationale</label>
                <textarea
                  rows={3}
                  value={rationaleText}
                  onChange={(e) => setRationaleText(e.target.value)}
                  placeholder="Enter evaluation notes..."
                  className="w-full p-2.5 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
                />
              </div>

              <button
                onClick={() => decisionMutation.mutate()}
                disabled={decisionMutation.isPending}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-xs transition disabled:opacity-50 shadow-lg shadow-emerald-600/30"
              >
                Submit Human Decision
              </button>
            </div>
          </div>

          {/* Decision Audit History */}
          <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-3">
            <h3 className="font-bold text-white text-sm">Decision Audit History</h3>
            <div className="space-y-2">
              {(decisionHistory || []).map((dh) => (
                <div key={dh.id} className="border-l-2 border-emerald-500/80 pl-3 py-1 text-xs">
                  <span className="font-bold text-white">{dh.new_status}</span>
                  <span className="text-slate-400 block text-[10px]">{new Date(dh.created_at).toLocaleString()}</span>
                  {dh.rationale_text && <p className="text-slate-300 italic mt-0.5">&quot;{dh.rationale_text}&quot;</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
