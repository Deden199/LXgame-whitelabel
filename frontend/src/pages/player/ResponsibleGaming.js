import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Skeleton } from '../../components/ui/skeleton';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { toast } from 'sonner';
import {
  Shield,
  Clock,
  DollarSign,
  Save,
  AlertTriangle,
  CheckCircle2,
  Bell,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';

export default function ResponsibleGamingPage() {
  const { api, updateUserPreferences } = useAuth();
  const { formatAppMoney } = useCurrency();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    deposit_limit: null,
    loss_limit_daily: '',
    wager_limit_daily: '',
    self_exclusion_days: '0',
    self_exclusion_until: null,
    session_reminder_enabled: true,
    preferred_currency: 'IDR',
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await api.get('/player/stats');
      setSettings({
        deposit_limit: response.data.deposit_limit || '',
        loss_limit_daily: response.data.loss_limit_daily || '',
        wager_limit_daily: response.data.wager_limit_daily || '',
        self_exclusion_until: response.data.self_exclusion_until || null,
        self_exclusion_days: '0',
        session_reminder_enabled: response.data.session_reminder_enabled ?? true,
        preferred_currency: response.data.preferred_currency || 'IDR',
      });
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const exclusionDays = parseInt(settings.self_exclusion_days || '0', 10);
      const selfExclusionUntil = exclusionDays > 0 ? new Date(Date.now() + exclusionDays * 24 * 60 * 60 * 1000).toISOString() : null;
      const payload = {
        deposit_limit: settings.deposit_limit ? parseFloat(settings.deposit_limit) : null,
        loss_limit_daily: settings.loss_limit_daily ? parseFloat(settings.loss_limit_daily) : null,
        wager_limit_daily: settings.wager_limit_daily ? parseFloat(settings.wager_limit_daily) : null,
        self_exclusion_until: selfExclusionUntil,
        session_reminder_enabled: settings.session_reminder_enabled,
        preferred_currency: settings.preferred_currency,
      };
      await api.put('/player/settings', payload);
      updateUserPreferences({ currency: settings.preferred_currency });
      toast.success('Pengaturan berhasil disimpan!');
    } catch (err) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message;
      toast.error(detail || 'Gagal menyimpan pengaturan');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="responsible-gaming-page">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="responsible-gaming-page">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Judi Bertanggung Jawab</h1>
        <p className="text-muted-foreground mt-1">Kelola batas dan alat keamanan bermain Anda</p>
      </div>

      <Card className="glass-card border-green-500/30">
        <CardContent className="pt-6">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-green-500/10">
              <Shield className="w-6 h-6 text-green-500" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-green-500" />
                <span className="font-semibold text-green-500">Alat Judi Bertanggung Jawab Aktif</span>
              </div>
              <p className="text-sm text-muted-foreground mt-1">Akun Anda memiliki fitur perlindungan pemain aktif</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-primary" />
              Batas Setoran Harian
            </CardTitle>
            <CardDescription>Tetapkan jumlah maksimum yang dapat Anda setor per hari</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="preferredCurrency">Mata Uang Default</Label>
              <Select
                value={settings.preferred_currency}
                onValueChange={(value) => setSettings({ ...settings, preferred_currency: value })}
              >
                <SelectTrigger id="preferredCurrency" data-testid="preferred-currency-select">
                  <SelectValue placeholder="Pilih mata uang" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="IDR">IDR</SelectItem>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="USDT">USDT</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="depositLimit">Setoran Harian Maksimum</Label>
              <p className="text-xs text-muted-foreground">Contoh: {formatAppMoney(100)}</p>
              <Input
                id="depositLimit"
                type="number"
                placeholder="Belum ada batas"
                value={settings.deposit_limit || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    deposit_limit: e.target.value,
                  })
                }
                min="0"
                step="100"
                data-testid="deposit-limit-input"
              />
            </div>

            <div className="grid grid-cols-4 gap-2">
              {[100, 500, 1000, 2000].map((amount) => (
                <Button
                  key={amount}
                  variant="outline"
                  size="sm"
                  onClick={() => setSettings({ ...settings, deposit_limit: amount.toString() })}
                  className={cn(settings.deposit_limit == amount && 'bg-primary/10 border-primary')}
                >
                  {formatAppMoney(amount)}
                </Button>
              ))}
            </div>

            <Button variant="outline" size="sm" onClick={() => setSettings({ ...settings, deposit_limit: '' })} className="w-full">
              Hapus Batas
            </Button>

            <div className="space-y-2">
              <Label htmlFor="wagerLimit">Batas Wager Harian</Label>
              <Input id="wagerLimit" type="number" min="0" value={settings.wager_limit_daily || ''} onChange={(e) => setSettings({ ...settings, wager_limit_daily: e.target.value })} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="lossLimit">Batas Loss Harian</Label>
              <Input id="lossLimit" type="number" min="0" value={settings.loss_limit_daily || ''} onChange={(e) => setSettings({ ...settings, loss_limit_daily: e.target.value })} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="selfExclusion">Self Exclusion</Label>
              <Select value={settings.self_exclusion_days} onValueChange={(value) => setSettings({ ...settings, self_exclusion_days: value })}>
                <SelectTrigger id="selfExclusion"><SelectValue placeholder="Pilih durasi" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">Tidak aktif</SelectItem>
                  <SelectItem value="7">7 hari</SelectItem>
                  <SelectItem value="30">30 hari</SelectItem>
                  <SelectItem value="90">90 hari</SelectItem>
                </SelectContent>
              </Select>
              {settings.self_exclusion_until && <p className="text-xs text-red-400">Aktif sampai: {new Date(settings.self_exclusion_until).toLocaleString('id-ID')}</p>}
            </div>

            <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-yellow-500 mt-0.5" />
                <p className="text-xs text-muted-foreground">
                  Perubahan batas setoran berlaku segera. Menurunkan batas berlaku instan, tetapi menaikkan batas mungkin
                  memiliki periode pendinginan.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Pengingat Sesi
            </CardTitle>
            <CardDescription>Dapatkan notifikasi tentang durasi sesi bermain Anda</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30">
              <div className="flex items-center gap-3">
                <Bell className="w-5 h-5 text-primary" />
                <div>
                  <p className="font-medium">Pengingat Sesi</p>
                  <p className="text-sm text-muted-foreground">Ingatkan saya setiap 30 menit</p>
                </div>
              </div>
              <Switch
                checked={settings.session_reminder_enabled}
                onCheckedChange={(checked) =>
                  setSettings({
                    ...settings,
                    session_reminder_enabled: checked,
                  })
                }
                data-testid="session-reminder-switch"
              />
            </div>

            <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-start gap-2">
                <Clock className="w-4 h-4 text-blue-500 mt-0.5" />
                <div className="text-xs text-muted-foreground">
                  <p className="font-medium text-blue-500 mb-1">Cara kerjanya</p>
                  <p>
                    Ketika diaktifkan, Anda akan menerima pengingat lembut setelah 30 menit bermain, membantu Anda tetap
                    sadar berapa lama Anda bermain.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={saving} className="glow-primary">
          {saving ? (
            <>
              <Clock className="w-4 h-4 mr-2 animate-spin" />
              Menyimpan...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Simpan Pengaturan
            </>
          )}
        </Button>
      </div>

      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Butuh Bantuan?</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground mb-4">Jika Anda merasa perjudian Anda menjadi masalah, silakan hubungi dukungan:</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="font-medium">Hotline Bantuan Judi</p>
              <p className="text-muted-foreground">021-500-XXX (24 jam)</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="font-medium">Gamblers Anonymous Indonesia</p>
              <p className="text-muted-foreground">www.gamblersanonymous.org</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
