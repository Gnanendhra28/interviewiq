from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CandidateProfileSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    years_experience: float = 0.0
    summary: str = ""
    primary_skills: List[str] = Field(default_factory=list)
    secondary_skills: List[str] = Field(default_factory=list)
    work_history: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)


class QuestionContext(BaseModel):
    candidate_profile: Dict[str, Any]
    target_role: str
    selected_topic: str
    retrieved_chunks: List[Dict[str, Any]]
    previous_performance_summary: Optional[str] = None
    difficulty: str = "MEDIUM"


class InterviewQuestionSchema(BaseModel):
    question_text: str
    question_type: str = "TECHNICAL_DEEP_DIVE"
    topic: str
    difficulty: str
    expected_key_points: List[str]
    sample_answer_guidelines: str
    traceability: Dict[str, Any]


class AnswerSubmissionContext(BaseModel):
    question_text: str
    expected_key_points: List[str]
    candidate_answer: str
    target_role: str
    difficulty: str


class EvaluationResultSchema(BaseModel):
    score_overall: float = Field(..., ge=0.0, le=10.0)
    score_technical_accuracy: float = Field(..., ge=0.0, le=10.0)
    score_depth: float = Field(..., ge=0.0, le=10.0)
    score_clarity: float = Field(..., ge=0.0, le=10.0)
    key_strengths: List[str]
    missing_elements: List[str]
    detailed_feedback: str
    recommended_next_difficulty: str
    suggested_follow_up_topic: Optional[str] = None


class SessionSummaryContext(BaseModel):
    candidate_profile: Dict[str, Any]
    target_role: str
    questions_and_evaluations: List[Dict[str, Any]]


class InterviewReportSchema(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=10.0)
    executive_summary: str
    seniority_assessment: str
    top_strengths: List[str]
    primary_growth_areas: List[str]
    skill_breakdown: List[Dict[str, Any]]
    recommendation: str


class AIProvider(ABC):
    """
    Abstract AI Provider Interface.
    All LLM capabilities (Gemini, etc.) must implement this contract.
    """

    @abstractmethod
    async def analyze_resume(self, file_bytes: bytes, file_type: str) -> CandidateProfileSchema:
        """Extract structured candidate profile from resume file."""
        pass

    @abstractmethod
    async def generate_question(self, context: QuestionContext) -> InterviewQuestionSchema:
        """Generate role-grounded adaptive interview question with RAG context."""
        pass

    @abstractmethod
    async def evaluate_answer(self, submission: AnswerSubmissionContext) -> EvaluationResultSchema:
        """Perform structured evaluation of candidate answer."""
        pass

    @abstractmethod
    async def generate_report(self, session_summary: SessionSummaryContext) -> InterviewReportSchema:
        """Synthesize final interview performance report."""
        pass

    @abstractmethod
    async def generate_embeddings(self, text_chunks: List[str]) -> List[List[float]]:
        """Generate high-dimensional vector embeddings for text chunks."""
        pass
