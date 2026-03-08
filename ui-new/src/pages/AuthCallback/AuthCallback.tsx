import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ErrorState, LoadingState } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';

export const AuthCallback = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);
  const loadActor = useAuthStore((state) => state.loadActor);
  const processedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const processToken = async () => {
      if (processedRef.current) return;
      processedRef.current = true;

      if (!token) {
        navigate('/sign-in', { replace: true });
        return;
      }

      try {
        setToken(token);
        await loadActor();
        navigate('/', { replace: true });
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Authentication callback failed';
        setError(message);
      }
    };

    void processToken();
  }, [token, navigate, setToken, loadActor]);

  if (error) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1rem' }}>
        <ErrorState
          title="Authentication could not be completed"
          description={error}
          retryLabel="Back to sign in"
          onRetry={() => navigate('/sign-in', { replace: true })}
        />
      </div>
    );
  }

  return <LoadingState fullScreen cards={1} lines={3} />;
};
