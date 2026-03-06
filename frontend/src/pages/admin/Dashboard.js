import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Skeleton } from '../../components/ui/skeleton';
import { Building2, Users, Gamepad2, Receipt } from 'lucide-react';

export default function SuperAdminDashboard() {
  const { api } = useAuth();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [recentTenants, setRecentTenants] = useState([]);
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    const run = async () => {
      try {
        const [statsRes, tenantsRes, logsRes] = await Promise.all([
          api.get('/stats/global'),
          api.get('/admin/tenants'),
          api.get('/admin/audit-logs'),
        ]);
        setStats(statsRes.data);
        setRecentTenants((tenantsRes.data || []).slice(0, 5));
        setLogs((logsRes.data || []).slice(0, 8));
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  const cards = [
    ['Tenants', stats?.total_tenants || 0, Building2],
    ['Players', stats?.total_players || 0, Users],
    ['Games', stats?.total_games || 0, Gamepad2],
    ['Transactions', stats?.total_transactions || 0, Receipt],
  ];

  if (loading) return <Skeleton className="h-56 w-full" />;

  return (
    <div className="space-y-6" data-testid="super-admin-dashboard">
      <h1 className="text-2xl font-bold">Super Admin Console</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cards.map(([title, value, Icon]) => (
          <Card key={title} className="glass-card">
            <CardContent className="py-5 flex items-center justify-between">
              <div><p className="text-xs text-muted-foreground">{title}</p><p className="text-2xl font-bold">{value}</p></div>
              <Icon className="w-5 h-5 text-primary" />
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="glass-card">
          <CardHeader><CardTitle>Recent Tenants</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!recentTenants.length && <p className="text-sm text-muted-foreground">No tenants yet.</p>}
            {recentTenants.map((tenant) => (
              <div key={tenant.id} className="p-3 rounded-lg border bg-card/60 flex items-center justify-between">
                <div>
                  <p className="font-medium">{tenant.name}</p>
                  <p className="text-xs text-muted-foreground">{tenant.slug}</p>
                </div>
                <span className="text-xs uppercase text-muted-foreground">{tenant.status || (tenant.is_active ? 'active' : 'suspended')}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader><CardTitle>Recent Audit Logs</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {!logs.length && <p className="text-sm text-muted-foreground">No activity yet.</p>}
            {logs.map((log) => (
              <div key={log.id} className="p-3 rounded-lg border bg-card/60">
                <p className="text-sm font-medium">{log.action}</p>
                <p className="text-xs text-muted-foreground">{log.target_type}:{log.target_id}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
