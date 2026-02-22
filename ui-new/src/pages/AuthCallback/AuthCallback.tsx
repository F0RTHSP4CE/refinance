import { Center, Loader, Text } from '@mantine/core';
import { useEffect, useRef } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuthStore } from '@/stores/auth';

export const AuthCallback = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);
  const loadActor = useAuthStore((state) => state.loadActor);
  const processedRef = useRef(false);

  useEffect(() => {
    const processToken = async () => {
      if (processedRef.current) return;
      processedRef.current = true;

      if (token) {
        setToken(token);
        await loadActor();
        navigate('/', { replace: true });
      } else {
        navigate('/sign-in', { replace: true });
      }
    };

    void processToken();
  }, [token, navigate, setToken, loadActor]);

  return (
    <Center h="100vh">
      <Loader size="lg" />
      <Text ml="md">Authenticating...</Text>
    </Center>
  );
};
