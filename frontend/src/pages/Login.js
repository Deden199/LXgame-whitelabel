import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Crown, Waves, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '../lib/utils';
import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

export default function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, isAuthenticated, user } = useAuth();
  const { setTheme } = useTheme();
  
  const [activeTab, setActiveTab] = useState('admin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tenantInfo, setTenantInfo] = useState(null);

  // Check for tenant param in URL
  useEffect(() => {
    const tenant = searchParams.get('tenant');
    if (tenant) {
      setTenantSlug(tenant);
      setActiveTab('player');
      fetchTenantInfo(tenant);
    }
  }, [searchParams]);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated && user) {
      redirectBasedOnRole(user.role);
    }
  }, [isAuthenticated, user]);

  const fetchTenantInfo = async (slug) => {
    try {
      const response = await axios.get(`${API_URL}/api/tenants/slug/${slug}`);
      setTenantInfo(response.data);
      setTheme(response.data.theme_preset || 'royal_gold');
    } catch (err) {
      console.error('Failed to fetch tenant:', err);
    }
  };

  const redirectBasedOnRole = (role) => {
    switch (role) {
      case 'super_admin':
        navigate('/admin');
        break;
      case 'tenant_admin':
        navigate('/tenant');
        break;
      case 'player':
        navigate('/play');
        break;
      default:
        navigate('/');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const slug = activeTab === 'player' ? tenantSlug : null;
      const result = await login(email, password, slug);
      
      if (result.tenant) {
        setTheme(result.tenant.theme_preset || 'royal_gold');
      }
      
      redirectBasedOnRole(result.user.role);
    } catch (err) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (type) => {
    setLoading(true);
    setError('');

    try {
      let demoEmail, demoPass, demoSlug;
      
      switch (type) {
        case 'loox_operator':
          // Aurora Bet operator - from seed_demo_fullpower.py
          demoEmail = 'admin@aurorabot.com';
          demoPass = 'AuroraDemo2024!';
          demoSlug = null;
          break;
        case 'loox_player':
          // Player from aurumbet tenant
          demoEmail = 'player1@aurumbet.demo';
          demoPass = 'player123';
          demoSlug = 'aurumbet';
          break;
        case 'superadmin':
          demoEmail = 'admin@platform.com';
          demoPass = 'admin123';
          demoSlug = null;
          break;
        case 'tenant_aurum':
          demoEmail = 'admin@aurumbet.com';
          demoPass = 'admin123';
          demoSlug = null;
          break;
        case 'tenant_bluewave':
          demoEmail = 'admin@bluewave.com';
          demoPass = 'admin123';
          demoSlug = null;
          break;
        case 'player_aurum':
          demoEmail = 'player1@aurumbet.demo';
          demoPass = 'player123';
          demoSlug = 'aurumbet';
          break;
        case 'player_bluewave':
          demoEmail = 'player1@bluewave.demo';
          demoPass = 'player123';
          demoSlug = 'bluewave';
          break;
        default:
          return;
      }

      const result = await login(demoEmail, demoPass, demoSlug);
      
      if (result.tenant) {
        setTheme(result.tenant.theme_preset || 'royal_gold');
      }
      
      redirectBasedOnRole(result.user.role);
    } catch (err) {
      setError(err.message || 'Demo login failed');
    } finally {
      setLoading(false);
    }
  };

  const LogoIcon = tenantInfo?.theme_preset === 'midnight_blue' ? Waves : Crown;

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-primary/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-accent/5 rounded-full blur-3xl" />
      </div>

      <div className="noise-overlay" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center glow-primary mb-4">
            <LogoIcon className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">
            {tenantInfo?.name || 'LooxGame'}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Operator Gaming Engine
          </p>
        </div>

        {/* Login Card */}
        <Card className="glass-card border-border/50">
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-xl">Selamat Datang</CardTitle>
            <CardDescription>
              Masuk untuk mengakses platform
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="admin" data-testid="tab-admin">Admin</TabsTrigger>
                <TabsTrigger value="player" data-testid="tab-player">Pemain</TabsTrigger>
              </TabsList>

              <form onSubmit={handleLogin} className="space-y-4">
                {activeTab === 'player' && (
                  <div className="space-y-2">
                    <Label htmlFor="tenant">Operator</Label>
                    <Input
                      id="tenant"
                      placeholder="contoh: aurumbet"
                      value={tenantSlug}
                      onChange={(e) => {
                        setTenantSlug(e.target.value);
                        if (e.target.value) fetchTenantInfo(e.target.value);
                      }}
                      data-testid="input-tenant"
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="anda@contoh.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="input-email"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Kata Sandi</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    data-testid="input-password"
                  />
                </div>

                {error && (
                  <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 p-3 rounded-lg">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                )}

                <Button 
                  type="submit" 
                  className="w-full glow-primary"
                  disabled={loading}
                  data-testid="login-submit-btn"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Masuk...
                    </>
                  ) : (
                    'Masuk'
                  )}
                </Button>
              </form>
            </Tabs>

            {/* Demo Accounts */}
            <div className="mt-6 pt-6 border-t border-border">
              <p className="text-xs text-muted-foreground text-center mb-4">
                Demo Access
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDemoLogin('loox_operator')}
                  disabled={loading}
                  className="text-xs"
                  data-testid="demo-loox-operator-btn"
                >
                  Operator Demo
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDemoLogin('loox_player')}
                  disabled={loading}
                  className="text-xs"
                  data-testid="demo-loox-player-btn"
                >
                  <Crown className="w-3 h-3 mr-1 text-yellow-500" />
                  Player Demo
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDemoLogin('tenant_aurum')}
                  disabled={loading}
                  className="text-xs"
                  data-testid="demo-aurum-admin-btn"
                >
                  Admin Aurum
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDemoLogin('player_aurum')}
                  disabled={loading}
                  className="text-xs"
                  data-testid="demo-aurum-player-btn"
                >
                  <Crown className="w-3 h-3 mr-1 text-yellow-500" />
                  Pemain Aurum
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          Powered by <span className="font-medium text-primary">LooxGame</span>
        </p>
      </div>
    </div>
  );
}
