import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
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
  Alert,
  AlertDescription,
  AlertTitle,
} from '../../components/ui/alert';
import { toast } from 'sonner';
import {
  Wallet,
  Shield,
  AlertTriangle,
  TrendingUp,
  ArrowUpCircle,
  Clock,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Percent,
  Calendar,
  CreditCard,
  Info,
} from 'lucide-react';
import { formatMoney } from '../../utils/formatMoney';

// Transaction type labels in Indonesian
const TX_TYPE_LABELS = {
  TOPUP: { label: 'Topup Buffer', color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  ADJUST: { label: 'Penyesuaian', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  SETTLEMENT_DEDUCT: { label: 'Settlement', color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
  INFRA_FEE: { label: 'Biaya Infra', color: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' },
  SETUP_FEE: { label: 'Deposit Aktivasi', color: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200' },
};

export default function TenantFinancePage() {
  const { api, tenant } = useAuth();
  const [finance, setFinance] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [topupLoading, setTopupLoading] = useState(false);
  
  // Topup form state
  const [topupAmount, setTopupAmount] = useState('');
  const [topupRefId, setTopupRefId] = useState('');
  const [topupNote, setTopupNote] = useState('');

  const fetchFinance = useCallback(async () => {
    try {
      const res = await api.get('/tenant/finance');
      setFinance(res.data);
    } catch (error) {
      console.error('Failed to fetch finance:', error);
      toast.error('Gagal memuat data keuangan');
    }
  }, [api]);

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await api.get('/tenant/finance/transactions', { params: { limit: 20 } });
      setTransactions(res.data.transactions || []);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    }
  }, [api]);

  const loadData = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchFinance(), fetchTransactions()]);
    setLoading(false);
  }, [fetchFinance, fetchTransactions]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleTopup = async (e) => {
    e.preventDefault();
    
    if (!topupAmount || !topupRefId) {
      toast.error('Mohon isi jumlah dan referensi');
      return;
    }

    const amount = parseInt(topupAmount.replace(/\D/g, ''), 10);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Jumlah tidak valid');
      return;
    }

    setTopupLoading(true);
    try {
      const res = await api.post('/tenant/buffer/topup', {
        amount_idr: amount,
        ref_id: topupRefId.trim(),
        note: topupNote.trim() || undefined,
      });

      if (res.data.idempotent) {
        toast.info('Transaksi sudah pernah diproses (idempotent)');
      } else {
        toast.success(`Topup berhasil! Saldo baru: ${formatMoney(res.data.new_balance_minor, { currency: 'IDR' })}`);
      }

      // Clear form
      setTopupAmount('');
      setTopupRefId('');
      setTopupNote('');

      // Refresh data
      await loadData();
    } catch (error) {
      console.error('Topup failed:', error);
      toast.error(error.response?.data?.detail || 'Topup gagal');
    } finally {
      setTopupLoading(false);
    }
  };

  const handleAmountChange = (e) => {
    // Allow only numbers
    const value = e.target.value.replace(/\D/g, '');
    setTopupAmount(value);
  };

  const formatDisplayAmount = (value) => {
    if (!value) return '';
    const num = parseInt(value, 10);
    if (isNaN(num)) return '';
    return new Intl.NumberFormat('id-ID').format(num);
  };

  const generateRefId = () => {
    const timestamp = Date.now();
    const random = Math.random().toString(36).substring(2, 8).toUpperCase();
    setTopupRefId(`TOPUP-${timestamp}-${random}`);
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid gap-6 md:grid-cols-3">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  const requiredTopup = finance?.required_topup_minor || 0;
  const isFrozen = finance?.is_frozen || false;
  const canOperate = finance?.can_operate || false;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Finance & Risk</h1>
          <p className="text-muted-foreground">
            Kelola Saldo Buffer (Escrow) dan pantau status operasional
          </p>
        </div>
        <Button variant="outline" onClick={loadData} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Frozen Alert Banner */}
      {isFrozen && (
        <Alert variant="destructive" className="border-red-500 bg-red-50 dark:bg-red-950">
          <AlertTriangle className="h-5 w-5" />
          <AlertTitle className="text-lg font-semibold">Akun Operator Dibekukan</AlertTitle>
          <AlertDescription className="mt-2">
            <p>
              {finance?.frozen_reason || 'Saldo Buffer di bawah minimum.'}
            </p>
            {requiredTopup > 0 && (
              <p className="mt-2 font-medium">
                Topup minimal <span className="text-red-700 dark:text-red-300">{formatMoney(requiredTopup, { currency: 'IDR' })}</span> untuk aktif kembali.
              </p>
            )}
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Buffer Balance Card */}
        <Card className={isFrozen ? 'border-red-300 dark:border-red-800' : 'border-green-300 dark:border-green-800'}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Saldo Buffer (Escrow)</CardTitle>
            <Wallet className={`h-5 w-5 ${isFrozen ? 'text-red-500' : 'text-green-500'}`} />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMoney(finance?.buffer_balance_minor || 0, { currency: 'IDR' })}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Saldo pengaman untuk cover variance / negative month
            </p>
            <div className="mt-3 flex items-center gap-2">
              {canOperate ? (
                <Badge variant="success" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Aktif
                </Badge>
              ) : (
                <Badge variant="destructive">
                  <XCircle className="mr-1 h-3 w-3" />
                  Dibekukan
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Threshold Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Threshold Minimum</CardTitle>
            <Shield className="h-5 w-5 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatMoney(finance?.buffer_min_threshold_minor || 0, { currency: 'IDR' })}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Batas minimum saldo buffer yang harus dijaga
            </p>
            {requiredTopup > 0 && (
              <div className="mt-3">
                <Badge variant="warning" className="bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200">
                  <ArrowUpCircle className="mr-1 h-3 w-3" />
                  Kurang {formatMoney(requiredTopup, { currency: 'IDR' })}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Commercial Terms Card */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Ketentuan Komersial</CardTitle>
            <Percent className="h-5 w-5 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">GGR Share</span>
                <span className="font-semibold">{finance?.ggr_share_percent || 15}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Biaya Infra/bulan</span>
                <span className="font-semibold">{formatMoney(finance?.infra_fee_monthly_minor || 5000000, { currency: 'IDR' })}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">Setup Fee</span>
                <Badge variant={finance?.setup_fee_paid ? 'success' : 'secondary'} className={finance?.setup_fee_paid ? 'bg-green-100 text-green-800' : ''}>
                  {finance?.setup_fee_paid ? 'Lunas' : 'Pending'}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Topup Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ArrowUpCircle className="h-5 w-5 text-green-500" />
            Topup Saldo Buffer
          </CardTitle>
          <CardDescription>
            Tambah saldo buffer untuk memastikan operasional tetap berjalan
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTopup} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="amount">Jumlah (IDR)</Label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">Rp</span>
                  <Input
                    id="amount"
                    type="text"
                    placeholder="25.000.000"
                    value={formatDisplayAmount(topupAmount)}
                    onChange={handleAmountChange}
                    className="pl-10"
                    required
                  />
                </div>
                <p className="text-xs text-muted-foreground">
                  Min. Rp 1.000.000
                </p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="ref_id">Referensi ID</Label>
                <div className="flex gap-2">
                  <Input
                    id="ref_id"
                    type="text"
                    placeholder="TOPUP-123456"
                    value={topupRefId}
                    onChange={(e) => setTopupRefId(e.target.value)}
                    required
                  />
                  <Button type="button" variant="outline" size="icon" onClick={generateRefId} title="Generate ID">
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  ID unik untuk pencatatan
                </p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="note">Catatan (opsional)</Label>
                <Input
                  id="note"
                  type="text"
                  placeholder="Topup bulanan"
                  value={topupNote}
                  onChange={(e) => setTopupNote(e.target.value)}
                />
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button type="submit" disabled={topupLoading} className="bg-green-600 hover:bg-green-700">
                {topupLoading ? (
                  <>
                    <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                    Memproses...
                  </>
                ) : (
                  <>
                    <ArrowUpCircle className="mr-2 h-4 w-4" />
                    Topup Buffer
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-blue-50 dark:bg-blue-950 border-blue-200 dark:border-blue-800">
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <Info className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
            <div className="space-y-2">
              <h4 className="font-semibold text-blue-900 dark:text-blue-100">Tentang Saldo Buffer (Escrow)</h4>
              <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1 list-disc list-inside">
                <li>Saldo Buffer adalah dana pengaman operator yang dikelola oleh LooxGame</li>
                <li>Digunakan untuk cover variance / negative month dari hasil gaming</li>
                <li>Jika saldo di bawah threshold minimum, akun akan dibekukan otomatis</li>
                <li>Pembekuan hanya memblokir game launch dan bet baru, tidak memblokir withdrawal player</li>
                <li>Settlement dilakukan mingguan, dikurangi dari GGR share</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transaction History */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" />
            Riwayat Transaksi Buffer
          </CardTitle>
          <CardDescription>
            20 transaksi terakhir
          </CardDescription>
        </CardHeader>
        <CardContent>
          {transactions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <CreditCard className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>Belum ada transaksi</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Tanggal</TableHead>
                  <TableHead>Tipe</TableHead>
                  <TableHead>Referensi</TableHead>
                  <TableHead>Catatan</TableHead>
                  <TableHead className="text-right">Jumlah</TableHead>
                  <TableHead className="text-right">Saldo Setelah</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((tx) => {
                  const txTypeConfig = TX_TYPE_LABELS[tx.type] || { label: tx.type, color: 'bg-gray-100 text-gray-800' };
                  const isCredit = tx.amount_minor > 0;
                  
                  return (
                    <TableRow key={tx.id}>
                      <TableCell className="font-mono text-sm">
                        {new Date(tx.created_at).toLocaleString('id-ID', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge className={txTypeConfig.color}>
                          {txTypeConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {tx.ref_id}
                      </TableCell>
                      <TableCell className="max-w-xs truncate">
                        {tx.note || '-'}
                      </TableCell>
                      <TableCell className={`text-right font-semibold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
                        {isCredit ? '+' : ''}{formatMoney(tx.amount_minor, { currency: 'IDR' })}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatMoney(tx.balance_after_minor || 0, { currency: 'IDR' })}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
