import { lazy, Suspense, useEffect } from 'react';
import { Navigate, Route, Routes, useParams } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { ErrorState, LoadingState } from '@/components/ui';
import { useAuthStore } from '@/stores/auth';

// Lazy load all pages for code splitting
const SignIn = lazy(() => import('@/pages/SignIn').then((m) => ({ default: m.SignIn })));
const AuthCallback = lazy(() =>
  import('@/pages/AuthCallback').then((m) => ({ default: m.AuthCallback }))
);
const Home = lazy(() => import('@/pages/Home').then((m) => ({ default: m.Home })));
const Transactions = lazy(() =>
  import('@/pages/Transactions').then((m) => ({ default: m.Transactions }))
);
const DepositDetail = lazy(() =>
  import('@/pages/DepositDetail').then((m) => ({ default: m.DepositDetail }))
);
const Fee = lazy(() => import('@/pages/Fee').then((m) => ({ default: m.Fee })));
const Splits = lazy(() => import('@/pages/Splits').then((m) => ({ default: m.Splits })));
const Stats = lazy(() => import('@/pages/Stats').then((m) => ({ default: m.Stats })));
const Users = lazy(() => import('@/pages/Users').then((m) => ({ default: m.Users })));
const Entities = lazy(() => import('@/pages/Entities').then((m) => ({ default: m.Entities })));
const Treasuries = lazy(() =>
  import('@/pages/Treasuries').then((m) => ({ default: m.Treasuries }))
);
const Tags = lazy(() => import('@/pages/Tags').then((m) => ({ default: m.Tags })));
const Profile = lazy(() => import('@/pages/Profile').then((m) => ({ default: m.Profile })));

const PageLoader = () => <LoadingState fullScreen cards={2} lines={4} />;

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.token);
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const isLoading = useAuthStore((state) => state.isLoading);
  const isInitialized = useAuthStore((state) => state.isInitialized);

  if (token && (!isInitialized || isLoading)) {
    return <LoadingState fullScreen cards={2} lines={3} />;
  }
  if (!actorEntity) {
    return <Navigate to="/sign-in" replace />;
  }
  return <>{children}</>;
};

const PublicRoute = ({ children }: { children: React.ReactNode }) => {
  const token = useAuthStore((state) => state.token);
  const actorEntity = useAuthStore((state) => state.actorEntity);
  const isLoading = useAuthStore((state) => state.isLoading);
  const isInitialized = useAuthStore((state) => state.isInitialized);

  if (token && (!isInitialized || isLoading)) {
    return <LoadingState fullScreen cards={1} lines={3} />;
  }
  if (actorEntity) {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};

const InvoiceListRedirect = () => <Navigate to="/fee?tab=invoices" replace />;

const InvoiceDetailsRedirect = () => {
  const { id } = useParams<{ id: string }>();
  return <Navigate to={`/fee?tab=invoices${id ? `&invoiceId=${id}` : ''}`} replace />;
};

export const App = () => {
  const loadActor = useAuthStore((state) => state.loadActor);
  const authError = useAuthStore((state) => state.authError);
  const clearSession = useAuthStore((state) => state.clearSession);

  useEffect(() => {
    void loadActor();
  }, [loadActor]);

  if (authError) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: '1rem' }}>
        <ErrorState
          title="Authentication could not be restored"
          description={authError}
          retryLabel="Sign out and retry"
          onRetry={() => {
            clearSession();
            window.location.assign('/sign-in');
          }}
        />
      </div>
    );
  }

  return (
    <Suspense fallback={<PageLoader />}>
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
          <Route path="transactions" element={<Transactions />} />
          <Route path="invoices" element={<InvoiceListRedirect />} />
          <Route path="invoices/:id" element={<InvoiceDetailsRedirect />} />
          <Route path="deposits/:id" element={<DepositDetail />} />
          <Route path="fee" element={<Fee />} />
          <Route path="splits" element={<Splits />} />
          <Route path="stats" element={<Stats />} />
          <Route path="users" element={<Users />} />
          <Route path="entities" element={<Entities />} />
          <Route path="treasuries" element={<Treasuries />} />
          <Route path="tags" element={<Tags />} />
          <Route path="profile/:id?" element={<Profile />} />
        </Route>
      </Routes>
    </Suspense>
  );
};
