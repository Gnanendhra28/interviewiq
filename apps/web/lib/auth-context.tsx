'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, Organization, Membership } from '../types';
import { authService } from '../services/auth-service';
import { organizationService } from '../services/organization-service';
import { setAccessToken, setActiveOrganizationId, getAccessToken, getActiveOrganizationId, getApiBaseUrl } from './api-client';

interface AuthContextType {
  user: User | null;
  activeOrganization: Organization | null;
  memberships: Membership[];
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  logout: () => Promise<void>;
  switchOrganization: (orgId: string) => Promise<void>;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  const [activeOrganization, setActiveOrganization] = useState<Organization | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const refreshSession = async () => {
    try {
      let token = getAccessToken();

      // If no token in memory/localStorage, attempt silent cookie refresh
      if (!token && typeof window !== 'undefined') {
        try {
          const baseUrl = getApiBaseUrl();
          const refreshRes = await fetch(`${baseUrl}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
          });
          if (refreshRes.ok) {
            const refreshData = await refreshRes.json();
            if (refreshData.access_token) {
              setAccessToken(refreshData.access_token);
              token = refreshData.access_token;
            }
          }
        } catch (e) {
          // Silent refresh failed
        }
      }

      if (!token) {
        setUser(null);
        if (typeof window !== 'undefined') {
          localStorage.removeItem('interviewiq_user');
        }
        setIsLoading(false);
        return;
      }

      // Fetch user profile to verify token & restore user context
      try {
        const meRes = await authService.getCurrentUser();
        if (meRes && meRes.user) {
          setUser(meRes.user);
          if (typeof window !== 'undefined') {
            localStorage.setItem('interviewiq_user', JSON.stringify(meRes.user));
          }
          if (meRes.active_organization) {
            setActiveOrganization(meRes.active_organization);
            setActiveOrganizationId(meRes.active_organization.id);
          }
        }
      } catch (e) {
        // me call failed
      }

      const mems = await organizationService.listMemberships();
      setMemberships(mems);
      const activeOrgId = getActiveOrganizationId();
      if (activeOrgId && mems.length > 0) {
        const activeMem = mems.find((m) => m.organization_id === activeOrgId);
        if (activeMem && activeMem.organization) {
          setActiveOrganization(activeMem.organization);
        }
      } else if (mems.length > 0 && mems[0].organization) {
        setActiveOrganization(mems[0].organization);
        setActiveOrganizationId(mems[0].organization_id);
      }
    } catch (e) {
      console.warn('Session refresh error:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('interviewiq_user');
      if (stored) {
        try {
          setUser(JSON.parse(stored));
        } catch (e) {}
      }
    }
    refreshSession();
  }, []);

  const login = async (email: string, pass: string) => {
    setIsLoading(true);
    try {
      const res = await authService.login(email, pass);
      setAccessToken(res.access_token);
      setUser(res.user);
      if (typeof window !== 'undefined') {
        localStorage.setItem('interviewiq_user', JSON.stringify(res.user));
      }
      setMemberships(res.memberships || []);
      if (res.active_organization) {
        setActiveOrganization(res.active_organization);
        setActiveOrganizationId(res.active_organization.id);
      } else if (res.memberships && res.memberships.length > 0 && res.memberships[0].organization) {
        setActiveOrganization(res.memberships[0].organization);
        setActiveOrganizationId(res.memberships[0].organization_id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authService.logout();
    } catch (e) {
      // Ignore logout errors
    } finally {
      setUser(null);
      setActiveOrganization(null);
      setMemberships([]);
      setAccessToken(null);
      setActiveOrganizationId(null);
      if (typeof window !== 'undefined') {
        localStorage.removeItem('interviewiq_user');
      }
      setIsLoading(false);
    }
  };

  const switchOrganization = async (orgId: string) => {
    setIsLoading(true);
    try {
      const mem = await organizationService.switchOrganization(orgId);
      if (mem.organization) {
        setActiveOrganization(mem.organization);
        setActiveOrganizationId(mem.organization.id);
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        activeOrganization,
        memberships,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        switchOrganization,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
