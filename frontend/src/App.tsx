import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import Landing from './components/Landing';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ClientList from './components/ClientList';
import ClientDetail from './components/ClientDetail';
import ComplianceCalendar from './components/ComplianceCalendar';
import DocumentManager from './components/DocumentManager';
import TaxComputer from './components/TaxComputer';
import QueryChat from './components/QueryChat';
import NoticeManager from './components/NoticeManager';
import NriWorkspace from './components/NriWorkspace';
import TaxRadar from './components/TaxRadar';
import { ReactNode } from 'react';

interface ProtectedRouteProps {
  children: ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-textura-bg">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-textura-accent border-t-transparent rounded-full animate-spin shadow-[0_0_15px_rgba(161,236,255,0.25)]" />
          <p className="text-textura-muted text-sm">Loading OperatorOS...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  const location = useLocation();

  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <div key={location.pathname} className="page-transition">
                <Routes>
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/clients" element={<ClientList />} />
                  <Route path="/clients/:id" element={<ClientDetail />} />
                  <Route path="/compliance" element={<ComplianceCalendar />} />
                  <Route path="/documents" element={<DocumentManager />} />
                  <Route path="/compute" element={<TaxComputer />} />
                  <Route path="/nri" element={<NriWorkspace />} />
                  <Route path="/radar" element={<TaxRadar />} />
                  <Route path="/queries" element={<QueryChat />} />
                  <Route path="/notices" element={<NoticeManager />} />
                  <Route path="*" element={<Navigate to="/dashboard" replace />} />
                </Routes>
              </div>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
