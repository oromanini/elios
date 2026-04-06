import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import { AuthProvider, useAuth } from './context/AuthContext';
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

// Protected Route Component
const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { isAuthenticated, loading, isAdmin } = useAuth();

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
