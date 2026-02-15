type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';

const API_BASE_URL = '/api';

type RequestOptions<TBody> = {
  method?: HttpMethod;
  body?: TBody;
  token?: string | null;
  signal?: AbortSignal;
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
  const { method = 'GET', body, token, signal } = options;

  const response = await fetch(`${API_BASE_URL}/${endpoint.replace(/^\//, '')}`, {
    method,
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-Token': token } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

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
