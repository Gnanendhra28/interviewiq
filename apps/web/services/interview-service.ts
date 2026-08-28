import { fetchApi } from '../lib/api-client';
import { InterviewSession, InterviewQuestion } from '../types';

export const interviewService = {
  async listInterviews(candidate_id?: string): Promise<InterviewSession[]> {
    const query = candidate_id ? `?candidate_profile_id=${candidate_id}` : '';
    return fetchApi<InterviewSession[]>(`/interviews${query}`);
  },

  async getInterview(id: string): Promise<InterviewSession> {
    return fetchApi<InterviewSession>(`/interviews/${id}`);
  },

  async createInterview(candidate_profile_id: string, job_role_id: string): Promise<InterviewSession> {
    return fetchApi<InterviewSession>('/interviews', {
      method: 'POST',
      body: JSON.stringify({ candidate_profile_id, job_role_id }),
    });
  },

  async prepareInterview(interview_id: string, knowledge_base_ids: string[] = []): Promise<void> {
    await fetchApi<void>(`/interviews/${interview_id}/prepare`, {
      method: 'POST',
      body: JSON.stringify({ knowledge_base_ids }),
    });
  },

  async startInterview(interview_id: string): Promise<void> {
    await fetchApi<void>(`/interviews/${interview_id}/start`, { method: 'POST' });
  },

  async getNextQuestion(interview_id: string, idempotency_key?: string): Promise<InterviewQuestion> {
    const key = idempotency_key || `q_${Math.random().toString(36).substring(2, 10)}`;
    return fetchApi<InterviewQuestion>(`/interviews/${interview_id}/question`, {
      method: 'POST',
      body: JSON.stringify({ idempotency_key: key }),
    });
  },

  async submitAnswer(interview_id: string, question_id: string, answer_text: string, idempotency_key: string): Promise<{ id: string }> {
    return fetchApi<{ id: string }>(`/interviews/${interview_id}/questions/${question_id}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answer_text, idempotency_key }),
    });
  },

  async getProgress(interview_id: string): Promise<{ turn_count: number; is_completed: boolean; current_status: string }> {
    return fetchApi<{ turn_count: number; is_completed: boolean; current_status: string }>(`/interviews/${interview_id}/progress`);
  },

  async pauseInterview(interview_id: string, reason?: string): Promise<void> {
    await fetchApi<void>(`/interviews/${interview_id}/pause`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  async resumeInterview(interview_id: string): Promise<void> {
    await fetchApi<void>(`/interviews/${interview_id}/resume`, { method: 'POST' });
  },

  async completeInterview(interview_id: string, reason?: string): Promise<void> {
    await fetchApi<void>(`/interviews/${interview_id}/complete`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },
};
