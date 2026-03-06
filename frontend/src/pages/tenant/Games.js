import React, { useCallback, useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';
import { Skeleton } from '../../components/ui/skeleton';
import { Badge } from '../../components/ui/badge';
import { Switch } from '../../components/ui/switch';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { 
  Gamepad2, 
  Search,
  Filter,
  Server,
  Users,
  RefreshCw
} from 'lucide-react';

// Game thumbnail with error handling
const GameThumbnail = ({ src, alt, className }) => {
  const [error, setError] = React.useState(false);
  
  if (error || !src) {
    return (
      <div className={`${className} bg-gradient-to-br from-muted to-card flex items-center justify-center`}>
        <Gamepad2 className="w-8 h-8 text-muted-foreground/30" />
      </div>
    );
  }
  
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={() => setError(true)}
    />
  );
};

export default function TenantGamesPage() {
  const { api, tenant } = useAuth();
  const [games, setGames] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');

  const fetchData = useCallback(async () => {
    try {
      const params = {};
      if (categoryFilter !== 'all') params.category = categoryFilter;
      
      const [gamesRes, catRes] = await Promise.all([
        api.get('/games', { params }),
        api.get('/games/categories')
      ]);
      setGames(gamesRes.data);
      setCategories(catRes.data);
    } catch (err) {
      console.error('Failed to fetch games:', err);
    } finally {
      setLoading(false);
    }
  }, [api, categoryFilter]);

  useEffect(() => {
    fetchData();
  }, [tenant?.id, categoryFilter, fetchData]);

  const handleToggleGame = async (gameId, enabled) => {
    try {
      await api.put(`/games/${gameId}`, { is_enabled: enabled });
      setGames(games.map(g => g.id === gameId ? { ...g, is_enabled: enabled } : g));
      toast.success(`Permainan ${enabled ? 'diaktifkan' : 'dinonaktifkan'}`);
    } catch (err) {
      toast.error('Gagal memperbarui permainan');
    }
  };

  const filteredGames = games.filter(g =>
    g.name.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total: games.length,
    enabled: games.filter(g => g.is_enabled !== false).length,
    totalPlays: games.reduce((sum, g) => sum + (g.play_count || 0), 0)
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="tenant-games-page">
        <Skeleton className="h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="tenant-games-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Manajemen Permainan</h1>
          <p className="text-muted-foreground mt-1">
            {stats.enabled}/{stats.total} permainan aktif • {stats.totalPlays.toLocaleString('id-ID')} total dimainkan
          </p>
        </div>
        <Button 
          onClick={fetchData}
          variant="outline"
          className="gap-2"
          data-testid="refresh-catalog-btn"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh Catalog
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {categories.slice(0, 4).map((cat) => (
          <Card key={cat.name} className="glass-card">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10">
                  <Gamepad2 className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{cat.count}</p>
                  <p className="text-sm text-muted-foreground capitalize">{cat.name}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <Card className="glass-card">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Cari permainan..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                data-testid="search-games"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-[180px]" data-testid="filter-category">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Kategori" />
              </SelectTrigger>
              <SelectContent>
                {categories.map(cat => (
                  <SelectItem key={cat.name} value={cat.name} className="capitalize">
                    {cat.name} ({cat.count})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Games Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {filteredGames.map((game) => (
          <Card 
            key={game.id} 
            className={`glass-card overflow-hidden transition-all duration-300 ${
              game.is_enabled === false ? 'opacity-60' : ''
            }`}
          >
            <div className="aspect-video relative overflow-hidden">
              <GameThumbnail
                src={game.thumbnail_url}
                alt={game.name}
                className="w-full h-full object-cover"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
              <Badge 
                className="absolute top-2 left-2 capitalize text-[10px]"
                variant="secondary"
              >
                {game.category}
              </Badge>
              <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded bg-black/60 text-[9px] text-white/80 flex items-center gap-1">
                <Server className="w-3 h-3" />
                {game.provider_id}
              </div>
            </div>
            <CardContent className="p-4">
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="min-w-0">
                  <h3 className="font-semibold truncate">{game.name}</h3>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3" />
                      RTP {game.rtp}%
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="w-3 h-3" />
                      {(game.play_count || 0).toLocaleString()}
                    </span>
                  </div>
                </div>
                <Switch
                  checked={game.is_enabled !== false}
                  onCheckedChange={(checked) => handleToggleGame(game.id, checked)}
                  data-testid={`toggle-game-${game.id}`}
                />
              </div>
              <div className="flex flex-wrap gap-1">
                {game.tags?.map(tag => (
                  <Badge key={tag} variant="outline" className="text-[10px] capitalize">
                    {tag}
                  </Badge>
                ))}
                <Badge variant="outline" className="text-[10px] capitalize">
                  {game.volatility} vol
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
