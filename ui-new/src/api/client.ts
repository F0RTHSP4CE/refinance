import { useAuthStore } from '@/stores/auth';

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

const API_BASE_URL = '/api';

// CSRF token storage
let csrfToken: string | null = null;

// Get CSRF token from cookie
const getCsrfToken = (): string | null => {
  if (csrfToken) return csrfToken;
  const match = document.cookie.match(/csrf_token=([^;]+)/);
  csrfToken = match ? match[1] : null;
  return csrfToken;
};

type RequestOptions<TBody> = {
  method?: HttpMethod;
  body?: TBody;
  token?: string | null;
  signal?: AbortSignal;
  withCredentials?: boolean;
};

type ApiErrorPayload = {
  error?: string;
  detail?: string;
};

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const apiRequest = async <TResponse, TBody = unknown>(
  endpoint: string,
  options: RequestOptions<TBody> = {}
): Promise<TResponse> => {
  const { method = 'GET', body, signal, withCredentials = true } = options;
  const token = options.token ?? useAuthStore.getState().token;

  // Build headers
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { 'X-Token': token } : {}),
  };

  // Add CSRF token for state-changing operations
  if (method !== 'GET') {
    const csrf = getCsrfToken();
    if (csrf) {
      headers['X-CSRF-Token'] = csrf;
    }
  }

  const response = await fetch(`${API_BASE_URL}/${endpoint.replace(/^\//, '')}`, {
    method,
    signal,
    headers,
    credentials: withCredentials ? 'include' : 'same-origin',
    body: body ? JSON.stringify(body) : undefined,
  });

  // Update CSRF token if provided in response
  const responseCsrf = response.headers.get('X-CSRF-Token');
  if (responseCsrf) {
    csrfToken = responseCsrf;
  }

  if (!response.ok) {
    let errorMessage = `Request failed: ${response.status}`;
    try {
      const payload = (await response.json()) as ApiErrorPayload;
      errorMessage = payload.detail ?? payload.error ?? errorMessage;
    } catch {
      // Keep fallback error message when JSON parsing fails.
    }
    throw new ApiError(errorMessage, response.status);
  }

  return (await response.json()) as TResponse;
};
