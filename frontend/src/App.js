import React, { useMemo, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster, toast } from './components/ui/sonner';
import { AuthProvider, useAuth } from './context/AuthContext';
import { authAPI } from './services/api';
import PrivacyPolicyDialog from './components/PrivacyPolicyDialog';
import { PRIVACY_POLICY_VERSION } from './config/privacyPolicy';
import './App.css';

// Pages
import LoginPage from './pages/LoginPage';
import FormPage from './pages/FormPage';
import FormSuccessPage from './pages/FormSuccessPage';
import DashboardPage from './pages/DashboardPage';
import PillaresPage from './pages/PillaresPage';
import ChatPage from './pages/ChatPage';
import MetasPage from './pages/MetasPage';
import AdminUsersPage from './pages/AdminUsersPage';
import AdminQuestionsPage from './pages/AdminQuestionsPage';
import AdminEliosPage from './pages/AdminEliosPage';
import AdminMentoradosPage from './pages/AdminMentoradosPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import PrivacyPolicyPage from './pages/PrivacyPolicyPage';

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthenticated, loading, isAdmin, user, checkAuth } = useAuth();
  const [submittingAcceptance, setSubmittingAcceptance] = useState(false);
  const [privacyOpen, setPrivacyOpen] = useState(true);

  const hasAcceptedCurrentPrivacyVersion = useMemo(
    () => user?.privacy_policy_accepted_version === PRIVACY_POLICY_VERSION,
    [user]
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  if (adminOnly && !isAdmin()) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleAcceptPrivacyPolicy = async () => {
    setSubmittingAcceptance(true);
    try {
      await authAPI.acceptPrivacyPolicy(PRIVACY_POLICY_VERSION);
      await checkAuth();
      toast.success('Política de Privacidade aceita.');
      setPrivacyOpen(false);
    } catch (error) {
      const message = error.response?.data?.detail || 'Não foi possível registrar o aceite da política.';
      toast.error(message);
      setPrivacyOpen(true);
    } finally {
      setSubmittingAcceptance(false);
    }
  };

  if (!hasAcceptedCurrentPrivacyVersion) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="text-center text-slate-300 max-w-md">
          <p className="mb-4">Para continuar, você precisa aceitar a Política de Privacidade.</p>
          <button
            type="button"
            className="underline hover:text-white"
            onClick={() => setPrivacyOpen(true)}
            disabled={submittingAcceptance}
          >
            Abrir política
          </button>
        </div>
        <PrivacyPolicyDialog
          open={privacyOpen}
          onOpenChange={setPrivacyOpen}
          onAccept={handleAcceptPrivacyPolicy}
        />
      </div>
    );
  }

  return children;
};

// Public Route Component (redirect if authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="spinner" />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route
        path="/"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />
      <Route
        path="/esqueci-senha"
        element={
          <PublicRoute>
            <ForgotPasswordPage />
          </PublicRoute>
        }
      />
      <Route path="/politica-privacidade" element={<PrivacyPolicyPage />} />
      <Route path="/form" element={<FormPage />} />
      <Route path="/form/success" element={<FormSuccessPage />} />

      {/* Protected Routes */}
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/pilares"
        element={
          <ProtectedRoute>
            <PillaresPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/metas"
        element={
          <ProtectedRoute>
            <MetasPage />
          </ProtectedRoute>
        }
      />

      {/* Admin Routes */}
      <Route
        path="/admin/usuarios"
        element={
          <ProtectedRoute adminOnly>
            <AdminUsersPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/perguntas"
        element={
          <ProtectedRoute adminOnly>
            <AdminQuestionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/elios"
        element={
          <ProtectedRoute adminOnly>
            <AdminEliosPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/mentorados"
        element={
          <ProtectedRoute adminOnly>
            <AdminMentoradosPage />
          </ProtectedRoute>
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster 
            position="top-right"
            toastOptions={{
              style: {
                background: '#112240',
                color: '#f8fafc',
                border: '1px solid rgba(255,255,255,0.1)',
              },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
