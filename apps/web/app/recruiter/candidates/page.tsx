'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { recruiterService } from '../../../services/recruiter-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { Search, Filter, ArrowRight, UserPlus, GitCompare } from 'lucide-react';

export default function CandidatesPipelinePage() {
  const router = useRouter();

  const [search, setSearch] = useState('');
  const [hiringSignal, setHiringSignal] = useState('');
  const [decisionStatus, setDecisionStatus] = useState('');
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [page, setPage] = useState(1);

  const { data, isLoading, error } = useQuery({
    queryKey: ['candidatePipeline', search, hiringSignal, decisionStatus, page],
    queryFn: () =>
      recruiterService.getCandidatePipeline({
        search,
        hiring_signal: hiringSignal || undefined,
        human_decision_status: decisionStatus || undefined,
        page,
        limit: 15,
      }),
  });

  const toggleSelectCandidate = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      if (selectedIds.length >= 5) {
        alert('Maximum 5 candidates can be selected for comparison.');
        return;
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleCompare = () => {
    if (selectedIds.length === 0) return;
    const params = new URLSearchParams({ ids: selectedIds.join(',') });
    router.push(`/recruiter/candidates/compare?${params.toString()}`);
  };

  if (isLoading) return <LoadingState message="Loading candidate pipeline..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Candidate Pipeline</h1>
          <p className="text-sm text-slate-500 mt-1">Manage candidates, review reports, and record human hiring decisions.</p>
        </div>

        <div className="flex items-center space-x-3">
          {selectedIds.length > 0 && (
            <button
              onClick={handleCompare}
              className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition"
            >
              <GitCompare className="w-4 h-4" />
              <span>Compare ({selectedIds.length})</span>
            </button>
          )}

          <Link
            href="/recruiter/candidates/new"
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Candidate</span>
          </Link>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center space-x-1 text-slate-500 text-xs font-semibold">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={hiringSignal}
            onChange={(e) => setHiringSignal(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white text-slate-700"
          >
            <option value="">All Hiring Signals</option>
            <option value="STRONG_HIRE_SIGNAL">Strong Hire Signal</option>
            <option value="HIRE_SIGNAL">Hire Signal</option>
            <option value="MIXED_SIGNAL">Mixed Signal</option>
            <option value="NO_HIRE_SIGNAL">No Hire Signal</option>
            <option value="INSUFFICIENT_EVIDENCE">Insufficient Evidence</option>
          </select>

          <select
            value={decisionStatus}
            onChange={(e) => setDecisionStatus(e.target.value)}
            className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white text-slate-700"
          >
            <option value="">All Human Decisions</option>
            <option value="PENDING_REVIEW">Pending Review</option>
            <option value="SHORTLISTED">Shortlisted</option>
            <option value="HIRED">Hired</option>
            <option value="REJECTED">Rejected</option>
            <option value="ON_HOLD">On Hold</option>
          </select>
        </div>
      </div>

      {/* Candidate Pipeline Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-left text-sm text-slate-600">
          <thead className="bg-slate-50 border-b border-slate-200 text-xs uppercase font-semibold text-slate-500">
            <tr>
              <th className="p-4 w-10 text-center">Compare</th>
              <th className="p-4">Candidate</th>
              <th className="p-4">Interview Status</th>
              <th className="p-4">Score</th>
              <th className="p-4">AI Signal</th>
              <th className="p-4">Human Decision</th>
              <th className="p-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {(data?.candidates || []).map((cand) => (
              <tr key={cand.candidate_id} className="hover:bg-slate-50 transition">
                <td className="p-4 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(cand.candidate_id)}
                    onChange={() => toggleSelectCandidate(cand.candidate_id)}
                    className="w-4 h-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
                  />
                </td>
                <td className="p-4 font-medium text-slate-900">
                  <Link href={`/recruiter/candidates/${cand.candidate_id}`} className="hover:text-indigo-600 transition">
                    {cand.full_name}
                  </Link>
                  <span className="block text-xs text-slate-400 font-normal">{cand.email}</span>
                </td>
                <td className="p-4">
                  <span className="px-2.5 py-1 bg-slate-100 text-slate-700 rounded-full text-xs font-semibold">
                    {cand.interview_status || 'NOT_STARTED'}
                  </span>
                </td>
                <td className="p-4 font-bold text-slate-900">
                  {cand.latest_score !== undefined && cand.latest_score !== null ? `${cand.latest_score.toFixed(1)}/10` : 'N/A'}
                </td>
                <td className="p-4">
                  {cand.hiring_signal ? (
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                        cand.hiring_signal.includes('STRONG_HIRE')
                          ? 'bg-emerald-100 text-emerald-800'
                          : cand.hiring_signal.includes('HIRE')
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-amber-100 text-amber-800'
                      }`}
                    >
                      {cand.hiring_signal}
                    </span>
                  ) : (
                    <span className="text-slate-400 text-xs">—</span>
                  )}
                </td>
                <td className="p-4">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                      cand.human_decision === 'HIRED'
                        ? 'bg-emerald-600 text-white'
                        : cand.human_decision === 'REJECTED'
                        ? 'bg-red-600 text-white'
                        : 'bg-slate-200 text-slate-800'
                    }`}
                  >
                    {cand.human_decision}
                  </span>
                </td>
                <td className="p-4 text-right">
                  <Link
                    href={`/recruiter/candidates/${cand.candidate_id}`}
                    className="inline-flex items-center space-x-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    <span>View Profile</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </td>
              </tr>
            ))}
            {(data?.candidates || []).length === 0 && (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-400 text-sm">
                  No candidates matching the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
