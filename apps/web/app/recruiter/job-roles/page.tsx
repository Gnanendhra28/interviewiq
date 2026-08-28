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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Job Role Management & Versioning</h1>
        <p className="text-sm text-slate-500 mt-1">
          Create immutable job role specifications and skill requirements for adaptive interviews.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Job Role Creation Form */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900 flex items-center space-x-2">
            <Plus className="w-5 h-5 text-indigo-600" />
            <span>Create New Job Role</span>
          </h2>

          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Senior Backend Architect"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Role Code</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                placeholder="SR_BE_ARCH"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono"
              />
            </div>

            <div className="border-t border-slate-100 pt-3">
              <label className="block text-xs font-semibold text-slate-600 mb-2">Requirements</label>
              <div className="flex space-x-2 mb-2">
                <input
                  type="text"
                  placeholder="Skill (e.g. PostgreSQL)"
                  value={skillName}
                  onChange={(e) => setSkillName(e.target.value)}
                  className="w-full px-3 py-1.5 border border-slate-300 rounded-lg text-xs"
                />
                <input
                  type="number"
                  step="0.5"
                  value={weight}
                  onChange={(e) => setWeight(Number(e.target.value))}
                  className="w-20 px-2 py-1.5 border border-slate-300 rounded-lg text-xs"
                />
                <button
                  type="button"
                  onClick={addRequirement}
                  className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-semibold"
                >
                  Add
                </button>
              </div>

              <div className="space-y-1 max-h-40 overflow-y-auto">
                {requirements.map((r, i) => (
                  <div key={i} className="flex justify-between items-center bg-slate-50 p-2 rounded text-xs">
                    <span>{r.skill_name}</span>
                    <span className="font-bold text-indigo-600">Weight: {r.weight}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => createMutation.mutate()}
              disabled={!title || !code || createMutation.isPending}
              className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm rounded-lg transition disabled:opacity-50"
            >
              Save Job Role
            </button>
          </div>
        </div>

        {/* Existing Job Roles List */}
        <div className="lg:col-span-2 space-y-4">
          {(jobRoles || []).map((role) => (
            <div key={role.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-bold text-slate-900 text-base">{role.title}</h3>
                  <span className="inline-block px-2.5 py-0.5 bg-slate-100 text-slate-600 rounded text-xs font-mono mt-1">
                    {role.code} (v{role.version_number})
                  </span>
                </div>
                <span className="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-bold rounded-full">ACTIVE</span>
              </div>

              <div className="border-t border-slate-100 pt-3">
                <p className="text-xs font-semibold text-slate-500 mb-2">Configured Skill Requirements:</p>
                <div className="flex flex-wrap gap-2">
                  {(role.requirements || []).map((req, idx) => (
                    <span key={idx} className="px-2.5 py-1 bg-slate-50 border border-slate-200 rounded text-xs font-medium text-slate-700">
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
