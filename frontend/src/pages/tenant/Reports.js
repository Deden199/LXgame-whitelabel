import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
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
  BarChart3,
  Download,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Gamepad2,
  RefreshCw
} from 'lucide-react';
import { useCurrency } from '../../hooks/useCurrency';

export default function ReportsPage() {
  const { api } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [revenue, setRevenue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const res = await api.get('/operator/reports/revenue');
      setRevenue(res.data || []);
    } catch (err) {
      console.error('Failed to fetch revenue:', err);
      toast.error('Gagal memuat data laporan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const downloadLedgerCSV = async () => {
    setDownloading(true);
    try {
      const res = await api.get('/operator/reports/ledger.csv', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `ledger_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('CSV berhasil diunduh');
    } catch (err) {
      toast.error('Gagal mengunduh CSV');
    } finally {
      setDownloading(false);
    }
  };

  // Calculate totals
  const totals = revenue.reduce((acc, r) => ({
    bet: acc.bet + (r.bet || 0),
    win: acc.win + (r.win || 0),
    ggr: acc.ggr + (r.ggr || 0),
  }), { bet: 0, win: 0, ggr: 0 });

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-32" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Laporan Revenue</h1>
          <p className="text-muted-foreground mt-1">Ringkasan pendapatan per game dan provider</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={fetchData} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={downloadLedgerCSV} disabled={downloading}>
            <Download className="w-4 h-4 mr-2" />
            {downloading ? 'Mengunduh...' : 'Export Ledger CSV'}
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1 mr-3">
                <p className="text-sm text-muted-foreground">Total Bet</p>
                <p className={`text-2xl font-bold ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(totals.bet)}>{formatAppMoney(totals.bet)}</p>
              </div>
              <div className="p-3 rounded-lg bg-blue-500/10 flex-shrink-0">
                <TrendingDown className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1 mr-3">
                <p className="text-sm text-muted-foreground">Total Win</p>
                <p className={`text-2xl font-bold ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(totals.win)}>{formatAppMoney(totals.win)}</p>
              </div>
              <div className="p-3 rounded-lg bg-green-500/10 flex-shrink-0">
                <TrendingUp className="w-6 h-6 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card border-primary/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="min-w-0 flex-1 mr-3">
                <p className="text-sm text-muted-foreground">GGR (Gross Gaming Revenue)</p>
                <p className={`text-2xl font-bold ${totals.ggr >= 0 ? 'text-green-500' : 'text-red-500'} ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(totals.ggr)}>
                  {formatAppMoney(totals.ggr)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-primary/10 flex-shrink-0">
                <DollarSign className="w-6 h-6 text-primary" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Revenue Table */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Revenue per Game
          </CardTitle>
          <CardDescription>Breakdown pendapatan berdasarkan provider dan game</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Provider</TableHead>
                <TableHead>Game ID</TableHead>
                <TableHead className="text-right">Total Bet</TableHead>
                <TableHead className="text-right">Total Win</TableHead>
                <TableHead className="text-right">GGR</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {revenue.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    Belum ada data revenue
                  </TableCell>
                </TableRow>
              ) : (
                revenue.map((r, i) => (
                  <TableRow key={i}>
                    <TableCell className="font-medium">{r.provider_id}</TableCell>
                    <TableCell className="text-muted-foreground">{r.game_id}</TableCell>
                    <TableCell className={`text-right font-mono ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(r.bet)}>{formatAppMoney(r.bet)}</TableCell>
                    <TableCell className={`text-right font-mono ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(r.win)}>{formatAppMoney(r.win)}</TableCell>
                    <TableCell className={`text-right font-mono font-medium ${r.ggr >= 0 ? 'text-green-500' : 'text-red-500'} ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(r.ggr)}>
                      {formatAppMoney(r.ggr)}
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
