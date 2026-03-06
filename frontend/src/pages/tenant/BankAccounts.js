import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Building2, Pencil, Power, Plus } from 'lucide-react';

const initialForm = { bank_name: '', account_number: '', account_name: '' };

export default function TenantBankAccountsPage() {
  const { api } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(initialForm);

  const fetchRows = async () => {
    setLoading(true);
    try {
      const res = await api.get('/operator/bank-accounts');
      setRows(res.data || []);
    } catch (err) {
      toast.error('Gagal memuat rekening bank');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRows();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(initialForm);
    setOpen(true);
  };

  const openEdit = (item) => {
    setEditing(item);
    setForm({ bank_name: item.bank_name || '', account_number: item.account_number || '', account_name: item.account_name || '' });
    setOpen(true);
  };

  const submit = async () => {
    const payload = {
      ...form,
      account_number: String(form.account_number || '').replace(/\D/g, ''),
    };
    if (!payload.bank_name || !payload.account_name || !payload.account_number) {
      toast.error('Semua field wajib diisi dengan benar');
      return;
    }

    try {
      if (editing) {
        await api.patch(`/operator/bank-accounts/${editing.id}`, payload);
        toast.success('Rekening berhasil diperbarui');
      } else {
        await api.post('/operator/bank-accounts', payload);
        toast.success('Rekening berhasil ditambahkan');
      }
      setOpen(false);
      fetchRows();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal menyimpan rekening');
    }
  };

  const toggle = async (id) => {
    try {
      await api.post(`/operator/bank-accounts/${id}/toggle`);
      toast.success('Status rekening diperbarui');
      fetchRows();
    } catch {
      toast.error('Gagal mengubah status rekening');
    }
  };

  return (
    <div className="space-y-6" data-testid="tenant-bank-accounts-page">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Deposit Bank Accounts</h1>
          <p className="text-muted-foreground">Kelola rekening tujuan transfer manual untuk deposit player.</p>
        </div>
        <Button onClick={openCreate}><Plus className="w-4 h-4 mr-2" />Tambah Rekening</Button>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Building2 className="w-5 h-5 text-primary" />Daftar Rekening</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Memuat data...</p>
          ) : rows.length === 0 ? (
            <div className="text-center py-14 border border-dashed rounded-xl">
              <p className="font-medium">Belum ada rekening bank</p>
              <p className="text-sm text-muted-foreground mb-4">Tambahkan rekening pertama untuk mulai menerima deposit manual.</p>
              <Button onClick={openCreate}>Tambah Rekening</Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bank</TableHead>
                  <TableHead>No. Rekening</TableHead>
                  <TableHead>Nama Rekening</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-medium">{item.bank_name}</TableCell>
                    <TableCell className="font-mono">{item.account_number}</TableCell>
                    <TableCell>{item.account_name}</TableCell>
                    <TableCell>
                      <Badge className={item.is_active ? 'bg-green-500/20 text-green-400' : 'bg-muted text-muted-foreground'}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="outline" size="sm" onClick={() => openEdit(item)}><Pencil className="w-4 h-4 mr-1" />Edit</Button>
                        <Button variant="outline" size="sm" onClick={() => toggle(item.id)}><Power className="w-4 h-4 mr-1" />Toggle</Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit Rekening Bank' : 'Tambah Rekening Bank'}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <Label>Nama Bank</Label>
              <Input value={form.bank_name} onChange={(e) => setForm((prev) => ({ ...prev, bank_name: e.target.value }))} />
            </div>
            <div>
              <Label>No. Rekening</Label>
              <Input value={form.account_number} onChange={(e) => setForm((prev) => ({ ...prev, account_number: e.target.value.replace(/\D/g, '') }))} />
            </div>
            <div>
              <Label>Nama Pemilik Rekening</Label>
              <Input value={form.account_name} onChange={(e) => setForm((prev) => ({ ...prev, account_name: e.target.value }))} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Batal</Button>
            <Button onClick={submit}>Simpan</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
