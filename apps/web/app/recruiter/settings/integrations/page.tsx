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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2">
          <Network className="w-6 h-6 text-indigo-600" />
          <span>ATS Integration Management</span>
        </h1>
        <p className="text-sm text-slate-500 mt-1">Configure Greenhouse, Lever, and Workday webhook connectors and synchronization.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Configure New Integration */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            <span>Configure Provider</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">ATS Provider</label>
              <select
                value={providerType}
                onChange={(e) => setProviderType(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white"
              >
                <option value="greenhouse">Greenhouse Harvest API</option>
                <option value="lever">Lever Postings API</option>
                <option value="workday">Workday RaaS Integration</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Integration Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Production Greenhouse Connector"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">API Key / Secret</label>
              <input
                type="password"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                placeholder="••••••••••••••••"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
              <p className="text-[10px] text-slate-400 mt-1">Secrets are encrypted and never returned in API responses.</p>
            </div>

            <button
              onClick={() => createMutation.mutate()}
              disabled={!secret || createMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              Save Integration
            </button>
          </div>
        </div>

        {/* Existing Integrations List */}
        <div className="lg:col-span-2 space-y-4">
          {(integrations || []).map((item) => (
            <div key={item.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex items-center justify-between">
              <div>
                <div className="flex items-center space-x-2">
                  <span className="font-bold text-slate-900 text-base">{item.name}</span>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      item.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
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
                  className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-semibold"
                >
                  Test Connection
                </button>

                <button
                  onClick={() => toggleStatusMutation.mutate({ id: item.id, active: item.status === 'ACTIVE' })}
                  className={`p-2 rounded-lg text-xs font-semibold ${
                    item.status === 'ACTIVE' ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-600'
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
