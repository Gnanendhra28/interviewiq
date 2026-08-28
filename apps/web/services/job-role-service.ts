import { fetchApi } from '../lib/api-client';
import { JobRole, Requirement } from '../types';

export const jobRoleService = {
  async listJobRoles(): Promise<JobRole[]> {
    return fetchApi<JobRole[]>('/job-roles');
  },

  async getJobRole(id: string): Promise<JobRole> {
    return fetchApi<JobRole>(`/job-roles/${id}`);
  },

  async createJobRole(data: { title: string; code: string; requirements: Requirement[] }): Promise<JobRole> {
    return fetchApi<JobRole>('/job-roles', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async createNewVersion(id: string, data: { requirements: Requirement[] }): Promise<JobRole> {
    return fetchApi<JobRole>(`/job-roles/${id}/versions`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async archiveJobRole(id: string): Promise<void> {
    await fetchApi<void>(`/job-roles/${id}/archive`, { method: 'POST' });
  },
};
