import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import ClientList from './components/ClientList';
import ClientDetail from './components/ClientDetail';
import ComplianceCalendar from './components/ComplianceCalendar';
import DocumentManager from './components/DocumentManager';
import TaxComputer from './components/TaxComputer';
import QueryChat from './components/QueryChat';
import NoticeManager from './components/NoticeManager';

function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-500 text-sm">Loading AuditMind...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/clients" element={<ClientList />} />
                <Route path="/clients/:id" element={<ClientDetail />} />
                <Route path="/compliance" element={<ComplianceCalendar />} />
                <Route path="/documents" element={<DocumentManager />} />
                <Route path="/compute" element={<TaxComputer />} />
                <Route path="/queries" element={<QueryChat />} />
                <Route path="/notices" element={<NoticeManager />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
