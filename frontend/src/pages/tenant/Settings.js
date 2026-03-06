import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { Switch } from '../../components/ui/switch';
import { Skeleton } from '../../components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';
import {
  Globe,
  Search,
  Code,
  Plus,
  Trash2,
  Save,
  AlertTriangle,
  ExternalLink,
  Info
} from 'lucide-react';

export default function OperatorSettingsPage() {
  const { api, tenant } = useAuth();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState('domain');
  
  // Local state for editing
  const [domain, setDomain] = useState({
    primary_domain: '',
    allowed_domains: [],
    enforce_domain: false
  });
  const [seo, setSeo] = useState({
    meta_title: '',
    meta_description: '',
    meta_keywords: '',
    og_title: '',
    og_description: '',
    og_image_url: '',
    favicon_url: '',
    robots_index: true,
    canonical_base_url: ''
  });
  const [customHeader, setCustomHeader] = useState({
    custom_head_html: '',
    custom_body_html: '',
    enable_custom_html: false
  });
  const [newDomain, setNewDomain] = useState('');

  const fetchSettings = async () => {
    try {
      const res = await api.get('/operator/settings');
      setSettings(res.data);
      
      // Initialize local state
      if (res.data.domain) setDomain(res.data.domain);
      if (res.data.seo) setSeo(res.data.seo);
      if (res.data.custom_header) setCustomHeader(res.data.custom_header);
    } catch (err) {
      console.error('Failed to fetch settings:', err);
      toast.error('Gagal memuat pengaturan');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (section) => {
    setSaving(true);
    try {
      const payload = {};
      if (section === 'domain') payload.domain = domain;
      if (section === 'seo') payload.seo = seo;
      if (section === 'custom_header') payload.custom_header = customHeader;
      
      await api.put('/operator/settings', payload);
      toast.success('Pengaturan berhasil disimpan');
      fetchSettings();
    } catch (err) {
      toast.error('Gagal menyimpan pengaturan');
    } finally {
      setSaving(false);
    }
  };

  const addAllowedDomain = () => {
    if (newDomain && !domain.allowed_domains.includes(newDomain)) {
      setDomain({
        ...domain,
        allowed_domains: [...domain.allowed_domains, newDomain]
      });
      setNewDomain('');
    }
  };

  const removeAllowedDomain = (d) => {
    setDomain({
      ...domain,
      allowed_domains: domain.allowed_domains.filter(x => x !== d)
    });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="operator-settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Operator Settings</h1>
        <p className="text-muted-foreground mt-1">
          Konfigurasi domain, SEO, dan custom scripts untuk {tenant?.name || 'tenant Anda'}
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="domain" className="flex items-center gap-2">
            <Globe className="w-4 h-4" />
            Domain
          </TabsTrigger>
          <TabsTrigger value="seo" className="flex items-center gap-2">
            <Search className="w-4 h-4" />
            SEO
          </TabsTrigger>
          <TabsTrigger value="custom" className="flex items-center gap-2">
            <Code className="w-4 h-4" />
            Custom Header
          </TabsTrigger>
        </TabsList>

        {/* Domain Tab */}
        <TabsContent value="domain">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="w-5 h-5" />
                Pengaturan Domain
              </CardTitle>
              <CardDescription>
                Konfigurasi custom domain untuk platform Anda
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* DNS Instructions */}
              <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
                <div className="flex items-start gap-3">
                  <Info className="w-5 h-5 text-blue-400 mt-0.5" />
                  <div>
                    <p className="font-medium text-blue-400">Instruksi DNS</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Untuk menggunakan custom domain, tambahkan CNAME record berikut di DNS Anda:
                    </p>
                    <code className="block mt-2 p-2 bg-black/30 rounded text-sm">
                      CNAME your-domain.com → looxgame.com
                    </code>
                  </div>
                </div>
              </div>

              {/* Primary Domain */}
              <div className="space-y-2">
                <Label>Primary Domain</Label>
                <Input
                  placeholder="casino.example.com"
                  value={domain.primary_domain || ''}
                  onChange={(e) => setDomain({ ...domain, primary_domain: e.target.value })}
                />
                <p className="text-sm text-muted-foreground">
                  Domain utama untuk platform Anda
                </p>
              </div>

              {/* Allowed Domains */}
              <div className="space-y-2">
                <Label>Allowed Domains</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Tambah domain..."
                    value={newDomain}
                    onChange={(e) => setNewDomain(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && addAllowedDomain()}
                  />
                  <Button variant="outline" onClick={addAllowedDomain}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex flex-wrap gap-2 mt-2">
                  {domain.allowed_domains.map((d) => (
                    <div
                      key={d}
                      className="flex items-center gap-2 px-3 py-1 rounded-full bg-muted"
                    >
                      <span className="text-sm">{d}</span>
                      <button
                        onClick={() => removeAllowedDomain(d)}
                        className="text-muted-foreground hover:text-red-400"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Enforce Domain */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div>
                  <Label>Enforce Domain</Label>
                  <p className="text-sm text-muted-foreground">
                    Blok akses dari domain yang tidak terdaftar
                  </p>
                </div>
                <Switch
                  checked={domain.enforce_domain}
                  onCheckedChange={(checked) => setDomain({ ...domain, enforce_domain: checked })}
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => handleSave('domain')} disabled={saving}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Menyimpan...' : 'Simpan Domain Settings'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* SEO Tab */}
        <TabsContent value="seo">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-5 h-5" />
                Pengaturan SEO
              </CardTitle>
              <CardDescription>
                Optimasi meta tags untuk search engine dan social sharing
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Basic Meta */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Meta Title</Label>
                  <Input
                    placeholder="Brand Name - Best Online Casino"
                    value={seo.meta_title || ''}
                    onChange={(e) => setSeo({ ...seo, meta_title: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Meta Keywords</Label>
                  <Input
                    placeholder="casino, slots, gaming"
                    value={seo.meta_keywords || ''}
                    onChange={(e) => setSeo({ ...seo, meta_keywords: e.target.value })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Meta Description</Label>
                <Textarea
                  placeholder="Deskripsi singkat tentang platform Anda..."
                  value={seo.meta_description || ''}
                  onChange={(e) => setSeo({ ...seo, meta_description: e.target.value })}
                  rows={3}
                />
              </div>

              {/* Open Graph */}
              <div className="pt-4 border-t">
                <h4 className="font-medium mb-4 flex items-center gap-2">
                  <ExternalLink className="w-4 h-4" />
                  Open Graph (Social Sharing)
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>OG Title</Label>
                    <Input
                      placeholder="Title untuk social sharing"
                      value={seo.og_title || ''}
                      onChange={(e) => setSeo({ ...seo, og_title: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>OG Image URL</Label>
                    <Input
                      placeholder="https://..."
                      value={seo.og_image_url || ''}
                      onChange={(e) => setSeo({ ...seo, og_image_url: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-2 mt-4">
                  <Label>OG Description</Label>
                  <Textarea
                    placeholder="Deskripsi untuk social sharing..."
                    value={seo.og_description || ''}
                    onChange={(e) => setSeo({ ...seo, og_description: e.target.value })}
                    rows={2}
                  />
                </div>
              </div>

              {/* Other Settings */}
              <div className="pt-4 border-t space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Favicon URL</Label>
                    <Input
                      placeholder="https://..."
                      value={seo.favicon_url || ''}
                      onChange={(e) => setSeo({ ...seo, favicon_url: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Canonical Base URL</Label>
                    <Input
                      placeholder="https://yourdomain.com"
                      value={seo.canonical_base_url || ''}
                      onChange={(e) => setSeo({ ...seo, canonical_base_url: e.target.value })}
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                  <div>
                    <Label>Allow Search Engine Indexing</Label>
                    <p className="text-sm text-muted-foreground">
                      Aktifkan robots index untuk mesin pencari
                    </p>
                  </div>
                  <Switch
                    checked={seo.robots_index}
                    onCheckedChange={(checked) => setSeo({ ...seo, robots_index: checked })}
                  />
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => handleSave('seo')} disabled={saving}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Menyimpan...' : 'Simpan SEO Settings'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* Custom Header Tab */}
        <TabsContent value="custom">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="w-5 h-5" />
                Custom Header Scripts
              </CardTitle>
              <CardDescription>
                Tambahkan custom HTML/scripts ke head atau body
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Warning */}
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5" />
                  <div>
                    <p className="font-medium text-yellow-400">Peringatan</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Custom scripts dapat mempengaruhi performa dan keamanan platform. 
                      Operator bertanggung jawab penuh atas scripts yang ditambahkan.
                    </p>
                  </div>
                </div>
              </div>

              {/* Enable Toggle */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                <div>
                  <Label>Enable Custom HTML</Label>
                  <p className="text-sm text-muted-foreground">
                    Aktifkan injection custom HTML/scripts
                  </p>
                </div>
                <Switch
                  checked={customHeader.enable_custom_html}
                  onCheckedChange={(checked) => setCustomHeader({ ...customHeader, enable_custom_html: checked })}
                />
              </div>

              {/* Head HTML */}
              <div className="space-y-2">
                <Label>Custom &lt;head&gt; HTML</Label>
                <Textarea
                  placeholder="<!-- Analytics, tracking scripts, etc -->"
                  value={customHeader.custom_head_html || ''}
                  onChange={(e) => setCustomHeader({ ...customHeader, custom_head_html: e.target.value })}
                  rows={6}
                  className="font-mono text-sm"
                  disabled={!customHeader.enable_custom_html}
                />
                <p className="text-sm text-muted-foreground">
                  Contoh: Google Analytics, Facebook Pixel, custom CSS
                </p>
              </div>

              {/* Body HTML */}
              <div className="space-y-2">
                <Label>Custom &lt;body&gt; HTML</Label>
                <Textarea
                  placeholder="<!-- Chat widgets, noscript tags, etc -->"
                  value={customHeader.custom_body_html || ''}
                  onChange={(e) => setCustomHeader({ ...customHeader, custom_body_html: e.target.value })}
                  rows={6}
                  className="font-mono text-sm"
                  disabled={!customHeader.enable_custom_html}
                />
                <p className="text-sm text-muted-foreground">
                  Contoh: Chat widget, noscript fallbacks
                </p>
              </div>
            </CardContent>
            <CardFooter>
              <Button onClick={() => handleSave('custom_header')} disabled={saving}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Menyimpan...' : 'Simpan Custom Header'}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
