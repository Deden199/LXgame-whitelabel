import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AuthContext = createContext(undefined);

// Create axios instance with credentials
const api = axios.create({
  baseURL: `${API_URL}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Secure API instance for financial endpoints
// Uses Bearer token instead of cookies (CSRF protection)
const createSecureApi = (token) => {
  const instance = axios.create({
    baseURL: `${API_URL}/api`,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    }
  });
  return instance;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [tenant, setTenant] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [accessToken, setAccessToken] = useState(null);

  // Check if user is logged in on mount
  const checkAuth = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data.user);
      setTenant(response.data.tenant);
      setError(null);
      // Note: access_token might be returned on /auth/me if backend supports it
      if (response.data.access_token) {
        setAccessToken(response.data.access_token);
      }
    } catch (err) {
      setUser(null);
      setTenant(null);
      setAccessToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password, tenantSlug = null) => {
    try {
      setError(null);
      const response = await api.post('/auth/login', {
        email,
        password,
        tenant_slug: tenantSlug
      });
      
      setUser(response.data.user);
      setTenant(response.data.tenant);
      // Store access token for secure API calls
      setAccessToken(response.data.access_token);
      
      return response.data;
    } catch (err) {
      const message = err.response?.data?.detail || 'Login failed';
      setError(message);
      throw new Error(message);
    }
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } catch (err) {
      // Ignore logout errors
    } finally {
      setUser(null);
      setTenant(null);
      setAccessToken(null);
    }
  };

  const switchTenant = async (newTenant) => {
    setTenant(newTenant);
  };

  const refreshTenant = async () => {
    try {
      const response = await api.get('/auth/me');
      setTenant(response.data.tenant);
    } catch (err) {
      console.error('Failed to refresh tenant:', err);
    }
  };

  const updateUserPreferences = (nextPreferences = {}) => {
    if (!user) return;
    const nextCurrency = nextPreferences.currency || user.preferred_currency;
    setUser({
      ...user,
      preferred_currency: nextCurrency,
      preferences: {
        ...(user.preferences || {}),
        ...nextPreferences,
      },
    });
  };

  const updateWalletBalance = (newBalance) => {
    if (user) {
      setUser({ ...user, wallet_balance: newBalance });
    }
  };

  /**
   * Secure API call for financial endpoints.
   * Uses Bearer token (CSRF protection) and adds Idempotency-Key header.
   * 
   * @param {string} method - HTTP method (post, put, delete)
   * @param {string} url - API endpoint
   * @param {object} data - Request body
   * @param {string} idempotencyKey - Optional idempotency key (auto-generated if not provided)
   * @returns {Promise} API response
   */
  const secureApiCall = useCallback(async (method, url, data = {}, idempotencyKey = null) => {
    if (!accessToken) {
      throw new Error('Not authenticated. Please login again.');
    }
    
    const secureApi = createSecureApi(accessToken);
    const headers = {
      'Idempotency-Key': idempotencyKey || uuidv4(),
    };
    
    const config = { headers };
    
    switch (method.toLowerCase()) {
      case 'post':
        return secureApi.post(url, data, config);
      case 'put':
        return secureApi.put(url, data, config);
      case 'delete':
        return secureApi.delete(url, config);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  }, [accessToken]);

  const value = {
    user,
    tenant,
    loading,
    error,
    login,
    logout,
    checkAuth,
    switchTenant,
    refreshTenant,
    updateWalletBalance,
    updateUserPreferences,
    isAuthenticated: !!user,
    isSuperAdmin: user?.role === 'super_admin',
    isTenantAdmin: user?.role === 'tenant_admin',
    isPlayer: user?.role === 'player',
    api,
    accessToken,
    secureApiCall, // New secure API call method for financial endpoints
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export { api };
