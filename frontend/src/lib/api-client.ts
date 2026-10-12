import type { StaffRead, TokenResponse } from '@/types/api';

/** Base API URL — proxied through Vite in dev, same-origin in prod */
const API_BASE = '/api/v1';

/** Auth token storage key */
const TOKEN_KEY = 'raven.auth.token';
const USER_KEY = 'raven.auth.user';

/** Get stored access token */
export function getAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/** Get stored user */
export function getStoredUser(): StaffRead | null {
  if (typeof window === 'undefined') return null;
  const stored = localStorage.getItem(USER_KEY);
  if (!stored) return null;
  try {
    return JSON.parse(stored) as StaffRead;
  } catch {
    return null;
  }
}

/** Store auth data */
export function setAuth(token: string, user: StaffRead): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Clear auth data */
export function clearAuth(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Check if authenticated */
export function isAuthenticated(): boolean {
  return getAccessToken() !== null;
}

/** Build headers with auth */
function authHeaders(extra?: Record<string, string>): HeadersInit {
  const token = getAccessToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

/** Generic request wrapper with error handling */
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;

  const response = await fetch(url, {
    ...options,
    headers: authHeaders(options.headers as Record<string, string>),
  });

  if (!response.ok) {
    let error: { error: string; message?: string; correlation_id?: string } = {
      error: 'api_error',
    };
    try {
      error = await response.json();
    } catch {
      error.message = response.statusText;
    }
    throw new ApiError(response.status, error.error, error.message, error.correlation_id);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message?: string,
    public readonly correlationId?: string
  ) {
    super(message || code);
    this.name = 'ApiError';
  }
}

/** HTTP methods */
export const api = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

/** Auth-specific helpers */
export const authApi = {
  login: (email: string, password: string) =>
    api.post<TokenResponse>('/auth/token', { username: email, password }),

  me: () => api.get<StaffRead>('/auth/me'),
};

/** Patient API */
export const patientApi = {
  list: (params?: { search?: string; page?: number; size?: number }) => {
    const searchParams = new URLSearchParams();
    if (params?.search) searchParams.set('search', params.search);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.size) searchParams.set('size', String(params.size));
    const query = searchParams.toString();
    return api.get<import('@/types/api').PatientPage>(`/patients${query ? `?${query}` : ''}`);
  },

  get: (id: string) => api.get<import('@/types/api').PatientRead>(`/patients/${id}`),

  create: (data: import('@/types/api').PatientCreate) =>
    api.post<import('@/types/api').PatientRead>('/patients', data),

  update: (id: string, data: import('@/types/api').PatientUpdate) =>
    api.patch<import('@/types/api').PatientRead>(`/patients/${id}`, data),

  delete: (id: string) => api.delete<void>(`/patients/${id}`),
};

/** Staff API */
export const staffApi = {
  list: (role?: string) => {
    const params = role ? `?role=${role}` : '';
    return api.get<StaffRead[]>(`/staff${params}`);
  },

  get: (id: string) => api.get<StaffRead>(`/staff/${id}`),

  create: (data: import('@/types/api').StaffCreate) => api.post<StaffRead>('/staff', data),

  update: (id: string, data: import('@/types/api').StaffUpdate) =>
    api.patch<StaffRead>(`/staff/${id}`, data),
};

/** Service API */
export const serviceApi = {
  list: (activeOnly = true) =>
    api.get<import('@/types/api').ServiceRead[]>(`/services?active_only=${activeOnly}`),

  get: (id: string) => api.get<import('@/types/api').ServiceRead>(`/services/${id}`),

  create: (data: import('@/types/api').ServiceCreate) =>
    api.post<import('@/types/api').ServiceRead>('/services', data),

  update: (id: string, data: import('@/types/api').ServiceUpdate) =>
    api.patch<import('@/types/api').ServiceRead>(`/services/${id}`, data),
};

/** Schedule API */
export const scheduleApi = {
  shifts: {
    list: (dentistId?: string) => {
      const params = dentistId ? `?dentistId=${dentistId}` : '';
      return api.get<import('@/types/api').WorkingShiftRead[]>(`/schedules/shifts${params}`);
    },

    create: (data: import('@/types/api').WorkingShiftCreate) =>
      api.post<import('@/types/api').WorkingShiftRead>('/schedules/shifts', data),

    delete: (id: string) => api.delete<void>(`/schedules/shifts/${id}`),
  },

  timeOff: {
    list: (dentistId: string, startDate: string, endDate: string) =>
      api.get<import('@/types/api').TimeOffBlockRead[]>(
        `/schedules/time-off?dentistId=${dentistId}&startDate=${startDate}&endDate=${endDate}`
      ),

    create: (data: import('@/types/api').TimeOffBlockCreate) =>
      api.post<import('@/types/api').TimeOffBlockRead>('/schedules/time-off', data),

    delete: (id: string) => api.delete<void>(`/schedules/time-off/${id}`),
  },

  availability: (params: { serviceId: string; date: string; dentistId?: string }) => {
    const searchParams = new URLSearchParams();
    searchParams.set('serviceId', params.serviceId);
    searchParams.set('date', params.date);
    if (params.dentistId) searchParams.set('dentistId', params.dentistId);
    return api.get<import('@/types/api').AvailabilityResponse>(
      `/schedules/availability?${searchParams.toString()}`
    );
  },
};

