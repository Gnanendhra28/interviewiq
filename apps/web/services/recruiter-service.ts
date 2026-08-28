import { fetchApi } from '../lib/api-client';
import {
  RecruiterDashboardMetrics,
  CandidatePipelineItem,
  CandidateComparisonItem,
  HiringDecision,
  HiringDecisionHistory,
  HiringDecisionStatus,
} from '../types';

export const recruiterService = {
  async getDashboard(): Promise<RecruiterDashboardMetrics> {
    return fetchApi<RecruiterDashboardMetrics>('/recruiter/dashboard');
  },

  async getCandidatePipeline(filters: {
    job_role_id?: string;
    interview_status?: string;
    hiring_signal?: string;
    human_decision_status?: string;
    search?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<{ candidates: CandidatePipelineItem[]; count: number; page: number; limit: number }> {
    const params = new URLSearchParams();
    if (filters.job_role_id) params.append('job_role_id', filters.job_role_id);
    if (filters.interview_status) params.append('interview_status', filters.interview_status);
    if (filters.hiring_signal) params.append('hiring_signal', filters.hiring_signal);
    if (filters.human_decision_status) params.append('human_decision_status', filters.human_decision_status);
    if (filters.search) params.append('search', filters.search);
    if (filters.page) params.append('page', String(filters.page));
    if (filters.limit) params.append('limit', String(filters.limit));

    return fetchApi<{ candidates: CandidatePipelineItem[]; count: number; page: number; limit: number }>(
      `/recruiter/candidates?${params.toString()}`
    );
  },

  async getCandidateTimeline(candidate_id: string): Promise<Array<{ event_type: string; description: string; timestamp: string }>> {
    return fetchApi<Array<{ event_type: string; description: string; timestamp: string }>>(
      `/recruiter/candidates/${candidate_id}/timeline`
    );
  },

  async compareCandidates(candidate_ids: string[]): Promise<{ comparison_count: number; candidates: CandidateComparisonItem[] }> {
    return fetchApi<{ comparison_count: number; candidates: CandidateComparisonItem[] }>('/recruiter/candidates/compare', {
      method: 'POST',
      body: JSON.stringify({ candidate_ids }),
    });
  },

  async getReviewQueue(): Promise<{ total_actionable_items: number; queue: Array<any> }> {
    return fetchApi<{ total_actionable_items: number; queue: Array<any> }>('/recruiter/review-queue');
  },

  async recordHiringDecision(interview_id: string, status: HiringDecisionStatus, rationale_text?: string): Promise<HiringDecision> {
    return fetchApi<HiringDecision>(`/interviews/${interview_id}/decision`, {
      method: 'POST',
      body: JSON.stringify({ status, rationale_text }),
    });
  },

  async getHiringDecision(interview_id: string): Promise<HiringDecision> {
    return fetchApi<HiringDecision>(`/interviews/${interview_id}/decision`);
  },

  async getHiringDecisionHistory(interview_id: string): Promise<HiringDecisionHistory[]> {
    return fetchApi<HiringDecisionHistory[]>(`/interviews/${interview_id}/decision-history`);
  },
};
