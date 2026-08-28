export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL && !process.env.NEXT_PUBLIC_API_URL.includes('localhost')) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname;
    if (hostname.includes('run.app') || hostname.includes('interviewiq')) {
      return 'https://interviewiq-staging-staging-api-q24ci75lba-uc.a.run.app/api/v1';
    }
  }

  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
}

let accessTokenMemory: string | null = null;
let activeOrganizationIdMemory: string | null = null;

export function setAccessToken(token: string | null) {
  accessTokenMemory = token;
  if (typeof window !== 'undefined') {
    if (token) {
      sessionStorage.setItem('access_token', token);
    } else {
      sessionStorage.removeItem('access_token');
    }
  }
}

export function getAccessToken(): string | null {
  if (accessTokenMemory) return accessTokenMemory;
  if (typeof window !== 'undefined') {
    accessTokenMemory = sessionStorage.getItem('access_token');
  }
  return accessTokenMemory;
}

export function setActiveOrganizationId(orgId: string | null) {
  activeOrganizationIdMemory = orgId;
  if (typeof window !== 'undefined') {
    if (orgId) {
      sessionStorage.setItem('active_org_id', orgId);
    } else {
      sessionStorage.removeItem('active_org_id');
    }
  }
}

export function getActiveOrganizationId(): string | null {
  if (activeOrganizationIdMemory) return activeOrganizationIdMemory;
  if (typeof window !== 'undefined') {
    activeOrganizationIdMemory = sessionStorage.getItem('active_org_id');
  }
  return activeOrganizationIdMemory;
}

export class ApiError extends Error {
  code: string;
  requestId?: string;
  status: number;

  constructor(message: string, code: string = 'UNKNOWN_ERROR', status: number = 400, requestId?: string) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.requestId = requestId;
  }
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}, isRetry: boolean = false): Promise<T> {
  const token = getAccessToken();
  const orgId = getActiveOrganizationId();
  const headers = new Headers(options.headers || {});

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  if (orgId && !headers.has('X-Organization-Id')) {
    headers.set('X-Organization-Id', orgId);
  }

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const reqId = `web_req_${Math.random().toString(36).substring(2, 10)}`;
  headers.set('X-Request-ID', reqId);

  const baseUrl = getApiBaseUrl();
  const response = await fetch(`${baseUrl}${endpoint}`, {
    ...options,
    headers,
    credentials: 'include', // Include HttpOnly refresh cookies
  });

  if (response.status === 401 && !isRetry && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    try {
      const refreshRes = await fetch(`${baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });
      if (refreshRes.ok) {
        const refreshData = await refreshRes.json();
        setAccessToken(refreshData.access_token);
        return fetchApi<T>(endpoint, options, true); // Retry original request with new token
      }
    } catch (e) {
      setAccessToken(null);
    }
  }

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const errObj = errorBody.error || {};
    throw new ApiError(
      errObj.message || `API Request failed with status ${response.status}`,
      errObj.code || 'HTTP_ERROR',
      response.status,
      errObj.request_id || response.headers.get('X-Request-ID') || reqId
    );
  }

  return response.json();
}
