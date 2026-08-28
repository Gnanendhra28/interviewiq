import uuid
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.app.core.logging import logger
from apps.api.app.modules.audit_logging.infrastructure.orm import AuditLogORM
from apps.api.app.modules.candidates.infrastructure.orm import (
    CandidateEducationORM,
    CandidateExperienceORM,
    CandidateProfileORM,
    CandidateSkillORM,
)
from apps.api.app.modules.resumes.domain.schemas import ResumeAnalysisOutput


class ApplyResumeProjectionUseCase:
    """
    Projects validated ResumeAnalysis intelligence into Candidate Profile components.
    Preserves MANUAL provenance (never overwrites recruiter- or candidate-entered skills).
    Enforces tenant organization boundaries (ADR 023).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute(
        self,
        organization_id: uuid.UUID,
        candidate_id: uuid.UUID,
        resume_id: uuid.UUID,
        analysis_output: ResumeAnalysisOutput,
        actor_user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        res = await self.db.execute(
            select(CandidateProfileORM).where(
                CandidateProfileORM.id == candidate_id,
                CandidateProfileORM.organization_id == organization_id
            )
        )
        candidate = res.scalar_one_or_none()
        if not candidate:
            logger.error(f"[PROJECTION] Candidate profile {candidate_id} not found in org {organization_id}")
            return {"status": "FAILED", "reason": "CANDIDATE_NOT_FOUND"}

        # 1. Skill Projection (Preserves MANUAL provenance)
        existing_skills_res = await self.db.execute(
            select(CandidateSkillORM).where(CandidateSkillORM.candidate_profile_id == candidate.id)
        )
        existing_skills = {s.skill_name.lower().strip(): s for s in existing_skills_res.scalars().all()}

        projected_skills_count = 0
        for skill_data in analysis_output.skills:
            norm_name = skill_data.skill_name.strip()
            key = norm_name.lower()

            if key in existing_skills:
                existing = existing_skills[key]
                if existing.source == "MANUAL":
                    logger.info(f"[PROJECTION] Preserving MANUAL skill '{norm_name}' for candidate {candidate.id}")
                    continue
                # Update AI skill if needed
                existing.category = skill_data.category or existing.category
                existing.years_experience = (
                    float(skill_data.years_experience) if skill_data.years_experience is not None else existing.years_experience
                )
                existing.proficiency_level = skill_data.proficiency_level or existing.proficiency_level
            else:
                new_skill = CandidateSkillORM(
                    candidate_profile_id=candidate.id,
                    skill_name=norm_name,
                    category=skill_data.category,
                    years_experience=float(skill_data.years_experience) if skill_data.years_experience is not None else None,
                    proficiency_level=skill_data.proficiency_level or "INTERMEDIATE",
                    source="RESUME_AI"
                )
                self.db.add(new_skill)
                existing_skills[key] = new_skill
                projected_skills_count += 1

        # 2. Experience Projection
        existing_exp_res = await self.db.execute(
            select(CandidateExperienceORM).where(CandidateExperienceORM.candidate_profile_id == candidate.id)
        )
        existing_exps = {(e.company_name.lower().strip(), e.job_title.lower().strip()) for e in existing_exp_res.scalars().all()}

        projected_exp_count = 0
        for exp_data in analysis_output.work_experience:
            key = (exp_data.company_name.lower().strip(), exp_data.job_title.lower().strip())
            if key not in existing_exps:
                new_exp = CandidateExperienceORM(
                    candidate_profile_id=candidate.id,
                    company_name=exp_data.company_name.strip(),
                    job_title=exp_data.job_title.strip(),
                    is_current=exp_data.is_current,
                    description=exp_data.description
                )
                self.db.add(new_exp)
                existing_exps.add(key)
                projected_exp_count += 1

        # 3. Education Projection
        existing_edu_res = await self.db.execute(
            select(CandidateEducationORM).where(CandidateEducationORM.candidate_profile_id == candidate.id)
        )
        existing_edus = {e.institution.lower().strip() for e in existing_edu_res.scalars().all()}

        projected_edu_count = 0
        for edu_data in analysis_output.education:
            key = edu_data.institution.lower().strip()
            if key not in existing_edus:
                new_edu = CandidateEducationORM(
                    candidate_profile_id=candidate.id,
                    institution=edu_data.institution.strip(),
                    degree=edu_data.degree,
                    field_of_study=edu_data.field_of_study,
                    end_year=edu_data.end_year
                )
                self.db.add(new_edu)
                existing_edus.add(key)
                projected_edu_count += 1

        # Record Audit Event
        audit = AuditLogORM(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_type="SYSTEM" if actor_user_id is None else "USER",
            action="candidate.projected_from_resume",
            resource_type="CandidateProfile",
            resource_id=candidate.id,
            metadata_json={
                "resume_id": str(resume_id),
                "projected_skills": projected_skills_count,
                "projected_experiences": projected_exp_count,
                "projected_educations": projected_edu_count
            }
        )
        self.db.add(audit)
        await self.db.flush()

        logger.info(f"[PROJECTION] Successfully projected candidate data for candidate {candidate.id} from resume {resume_id}")
        return {
            "status": "SUCCESS",
            "candidate_id": str(candidate.id),
            "projected_skills": projected_skills_count,
            "projected_experiences": projected_exp_count,
            "projected_educations": projected_edu_count
        }
