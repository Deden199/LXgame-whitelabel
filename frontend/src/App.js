import React, { useEffect, useState, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet, useNavigate } from 'react-router-dom';
import { Toaster, toast } from 'sonner';
import { HelmetProvider } from 'react-helmet-async';

import { ThemeProvider, useTheme } from './context/ThemeContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Layout } from './components/layout/Layout';
import { SEOHead, CustomHTMLInjector } from './components/SEOHead';

// Pages
import LandingPage from './pages/Landing';
import LoginPage from './pages/Login';
import SuperAdminDashboard from './pages/admin/Dashboard';
import SuperAdminTenants from './pages/admin/Tenants';
import SuperAdminTenantDetail from './pages/admin/TenantDetail';
import TenantDashboard from './pages/tenant/Dashboard';
import TenantPlayers from './pages/tenant/Players';
import TenantGames from './pages/tenant/Games';
import TenantTransactions from './pages/tenant/Transactions';
import TenantBranding from './pages/tenant/Branding';
import TenantWithdrawals from './pages/tenant/Withdrawals';
import TenantBankAccounts from './pages/tenant/BankAccounts';
import TenantDeposits from './pages/tenant/Deposits';
import TenantReports from './pages/tenant/Reports';
import TenantAPIKeys from './pages/tenant/APIKeys';
import TenantRiskFlags from './pages/tenant/RiskFlags';
import TenantSettings from './pages/tenant/Settings';
import TenantFinance from './pages/tenant/Finance';
import PlayerDashboard from './pages/player/Dashboard';
import PlayerGames from './pages/player/Games';
import PlayerProviders from './pages/player/Providers';
import PlayerWallet from './pages/player/Wallet';
import PlayerWithdraw from './pages/player/Withdraw';
import PlayerHistory from './pages/player/History';
import ResponsibleGaming from './pages/player/ResponsibleGaming';

// Session timeout in milliseconds (15 minutes)
const SESSION_TIMEOUT = 15 * 60 * 1000;
const SESSION_WARNING = 2 * 60 * 1000; // 2 minutes before timeout

// Component to sync theme with tenant
const ThemeSyncer = ({ children }) => {
  const { tenant } = useAuth();
  const { setTheme } = useTheme();

  useEffect(() => {
    if (tenant?.theme_preset) {
      setTheme(tenant.theme_preset);
    }
  }, [tenant, setTheme]);

  return children;
};

