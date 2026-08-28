'use client';

import React from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { recruiterService } from '../../../services/recruiter-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { ShieldAlert, ArrowRight, AlertCircle, FileCheck } from 'lucide-react';

export default function ReviewQueuePage() {
  const { data: queueData, isLoading, error } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: () => recruiterService.getReviewQueue(),
  });

  if (isLoading) return <LoadingState message="Loading recruiter review queue..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="border-b border-slate-800/80 pb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center space-x-2">
          <ShieldAlert className="w-6 h-6 text-amber-400" />
          <span>Actionable Recruiter Review Queue</span>
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Completed interview reports awaiting recruiter decisions and operational processing exceptions.
        </p>
      </div>

      <div className="glass-panel border border-slate-800/80 rounded-xl shadow-2xl overflow-hidden">
        <div className="p-4 bg-slate-900/90 border-b border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
          Actionable Items ({queueData?.total_actionable_items ?? 0})
        </div>

        <div className="divide-y divide-slate-800/60">
          {(queueData?.queue || []).map((item, idx) => (
            <div key={idx} className="p-5 flex items-center justify-between hover:bg-slate-800/40 transition">
              <div className="flex items-start space-x-4">
                <div
                  className={`p-2.5 rounded-lg border ${
                    item.queue_item_type === 'REPORT_PENDING_DECISION' ? 'bg-amber-500/20 text-amber-300 border-amber-500/30' : 'bg-rose-500/20 text-rose-300 border-rose-500/30'
                  }`}
                >
                  {item.queue_item_type === 'REPORT_PENDING_DECISION' ? (
                    <FileCheck className="w-5 h-5" />
                  ) : (
                    <AlertCircle className="w-5 h-5" />
                  )}
                </div>

                <div>
                  <span
                    className={`inline-block px-2 py-0.5 text-[10px] font-bold uppercase rounded border ${
                      item.priority === 'CRITICAL' ? 'bg-rose-500/20 text-rose-300 border-rose-500/30' : 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                    }`}
                  >
                    {item.priority}
                  </span>
                  <h3 className="font-bold text-white text-base mt-1">
                    {item.queue_item_type === 'REPORT_PENDING_DECISION'
                      ? `Report Decision Pending: ${item.candidate_name}`
                      : `Processing Failure: ${item.job_type}`}
                  </h3>
                  {item.overall_score !== undefined && (
                    <p className="text-xs text-slate-400 mt-0.5">
                      Score: <strong className="text-indigo-300">{item.overall_score.toFixed(1)}/10</strong> | Signal: <strong className="text-slate-200">{item.hiring_signal}</strong>
                    </p>
                  )}
                  {item.error_message && <p className="text-xs text-rose-400 mt-0.5">{item.error_message}</p>}
                </div>
              </div>

              <div>
                {item.interview_id && (
                  <Link
                    href={`/recruiter/interviews/${item.interview_id}/report`}
                    className="inline-flex items-center space-x-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-indigo-600/30 transition"
                  >
                    <span>Review Report</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                )}
              </div>
            </div>
          ))}

          {(queueData?.queue || []).length === 0 && (
            <div className="p-8 text-center text-slate-400 text-sm">
              All review queue items are clear. No pending hiring decisions or failed background jobs!
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
