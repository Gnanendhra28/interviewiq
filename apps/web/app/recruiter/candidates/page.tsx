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
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Candidate Pipeline</h1>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">Manage candidates, review reports, and record human hiring decisions.</p>
        </div>

        <div className="flex items-center space-x-3">
          {selectedIds.length > 0 && (
            <button
              onClick={handleCompare}
              className="flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition"
            >
              <GitCompare className="w-4 h-4" />
              <span>Compare ({selectedIds.length})</span>
            </button>
          )}

          <Link
            href="/recruiter/job-roles"
            className="flex items-center space-x-1.5 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 text-xs font-bold rounded-xl transition"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Candidate</span>
          </Link>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel p-4 rounded-xl border border-slate-800/80 shadow-2xl flex flex-col md:flex-row gap-4 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
          <input
            type="text"
            placeholder="Search name or email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center space-x-1 text-slate-400 text-xs font-semibold">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={hiringSignal}
            onChange={(e) => setHiringSignal(e.target.value)}
            className="px-3 py-2 border border-slate-800 rounded-lg text-xs bg-slate-950 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="" className="bg-slate-900 text-slate-200">All Hiring Signals</option>
            <option value="STRONG_HIRE_SIGNAL" className="bg-slate-900 text-slate-200">Strong Hire Signal</option>
            <option value="HIRE_SIGNAL" className="bg-slate-900 text-slate-200">Hire Signal</option>
            <option value="MIXED_SIGNAL" className="bg-slate-900 text-slate-200">Mixed Signal</option>
            <option value="NO_HIRE_SIGNAL" className="bg-slate-900 text-slate-200">No Hire Signal</option>
            <option value="INSUFFICIENT_EVIDENCE" className="bg-slate-900 text-slate-200">Insufficient Evidence</option>
          </select>

          <select
            value={decisionStatus}
            onChange={(e) => setDecisionStatus(e.target.value)}
            className="px-3 py-2 border border-slate-800 rounded-lg text-xs bg-slate-950 text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            <option value="" className="bg-slate-900 text-slate-200">All Human Decisions</option>
            <option value="PENDING_REVIEW" className="bg-slate-900 text-slate-200">Pending Review</option>
            <option value="SHORTLISTED" className="bg-slate-900 text-slate-200">Shortlisted</option>
            <option value="HIRED" className="bg-slate-900 text-slate-200">Hired</option>
            <option value="REJECTED" className="bg-slate-900 text-slate-200">Rejected</option>
            <option value="ON_HOLD" className="bg-slate-900 text-slate-200">On Hold</option>
          </select>
        </div>
      </div>

      {/* Candidate Pipeline Table */}
      <div className="glass-panel border border-slate-800/80 rounded-xl shadow-2xl overflow-hidden">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-900/90 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold text-slate-400">
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
          <tbody className="divide-y divide-slate-800/60">
            {(data?.candidates || []).map((cand) => (
              <tr key={cand.candidate_id} className="hover:bg-slate-800/40 transition">
                <td className="p-4 text-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(cand.candidate_id)}
                    onChange={() => toggleSelectCandidate(cand.candidate_id)}
                    className="w-4 h-4 text-indigo-600 rounded border-slate-700 bg-slate-950 focus:ring-indigo-500"
                  />
                </td>
                <td className="p-4 font-semibold text-white">
                  <Link href={`/recruiter/candidates/${cand.candidate_id}`} className="hover:text-indigo-400 transition">
                    {cand.full_name}
                  </Link>
                  <span className="block text-xs text-slate-400 font-normal mt-0.5">{cand.email}</span>
                </td>
                <td className="p-4">
                  <span className="px-2.5 py-1 bg-slate-800/80 text-slate-300 border border-slate-700/60 rounded-full text-xs font-semibold">
                    {cand.interview_status || 'NOT_STARTED'}
                  </span>
                </td>
                <td className="p-4 font-bold text-indigo-300">
                  {cand.latest_score !== undefined && cand.latest_score !== null ? `${cand.latest_score.toFixed(1)}/10` : 'N/A'}
                </td>
                <td className="p-4">
                  {cand.hiring_signal ? (
                    <span
                      className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                        cand.hiring_signal.includes('STRONG_HIRE')
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                          : cand.hiring_signal.includes('HIRE')
                          ? 'bg-blue-500/20 text-blue-300 border-blue-500/30'
                          : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                      }`}
                    >
                      {cand.hiring_signal}
                    </span>
                  ) : (
                    <span className="text-slate-500 text-xs">—</span>
                  )}
                </td>
                <td className="p-4">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-bold border ${
                      cand.human_decision === 'HIRED'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                        : cand.human_decision === 'REJECTED'
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                        : 'bg-slate-800/80 text-slate-400 border-slate-700/60'
                    }`}
                  >
                    {cand.human_decision}
                  </span>
                </td>
                <td className="p-4 text-right">
                  <Link
                    href={`/recruiter/candidates/${cand.candidate_id}`}
                    className="inline-flex items-center space-x-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300"
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
