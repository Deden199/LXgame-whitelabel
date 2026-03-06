import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../../components/ui/alert-dialog';
import { toast } from 'sonner';
import { useCurrency } from '../../hooks/useCurrency';

const canActionStatus = ['created', 'pending', 'requested', 'review'];

const statusClass = {
  created: 'bg-yellow-500/20 text-yellow-400',
  pending: 'bg-yellow-500/20 text-yellow-400',
  review: 'bg-blue-500/20 text-blue-400',
  requested: 'bg-blue-500/20 text-blue-400',
  success: 'bg-green-500/20 text-green-400',
  rejected: 'bg-red-500/20 text-red-400',
  cancelled: 'bg-muted text-muted-foreground',
};

export default function TenantDepositsPage() {
  const { api } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [rows, setRows] = useState([]);
  const [status, setStatus] = useState('all');
  const [search, setSearch] = useState('');
  const [confirm, setConfirm] = useState({ open: false, action: null, item: null });

  const fetchRows = async () => {
    try {
      const params = {};
      if (status !== 'all') params.status = status;
      if (search) params.search = search;
      const res = await api.get('/operator/deposits', { params });
      setRows(res.data || []);
    } catch {
      toast.error('Gagal memuat deposit orders');
    }
  };

  useEffect(() => {
    fetchRows();
  }, [status]);

  const action = async () => {
    if (!confirm.item) return;
    try {
      await api.post(`/operator/deposits/${confirm.item.id}/${confirm.action}`);
      toast.success(confirm.action === 'approve' ? 'Deposit approved' : 'Deposit rejected');
      fetchRows();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Aksi gagal');
    } finally {
      setConfirm({ open: false, action: null, item: null });
    }
  };

  return (
    <div className="space-y-6" data-testid="tenant-deposits-page">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Deposit Approvals</h1>
        <p className="text-muted-foreground">Verifikasi transfer manual dan approve/reject secara aman.</p>
      </div>

      <Card className="glass-card">
        <CardContent className="pt-6 flex flex-wrap gap-3">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-[180px]"><SelectValue placeholder="Status" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Semua status</SelectItem>
              <SelectItem value="created">Created</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="review">Review</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
          <Input placeholder="Search player_id" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-xs" />
          <Button variant="outline" onClick={fetchRows}>Refresh</Button>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Daftar Deposit Order</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Tanggal</TableHead>
                <TableHead>Player</TableHead>
                <TableHead>Jumlah</TableHead>
                <TableHead>Bank Tujuan</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Proof</TableHead>
                <TableHead>Note</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 ? (
                <TableRow><TableCell colSpan={8} className="text-center py-8 text-muted-foreground">Belum ada deposit order</TableCell></TableRow>
              ) : rows.map((row) => {
                const normalizedStatus = String(row.status || '').toLowerCase();
                return (
                  <TableRow key={row.id}>
                    <TableCell>{new Date(row.created_at).toLocaleString('id-ID')}</TableCell>
                    <TableCell className="font-medium">{row.player_id}</TableCell>
                    <TableCell className={`font-mono ${MONEY_DISPLAY_CLASSES}`}>{formatAppMoney(row.amount)} {row.currency}</TableCell>
                    <TableCell>{row.bank_account?.bank_name} - {row.bank_account?.account_number}</TableCell>
                    <TableCell><Badge className={statusClass[normalizedStatus] || 'bg-muted'}>{normalizedStatus || '-'}</Badge></TableCell>
                    <TableCell>{row.proof_url ? <a href={row.proof_url} target="_blank" rel="noreferrer" className="text-primary underline">Lihat</a> : '-'}</TableCell>
                    <TableCell className="max-w-[220px] truncate">{row.note || '-'}</TableCell>
                    <TableCell className="text-right">
                      {canActionStatus.includes(normalizedStatus) && (
                        <div className="flex justify-end gap-2">
                          <Button size="sm" variant="outline" className="text-green-500" onClick={() => setConfirm({ open: true, action: 'approve', item: row })}>Approve</Button>
                          <Button size="sm" variant="outline" className="text-red-500" onClick={() => setConfirm({ open: true, action: 'reject', item: row })}>Reject</Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <AlertDialog open={confirm.open} onOpenChange={(open) => !open && setConfirm({ open: false, action: null, item: null })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirm.action === 'approve' ? 'Approve deposit?' : 'Reject deposit?'}</AlertDialogTitle>
            <AlertDialogDescription>
              {confirm.action === 'approve' ? 'Saldo pemain akan dikreditkan secara atomic ledger.' : 'Order akan ditolak tanpa credit saldo.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction onClick={action}>{confirm.action === 'approve' ? 'Approve' : 'Reject'}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
