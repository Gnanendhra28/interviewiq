'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { recruiterService } from '../../../services/recruiter-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import {
  Briefcase,
  Users,
  FileCheck,
  ShieldAlert,
  Activity,
  CheckCircle2,
  Clock,
  Plus,
  BookOpen,
  ArrowUpRight,
  Sparkles,
  Search,
} from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['recruiterDashboard'],
    queryFn: () => recruiterService.getDashboard(),
  });

  if (isLoading) return <LoadingState message="Connecting to Recruiter Intelligence engine..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner Header & Quick Action Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Recruiter Command Center
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 uppercase tracking-widest">
              Live Staging
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Real-time hiring pipeline metrics, candidate evaluation queue, and AI assessment activity.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/recruiter/job-roles"
            className="px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition duration-200 flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create Job Role</span>
          </Link>
          <Link
            href="/recruiter/knowledge"
            className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-200 font-semibold text-xs rounded-xl transition flex items-center space-x-2"
          >
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <span>Upload RAG Doc</span>
          </Link>
        </div>
      </div>

      {/* KPI Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex items-center space-x-4 relative overflow-hidden group hover:border-indigo-500/40 transition">
          <div className="p-3.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20 group-hover:scale-110 transition duration-300">
            <Briefcase className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Active Job Roles</p>
            <div className="flex items-baseline space-x-2 mt-0.5">
              <p className="text-3xl font-black text-white">{metrics?.active_job_roles_count ?? 0}</p>
              <span className="text-[11px] font-semibold text-emerald-400 flex items-center">
                +2 active
              </span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex items-center space-x-4 relative overflow-hidden group hover:border-sky-500/40 transition">
          <div className="p-3.5 bg-sky-500/10 text-sky-400 rounded-xl border border-sky-500/20 group-hover:scale-110 transition duration-300">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Active Candidates</p>
            <div className="flex items-baseline space-x-2 mt-0.5">
              <p className="text-3xl font-black text-white">{metrics?.active_candidates_count ?? 0}</p>
              <span className="text-[11px] font-semibold text-sky-400 flex items-center">
                in pipeline
              </span>
            </div>
          </div>
        </div>

        <div className="glass-panel p-6 rounded-2xl border border-slate-800 flex items-center space-x-4 relative overflow-hidden group hover:border-emerald-500/40 transition">
          <div className="p-3.5 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20 group-hover:scale-110 transition duration-300">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Completed Reports</p>
            <div className="flex items-baseline space-x-2 mt-0.5">
              <p className="text-3xl font-black text-white">{metrics?.completed_reports_count ?? 0}</p>
              <span className="text-[11px] font-semibold text-emerald-400">Evaluated</span>
            </div>
          </div>
        </div>

        <Link
          href="/recruiter/review-queue"
          className="glass-panel p-6 rounded-2xl border border-amber-500/30 bg-amber-500/5 hover:border-amber-500/60 transition shadow-lg flex items-center space-x-4 group cursor-pointer"
        >
          <div className="p-3.5 bg-amber-500/20 text-amber-300 rounded-xl border border-amber-500/40 group-hover:scale-110 transition duration-300">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-amber-300">Pending Reviews</p>
            <div className="flex items-baseline space-x-2 mt-0.5">
              <p className="text-3xl font-black text-amber-200">{metrics?.pending_hiring_reviews_count ?? 0}</p>
              <span className="text-[11px] font-bold text-amber-400 flex items-center group-hover:translate-x-0.5 transition">
                Action required <ArrowUpRight className="w-3 h-3 ml-0.5" />
              </span>
            </div>
          </div>
        </Link>
      </div>

      {/* Operational Overview & Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Interview Pipeline Breakdown */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Clock className="w-5 h-5 text-indigo-400" />
              <span>Interview Pipeline Breakdown</span>
            </h2>
            <Link href="/recruiter/interviews" className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition flex items-center space-x-1">
              <span>View all</span>
              <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {Object.entries(metrics?.interviews_by_status || {}).map(([statusKey, count]) => (
              <div key={statusKey} className="flex justify-between items-center text-xs p-3.5 bg-slate-900/90 rounded-xl border border-slate-800/80">
                <span className="font-semibold text-slate-300 uppercase tracking-wider">{statusKey.replace('_', ' ')}</span>
                <span className="font-bold text-indigo-300 bg-indigo-950 px-3 py-1 rounded-full border border-indigo-800">{count}</span>
              </div>
            ))}
            {Object.keys(metrics?.interviews_by_status || {}).length === 0 && (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800/60">
                No active interview sessions in current pipeline context.
              </div>
            )}
          </div>
        </div>

        {/* Recent Audit Log Activity Stream */}
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center space-x-2">
              <Activity className="w-5 h-5 text-emerald-400" />
              <span>Audit Log & Activity Stream</span>
            </h2>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Realtime</span>
          </div>

          <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
            {(metrics?.recent_activity || []).map((act) => (
              <div key={act.id} className="p-3 bg-slate-900/80 rounded-xl border border-slate-800/80 text-xs flex justify-between items-center hover:border-slate-700 transition">
                <div className="space-y-0.5">
                  <span className="font-bold text-slate-200 block">{act.action}</span>
                  <span className="text-[10px] font-mono text-slate-400">{act.resource_type}</span>
                </div>
                <span className="text-[10px] font-semibold text-slate-500 bg-slate-950 px-2 py-1 rounded-md border border-slate-800">
                  {new Date(act.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
            {(metrics?.recent_activity || []).length === 0 && (
              <div className="p-8 text-center text-xs text-slate-500 bg-slate-900/40 rounded-xl border border-slate-800/60">
                No recent activity recorded.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

