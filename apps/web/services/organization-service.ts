import { fetchApi } from '../lib/api-client';
import { Organization, Membership } from '../types';

export const organizationService = {
  async bootstrap(data: { name: string; slug: string }): Promise<Organization> {
    return fetchApi<Organization>('/organizations/bootstrap', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  async listMemberships(): Promise<Membership[]> {
    return fetchApi<Membership[]>('/organizations/memberships');
  },

  async switchOrganization(organization_id: string): Promise<Membership> {
    return fetchApi<Membership>(`/organizations/${organization_id}/switch`, {
      method: 'POST',
    });
  },
};
