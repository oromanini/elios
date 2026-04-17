import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authAPI, AUTH_UNAUTHORIZED_EVENT } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const clearAuthState = () => {
    setUser(null);
  };

  const checkAuth = useCallback(async () => {
    try {
      const response = await authAPI.getMe();
      setUser(response.data);
      return response.data;
    } catch (error) {
      clearAuthState();
      return null;
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      await checkAuth();
      setLoading(false);
    };

    initAuth();
  }, [checkAuth]);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearAuthState();
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const login = async (email, password) => {
    const response = await authAPI.login(email, password);
    // Garantia de sessão persistida via cookie HttpOnly.
    // Sem essa validação o app pode navegar para o dashboard,
    // mas as próximas requisições autenticadas falham com 401.
    const authenticatedUser = await checkAuth();
    if (authenticatedUser) {
      return authenticatedUser;
    }

    // Fallback para manter compatibilidade com cenários antigos
    // e fornecer uma mensagem de erro mais clara para a UI.
    setUser(null);
    const sessionError = new Error('Sessão não foi estabelecida após o login. Verifique cookies/autenticação.');
    sessionError.code = 'SESSION_NOT_ESTABLISHED';
    throw sessionError;
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      // noop: local client state will still be cleaned up
    }
    clearAuthState();
  };

  const isAdmin = () => {
    return user?.role === 'ADMIN';
  };

  const value = {
    user,
    loading,
    login,
    logout,
    checkAuth,
    isAdmin,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
