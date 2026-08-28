import { fetchApi } from '../lib/api-client';
import { CandidateProfile } from '../types';

export const candidateService = {
  async listCandidates(search?: string, page: number = 1, limit: number = 20): Promise<CandidateProfile[]> {
    const params = new URLSearchParams({ page: String(page), limit: String(limit) });
    if (search) params.append('search', search);
    return fetchApi<CandidateProfile[]>(`/candidates?${params.toString()}`);
  },

  async getCandidate(id: string): Promise<CandidateProfile> {
    return fetchApi<CandidateProfile>(`/candidates/${id}`);
  },

  async createCandidate(data: {
    first_name: string;
    last_name: string;
    email: string;
    phone?: string;
    headline?: string;
    summary?: string;
  }): Promise<CandidateProfile> {
    return fetchApi<CandidateProfile>('/candidates', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async updateCandidate(id: string, data: Partial<CandidateProfile>): Promise<CandidateProfile> {
    return fetchApi<CandidateProfile>(`/candidates/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  async archiveCandidate(id: string): Promise<void> {
    await fetchApi<void>(`/candidates/${id}/archive`, { method: 'POST' });
  },
};
