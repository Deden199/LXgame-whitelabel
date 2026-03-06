import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
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
  Key,
  Plus,
  Trash2,
  Copy,
  CheckCircle2,
  XCircle,
  Clock,
  Shield
} from 'lucide-react';

export default function APIKeysPage() {
  const { api } = useAuth();
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyLabel, setNewKeyLabel] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [revokeDialog, setRevokeDialog] = useState({ open: false, keyId: null, keyLabel: null });

  const fetchKeys = async () => {
    try {
      const res = await api.get('/operator/api-keys');
      setKeys(res.data || []);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
      toast.error('Gagal memuat API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const createKey = async () => {
    setCreating(true);
    try {
      const res = await api.post('/operator/api-keys', { label: newKeyLabel || null });
      setNewKeyValue(res.data.key);
      setNewKeyLabel('');
      toast.success('API key berhasil dibuat');
      fetchKeys();
    } catch (err) {
      toast.error('Gagal membuat API key');
    } finally {
      setCreating(false);
    }
  };

  const revokeKey = async (keyId) => {
    try {
      await api.post(`/operator/api-keys/${keyId}/revoke`);
      toast.success('API key berhasil dicabut');
      fetchKeys();
    } catch (err) {
      toast.error('Gagal mencabut API key');
    }
    setRevokeDialog({ open: false, keyId: null, keyLabel: null });
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Disalin ke clipboard');
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="api-keys-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">API Keys</h1>
        <p className="text-muted-foreground mt-1">Kelola kunci API untuk integrasi QTech wallet callback</p>
      </div>

      {/* Create New Key */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5" />
            Buat API Key Baru
          </CardTitle>
          <CardDescription>Key hanya ditampilkan sekali saat pembuatan</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <Input
              placeholder="Label (opsional)"
              value={newKeyLabel}
              onChange={(e) => setNewKeyLabel(e.target.value)}
              className="flex-1"
            />
            <Button onClick={createKey} disabled={creating}>
              <Key className="w-4 h-4 mr-2" />
              {creating ? 'Membuat...' : 'Generate Key'}
            </Button>
          </div>

          {newKeyValue && (
            <div className="mt-4 p-4 rounded-lg bg-green-500/10 border border-green-500/30">
              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <p className="text-sm text-green-400 mb-1">API Key baru (salin sekarang, tidak akan ditampilkan lagi):</p>
                  <code className="text-sm font-mono bg-black/30 px-3 py-2 rounded block overflow-x-auto">
                    {newKeyValue}
                  </code>
                </div>
                <Button variant="ghost" size="icon" onClick={() => copyToClipboard(newKeyValue)}>
                  <Copy className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Keys List */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Active Keys
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Label</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Last Used</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
                    Belum ada API key
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((k) => (
                  <TableRow key={k.id}>
                    <TableCell className="font-medium">{k.label || '-'}</TableCell>
                    <TableCell>
                      <code className="text-sm font-mono bg-muted px-2 py-1 rounded">
                        {k.prefix}...
                      </code>
                    </TableCell>
                    <TableCell>
                      {k.is_active ? (
                        <Badge className="bg-green-500/20 text-green-400">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Active
                        </Badge>
                      ) : (
                        <Badge className="bg-red-500/20 text-red-400">
                          <XCircle className="w-3 h-3 mr-1" />
                          Revoked
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(k.created_at).toLocaleDateString('id-ID')}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString('id-ID') : 'Belum pernah'}
                    </TableCell>
                    <TableCell className="text-right">
                      {k.is_active && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-red-500 hover:text-red-400 hover:bg-red-500/10"
                          onClick={() => setRevokeDialog({ open: true, keyId: k.id, keyLabel: k.label || k.prefix })}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Revoke Dialog */}
      <AlertDialog open={revokeDialog.open} onOpenChange={(open) => !open && setRevokeDialog({ open: false, keyId: null, keyLabel: null })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cabut API Key?</AlertDialogTitle>
            <AlertDialogDescription>
              Anda akan mencabut API key "{revokeDialog.keyLabel}". Key yang sudah dicabut tidak dapat digunakan lagi untuk autentikasi.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Batal</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => revokeKey(revokeDialog.keyId)}
            >
              Cabut Key
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
