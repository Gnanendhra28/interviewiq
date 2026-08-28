from typing import List, Optional

from pydantic import BaseModel, Field


class ExtractedSkill(BaseModel):
    skill_name: str = Field(..., description="Normalized name of the skill")
    category: Optional[str] = Field(None, description="Domain category e.g. Programming Languages, Cloud, Frameworks")
    proficiency_level: Optional[str] = Field("INTERMEDIATE", description="BEGINNER, INTERMEDIATE, ADVANCED, EXPERT")
    years_experience: Optional[float] = Field(None, description="Estimated years of experience if stated or inferred")
    source_evidence: Optional[str] = Field(None, description="Direct quote or snippet from resume text")


class ExtractedExperience(BaseModel):
    company_name: str = Field(..., description="Name of the employing company or organization")
    job_title: str = Field(..., description="Title of the position held")
    start_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD or YYYY-MM if available")
    end_date: Optional[str] = Field(None, description="ISO format YYYY-MM-DD or YYYY-MM if available")
    is_current: bool = Field(False, description="True if currently employed in this role")
    description: Optional[str] = Field(None, description="Summary of responsibilities and achievements")
    source_evidence: Optional[str] = Field(None, description="Direct text snippet from resume")


class ExtractedEducation(BaseModel):
    institution: str = Field(..., description="Name of university, college, or school")
    degree: Optional[str] = Field(None, description="Degree earned e.g. B.S., M.S., Ph.D.")
    field_of_study: Optional[str] = Field(None, description="Major or specialization e.g. Computer Science")
    end_year: Optional[int] = Field(None, description="Graduation year")
    source_evidence: Optional[str] = Field(None, description="Direct text snippet from resume")


class ResumeAnalysisOutput(BaseModel):
    candidate_summary: str = Field(..., description="Executive 2-3 sentence summary of candidate profile")
    inferred_seniority: Optional[str] = Field("MID_LEVEL", description="JUNIOR, MID_LEVEL, SENIOR, LEAD, EXECUTIVE")
    skills: List[ExtractedSkill] = Field(default_factory=list)
    work_experience: List[ExtractedExperience] = Field(default_factory=list)
    education: List[ExtractedEducation] = Field(default_factory=list)
    confidence_score: float = Field(0.95, description="Confidence score between 0.0 and 1.0")
