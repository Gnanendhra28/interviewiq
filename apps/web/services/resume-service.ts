import { fetchApi } from '../lib/api-client';
import { ResumeMetadata } from '../types';

export const resumeService = {
  async uploadResume(candidate_id: string, file: File): Promise<ResumeMetadata> {
    const formData = new FormData();
    formData.append('file', file);

    return fetchApi<ResumeMetadata>(`/candidates/${candidate_id}/resumes/upload`, {
      method: 'POST',
      body: formData,
    });
  },

  async getResumeStatus(resume_id: string): Promise<ResumeMetadata> {
    return fetchApi<ResumeMetadata>(`/resumes/${resume_id}/processing-status`);
  },

  async listResumeVersions(candidate_id: string): Promise<ResumeMetadata[]> {
    return fetchApi<ResumeMetadata[]>(`/candidates/${candidate_id}/resumes`);
  },
};
