import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';

export default function SuperAdminTenants() {
  const { api } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tenants, setTenants] = useState([]);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: '', slug: '' });

  const fetchTenants = async () => {
    setLoading(true);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (status !== 'all') params.status = status;
      const res = await api.get('/admin/tenants', { params });
      setTenants(res.data);
    } catch {
      toast.error('Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTenants(); }, []);

  const filtered = useMemo(() => tenants, [tenants]);

  const onCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/admin/tenants', { ...form, slug: form.slug.toLowerCase().trim() });
      toast.success('Tenant created');
      setOpen(false);
      setForm({ name: '', slug: '' });
      await fetchTenants();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Create tenant failed');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Tenant Management</h1>
          <p className="text-muted-foreground">Create, search, and manage tenant status.</p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button>Create Tenant</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Tenant</DialogTitle></DialogHeader>
            <form className="space-y-3" onSubmit={onCreate}>
              <Input required placeholder="Tenant name" value={form.name} onChange={(e) => setForm((s) => ({ ...s, name: e.target.value }))} />
              <Input required placeholder="slug-example" value={form.slug} onChange={(e) => setForm((s) => ({ ...s, slug: e.target.value }))} />
              <Button className="w-full" type="submit">Create</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Card className="glass-card">
        <CardHeader className="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
          <CardTitle>Tenants</CardTitle>
          <div className="flex gap-2">
            <Input placeholder="Search name or slug" value={search} onChange={(e) => setSearch(e.target.value)} />
            <select className="bg-background border rounded-md px-3" value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
            <Button variant="secondary" onClick={fetchTenants}>Apply</Button>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? <Skeleton className="h-40 w-full" /> : (
            <div className="space-y-2">
              {!filtered.length && <div className="text-sm text-muted-foreground">No tenants found.</div>}
              {filtered.map((tenant) => (
                <div key={tenant.id} className="p-3 rounded-lg border bg-card/60 flex items-center justify-between">
                  <div>
                    <div className="font-medium">{tenant.name}</div>
                    <div className="text-xs text-muted-foreground">{tenant.slug} • {new Date(tenant.created_at).toLocaleString()}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={tenant.status === 'active' ? 'default' : 'secondary'}>{tenant.status}</Badge>
                    <Button size="sm" variant="outline" onClick={() => navigate(`/admin/tenants/${tenant.id}`)}>Open</Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
