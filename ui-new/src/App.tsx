import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import {
  AuthCallback,
  CardTopUp,
  DepositDetail,
  Home,
  ManualTopUp,
  Profile,
  SignIn,
} from '@/pages';
import { useAuthStore } from '@/stores/auth';

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.token);
  if (!token) {
    return <Navigate to="/sign-in" replace />;
  }
  return <>{children}</>;
};

const PublicRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.token);
  if (token) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

export const App = () => {
  const loadActor = useAuthStore((state) => state.loadActor);

  useEffect(() => {
    void loadActor();
  }, [loadActor]);

  return (
    <Routes>
      <Route
        path="/sign-in"
        element={
          <PublicRoute>
            <SignIn />
          </PublicRoute>
        }
      />
      <Route
        path="/auth/token/:token"
        element={
          <PublicRoute>
            <AuthCallback />
          </PublicRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Home />} />
        <Route path="top-up/card" element={<CardTopUp />} />
        <Route path="top-up/manual" element={<ManualTopUp />} />
        <Route path="deposits/:id" element={<DepositDetail />} />
        <Route path="profile/:id?" element={<Profile />} />
      </Route>
    </Routes>
  );
};
