'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobRoleService } from '../../../services/job-role-service';
import { LoadingState } from '../../../components/LoadingState';
import { ErrorBanner } from '../../../components/ErrorBanner';
import { Briefcase, Plus, Layers } from 'lucide-react';

export default function JobRolesPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [code, setCode] = useState('');
  const [skillName, setSkillName] = useState('');
  const [weight, setWeight] = useState(1.0);
  const [requirements, setRequirements] = useState<Array<{ skill_name: string; weight: number }>>([]);

  const { data: jobRoles, isLoading, error } = useQuery({
    queryKey: ['jobRoles'],
    queryFn: () => jobRoleService.listJobRoles(),
  });

  const createMutation = useMutation({
    mutationFn: () => jobRoleService.createJobRole({ title, code, requirements }),
    onSuccess: () => {
      setTitle('');
      setCode('');
      setRequirements([]);
      queryClient.invalidateQueries({ queryKey: ['jobRoles'] });
    },
  });

  const addRequirement = () => {
    if (!skillName) return;
    setRequirements([...requirements, { skill_name: skillName, weight: Number(weight) }]);
    setSkillName('');
    setWeight(1.0);
  };

  if (isLoading) return <LoadingState message="Loading job roles..." />;
  if (error) return <ErrorBanner message={(error as Error).message} />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="border-b border-slate-800/80 pb-6">
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Job Role Management & Versioning</h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Create immutable job role specifications and skill requirements for adaptive interviews.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Job Role Creation Form */}
        <div className="glass-panel p-6 rounded-xl border border-slate-800/80 shadow-2xl space-y-4">
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-400" />
            <span>Create New Job Role</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Senior Backend Architect"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Role Code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="SR_BE_ARCH"
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs font-mono focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="border-t border-slate-800/60 pt-3">
              <label className="block text-xs font-semibold text-slate-400 mb-2">Requirements</label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  placeholder="Skill (e.g. PostgreSQL)"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
                />
                <input
                  type="number"
                  step="0.5"
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-20 px-2 py-1.5 bg-slate-950 border border-slate-800 text-slate-100 rounded-lg text-xs focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={addRequirement}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-bold transition"
                >
                  Add
                </button>
              </div>

              <div className="space-y-1 max-h-40 overflow-y-auto">
                {requirements.map((r, i) => (
                  <div key={i} className="flex justify-between items-center bg-slate-900/90 border border-slate-800 p-2 rounded text-xs">
                    <span className="text-slate-200">{r.skill_name}</span>
                    <span className="font-bold text-indigo-400">Weight: {r.weight}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => createMutation.mutate()}
              disabled={!title || !code || createMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs rounded-xl shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
            >
              Save Job Role
            </button>
          </div>
        </div>

        {/* Existing Job Roles List */}
        <div className="lg:col-span-2 space-y-4">
          {(jobRoles || []).map((role) => (
            <div key={role.id} className="glass-panel p-5 rounded-xl border border-slate-800/80 shadow-2xl space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-white text-base">{role.title}</h3>
                  <span className="inline-block px-2.5 py-0.5 bg-slate-900 border border-slate-800 text-indigo-300 rounded text-xs font-mono mt-1">
                    {role.code} (v{role.version_number})
                  </span>
                </div>
                <span className="px-2.5 py-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-bold rounded-full">ACTIVE</span>
              </div>

              <div className="border-t border-slate-800/60 pt-3">
                <p className="text-xs font-semibold text-slate-400 mb-2">Configured Skill Requirements:</p>
                <div className="flex flex-wrap gap-2">
                  {(role.requirements || []).map((req, idx) => (
                    <span key={idx} className="px-2.5 py-1 bg-slate-900/90 border border-slate-800 rounded text-xs font-medium text-slate-300">
                      {req.skill_name} (Weight: {req.weight})
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
