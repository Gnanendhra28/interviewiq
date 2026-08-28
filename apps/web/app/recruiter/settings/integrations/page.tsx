'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { integrationService } from '../../../../services/integration-service';
import { LoadingState } from '../../../../components/LoadingState';
import { ErrorBanner } from '../../../../components/ErrorBanner';
import { Network, Plus, CheckCircle, Power } from 'lucide-react';

export default function IntegrationsSettingsPage() {
  const queryClient = useQueryClient();
  const [providerType, setProviderType] = useState('greenhouse');
  const [name, setName] = useState('');
  const [secret, setSecret] = useState('');

  const { data: integrations, isLoading, error } = useQuery({
    queryKey: ['integrationsList'],
    queryFn: () => integrationService.listIntegrations(),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      integrationService.createIntegration({
        provider_type: providerType,
        name: name || `${providerType.toUpperCase()} Integration`,
        config_metadata_json: { environment: 'production' },
        secret,
      }),
    onSuccess: () => {
      setName('');
      setSecret('');
      queryClient.invalidateQueries({ queryKey: ['integrationsList'] });
    },
  });

  const testMutation = useMutation({
    mutationFn: (id: string) => integrationService.testIntegration(id),
    onSuccess: (res) => alert(`Connection Test Result: ${res.message || 'SUCCESS'}`),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      active ? integrationService.disableIntegration(id) : integrationService.enableIntegration(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['integrationsList'] }),
  });

  if (isLoading) return <LoadingState message="Loading organization ATS integrations..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="border-b border-slate-800/80 pb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center space-x-2">
          <Network className="w-6 h-6 text-indigo-400" />
          <span>ATS Integration Management</span>
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">Configure Greenhouse, Lever, and Workday webhook connectors and synchronization.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Configure New Integration */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-400" />
            <span>Configure Provider</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">ATS Provider</label>
              <select
                value={providerType}
                onChange={(e) => setProviderType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-800 rounded-lg text-xs bg-slate-950 text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="greenhouse" className="bg-slate-900 text-slate-200">Greenhouse Harvest API</option>
                <option value="lever" className="bg-slate-900 text-slate-200">Lever Postings API</option>
                <option value="workday" className="bg-slate-900 text-slate-200">Workday RaaS Integration</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Integration Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Production Greenhouse Connector"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">API Key / Secret</label>
              <input
                type="password"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                placeholder="••••••••••••••••"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[10px] text-slate-400 mt-1">Secrets are encrypted and never returned in API responses.</p>
            </div>

            <button
              onClick={() => createMutation.mutate()}
              disabled={!secret || createMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              Save Integration
            </button>
          </div>
        </div>

        {/* Existing Integrations List */}
        <div className="lg:col-span-2 space-y-4">
          {(integrations || []).map((item) => (
            <div key={item.id} className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-2xl flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-white text-base">{item.name}</span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${
                      item.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700/60'
                    }`}
                  >
                    {item.status}
                  </span>
                </div>
                <span className="text-xs text-slate-400 block mt-1 uppercase font-mono">Provider: {item.provider_type}</span>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => testMutation.mutate(item.id)}
                  disabled={testMutation.isPending}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-bold transition"
                >
                  Test Connection
                </button>

                <button
                  onClick={() => toggleStatusMutation.mutate({ id: item.id, active: item.status === 'ACTIVE' })}
                  className={`p-2 rounded-xl border transition ${
                    item.status === 'ACTIVE' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                  title="Toggle Active Status"
                >
                  <Power className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
          {(integrations || []).length === 0 && <p className="text-slate-400 text-sm py-4 text-center">No ATS integrations configured.</p>}
        </div>
      </div>
    </div>
  );
}
