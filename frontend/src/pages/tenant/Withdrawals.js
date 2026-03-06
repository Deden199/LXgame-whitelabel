import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../../components/ui/alert-dialog';
import {
  Wallet,
  CheckCircle2,
  XCircle,
  Clock,
  Filter,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import { useCurrency } from '../../hooks/useCurrency';

const statusConfig = {
  requested: { label: 'Menunggu', color: 'bg-yellow-500/20 text-yellow-400', icon: Clock },
  review: { label: 'Dalam Review', color: 'bg-blue-500/20 text-blue-400', icon: Clock },
  processing: { label: 'Diproses', color: 'bg-blue-500/20 text-blue-400', icon: Clock },
  success: { label: 'Berhasil', color: 'bg-green-500/20 text-green-400', icon: CheckCircle2 },
  failed: { label: 'Gagal', color: 'bg-red-500/20 text-red-400', icon: XCircle },
  rejected: { label: 'Ditolak', color: 'bg-red-500/20 text-red-400', icon: XCircle },
  cancelled: { label: 'Dibatalkan', color: 'bg-gray-500/20 text-gray-400', icon: XCircle },
};

export default function WithdrawalsPage() {
  const { api } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [withdrawals, setWithdrawals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [currencyFilter, setCurrencyFilter] = useState('all');
  const [confirmDialog, setConfirmDialog] = useState({ open: false, action: null, item: null });

  const fetchWithdrawals = async () => {
    setLoading(true);
    try {
      const params = {};
      if (statusFilter !== 'all') params.status = statusFilter;
      if (currencyFilter !== 'all') params.currency = currencyFilter;
      
      const res = await api.get('/operator/withdrawals', { params });
      setWithdrawals(res.data || []);
    } catch (err) {
      console.error('Failed to fetch withdrawals:', err);
      toast.error('Gagal memuat data penarikan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWithdrawals();
  }, [statusFilter, currencyFilter]);

  const handleApprove = async (id) => {
    try {
      await api.post(`/operator/withdrawals/${id}/approve`);
      toast.success('Penarikan disetujui');
      fetchWithdrawals();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyetujui penarikan');
    }
    setConfirmDialog({ open: false, action: null, item: null });
  };

  const handleReject = async (id) => {
    try {
      await api.post(`/operator/withdrawals/${id}/reject`);
      toast.success('Penarikan ditolak dan dana dikembalikan');
      fetchWithdrawals();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menolak penarikan');
    }
    setConfirmDialog({ open: false, action: null, item: null });
  };

  const stats = {
    pending: withdrawals.filter(w => ['requested', 'review', 'created', 'pending'].includes(String(w.status || '').toLowerCase())).length,
    processing: withdrawals.filter(w => w.status === 'processing').length,
    completed: withdrawals.filter(w => w.status === 'success').length,
    rejected: withdrawals.filter(w => ['rejected', 'failed', 'cancelled'].includes(w.status)).length,
  };

  if (loading && withdrawals.length === 0) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-24" />)}
        </div>
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="withdrawals-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Manajemen Penarikan</h1>
          <p className="text-muted-foreground mt-1">
            {stats.pending} menunggu persetujuan
          </p>
        </div>
        <Button onClick={fetchWithdrawals} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-yellow-500/10">
                <Clock className="w-5 h-5 text-yellow-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.pending}</p>
                <p className="text-sm text-muted-foreground">Menunggu</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-500/10">
                <RefreshCw className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.processing}</p>
                <p className="text-sm text-muted-foreground">Diproses</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-green-500/10">
                <CheckCircle2 className="w-5 h-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.completed}</p>
                <p className="text-sm text-muted-foreground">Selesai</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="glass-card">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-red-500/10">
                <XCircle className="w-5 h-5 text-red-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.rejected}</p>
                <p className="text-sm text-muted-foreground">Ditolak</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="glass-card">
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Status</SelectItem>
                <SelectItem value="requested">Menunggu</SelectItem>
                <SelectItem value="review">Dalam Review</SelectItem>
                <SelectItem value="processing">Diproses</SelectItem>
                <SelectItem value="success">Berhasil</SelectItem>
                <SelectItem value="rejected">Ditolak</SelectItem>
              </SelectContent>
            </Select>
            <Select value={currencyFilter} onValueChange={setCurrencyFilter}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Currency" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="IDR">IDR</SelectItem>
                <SelectItem value="USD">USD</SelectItem>
                <SelectItem value="USDT">USDT</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card className="glass-card">
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Player</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {withdrawals.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                    Tidak ada data penarikan
                  </TableCell>
                </TableRow>
              ) : (
                withdrawals.map((w) => {
                  const status = statusConfig[w.status] || statusConfig.requested;
                  const StatusIcon = status.icon;
                  return (
                    <TableRow key={w.id}>
                      <TableCell>
                        <div>
                          <p className="font-medium">{w.player_name || w.player_id}</p>
                          <p className="text-sm text-muted-foreground">{w.player_email}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className={`font-mono font-medium ${MONEY_DISPLAY_CLASSES}`} title={`${formatAppMoney(w.amount)} ${w.currency}`}>
                          {formatAppMoney(w.amount)} {w.currency}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge className={status.color}>
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {status.label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(w.created_at).toLocaleString('id-ID')}
                      </TableCell>
                      <TableCell className="text-right">
                        {['requested', 'review', 'created', 'pending', 'processing'].includes(String(w.status || '').toLowerCase()) && (
                          <div className="flex justify-end gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-green-500 border-green-500/50 hover:bg-green-500/10"
                              onClick={() => setConfirmDialog({ open: true, action: 'approve', item: w })}
                            >
                              <CheckCircle2 className="w-4 h-4 mr-1" />
                              Approve
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-500 border-red-500/50 hover:bg-red-500/10"
                              onClick={() => setConfirmDialog({ open: true, action: 'reject', item: w })}
                            >
                              <XCircle className="w-4 h-4 mr-1" />
                              Reject
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Confirm Dialog */}
      <AlertDialog open={confirmDialog.open} onOpenChange={(open) => !open && setConfirmDialog({ open: false, action: null, item: null })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmDialog.action === 'approve' ? 'Setujui Penarikan?' : 'Tolak Penarikan?'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmDialog.action === 'approve'
                ? `Anda akan menyetujui penarikan sebesar ${formatAppMoney(confirmDialog.item?.amount)} ${confirmDialog.item?.currency} untuk ${confirmDialog.item?.player_name || confirmDialog.item?.player_id}.`
                : `Anda akan menolak penarikan. Dana sebesar ${formatAppMoney(confirmDialog.item?.amount)} ${confirmDialog.item?.currency} akan dikembalikan ke wallet pemain.`
              }
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction
              className={confirmDialog.action === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}
              onClick={() => confirmDialog.action === 'approve' ? handleApprove(confirmDialog.item?.id) : handleReject(confirmDialog.item?.id)}
            >
              {confirmDialog.action === 'approve' ? 'Setujui' : 'Tolak'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
