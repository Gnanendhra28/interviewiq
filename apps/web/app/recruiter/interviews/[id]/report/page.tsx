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
    <div className="space-y-8">
      {/* Report Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 text-xs font-bold rounded-full">Report v{report.report_version}</span>
            <span className="text-xs text-slate-400 font-mono">Scoring Engine: {report.scoring_version}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">{report.seniority_assessment}</h1>
          <p className="text-xs text-slate-500">{new Date(report.created_at).toLocaleString()}</p>
        </div>

        <div className="flex items-center space-x-3">
          {readyExport ? (
            <a
              href={pdfExportService.getDownloadUrl(readyExport.id)}
              download
              className="flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-lg transition"
            >
              <Download className="w-4 h-4" />
              <span>Download PDF</span>
            </a>
          ) : (
            <button
              onClick={() => pdfExportMutation.mutate()}
              disabled={pdfExportMutation.isPending}
              className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-lg transition disabled:opacity-50"
            >
              <FileDown className="w-4 h-4" />
              <span>Export PDF</span>
            </button>
          )}

          <button
            onClick={() => regenerateMutation.mutate()}
            disabled={regenerateMutation.isPending}
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold rounded-lg transition"
          >
            <RefreshCw className="w-4 h-4" />
            <span>Regenerate</span>
          </button>
        </div>
      </div>

      {/* Scores Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-indigo-100 bg-indigo-50/20 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">Overall Score</p>
          <p className="text-2xl font-extrabold text-indigo-600 mt-1">{report.overall_score.toFixed(1)}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">Technical Accuracy</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{report.technical_competency_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">Reasoning</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{report.reasoning_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">Communication</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{report.communication_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">Completeness</p>
          <p className="text-xl font-bold text-slate-800 mt-1">{report.completeness_score?.toFixed(1) || 'N/A'}</p>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 text-center">
          <p className="text-xs font-semibold text-slate-500 uppercase">AI Signal</p>
          <span className="inline-block px-2.5 py-1 bg-indigo-100 text-indigo-800 font-bold text-xs rounded-full mt-2">
            {report.hiring_signal}
          </span>
        </div>
      </div>

      {/* Main Breakdown & Scorecards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Executive Summary */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h2 className="font-bold text-slate-900 text-base">Executive Summary</h2>
            <p className="text-sm text-slate-700 leading-relaxed">{report.executive_summary}</p>
          </div>

          {/* Strengths & Growth Areas */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-white p-5 rounded-xl border border-emerald-200 bg-emerald-50/20 space-y-2">
              <h3 className="font-bold text-emerald-900 text-sm">Key Strengths</h3>
              <ul className="list-disc list-inside text-xs text-emerald-800 space-y-1">
                {(report.top_strengths?.strengths || []).map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>

            <div className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/20 space-y-2">
              <h3 className="font-bold text-amber-900 text-sm">Growth Areas</h3>
              <ul className="list-disc list-inside text-xs text-amber-800 space-y-1">
                {(report.growth_areas?.growth_areas || []).map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </div>
          </div>

          {/* Requirement Scorecards */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="font-bold text-slate-900 text-base">Job Requirement Scorecards</h2>
            <div className="space-y-3">
              {(report.requirement_scorecards_json?.scorecards || []).map((sc, idx) => (
                <div key={idx} className="p-4 bg-slate-50 rounded-lg border border-slate-200 flex justify-between items-center text-xs">
                  <div>
                    <span className="font-bold text-slate-900 text-sm block">{sc.requirement_skill}</span>
                    <span className="text-slate-500">
                      Evidence Count: {sc.evidence_count} | Status: <strong className="text-slate-700">{sc.status}</strong>
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-base font-extrabold text-indigo-600">{sc.average_score.toFixed(1)}</span>
                    <span className="text-slate-400 block text-[10px]">Weight: {sc.weight}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Human Decision Authority */}
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <span>Record Human Decision</span>
            </h2>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Human Decision Status</label>
                <select
                  value={decisionStatus}
                  onChange={(e) => setDecisionStatus(e.target.value as HiringDecisionStatus)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
                >
                  <option value="SHORTLISTED">Shortlisted</option>
                  <option value="HIRED">Hired</option>
                  <option value="REJECTED">Rejected</option>
                  <option value="ON_HOLD">On Hold</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Recruiter Rationale</label>
                <textarea
                  rows={3}
                  value={rationaleText}
                  onChange={(e) => setRationaleText(e.target.value)}
                  placeholder="Enter evaluation notes..."
                  className="w-full p-2.5 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <button
                onClick={() => decisionMutation.mutate()}
                disabled={decisionMutation.isPending}
                className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg text-sm transition disabled:opacity-50"
              >
                Submit Human Decision
              </button>
            </div>
          </div>

          {/* Decision Audit History */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="font-bold text-slate-900 text-sm">Decision Audit History</h3>
            <div className="space-y-2">
              {(decisionHistory || []).map((dh) => (
                <div key={dh.id} className="border-l-2 border-emerald-500 pl-3 py-1 text-xs">
                  <span className="font-bold text-slate-900">{dh.new_status}</span>
                  <span className="text-slate-400 block">{new Date(dh.created_at).toLocaleString()}</span>
                  {dh.rationale_text && <p className="text-slate-600 italic mt-0.5">&quot;{dh.rationale_text}&quot;</p>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
