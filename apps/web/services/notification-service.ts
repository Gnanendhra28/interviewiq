import { fetchApi } from '../lib/api-client';

export interface NotificationItem {
  id: string;
  channel: string;
  event_type: string;
  title: string;
  message: string;
  is_read: boolean;
  resource_id?: string;
  created_at: string;
}

export const notificationService = {
  async listNotifications(): Promise<NotificationItem[]> {
    return fetchApi<NotificationItem[]>('/notifications');
  },

  async markAsRead(notification_id: string): Promise<void> {
    await fetchApi<void>(`/notifications/${notification_id}/read`, {
      method: 'PATCH',
    });
  },

  async getNotificationPreferences(): Promise<Array<{ id: string; channel: string; enabled_events_json: any; webhook_url?: string }>> {
    return fetchApi<Array<{ id: string; channel: string; enabled_events_json: any; webhook_url?: string }>>('/notification-preferences');
  },

  async saveNotificationPreference(data: { channel: string; enabled_events_json: any; webhook_url?: string }): Promise<void> {
    await fetchApi<void>('/notification-preferences', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },
};
