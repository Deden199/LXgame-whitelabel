import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Skeleton } from '../../components/ui/skeleton';

export default function SuperAdminTenantDetail() {
  const { id } = useParams();
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [adminForm, setAdminForm] = useState({ email: '', password: '', display_name: '' });

  const fetchTenant = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/tenants/${id}`);
      setData(res.data);
    } catch {
      toast.error('Failed to load tenant');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTenant(); }, [id]);

  const toggleStatus = async () => {
    const next = data?.tenant?.status === 'active' ? 'suspended' : 'active';
    try {
      await api.patch(`/admin/tenants/${id}`, { status: next });
      toast.success(`Tenant ${next}`);
      await fetchTenant();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Status update failed');
    }
  };

  const createAdmin = async (e) => {
    e.preventDefault();
    try {
      await api.post(`/admin/tenants/${id}/admins`, adminForm);
      toast.success('Tenant admin created');
      setAdminForm({ email: '', password: '', display_name: '' });
      await fetchTenant();
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Create tenant admin failed');
    }
  };

  if (loading) return <Skeleton className="h-56 w-full" />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">{data.tenant.name} <Badge variant={data.tenant.status === 'active' ? 'default' : 'secondary'}>{data.tenant.status}</Badge></CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-muted-foreground">Slug: {data.tenant.slug}</p>
          <Button onClick={toggleStatus} variant="outline">{data.tenant.status === 'active' ? 'Suspend' : 'Activate'} Tenant</Button>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader><CardTitle>Create Tenant Admin</CardTitle></CardHeader>
        <CardContent>
          <form className="grid md:grid-cols-4 gap-2" onSubmit={createAdmin}>
            <Input required placeholder="Name" value={adminForm.display_name} onChange={(e) => setAdminForm((s) => ({ ...s, display_name: e.target.value }))} />
            <Input required type="email" placeholder="Email" value={adminForm.email} onChange={(e) => setAdminForm((s) => ({ ...s, email: e.target.value }))} />
            <Input required type="password" placeholder="Password" value={adminForm.password} onChange={(e) => setAdminForm((s) => ({ ...s, password: e.target.value }))} />
            <Button type="submit">Create</Button>
          </form>
        </CardContent>
      </Card>

      <Card className="glass-card">
        <CardHeader><CardTitle>Tenant Admins</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {!data.admins.length && <div className="text-sm text-muted-foreground">No tenant admins.</div>}
          {data.admins.map((admin) => (
            <div key={admin.id} className="p-3 rounded-lg border bg-card/60 flex items-center justify-between">
              <div>
                <div className="font-medium">{admin.display_name}</div>
                <div className="text-xs text-muted-foreground">{admin.email}</div>
              </div>
              <Badge variant={admin.is_active ? 'default' : 'secondary'}>{admin.is_active ? 'active' : 'disabled'}</Badge>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}
