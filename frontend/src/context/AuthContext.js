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
    const { user: userData } = response.data;
    setUser(userData);

    // Validação defensiva: confirma persistência do cookie sem bloquear login em falhas transitórias.
    const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const maxAttempts = 3;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        const me = await authAPI.getMe();
        setUser(me.data);
        return me.data;
      } catch (error) {
        const status = error?.response?.status;
        const isUnauthorized = status === 401;
        const isLastAttempt = attempt === maxAttempts;

        if (isUnauthorized && isLastAttempt) {
          clearAuthState();
          const cookieBlockedError = new Error(
            'Sessão não persistida no navegador. Verifique bloqueio de cookies e configurações de privacidade.'
          );
          cookieBlockedError.cause = error;
          throw cookieBlockedError;
        }

        if (!isUnauthorized || isLastAttempt) {
          return userData;
        }

        await sleep(150 * attempt);
      }
    }

    return userData;
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
