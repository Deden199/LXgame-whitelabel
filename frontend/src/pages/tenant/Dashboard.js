import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { 
  Users, 
  Gamepad2, 
  Receipt,
  TrendingUp,
  DollarSign,
  ArrowDownRight,
  Trophy,
  Target
} from 'lucide-react';
import { useCurrency } from '../../hooks/useCurrency';

export default function TenantDashboard() {
  const { api, tenant } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [stats, setStats] = useState(null);
  const [topGames, setTopGames] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiKeys, setApiKeys] = useState([]);
  const [apiKeyLabel, setApiKeyLabel] = useState('');
  const [newApiKey, setNewApiKey] = useState('');

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, topGamesRes, keysRes] = await Promise.all([
        api.get(`/stats/tenant/${tenant.id}`),
        api.get(`/stats/tenant/${tenant.id}/top-games`),
        api.get('/operator/api-keys').catch(() => ({ data: [] })),
      ]);
      setStats(statsRes.data);
      setTopGames(topGamesRes.data);
      setApiKeys(keysRes.data || []);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    } finally {
      setLoading(false);
    }
  }, [api, tenant?.id]);

  useEffect(() => {
    if (tenant?.id) {
      fetchData();
    }
  }, [tenant?.id, fetchData]);


  const createApiKey = async () => {
    try {
      const response = await api.post('/operator/api-keys', { label: apiKeyLabel || null });
      setNewApiKey(response.data.key);
      setApiKeyLabel('');
      const keysRes = await api.get('/operator/api-keys');
      setApiKeys(keysRes.data || []);
    } catch (err) {
      console.error('Failed to create API key:', err);
    }
  };

  const revokeApiKey = async (keyId) => {
    try {
      await api.post(`/operator/api-keys/${keyId}/revoke`);
      setApiKeys((prev) => prev.map((key) => key.id === keyId ? { ...key, is_active: false } : key));
    } catch (err) {
      console.error('Failed to revoke API key:', err);
    }
  };

  const statCards = [
    {
      title: 'Total Pemain',
      value: stats?.total_players || 0,
      subValue: `${stats?.active_players || 0} aktif`,
      icon: Users,
      color: 'text-green-500',
      bg: 'bg-green-500/10'
    },
    {
      title: 'Total Permainan',
      value: stats?.total_games || 0,
      icon: Gamepad2,
      color: 'text-purple-500',
      bg: 'bg-purple-500/10'
    },
    {
      title: 'Transaksi',
      value: stats?.total_transactions || 0,
      icon: Receipt,
      color: 'text-orange-500',
      bg: 'bg-orange-500/10'
    },
    {
      title: 'Total Setoran',
      value: formatAppMoney(stats?.total_deposits || 0),
      icon: ArrowDownRight,
      color: 'text-blue-500',
      bg: 'bg-blue-500/10'
    },
    {
      title: 'Total Taruhan',
      value: formatAppMoney(stats?.total_bets || 0),
      icon: DollarSign,
      color: 'text-yellow-500',
      bg: 'bg-yellow-500/10'
    },
    {
      title: 'GGR',
      value: formatAppMoney(stats?.gross_gaming_revenue || 0),
      icon: TrendingUp,
      color: 'text-primary',
      bg: 'bg-primary/10',
      isHighlight: true
    }
  ];

  if (loading) {
    return (
      <div className="space-y-6" data-testid="tenant-dashboard">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="tenant-dashboard">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
          Dasbor {tenant?.name || 'Tenant'}
        </h1>
        <p className="text-muted-foreground mt-1">
          Gambaran umum dan statistik operator
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((stat, index) => (
          <Card 
            key={index} 
            className={`glass-card hover:glow-accent transition-shadow duration-300 ${
              stat.isHighlight ? 'border-primary/30' : ''
            }`}
          >
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-muted-foreground">{stat.title}</p>
                  <p className={`text-2xl font-bold mt-1 ${MONEY_DISPLAY_CLASSES}`} title={String(stat.value)}>{stat.value}</p>
                  {stat.subValue && (
                    <p className="text-xs text-muted-foreground mt-1">{stat.subValue}</p>
                  )}
                </div>
                <div className={`p-2 rounded-lg ${stat.bg} flex-shrink-0 ml-3`}>
                  <stat.icon className={`w-5 h-5 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Quick Info */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Info Platform</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-muted-foreground">ID Operator</span>
              <code className="text-xs bg-muted px-2 py-1 rounded truncate max-w-[100px]" title={tenant?.id}>{tenant?.id?.slice(0, 12)}...</code>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-muted-foreground">Slug</span>
              <span className="font-medium">{tenant?.slug}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-muted-foreground">Tema</span>
              <span className="font-medium capitalize">{tenant?.theme_preset?.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between items-center py-2">
              <span className="text-muted-foreground">Status</span>
              <span className={`px-2 py-1 rounded-full text-xs ${
                tenant?.is_active ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
              }`}>
                {tenant?.is_active ? 'Aktif' : 'Tidak Aktif'}
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-lg">Rincian Pendapatan</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-muted-foreground">Total Taruhan</span>
              <span className={`font-medium text-yellow-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats?.total_bets || 0)}>
                {formatAppMoney(stats?.total_bets || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-border/50">
              <span className="text-muted-foreground">Total Kemenangan</span>
              <span className={`font-medium text-red-400 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats?.total_wins || 0)}>
                -{formatAppMoney(stats?.total_wins || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-t-2 border-primary/30 mt-2 pt-4">
              <span className="font-semibold">GGR</span>
              <span className={`font-bold text-primary text-lg ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats?.gross_gaming_revenue || 0)}>
                {formatAppMoney(stats?.gross_gaming_revenue || 0)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Games Section - Operator Snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="glass-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Target className="w-5 h-5 text-yellow-500" />
              Top 5 Games by Bets
            </CardTitle>
            <CardDescription>Permainan dengan total taruhan tertinggi</CardDescription>
          </CardHeader>
          <CardContent>
            {topGames?.top_by_bets?.length > 0 ? (
              <div className="space-y-2">
                {topGames.top_by_bets.map((game, idx) => (
                  <div 
                    key={game.game_id} 
                    className="flex items-center gap-3 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-xs font-bold text-muted-foreground w-5">#{idx + 1}</span>
                    <div className="w-10 h-8 rounded overflow-hidden bg-muted flex-shrink-0">
                      {game.thumbnail_url ? (
                        <img src={game.thumbnail_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Gamepad2 className="w-4 h-4 text-muted-foreground/30" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{game.name}</p>
                    </div>
                    <span className={`text-sm font-bold text-yellow-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(game.total_bets)}>
                      {formatAppMoney(game.total_bets)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground text-sm">
                Belum ada data taruhan
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <Trophy className="w-5 h-5 text-green-500" />
              Top 5 Games by Wins
            </CardTitle>
            <CardDescription>Permainan dengan total kemenangan tertinggi</CardDescription>
          </CardHeader>
          <CardContent>
            {topGames?.top_by_wins?.length > 0 ? (
              <div className="space-y-2">
                {topGames.top_by_wins.map((game, idx) => (
                  <div 
                    key={game.game_id} 
                    className="flex items-center gap-3 p-2 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
                  >
                    <span className="text-xs font-bold text-muted-foreground w-5">#{idx + 1}</span>
                    <div className="w-10 h-8 rounded overflow-hidden bg-muted flex-shrink-0">
                      {game.thumbnail_url ? (
                        <img src={game.thumbnail_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <Gamepad2 className="w-4 h-4 text-muted-foreground/30" />
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{game.name}</p>
                    </div>
                    <span className={`text-sm font-bold text-green-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(game.total_wins)}>
                      {formatAppMoney(game.total_wins)}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-6 text-muted-foreground text-sm">
                Belum ada data kemenangan
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-lg">QTech API Keys</CardTitle>
          <CardDescription>Generate and manage callback API keys (X-API-Key)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input value={apiKeyLabel} onChange={(e) => setApiKeyLabel(e.target.value)} placeholder="Optional label" className="max-w-xs" />
            <Button onClick={createApiKey}>Generate Key</Button>
          </div>
          {newApiKey && (
            <div className="rounded border border-yellow-500/40 bg-yellow-500/10 p-2 text-xs break-all">
              Save this key now (shown once): <code>{newApiKey}</code>
            </div>
          )}
          <div className="space-y-2">
            {apiKeys.map((key) => (
              <div key={key.id} className="flex items-center justify-between rounded border border-border/50 p-2 text-xs">
                <div>
                  <p className="font-medium">{key.label || 'Unlabeled key'}</p>
                  <p className="text-muted-foreground">{key.prefix}... · {key.is_active ? 'active' : 'revoked'}</p>
                </div>
                {key.is_active && <Button variant="outline" size="sm" onClick={() => revokeApiKey(key.id)}>Revoke</Button>}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
