# Requirement Scorecards Architecture

## 1. Overview
**Requirement Scorecards** provide job-requirement-level evidence breakdown in interview reports. High overall candidate scores cannot conceal unassessed critical skills.

## 2. Requirement Status Mapping
For each job requirement in `InterviewSnapshotORM.job_role_requirements_snapshot_json`:
- `ASSESSED`: $\ge 2$ evaluated questions matching requirement.
- `PARTIALLY_ASSESSED`: 1 evaluated question matching requirement.
- `NOT_ASSESSED`: 0 evaluated questions matching requirement.

## 3. Data Model Structure
```json
[
  {
    "requirement_skill": "PostgreSQL",
    "weight": 2.0,
    "evidence_count": 3,
    "average_score": 8.5,
    "status": "ASSESSED"
  }
]
```
