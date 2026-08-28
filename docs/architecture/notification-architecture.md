# Multi-Channel Notification Engine

## 1. Overview
The Notification Engine (ADR 049) processes alerts across `IN_APP`, `EMAIL`, `SLACK`, and `TEAMS` channels.

## 2. Notification Preferences & Dispatch
- `NotificationPreferenceORM`: Stores user channel preferences and webhook URLs per organization.
- `ProcessNotificationWorkerTask`: Asynchronously dispatches notification jobs in the background without blocking HTTP request execution.
- `NotificationDeliveryORM`: Tracks in-app notification state (`is_read`).
