import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('useAuthStore token storage', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unmock('@/api/client');
    window.localStorage.clear();
  });

  it('reads the current token key on initialization', async () => {
    window.localStorage.setItem('refinance_token', 'new-token');

    const { useAuthStore } = await import('./auth');

    expect(useAuthStore.getState().token).toBe('new-token');
  });

  it('clears the current token key on logout', async () => {
    window.localStorage.setItem('refinance_token', 'current-token');

    const { useAuthStore } = await import('./auth');

    expect(useAuthStore.getState().token).toBe('current-token');

    useAuthStore.getState().clearSession();

    expect(window.localStorage.getItem('refinance_token')).toBeNull();
  });

  it('clears the current token key after an unauthorized actor refresh', async () => {
    class MockApiError extends Error {
      readonly status: number;

      constructor(message: string, status: number) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
      }
    }

    const apiRequest = vi
      .fn()
      .mockRejectedValue(new MockApiError('Unauthorized', 401));

    vi.doMock('@/api/client', () => ({
      ApiError: MockApiError,
      apiRequest,
    }));

    window.localStorage.setItem('refinance_token', 'current-token');

    const { useAuthStore } = await import('./auth');

    await useAuthStore.getState().loadActor();

    expect(apiRequest).toHaveBeenCalledWith('entities/me', { token: 'current-token' });
    expect(window.localStorage.getItem('refinance_token')).toBeNull();
    expect(useAuthStore.getState().token).toBeNull();
  });
});