// Session Manager Component
const SessionManager = ({ children }) => {
  const { isAuthenticated, logout, api } = useAuth();
  const navigate = useNavigate();
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [showWarning, setShowWarning] = useState(false);

  const resetTimer = useCallback(() => {
    setLastActivity(Date.now());
    setShowWarning(false);
  }, []);

  // Track user activity
  useEffect(() => {
    if (!isAuthenticated) return;

    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    
    const handleActivity = () => {
      resetTimer();
    };

    events.forEach(event => {
      window.addEventListener(event, handleActivity);
    });

    return () => {
      events.forEach(event => {
        window.removeEventListener(event, handleActivity);
      });
    };
  }, [isAuthenticated, resetTimer]);

  // Check for timeout
  useEffect(() => {
    if (!isAuthenticated) return;

    const checkTimeout = setInterval(() => {
      const elapsed = Date.now() - lastActivity;
      
      if (elapsed >= SESSION_TIMEOUT) {
        logout();
        navigate('/login');
        toast.error('Session expired due to inactivity');
      } else if (elapsed >= SESSION_TIMEOUT - SESSION_WARNING && !showWarning) {
        setShowWarning(true);
        toast.warning('Your session will expire in 2 minutes due to inactivity', {
          duration: 10000,
          action: {
            label: 'Stay logged in',
            onClick: async () => {
              try {
                await api.post('/auth/refresh');
                resetTimer();
                toast.success('Session extended');
              } catch (e) {
                // Ignore
              }
            }
          }
        });
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(checkTimeout);
  }, [isAuthenticated, lastActivity, showWarning, logout, navigate, api, resetTimer]);

  return children;
};

// Protected Route wrapper
const ProtectedRoute = ({ allowedRoles, children }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    if (user?.role === 'super_admin') return <Navigate to="/admin/dashboard" replace />;
    if (user?.role === 'tenant_admin') return <Navigate to="/tenant" replace />;
    if (user?.role === 'player') return <Navigate to="/play" replace />;
    return <Navigate to="/login" replace />;
  }

  return children || <Outlet />;
};

// Layout wrapper for authenticated routes
const AuthenticatedLayout = () => {
  return (
    <SessionManager>
      <Layout>
        <Outlet />
      </Layout>
    </SessionManager>
  );
};

// Home redirect based on role
const HomeRedirect = () => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  switch (user?.role) {
    case 'super_admin':
      return <Navigate to="/admin/dashboard" replace />;
    case 'tenant_admin':
      return <Navigate to="/tenant" replace />;
    case 'player':
      return <Navigate to="/play/dashboard" replace />;
    default:
      return <Navigate to="/login" replace />;
  }
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      
      {/* Home redirect for authenticated users */}
      <Route path="/home" element={<HomeRedirect />} />

      {/* Super Admin routes */}
      <Route
        element={
          <ProtectedRoute allowedRoles={['super_admin']}>
            <AuthenticatedLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
        <Route path="/admin/dashboard" element={<SuperAdminDashboard />} />
        <Route path="/admin/tenants" element={<SuperAdminTenants />} />
        <Route path="/admin/tenants/:id" element={<SuperAdminTenantDetail />} />
        <Route path="/admin/transactions" element={<TenantTransactions />} />
        <Route path="/admin/themes" element={<TenantBranding />} />
      </Route>

      {/* Tenant Admin routes */}
      <Route
        element={
          <ProtectedRoute allowedRoles={['tenant_admin']}>
            <AuthenticatedLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/tenant" element={<TenantDashboard />} />
        <Route path="/tenant/players" element={<TenantPlayers />} />
        <Route path="/tenant/games" element={<TenantGames />} />
        <Route path="/tenant/transactions" element={<TenantTransactions />} />
        <Route path="/tenant/branding" element={<TenantBranding />} />
        <Route path="/tenant/withdrawals" element={<TenantWithdrawals />} />
        <Route path="/tenant/bank-accounts" element={<TenantBankAccounts />} />
        <Route path="/tenant/deposits" element={<TenantDeposits />} />
        <Route path="/tenant/reports" element={<TenantReports />} />
        <Route path="/tenant/finance" element={<TenantFinance />} />
        <Route path="/tenant/api-keys" element={<TenantAPIKeys />} />
        <Route path="/tenant/risk" element={<TenantRiskFlags />} />
        <Route path="/tenant/settings" element={<TenantSettings />} />
      </Route>

      {/* Player routes */}
      <Route
        element={
          <ProtectedRoute allowedRoles={['player']}>
            <AuthenticatedLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/play" element={<PlayerGames />} />
        <Route path="/play/dashboard" element={<PlayerDashboard />} />
        <Route path="/play/games" element={<PlayerGames />} />
        <Route path="/play/providers" element={<PlayerProviders />} />
        <Route path="/play/wallet" element={<PlayerWallet />} />
        <Route path="/play/withdraw" element={<PlayerWithdraw />} />
        <Route path="/play/history" element={<PlayerHistory />} />
        <Route path="/play/responsible-gaming" element={<ResponsibleGaming />} />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <HelmetProvider>
      <BrowserRouter>
        <ThemeProvider defaultTheme="royal_gold">
          <AuthProvider>
            <ThemeSyncer>
              <AppRoutes />
              <Toaster 
                position="top-right" 
                richColors 
                closeButton
                toastOptions={{
                  className: 'glass-card'
                }}
              />
            </ThemeSyncer>
          </AuthProvider>
        </ThemeProvider>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
