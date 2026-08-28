# ADR 049: Multi-Channel Notification Architecture & Preferences

## Context
Recruiter notifications must support multiple channels (In-App, Email, Slack, Teams) without delaying candidate workflow transactions.

## Decision
1. Notification preferences (`NotificationPreferenceORM`) define enabled channels and webhook URLs per user and organization.
2. Background worker task `ProcessNotificationWorkerTask` executes multi-channel delivery asynchronously.

## Consequences
- Flexible notification subscriptions per user.
- Zero impact on API request performance.
