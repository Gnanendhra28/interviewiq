'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { interviewService } from '../../../services/interview-service';
import { candidateService } from '../../../services/candidate-service';
import { jobRoleService } from '../../../services/job-role-service';
import { knowledgeService } from '../../../services/knowledge-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { FileCheck, Plus, Play, CheckCircle } from 'lucide-react';

export default function InterviewsPage() {
  const queryClient = useQueryClient();
  const [candidateId, setCandidateId] = useState('');
  const [jobRoleId, setJobRoleId] = useState('');
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);

  const { data: interviews, isLoading, error } = useQuery({
    queryKey: ['interviews'],
    queryFn: () => interviewService.listInterviews(),
  });

  const { data: candidates } = useQuery({
    queryKey: ['candidates'],
    queryFn: () => candidateService.listCandidates(),
  });

  const { data: jobRoles } = useQuery({
    queryKey: ['jobRoles'],
    queryFn: () => jobRoleService.listJobRoles(),
  });

  const { data: knowledgeBases } = useQuery({
    queryKey: ['knowledgeBases'],
    queryFn: () => knowledgeService.listBases(),
  });

  const createMutation = useMutation({
    mutationFn: () => interviewService.createInterview(candidateId, jobRoleId),
    onSuccess: (newInterview) => {
      queryClient.invalidateQueries({ queryKey: ['interviews'] });
      // Automatically prepare interview
      interviewService.prepareInterview(newInterview.id, selectedKbIds).then(() => {
        queryClient.invalidateQueries({ queryKey: ['interviews'] });
      });
    },
  });

  const startMutation = useMutation({
    mutationFn: (id: string) => interviewService.startInterview(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['interviews'] }),
  });

  if (isLoading) return <LoadingState message="Loading interview sessions..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Interview Sessions</h1>
        <p className="text-sm text-slate-500 mt-1">Create, prepare snapshots/blueprints, and launch adaptive interviews.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Create & Prepare Interview Form */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            <span>Create & Prepare Interview</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Select Candidate</label>
              <select
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
              >
                <option value="">-- Choose Candidate --</option>
                {(candidates || []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.first_name} {c.last_name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Select Job Role</label>
              <select
                value={jobRoleId}
                onChange={(e) => setJobRoleId(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
              >
                <option value="">-- Choose Job Role --</option>
                {(jobRoles || []).map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} ({r.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Select Grounding Knowledge Bases</label>
              <div className="space-y-1 max-h-32 overflow-y-auto">
                {(knowledgeBases || []).map((kb) => (
                  <label key={kb.id} className="flex items-center space-x-2 text-xs p-1.5 bg-slate-50 rounded">
                    <input
                      type="checkbox"
                      checked={selectedKbIds.includes(kb.id)}
                      onChange={(e) => {
                        if (e.target.checked) setSelectedKbIds([...selectedKbIds, kb.id]);
                        else setSelectedKbIds(selectedKbIds.filter((id) => id !== kb.id));
                      }}
                      className="rounded text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="font-medium text-slate-700">{kb.name}</span>
                  </label>
                ))}
              </div>
            </div>

            <button
              onClick={() => createMutation.mutate()}
              disabled={!candidateId || !jobRoleId || createMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              Create & Prepare Snapshot
            </button>
          </div>
        </div>

        {/* Existing Interviews List */}
        <div className="lg:col-span-2 space-y-4">
          {(interviews || []).map((sess) => (
            <div key={sess.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
              <div>
                <span className="text-xs font-mono text-slate-400">ID: {sess.id.substring(0, 8)}</span>
                <div className="flex items-center space-x-2 mt-1">
                  <span className="px-2.5 py-0.5 bg-indigo-50 text-indigo-700 rounded-full text-xs font-bold">{sess.status}</span>
                  <span className="text-xs text-slate-500">Created: {new Date(sess.created_at).toLocaleDateString()}</span>
                </div>
              </div>

              <div className="flex items-center space-x-3">
                {sess.status === 'READY' && (
                  <button
                    onClick={() => startMutation.mutate(sess.id)}
                    className="flex items-center space-x-1 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Start Interview</span>
                  </button>
                )}

                {sess.status === 'IN_PROGRESS' && (
                  <Link
                    href={`/candidate/interview/${sess.id}`}
                    className="flex items-center space-x-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold"
                  >
                    <span>Open Candidate UX</span>
                  </Link>
                )}

                {(sess.status === 'COMPLETED' || sess.status === 'COMPLETING') && (
                  <Link
                    href={`/recruiter/interviews/${sess.id}/report`}
                    className="flex items-center space-x-1 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold"
                  >
                    <span>View Report</span>
                  </Link>
                )}
              </div>
            </div>
          ))}
          {(interviews || []).length === 0 && <p className="text-slate-400 text-sm py-4 text-center">No interviews created yet.</p>}
        </div>
      </div>
    </div>
  );
}
