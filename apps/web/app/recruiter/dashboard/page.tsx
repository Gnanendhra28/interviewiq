'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { recruiterService } from '../../../services/recruiter-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { Briefcase, Users, FileCheck, ShieldAlert, Activity, CheckCircle, Clock } from 'lucide-react';
import Link from 'next/link';

export default function DashboardPage() {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ['recruiterDashboard'],
    queryFn: () => recruiterService.getDashboard(),
  });

  if (isLoading) return <LoadingState message="Loading recruiter dashboard metrics..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Recruiter Command Center</h1>
        <p className="text-sm text-slate-500 mt-1">Authoritative operational pipeline metrics and candidate review status.</p>
      </div>

      {/* KPI Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-indigo-50 text-indigo-600 rounded-lg">
            <Briefcase className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Job Roles</p>
            <p className="text-2xl font-bold text-slate-900">{metrics?.active_job_roles_count ?? 0}</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-blue-50 text-blue-600 rounded-lg">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Active Candidates</p>
            <p className="text-2xl font-bold text-slate-900">{metrics?.active_candidates_count ?? 0}</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center space-x-4">
          <div className="p-3 bg-emerald-50 text-emerald-600 rounded-lg">
            <CheckCircle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">Completed Reports</p>
            <p className="text-2xl font-bold text-slate-900">{metrics?.completed_reports_count ?? 0}</p>
          </div>
        </div>

        <Link
          href="/recruiter/review-queue"
          className="bg-white p-5 rounded-xl border border-amber-200 bg-amber-50/30 hover:border-amber-300 transition shadow-sm flex items-center space-x-4 cursor-pointer"
        >
          <div className="p-3 bg-amber-100 text-amber-700 rounded-lg">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-800">Pending Reviews</p>
            <p className="text-2xl font-bold text-amber-900">{metrics?.pending_hiring_reviews_count ?? 0}</p>
          </div>
        </Link>
      </div>

      {/* Operational Overview & Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Interview Status Breakdown */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            <span>Interview Pipeline Breakdown</span>
          </h2>

          <div className="space-y-3">
            {Object.entries(metrics?.interviews_by_status || {}).map(([statusKey, count]) => (
              <div key={statusKey} className="flex justify-between items-center text-sm p-3 bg-slate-50 rounded-lg">
                <span className="font-medium text-slate-700">{statusKey}</span>
                <span className="font-bold text-slate-900 bg-slate-200 px-2.5 py-1 rounded-full text-xs">{count}</span>
              </div>
            ))}
            {Object.keys(metrics?.interviews_by_status || {}).length === 0 && (
              <p className="text-sm text-slate-500 py-4 text-center">No active interview sessions found.</p>
            )}
          </div>
        </div>

        {/* Recent Audit Log Activity */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Activity className="w-5 h-5 text-indigo-600" />
            <span>Recent Activity Stream</span>
          </h2>

          <div className="space-y-3 max-h-80 overflow-y-auto">
            {(metrics?.recent_activity || []).map((act) => (
              <div key={act.id} className="border-b border-slate-100 pb-2 text-xs flex justify-between items-center">
                <div>
                  <span className="font-semibold text-slate-800">{act.action}</span>
                  <span className="text-slate-400 block">{act.resource_type}</span>
                </div>
                <span className="text-slate-400">{new Date(act.created_at).toLocaleTimeString()}</span>
              </div>
            ))}
            {(metrics?.recent_activity || []).length === 0 && (
              <p className="text-sm text-slate-500 py-4 text-center">No recent activity recorded.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
