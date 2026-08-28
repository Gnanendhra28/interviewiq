'use client';

import React, { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { recruiterService } from '../../../../services/recruiter-service';
import { LoadingState } from '../../../../components/LoadingState';
import { ErrorBanner } from '../../../../components/ErrorBanner';
import { GitCompare } from 'lucide-react';

function CompareCandidatesContent() {
  const searchParams = useSearchParams();
  const idsParam = searchParams.get('ids') || '';
  const candidateIds = idsParam ? idsParam.split(',').filter(Boolean) : [];

  const { data, isLoading, error } = useQuery({
    queryKey: ['compareCandidates', candidateIds],
    queryFn: () => recruiterService.compareCandidates(candidateIds),
    enabled: candidateIds.length > 0,
  });

  if (candidateIds.length === 0) {
    return <ErrorBanner message="No candidates selected for comparison. Please select candidates from the Pipeline page." />;
  }

  if (isLoading) return <LoadingState message="Calculating candidate side-by-side metrics..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <GitCompare className="w-6 h-6 text-indigo-600" />
          <span>Candidate Comparison Matrix</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Side-by-side score breakdown, requirement scorecards, and hiring decision status for up to 5 candidates.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-700">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-4 font-semibold text-slate-500 min-w-[200px]">Metric / Candidate</th>
              {(data?.candidates || []).map((cand) => (
                <th key={cand.candidate_id} className="p-4 font-bold text-slate-900 min-w-[220px]">
                  {cand.full_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Overall Score</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4 font-bold text-indigo-700 text-base">
                  {cand.overall_score !== undefined && cand.overall_score !== null ? `${cand.overall_score.toFixed(2)} / 10.0` : 'N/A'}
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Technical Accuracy</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4">
                  {cand.technical_competency_score !== undefined && cand.technical_competency_score !== null
                    ? `${cand.technical_competency_score.toFixed(2)}`
                    : 'N/A'}
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Reasoning Score</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4">
                  {cand.reasoning_score !== undefined && cand.reasoning_score !== null ? `${cand.reasoning_score.toFixed(2)}` : 'N/A'}
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Communication Score</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4">
                  {cand.communication_score !== undefined && cand.communication_score !== null ? `${cand.communication_score.toFixed(2)}` : 'N/A'}
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">AI Hiring Signal</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4">
                  <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 font-bold text-xs rounded-full">{cand.hiring_signal}</span>
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Human Decision</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4">
                  <span className="px-2.5 py-1 bg-emerald-600 text-white font-bold text-xs rounded-full">{cand.human_decision}</span>
                </td>
              ))}
            </tr>

            <tr>
              <td className="p-4 font-semibold text-slate-600 bg-slate-50/50">Requirement Scorecards</td>
              {(data?.candidates || []).map((cand) => (
                <td key={cand.candidate_id} className="p-4 space-y-1.5 text-xs">
                  {(cand.requirement_scorecards || []).map((sc, idx) => (
                    <div key={idx} className="p-2 bg-slate-50 rounded border border-slate-200">
                      <div className="font-semibold text-slate-800">{sc.requirement_skill}</div>
                      <div className="text-slate-500">Score: {sc.average_score} ({sc.status})</div>
                    </div>
                  ))}
                  {(cand.requirement_scorecards || []).length === 0 && <span className="text-slate-400">No scorecards available</span>}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function CompareCandidatesPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading comparison matrix..." />}>
      <CompareCandidatesContent />
    </Suspense>
  );
}
