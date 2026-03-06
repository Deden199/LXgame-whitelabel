import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { Badge } from '../../components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { 
  Users, 
  Search,
  Wallet,
  Calendar,
  TrendingUp,
  Clock,
  Gamepad2
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';

export default function PlayersPage() {
  const { api, tenant } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchPlayers();
  }, [tenant?.id]);

  const fetchPlayers = async () => {
    try {
      const response = await api.get('/users', {
        params: { role: 'player' }
      });
      setPlayers(response.data);
    } catch (err) {
      console.error('Failed to fetch players:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredPlayers = players.filter(p =>
    p.display_name.toLowerCase().includes(search.toLowerCase()) ||
    p.email.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: players.length,
    active: players.filter(p => p.is_active).length,
    totalBalance: players.reduce((sum, p) => sum + (p.wallet_balance || 0), 0),
    totalBets: players.reduce((sum, p) => sum + (p.total_bets || 0), 0),
    recentlyActive: players.filter(p => {
      if (!p.last_login) return false;
      const lastLogin = new Date(p.last_login);
      const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
      return lastLogin > dayAgo;
    }).length
  };

  const getLastLoginBadge = (lastLogin) => {
    if (!lastLogin) return { label: 'Tidak pernah', color: 'bg-gray-500/10 text-gray-500' };
    
    const date = new Date(lastLogin);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    
    if (diffHours < 1) return { label: 'Online', color: 'bg-green-500/10 text-green-500' };
    if (diffHours < 24) return { label: 'Hari ini', color: 'bg-blue-500/10 text-blue-500' };
    if (diffHours < 168) return { label: 'Minggu ini', color: 'bg-yellow-500/10 text-yellow-500' };
    return { label: 'Tidak aktif', color: 'bg-gray-500/10 text-gray-500' };
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="players-page">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="players-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Pemain</h1>
          <p className="text-muted-foreground mt-1">
            {stats.recentlyActive} aktif 24 jam terakhir • Kelola pemain operator Anda
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Cari pemain..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 w-64"
              data-testid="search-players"
            />
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10">
                <Users className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/10">
                <Clock className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.recentlyActive}</p>
                <p className="text-sm text-muted-foreground">Aktif 24j</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/10 flex-shrink-0">
                <Wallet className="w-5 h-5 text-yellow-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className={`text-2xl font-bold ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats.totalBalance || 0)}>{formatAppMoney(stats.totalBalance || 0)}</p>
                <p className="text-sm text-muted-foreground">Total Saldo</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10 flex-shrink-0">
                <TrendingUp className="w-5 h-5 text-blue-500" />
              </div>
              <div className="min-w-0 flex-1">
                <p className={`text-2xl font-bold ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats.totalBets || 0)}>{formatAppMoney(stats.totalBets || 0)}</p>
                <p className="text-sm text-muted-foreground">Total Taruhan</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/10">
                <Gamepad2 className="w-5 h-5 text-purple-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {players.reduce((sum, p) => sum + (p.games_played_count || 0), 0).toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Permainan</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Players Table */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Semua Pemain ({filteredPlayers.length})</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Pemain</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                  <TableHead className="text-right">Total Taruhan</TableHead>
                  <TableHead className="text-right">Permainan</TableHead>
                  <TableHead>Login Terakhir</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Bergabung</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredPlayers.map((player) => {
                  const loginBadge = getLastLoginBadge(player.last_login);
                  return (
                    <TableRow key={player.id}>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                            <span className="text-xs font-bold text-primary">
                              {player.display_name.charAt(0)}
                            </span>
                          </div>
                          <span className="font-medium">{player.display_name}</span>
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {player.email}
                      </TableCell>
                      <TableCell className={`text-right font-mono font-medium ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(player.wallet_balance || 0)}>
                        {formatAppMoney(player.wallet_balance || 0)}
                      </TableCell>
                      <TableCell className={`text-right font-mono text-sm ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(player.total_bets || 0)}>
                        {formatAppMoney(player.total_bets || 0)}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {player.games_played_count || 0}
                      </TableCell>
                      <TableCell>
                        <Badge className={cn("text-[10px]", loginBadge.color)}>
                          {loginBadge.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant={player.is_active ? 'default' : 'secondary'}>
                          {player.is_active ? 'Aktif' : 'Tidak Aktif'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(player.created_at).toLocaleDateString('id-ID')}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
