# Integration Architecture Documentation

## 1. Overview
The **InterviewIQ Integration Architecture** provides organization-scoped, enterprise-grade connectors for Applicant Tracking Systems (Greenhouse, Lever, Workday) and notification channels (Slack, Teams, Email, In-App).

```text
apps/api/app/modules/integrations/
    infrastructure/
        providers/
            base.py
            greenhouse.py
            lever.py
            workday.py
    presentation/
        router.py
```

## 2. Provider Abstraction Interface (`IntegrationProvider`)
Every ATS connector inherits from `IntegrationProvider` (`base.py`), implementing:
- `validate_configuration(config, secret)`
- `test_connection(config, secret)`
- `deliver_hiring_decision(config, secret, payload)`
- `deliver_interview_report(config, secret, payload)`

## 3. Multi-Tenant Security & Secrets Rules (ADR 046)
- **Tenant Isolation**: Every integration record belongs to an `organization_id`. API endpoints enforce tenant boundaries.
- **Secrets Protection**: Secrets are encrypted/masked and NEVER returned in API GET responses or written to system logs.
