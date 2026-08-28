from typing import Any, Dict, List

from apps.api.app.modules.interview_intelligence.infrastructure.orm import (
    AnswerEvaluationORM,
    InterviewQuestionORM,
)
from apps.api.app.modules.interviews.infrastructure.orm import (
    InterviewBlueprintORM,
    InterviewSnapshotORM,
)


class InterviewScoringEngine:
    """
    Deterministic Backend Interview Scoring & Requirement Scorecard Engine (ADR 035).
    Guarantees reproducible, bounded, weighted numerical scoring decoupled from LLM output.
    """

    def calculate_scores(
        self,
        snapshot: InterviewSnapshotORM,
        blueprint: InterviewBlueprintORM,
        questions: List[InterviewQuestionORM],
        evaluations: List[AnswerEvaluationORM]
    ) -> Dict[str, Any]:
        if not evaluations:
            return {
                "overall_score": 0.0,
                "technical_competency_score": 0.0,
                "reasoning_score": 0.0,
                "communication_score": 0.0,
                "completeness_score": 0.0,
                "requirement_coverage_score": 0.0,
                "hiring_signal": "INSUFFICIENT_EVIDENCE",
                "recommendation": "BORDERLINE",
                "requirement_scorecards": [],
                "scoring_version": "v1"
            }

        # 1. Aggregate Sub-Scores across Evaluated Turns
        tech_scores = [float(e.score_technical_accuracy) for e in evaluations]
        depth_scores = [float(e.score_depth) for e in evaluations]
        reason_scores = [float(e.reasoning_quality_score) for e in evaluations if e.reasoning_quality_score is not None]
        clarity_scores = [float(e.score_clarity) for e in evaluations]
        comp_scores = [float(e.completeness_score) for e in evaluations if e.completeness_score is not None]

        tech_avg = sum(tech_scores) / len(tech_scores) if tech_scores else 0.0
        
        all_reasoning = depth_scores + reason_scores
        reason_avg = sum(all_reasoning) / len(all_reasoning) if all_reasoning else tech_avg
        
        comm_avg = sum(clarity_scores) / len(clarity_scores) if clarity_scores else tech_avg
        comp_avg = sum(comp_scores) / len(comp_scores) if comp_scores else tech_avg

        # 2. Build Job Requirement Scorecards
        reqs_json = snapshot.job_role_requirements_snapshot_json or []
        eval_by_q_id = {e.answer.question_id: e for e in evaluations if e.answer and e.answer.question_id}
        
        scorecards = []
        assessed_req_count = 0

        for req in reqs_json:
            req_skill = req.get("skill_name", "General Skill")
            req_weight = float(req.get("weight", 1.0))
            
            # Find matching questions evaluated for this requirement
            matched_evals = []
            for q in questions:
                if q.id in eval_by_q_id:
                    q_topic = q.topic.lower()
                    req_lower = req_skill.lower()
                    if req_lower in q_topic or q_topic in req_lower or (q.job_requirement_ids and req_skill in q.job_requirement_ids):
                        matched_evals.append(eval_by_q_id[q.id])

            ev_count = len(matched_evals)
            if ev_count > 0:
                assessed_req_count += 1
                req_avg = sum(float(e.overall_score) for e in matched_evals) / ev_count
                status = "ASSESSED" if ev_count >= 2 else "PARTIALLY_ASSESSED"
            else:
                req_avg = 0.0
                status = "NOT_ASSESSED"

            scorecards.append({
                "requirement_skill": req_skill,
                "weight": req_weight,
                "evidence_count": ev_count,
                "average_score": round(req_avg, 2),
                "status": status
            })

        req_coverage_score = (assessed_req_count / len(reqs_json) * 10.0) if reqs_json else 10.0

        # 3. Compute Bounded Overall Weighted Composite Score
        overall = (0.40 * tech_avg) + (0.25 * reason_avg) + (0.15 * comm_avg) + (0.20 * req_coverage_score)
        overall = max(0.0, min(10.0, overall))

        # 4. Determine Hiring Signal & Recommendation (ADR 037)
        if len(evaluations) < 3:
            hiring_signal = "INSUFFICIENT_EVIDENCE"
            recommendation = "BORDERLINE"
        elif overall >= 8.5 and req_coverage_score >= 7.5:
            hiring_signal = "STRONG_HIRE_SIGNAL"
            recommendation = "STRONG_HIRE"
        elif overall >= 7.0 and req_coverage_score >= 5.0:
            hiring_signal = "HIRE_SIGNAL"
            recommendation = "HIRE"
        elif overall >= 5.5:
            hiring_signal = "MIXED_SIGNAL"
            recommendation = "BORDERLINE"
        else:
            hiring_signal = "NO_HIRE_SIGNAL"
            recommendation = "NO_HIRE"

        return {
            "overall_score": round(overall, 2),
            "technical_competency_score": round(tech_avg, 2),
            "reasoning_score": round(reason_avg, 2),
            "communication_score": round(comm_avg, 2),
            "completeness_score": round(comp_avg, 2),
            "requirement_coverage_score": round(req_coverage_score, 2),
            "hiring_signal": hiring_signal,
            "recommendation": recommendation,
            "requirement_scorecards": scorecards,
            "scoring_version": "v1"
        }
