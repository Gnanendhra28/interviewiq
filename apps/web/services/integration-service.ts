import { fetchApi } from '../lib/api-client';

export interface IntegrationItem {
  id: string;
  organization_id: string;
  provider_type: string;
  name: string;
  status: string;
  config_metadata_json: Record<string, any>;
  created_at: string;
}

export const integrationService = {
  async listIntegrations(): Promise<IntegrationItem[]> {
    return fetchApi<IntegrationItem[]>('/integrations');
  },

  async createIntegration(data: {
    provider_type: string;
    name: string;
    config_metadata_json: Record<string, any>;
    secret?: string;
  }): Promise<IntegrationItem> {
    return fetchApi<IntegrationItem>('/integrations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async testIntegration(id: string): Promise<Record<string, any>> {
    return fetchApi<Record<string, any>>(`/integrations/${id}/test`, {
      method: 'POST',
    });
  },

  async enableIntegration(id: string): Promise<{ status: string }> {
    return fetchApi<{ status: string }>(`/integrations/${id}/enable`, {
      method: 'POST',
    });
  },

  async disableIntegration(id: string): Promise<{ status: string }> {
    return fetchApi<{ status: string }>(`/integrations/${id}/disable`, {
      method: 'POST',
    });
  },
};
