import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Switch } from '../../components/ui/switch';
import { Skeleton } from '../../components/ui/skeleton';
import { toast } from 'sonner';
import { 
  Palette, 
  Check,
  Crown,
  Waves,
  Gem,
  Flame,
  Moon,
  Sun,
  Save,
  RotateCcw,
  Image,
  LayoutGrid,
  Eye,
  EyeOff
} from 'lucide-react';
import { cn } from '../../lib/utils';

const THEME_ICONS = {
  royal_gold: Crown,
  midnight_blue: Waves,
  emerald_green: Gem,
  crimson_red: Flame,
  purple_night: Moon,
  light_professional: Sun
};

const THEME_COLORS = {
  royal_gold: 'from-yellow-600 to-yellow-400',
  midnight_blue: 'from-blue-600 to-cyan-400',
  emerald_green: 'from-emerald-600 to-green-400',
  crimson_red: 'from-red-600 to-rose-400',
  purple_night: 'from-purple-600 to-violet-400',
  light_professional: 'from-blue-500 to-indigo-400'
};

export default function BrandingPage() {
  const { api, tenant, refreshTenant } = useAuth();
  const { theme, setTheme, themePresets } = useTheme();
  
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selectedTheme, setSelectedTheme] = useState(tenant?.theme_preset || 'royal_gold');
  const [primaryColor, setPrimaryColor] = useState(tenant?.branding?.primary_color || '');
  const [accentColor, setAccentColor] = useState(tenant?.branding?.accent_color || '');
  const [logoUrl, setLogoUrl] = useState(tenant?.branding?.logo_url || '');
  const [heroUrl, setHeroUrl] = useState(tenant?.branding?.hero_url || '');
  // Section toggles
  const [showHero, setShowHero] = useState(tenant?.branding?.show_hero !== false);
  const [showCategories, setShowCategories] = useState(tenant?.branding?.show_categories !== false);
  const [showFeatured, setShowFeatured] = useState(tenant?.branding?.show_featured !== false);

  useEffect(() => {
    if (tenant) {
      setSelectedTheme(tenant.theme_preset || 'royal_gold');
      setPrimaryColor(tenant.branding?.primary_color || '');
      setAccentColor(tenant.branding?.accent_color || '');
      setLogoUrl(tenant.branding?.logo_url || '');
      setHeroUrl(tenant.branding?.hero_url || '');
      setShowHero(tenant.branding?.show_hero !== false);
      setShowCategories(tenant.branding?.show_categories !== false);
      setShowFeatured(tenant.branding?.show_featured !== false);
    }
  }, [tenant]);

  const handleThemePreview = (themeKey) => {
    setSelectedTheme(themeKey);
    setTheme(themeKey);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put(`/tenants/${tenant.id}`, {
        theme_preset: selectedTheme,
        branding: {
          primary_color: primaryColor || null,
          accent_color: accentColor || null,
          logo_url: logoUrl || null,
          hero_url: heroUrl || null,
          show_hero: showHero,
          show_categories: showCategories,
          show_featured: showFeatured
        }
      });
      // Refresh tenant data to propagate changes
      if (refreshTenant) {
        await refreshTenant();
      }
      toast.success('Pengaturan branding berhasil disimpan!');
    } catch (err) {
      toast.error('Gagal menyimpan pengaturan');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    if (tenant) {
      setSelectedTheme(tenant.theme_preset || 'royal_gold');
      setTheme(tenant.theme_preset || 'royal_gold');
      setPrimaryColor(tenant.branding?.primary_color || '');
      setAccentColor(tenant.branding?.accent_color || '');
      setLogoUrl(tenant.branding?.logo_url || '');
      setHeroUrl(tenant.branding?.hero_url || '');
      setShowHero(tenant.branding?.show_hero !== false);
      setShowCategories(tenant.branding?.show_categories !== false);
      setShowFeatured(tenant.branding?.show_featured !== false);
    }
  };

  return (
    <div className="space-y-6" data-testid="branding-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Branding & Tema</h1>
          <p className="text-muted-foreground mt-1">
            Sesuaikan tampilan operator Anda
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleReset} data-testid="reset-branding-btn">
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </Button>
          <Button onClick={handleSave} disabled={saving} data-testid="save-branding-btn">
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Menyimpan...' : 'Simpan'}
          </Button>
        </div>
      </div>

      {/* Theme Selection */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="w-5 h-5 text-primary" />
            Preset Tema
          </CardTitle>
          <CardDescription>
            Pilih tema preset untuk operator Anda. Perubahan langsung terlihat.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Object.entries(themePresets).map(([key, preset]) => {
              const Icon = THEME_ICONS[key] || Palette;
              const isSelected = selectedTheme === key;
              
              return (
                <button
                  key={key}
                  onClick={() => handleThemePreview(key)}
                  className={cn(
                    "relative p-4 rounded-xl border-2 transition-all duration-300",
                    "flex flex-col items-center gap-3 text-center",
                    "hover:scale-105",
                    isSelected 
                      ? "border-primary bg-primary/10 glow-primary" 
                      : "border-border bg-card hover:border-primary/50"
                  )}
                  data-testid={`theme-${key}`}
                >
                  {isSelected && (
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center">
                      <Check className="w-4 h-4 text-primary-foreground" />
                    </div>
                  )}
                  <div className={cn(
                    "w-12 h-12 rounded-xl flex items-center justify-center",
                    `bg-gradient-to-br ${THEME_COLORS[key]}`
                  )}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>
                  <span className="text-sm font-medium">{preset.name}</span>
                  <span className="text-xs text-muted-foreground capitalize">
                    {preset.mode} mode
                  </span>
                </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Custom Colors */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle>Warna Kustom</CardTitle>
          <CardDescription>
            Override warna tema dengan warna brand Anda (opsional)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label htmlFor="primaryColor">Warna Primer</Label>
              <div className="flex gap-2">
                <Input
                  id="primaryColor"
                  type="text"
                  placeholder="#FFD700"
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  data-testid="input-primary-color"
                />
                <Input
                  type="color"
                  value={primaryColor || '#FFD700'}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="w-14 p-1 h-10"
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="accentColor">Warna Aksen</Label>
              <div className="flex gap-2">
                <Input
                  id="accentColor"
                  type="text"
                  placeholder="#B8860B"
                  value={accentColor}
                  onChange={(e) => setAccentColor(e.target.value)}
                  data-testid="input-accent-color"
                />
                <Input
                  type="color"
                  value={accentColor || '#B8860B'}
                  onChange={(e) => setAccentColor(e.target.value)}
                  className="w-14 p-1 h-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Logo Upload */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Image className="w-5 h-5 text-primary" />
            Logo & Hero Image
          </CardTitle>
          <CardDescription>
            Masukkan URL logo dan gambar hero untuk branding operator
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="logoUrl">URL Logo</Label>
                <Input
                  id="logoUrl"
                  type="url"
                  placeholder="https://example.com/logo.svg"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  data-testid="input-logo-url"
                />
              </div>
              {logoUrl && (
                <div className="p-4 bg-muted/30 rounded-xl">
                  <p className="text-xs text-muted-foreground mb-2">Pratinjau Logo:</p>
                  <img 
                    src={logoUrl} 
                    alt="Logo preview" 
                    className="h-12 object-contain"
                    onError={(e) => e.target.style.display = 'none'}
                  />
                </div>
              )}
            </div>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="heroUrl">URL Hero Image</Label>
                <Input
                  id="heroUrl"
                  type="url"
                  placeholder="https://example.com/hero-banner.jpg"
                  value={heroUrl}
                  onChange={(e) => setHeroUrl(e.target.value)}
                  data-testid="input-hero-url"
                />
              </div>
              {heroUrl && (
                <div className="p-4 bg-muted/30 rounded-xl">
                  <p className="text-xs text-muted-foreground mb-2">Pratinjau Hero:</p>
                  <img 
                    src={heroUrl} 
                    alt="Hero preview" 
                    className="w-full h-24 object-cover rounded-lg"
                    onError={(e) => e.target.style.display = 'none'}
                  />
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section Toggles - Home Content Control */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LayoutGrid className="w-5 h-5 text-primary" />
            Kontrol Konten Home
          </CardTitle>
          <CardDescription>
            Aktifkan atau nonaktifkan section di halaman home player
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                {showHero ? (
                  <Eye className="w-5 h-5 text-green-500" />
                ) : (
                  <EyeOff className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">Hero Section</p>
                  <p className="text-xs text-muted-foreground">Banner utama dengan saldo dan tombol deposit</p>
                </div>
              </div>
              <Switch
                checked={showHero}
                onCheckedChange={setShowHero}
                data-testid="toggle-hero"
              />
            </div>
            
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                {showCategories ? (
                  <Eye className="w-5 h-5 text-green-500" />
                ) : (
                  <EyeOff className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">Categories Row</p>
                  <p className="text-xs text-muted-foreground">Baris kategori game (Slots, Live, Table, dll)</p>
                </div>
              </div>
              <Switch
                checked={showCategories}
                onCheckedChange={setShowCategories}
                data-testid="toggle-categories"
              />
            </div>
            
            <div className="flex items-center justify-between p-4 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
              <div className="flex items-center gap-3">
                {showFeatured ? (
                  <Eye className="w-5 h-5 text-green-500" />
                ) : (
                  <EyeOff className="w-5 h-5 text-muted-foreground" />
                )}
                <div>
                  <p className="font-medium">Featured Games</p>
                  <p className="text-xs text-muted-foreground">Section Hot Games dan game unggulan</p>
                </div>
              </div>
              <Switch
                checked={showFeatured}
                onCheckedChange={setShowFeatured}
                data-testid="toggle-featured"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
