import { fetchApi } from '../lib/api-client';
import { InterviewReport } from '../types';

export const reportService = {
  async getLatestReport(interview_id: string): Promise<InterviewReport> {
    return fetchApi<InterviewReport>(`/interviews/${interview_id}/report`);
  },

  async listReportVersions(interview_id: string): Promise<InterviewReport[]> {
    return fetchApi<InterviewReport[]>(`/interviews/${interview_id}/reports`);
  },

  async regenerateReport(interview_id: string): Promise<{ target_version: number; message: string }> {
    return fetchApi<{ target_version: number; message: string }>(`/interviews/${interview_id}/reports/regenerate`, {
      method: 'POST',
    });
  },

  async getDecisionSupport(interview_id: string): Promise<Record<string, any>> {
    return fetchApi<Record<string, any>>(`/interviews/${interview_id}/decision-support`);
  },
};
