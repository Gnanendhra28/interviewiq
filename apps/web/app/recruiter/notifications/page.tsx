'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationService } from '../../../services/notification-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { Bell, Check, Slack } from 'lucide-react';

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('');

  const { data: notifications, isLoading, error } = useQuery({
    queryKey: ['notificationsList'],
    queryFn: () => notificationService.listNotifications(),
  });

  const markReadMutation = useMutation({
    mutationFn: (id: string) => notificationService.markAsRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notificationsList'] }),
  });

  const saveSlackPrefMutation = useMutation({
    mutationFn: () =>
      notificationService.saveNotificationPreference({
        channel: 'SLACK',
        enabled_events_json: { report_generated: true, hiring_decision: true },
        webhook_url: slackWebhookUrl,
      }),
    onSuccess: () => alert('Slack notification preference saved!'),
  });

  if (isLoading) return <LoadingState message="Loading recruiter notifications..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <Bell className="w-6 h-6 text-indigo-600" />
          <span>Notification Center & Webhook Channels</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">Manage in-app notifications and Slack/Teams webhook alert subscriptions.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Slack/Teams Webhook Preferences */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Slack className="w-5 h-5 text-indigo-600" />
            <span>Slack Webhook Subscription</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Incoming Webhook URL</label>
              <input
                type="text"
                value={slackWebhookUrl}
                onChange={(e) => setSlackWebhookUrl(e.target.value)}
                placeholder="https://hooks.slack.com/services/..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono text-xs"
              />
            </div>

            <button
              onClick={() => saveSlackPrefMutation.mutate()}
              disabled={!slackWebhookUrl || saveSlackPrefMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              Save Slack Preference
            </button>
          </div>
        </div>

        {/* Notifications Stream */}
        <div className="lg:col-span-2 space-y-3">
          {(notifications || []).map((n) => (
            <div
              key={n.id}
              className={`p-4 rounded-xl border transition flex items-center justify-between ${
                n.is_read ? 'bg-slate-50 border-slate-200' : 'bg-white border-indigo-200 shadow-sm'
              }`}
            >
              <div>
                <span className="text-xs font-bold text-indigo-600 uppercase tracking-wider">{n.channel}</span>
                <h3 className="font-bold text-slate-900 text-sm mt-0.5">{n.title}</h3>
                <p className="text-xs text-slate-600 mt-1">{n.message}</p>
                <span className="text-[10px] text-slate-400 block mt-1">{new Date(n.created_at).toLocaleString()}</span>
              </div>

              {!n.is_read && (
                <button
                  onClick={() => markReadMutation.mutate(n.id)}
                  className="p-2 text-slate-400 hover:text-emerald-600 rounded-lg"
                  title="Mark as read"
                >
                  <Check className="w-4 h-4" />
                </button>
              )}
            </div>
          ))}

          {(notifications || []).length === 0 && <p className="text-slate-400 text-sm py-4 text-center">No notifications found.</p>}
        </div>
      </div>
    </div>
  );
}
