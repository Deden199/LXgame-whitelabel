import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { toast } from 'sonner';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import {
  AlertTriangle,
  Shield,
  ShieldOff,
  RefreshCw,
  TrendingUp,
  Banknote,
  Activity
} from 'lucide-react';
import { useCurrency } from '../../hooks/useCurrency';

const reasonLabels = {
  high_volume: { label: 'Volume Tinggi', color: 'bg-orange-500/20 text-orange-400', icon: TrendingUp },
  withdraw_spike: { label: 'WD Spike', color: 'bg-red-500/20 text-red-400', icon: Banknote },
  high_frequency: { label: 'Frekuensi Tinggi', color: 'bg-yellow-500/20 text-yellow-400', icon: Activity },
};

export default function RiskFlagsPage() {
  const { api } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [autoFlags, setAutoFlags] = useState([]);
  const [manualFlags, setManualFlags] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [autoRes, manualRes] = await Promise.all([
        api.get('/operator/risk/flags'),
        api.get('/operator/risk/flagged')
      ]);
      setAutoFlags(autoRes.data || []);
      setManualFlags(manualRes.data || []);
    } catch (err) {
      console.error('Failed to fetch risk data:', err);
      toast.error('Gagal memuat data risiko');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleFlag = async (playerId) => {
    try {
      await api.post(`/operator/risk/flag/${playerId}`, { reason: 'Manual review' });
      toast.success('Player ditandai untuk review');
      fetchData();
    } catch (err) {
      toast.error('Gagal menandai player');
    }
  };

  const handleUnflag = async (playerId) => {
    try {
      await api.post(`/operator/risk/unflag/${playerId}`);
      toast.success('Flag dihapus dari player');
      fetchData();
    } catch (err) {
      toast.error('Gagal menghapus flag');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(2)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="risk-flags-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Risk Management</h1>
          <p className="text-muted-foreground mt-1">Monitor dan kelola player berisiko tinggi</p>
        </div>
        <Button onClick={fetchData} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="glass-card border-orange-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Auto-Flagged (Algoritma)</p>
                <p className="text-2xl font-bold text-orange-400">{autoFlags.length}</p>
              </div>
              <div className="p-3 rounded-lg bg-orange-500/10">
                <AlertTriangle className="w-6 h-6 text-orange-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card border-red-500/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Manual Flagged</p>
                <p className="text-2xl font-bold text-red-400">{manualFlags.length}</p>
              </div>
              <div className="p-3 rounded-lg bg-red-500/10">
                <Shield className="w-6 h-6 text-red-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Auto-Flagged Players */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            Auto-Detected Risk Flags
          </CardTitle>
          <CardDescription>Player yang terdeteksi oleh sistem monitoring otomatis</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player ID</TableHead>
                <TableHead>Risk Indicators</TableHead>
                <TableHead className="text-right">Total Volume</TableHead>
                <TableHead className="text-right">Deposits</TableHead>
                <TableHead className="text-right">Withdrawals</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {autoFlags.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    Tidak ada risk flag otomatis
                  </TableCell>
                </TableRow>
              ) : (
                autoFlags.map((f) => (
                  <TableRow key={f.player_id}>
                    <TableCell className="font-mono text-sm">{f.player_id}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(f.reasons || []).map((r) => {
                          const config = reasonLabels[r] || { label: r, color: 'bg-gray-500/20 text-gray-400' };
                          return (
                            <Badge key={r} className={config.color}>
                              {config.label}
                            </Badge>
                          );
                        })}
                      </div>
                    </TableCell>
                    <TableCell className={`text-right font-mono ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(f.total_volume)}>{formatAppMoney(f.total_volume)}</TableCell>
                    <TableCell className={`text-right font-mono text-green-400 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(f.deposits)}>{formatAppMoney(f.deposits)}</TableCell>
                    <TableCell className={`text-right font-mono text-red-400 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(f.withdrawals)}>{formatAppMoney(f.withdrawals)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-orange-500 border-orange-500/50 hover:bg-orange-500/10"
                        onClick={() => handleFlag(f.player_id)}
                      >
                        <Shield className="w-4 h-4 mr-1" />
                        Flag
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Manually Flagged Players */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-red-500" />
            Manually Flagged Players
          </CardTitle>
          <CardDescription>Player yang ditandai untuk review manual</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead>Flagged At</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {manualFlags.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-muted-foreground">
                    Tidak ada player yang di-flag manual
                  </TableCell>
                </TableRow>
              ) : (
                manualFlags.map((f) => (
                  <TableRow key={f.player_id}>
                    <TableCell>
                      <div>
                        <p className="font-medium">{f.player_name || f.player_id}</p>
                        <p className="text-sm text-muted-foreground">{f.player_email}</p>
                      </div>
                    </TableCell>
                    <TableCell>{f.reason || '-'}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {f.flagged_at ? new Date(f.flagged_at).toLocaleString('id-ID') : '-'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-green-500 hover:text-green-400 hover:bg-green-500/10"
                        onClick={() => handleUnflag(f.player_id)}
                      >
                        <ShieldOff className="w-4 h-4 mr-1" />
                        Unflag
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
