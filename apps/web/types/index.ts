export type AccountStatus = 'ACTIVE' | 'PENDING_VERIFICATION' | 'SUSPENDED';

export interface User {
  id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  account_status: AccountStatus;
  is_super_admin: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  role: 'ORGANIZATION_ADMIN' | 'RECRUITER' | 'HIRING_MANAGER' | 'CANDIDATE';
  status: 'ACTIVE' | 'SUSPENDED';
  organization?: Organization;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
  active_organization?: Organization;
  memberships: Membership[];
}

export interface CandidateSkill {
  id: string;
  skill_name: string;
  category?: string;
  years_experience?: number;
  proficiency_level?: string;
  source: 'MANUAL' | 'RESUME_AI';
}

export interface CandidateExperience {
  id: string;
  company_name: string;
  job_title: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  description?: string;
}

export interface CandidateEducation {
  id: string;
  institution: string;
  degree?: string;
  field_of_study?: string;
  end_year?: number;
}

export interface CandidateProfile {
  id: string;
  organization_id: string;
  user_id?: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  headline?: string;
  summary?: string;
  status: 'ACTIVE' | 'ARCHIVED';
  skills: CandidateSkill[];
  experiences: CandidateExperience[];
  educations: CandidateEducation[];
  created_at: string;
  updated_at: string;
}

export interface ResumeMetadata {
  id: string;
  candidate_profile_id: string;
  version_number: number;
  file_name: string;
  content_type: string;
  file_size_bytes: number;
  storage_object_key: string;
  processing_status: 'QUEUED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'OCR_REQUIRED';
  created_at: string;
}

export interface Requirement {
  skill_name: string;
  weight: number;
  required?: boolean;
}

export interface JobRole {
  id: string;
  organization_id: string;
  title: string;
  code: string;
  version_number: number;
  is_active_version: boolean;
  requirements: Requirement[];
  created_at: string;
}

export interface KnowledgeBase {
  id: string;
  organization_id: string;
  name: string;
  description?: string;
  document_count: number;
  created_at: string;
}

export interface KnowledgeDocument {
  id: string;
  knowledge_base_id: string;
  title: string;
  filename: string;
  chunk_count: number;
  ingestion_status: 'PENDING' | 'QUEUED' | 'PROCESSING' | 'READY' | 'FAILED' | 'OCR_REQUIRED';
  created_at: string;
}

export type InterviewStatus = 'CREATED' | 'READY' | 'IN_PROGRESS' | 'PAUSED' | 'COMPLETING' | 'COMPLETED' | 'CANCELLED';

export interface InterviewSession {
  id: string;
  organization_id: string;
  candidate_profile_id: string;
  job_role_id: string;
  status: InterviewStatus;
  created_at: string;
  completed_at?: string;
}

export interface InterviewQuestion {
  id: string;
  interview_session_id: string;
  sequence_number: number;
  question_text: string;
  question_type: string;
  topic: string;
  subtopic?: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
}

export interface RequirementScorecard {
  requirement_skill: string;
  weight: number;
  evidence_count: number;
  average_score: number;
  status: 'ASSESSED' | 'PARTIALLY_ASSESSED' | 'NOT_ASSESSED';
}

export interface InterviewReport {
  id: string;
  interview_session_id: string;
  report_version: number;
  scoring_version: string;
  overall_score: number;
  technical_competency_score?: number;
  reasoning_score?: number;
  communication_score?: number;
  completeness_score?: number;
  requirement_coverage_score?: number;
  seniority_assessment: string;
  executive_summary: string;
  top_strengths: { strengths: string[] };
  growth_areas: { growth_areas: string[] };
  recommendation: 'STRONG_HIRE' | 'HIRE' | 'BORDERLINE' | 'NO_HIRE';
  hiring_signal: 'STRONG_HIRE_SIGNAL' | 'HIRE_SIGNAL' | 'MIXED_SIGNAL' | 'NO_HIRE_SIGNAL' | 'INSUFFICIENT_EVIDENCE';
  requirement_scorecards_json?: { scorecards: RequirementScorecard[] };
  created_at: string;
}

export type HiringDecisionStatus = 'PENDING_REVIEW' | 'SHORTLISTED' | 'HIRED' | 'REJECTED' | 'ON_HOLD';

export interface HiringDecision {
  id?: string;
  interview_session_id: string;
  candidate_profile_id: string;
  status: HiringDecisionStatus;
  decision_maker_user_id: string;
  rationale_text?: string;
  created_at?: string;
  updated_at?: string;
}

export interface HiringDecisionHistory {
  id: string;
  interview_session_id: string;
  previous_status?: string;
  new_status: string;
  actor_user_id: string;
  rationale_text?: string;
  created_at: string;
}

export interface RecruiterDashboardMetrics {
  organization_id: string;
  active_job_roles_count: number;
  active_candidates_count: number;
  interviews_by_status: Record<string, number>;
  completed_reports_count: number;
  pending_hiring_reviews_count: number;
  recent_activity: Array<{
    id: string;
    action: string;
    actor_type: string;
    resource_type: string;
    resource_id?: string;
    created_at: string;
  }>;
}

export interface CandidatePipelineItem {
  candidate_id: string;
  full_name: string;
  email: string;
  interview_id?: string;
  interview_status?: string;
  job_role_id?: string;
  latest_score?: number;
  hiring_signal?: string;
  human_decision: HiringDecisionStatus;
  last_activity_at: string;
}

export interface CandidateComparisonItem {
  candidate_id: string;
  full_name: string;
  interview_id?: string;
  overall_score?: number;
  technical_competency_score?: number;
  reasoning_score?: number;
  communication_score?: number;
  requirement_scorecards: RequirementScorecard[];
  hiring_signal: string;
  human_decision: HiringDecisionStatus;
}