/** Appointment API */
export const appointmentApi = {
  list: (params?: {
    dentistId?: string;
    patientId?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.dentistId) searchParams.set('dentistId', params.dentistId);
    if (params?.patientId) searchParams.set('patientId', params.patientId);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.startDate) searchParams.set('startDate', params.startDate);
    if (params?.endDate) searchParams.set('endDate', params.endDate);
    const query = searchParams.toString();
    return api.get<import('@/types/api').AppointmentDetailRead[]>(
      `/appointments${query ? `?${query}` : ''}`
    );
  },

  get: (id: string) => api.get<import('@/types/api').AppointmentDetailRead>(`/appointments/${id}`),

  create: (data: import('@/types/api').AppointmentCreate) =>
    api.post<import('@/types/api').AppointmentDetailRead>('/appointments', data),

  reschedule: (id: string, data: import('@/types/api').AppointmentReschedule) =>
    api.post<import('@/types/api').AppointmentDetailRead>(`/appointments/${id}/reschedule`, data),

  cancel: (id: string, data: import('@/types/api').AppointmentCancel) =>
    api.post<import('@/types/api').AppointmentDetailRead>(`/appointments/${id}/cancel`, data),

  updateStatus: (id: string, data: import('@/types/api').AppointmentStatusUpdate) =>
    api.post<import('@/types/api').AppointmentDetailRead>(`/appointments/${id}/status`, data),

  auditLogs: (id: string) =>
    api.get<import('@/types/api').AuditLogRead[]>(`/appointments/${id}/audit-logs`),

  reminders: {
    dispatch: () =>
      api.post<import('@/types/api').ReminderDispatchResult>(
        '/appointments/reminders/dispatch',
        {}
      ),
  },
};

/** Live SSE stream helpers */
export interface AppointmentLiveEvent {
  eventType: string;
  appointmentId: string;
  dentistId: string;
  patientName: string;
  status: string;
  startTime: string;
  timestamp: string;
}

export type LiveEventHandler = (event: AppointmentLiveEvent) => void;
export type ResyncHandler = () => void;

let sseController: AbortController | null = null;

export function connectLive(onEvent: LiveEventHandler, onResync: ResyncHandler): () => void {
  if (sseController) {
    sseController.abort();
  }

  sseController = new AbortController();

  const token = getAccessToken();
  if (!token) return () => {};

  const eventSource = new EventSource(`${API_BASE}/appointments/live`, {
    withCredentials: true,
  });

  // Note: EventSource doesn't support custom headers for auth.
  // For production with auth, use fetch-based SSE (see fetchLiveStream below).
  // This is a fallback for environments where the proxy handles auth.

  eventSource.addEventListener('appointment.resync_required', () => {
    onResync();
    eventSource.close();
  });

  const eventTypes = [
    'appointment.booked',
    'appointment.rescheduled',
    'appointment.cancelled',
    'appointment.confirmed',
    'appointment.checked_in',
    'appointment.started',
    'appointment.completed',
    'appointment.no_show',
  ];

  eventTypes.forEach((type) => {
    eventSource.addEventListener(type, (e) => {
      try {
        const event = JSON.parse(e.data) as AppointmentLiveEvent;
        onEvent(event);
      } catch {
        // Ignore parse errors
      }
    });
  });

  eventSource.onerror = () => {
    eventSource.close();
  };

  return () => {
    eventSource.close();
    sseController = null;
  };
}

/** Fetch-based SSE for authenticated streams (recommended) */
export async function* fetchLiveStream(signal: AbortSignal): AsyncGenerator<AppointmentLiveEvent> {
  const token = getAccessToken();
  if (!token) return;

  const response = await fetch(`${API_BASE}/appointments/live`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'text/event-stream',
    },
    signal,
  });

  if (!response.ok || !response.body) {
    throw new ApiError(response.status, 'sse_failed', 'Failed to connect to live stream');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6)) as AppointmentLiveEvent;
            yield event;
          } catch {
            // Ignore parse errors
          }
        } else if (line.startsWith('event: appointment.resync_required')) {
          // The next data line will have the resync payload
        } else if (line.startsWith(': ping')) {
          // Keep-alive, ignore
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
