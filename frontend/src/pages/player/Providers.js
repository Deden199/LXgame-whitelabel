import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, ArrowLeft, Building2, Gamepad2, List, RefreshCw, Search, Sparkles, Star } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Badge } from '../../components/ui/badge';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { cn } from '../../lib/utils';
import { EmptyIllustration, GameThumbnail, ProviderLogoBadge } from '../../components/catalog/CatalogMedia';

export default function PlayerProvidersPage() {
  const { api } = useAuth();
  const [providers, setProviders] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('count');
  const [selectedProviderCode, setSelectedProviderCode] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [providersResponse, gamesResponse] = await Promise.all([api.get('/providers'), api.get('/games')]);
      setProviders(providersResponse.data || []);
      setGames(gamesResponse.data || []);
    } catch (requestError) {
      console.error('Failed to fetch providers data', requestError);
      setError(requestError.response?.data?.detail || 'Failed to load providers.');
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredProviders = useMemo(() => {
    const query = search.trim().toLowerCase();
    const results = providers.filter((provider) => {
      if (!query) return true;
      return [provider.name, provider.code, provider.slug].some((value) => String(value || '').toLowerCase().includes(query));
    });
    results.sort((left, right) => {
      if (sortBy === 'az') return left.name.localeCompare(right.name);
      return (right.gameCount || 0) - (left.gameCount || 0);
    });
    return results;
  }, [providers, search, sortBy]);

  const selectedProvider = useMemo(
    () => providers.find((provider) => provider.code === selectedProviderCode || provider.slug === selectedProviderCode),
    [providers, selectedProviderCode]
  );

  const selectedProviderGames = useMemo(
    () => games.filter((game) => game.provider_code === selectedProviderCode || game.provider_slug === selectedProviderCode),
    [games, selectedProviderCode]
  );

  const categoryChips = useMemo(() => {
    const source = selectedProvider ? selectedProvider.categories || [] : Array.from(new Set(providers.flatMap((provider) => provider.categories || [])));
    return source.slice(0, 8);
  }, [providers, selectedProvider]);

  const launchGame = async (game) => {
    try {
      const response = await api.post(`/games/${game.id}/launch`);
      if (response.data?.launch_url) {
        window.open(response.data.launch_url, '_blank', 'noopener,noreferrer');
        toast.success(`${game.name} opened in a new tab.`);
      } else {
        toast.info(`${game.name} launch response received.`);
      }
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : detail?.message || 'Game launch is temporarily unavailable.';
      toast.error(message);
    }
  };

  if (loading) {
    return (
      <div className="player-content-container space-y-4" data-testid="providers-page">
        <Skeleton className="h-9 w-48" />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {[...Array(8)].map((_, index) => <Skeleton key={index} className="h-32 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="player-content-container space-y-4" data-testid="providers-page">
      <section className="rounded-2xl border border-border/50 bg-card/55 p-4 backdrop-blur-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Providers</h1>
            <p className="text-sm text-muted-foreground">{providers.length.toLocaleString()} providers available</p>
          </div>
          <Button variant="outline" className="h-10 rounded-full" onClick={fetchData} data-testid="providers-refresh-button">
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>

        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search providers"
              className="h-10 rounded-full border-border/60 bg-card/70 pl-10"
            />
          </div>
          <Button
            variant={sortBy === 'count' ? 'secondary' : 'outline'}
            className={cn('h-10 rounded-full px-4 text-sm', sortBy === 'count' && 'border-primary/30 bg-primary/10 text-primary')}
            onClick={() => setSortBy('count')}
          >
            Most games
          </Button>
          <Button
            variant={sortBy === 'az' ? 'secondary' : 'outline'}
            className={cn('h-10 rounded-full px-4 text-sm', sortBy === 'az' && 'border-primary/30 bg-primary/10 text-primary')}
            onClick={() => setSortBy('az')}
          >
            <List className="mr-2 h-4 w-4" />
            A–Z
          </Button>
        </div>

        {categoryChips.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {categoryChips.map((category) => (
              <Badge key={category} variant="outline" className="rounded-full border-border/60 px-3 py-1 text-[11px] capitalize">
                {category}
              </Badge>
            ))}
          </div>
        ) : null}
      </section>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Couldn’t load providers</AlertTitle>
          <AlertDescription className="space-y-3">
            <p>{error}</p>
            <Button variant="outline" size="sm" onClick={fetchData}>Retry</Button>
          </AlertDescription>
        </Alert>
      ) : null}

      {selectedProvider ? (
        <section className="space-y-4" data-testid="provider-detail-panel">
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="ghost" className="h-10 rounded-full px-3" onClick={() => setSelectedProviderCode('')} data-testid="provider-detail-back-button">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to providers
            </Button>
            <ProviderLogoBadge provider={selectedProvider} className="h-14 w-14 rounded-2xl" testId={`provider-logo-img-${selectedProvider.slug || selectedProvider.code}`} />
            <div>
              <h2 className="text-xl font-semibold">{selectedProvider.name}</h2>
              <p className="text-sm text-muted-foreground">{selectedProvider.gameCount} games • {selectedProvider.code}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {(selectedProvider.categories || []).map((category) => (
              <Badge key={category} variant="outline" className="rounded-full border-border/60 px-3 py-1 text-[11px] capitalize">{category}</Badge>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {selectedProviderGames.map((game) => (
              <Card key={game.id} className="solid-card overflow-hidden rounded-2xl border-border/50 transition-transform hover:-translate-y-0.5">
                <div className="aspect-[16/10] overflow-hidden">
                  <GameThumbnail game={game} className="h-full w-full object-cover" imageTestId={`game-thumbnail-img-${game.id}`} fallbackTestId={`game-thumbnail-fallback-${game.id}`} />
                </div>
                <CardContent className="space-y-3 p-4">
                  <div>
                    <h3 className="line-clamp-1 text-base font-semibold" data-testid={`provider-game-${game.id}`}>{game.name}</h3>
                    <p className="text-sm text-muted-foreground">{game.category} • {game.provider_name}</p>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex flex-wrap gap-2">
                      {game.is_hot ? <Badge className="bg-primary/15 text-primary">Hot</Badge> : null}
                      {game.is_new ? <Badge className="bg-emerald-500/10 text-emerald-300">New</Badge> : null}
                      {game.is_popular ? <Badge className="bg-sky-500/10 text-sky-300">Popular</Badge> : null}
                    </div>
                    <Button size="sm" className="rounded-full" onClick={() => launchGame(game)}>Play</Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      ) : filteredProviders.length === 0 ? (
        <div className="solid-card flex flex-col items-start gap-2 rounded-2xl p-6">
          <EmptyIllustration />
          <h3 className="text-base font-semibold">No providers found</h3>
          <p className="text-sm text-muted-foreground">Try another search term.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {filteredProviders.map((provider) => (
            <Card
              key={provider.code}
              className="solid-card cursor-pointer rounded-2xl border-border/50 transition-transform hover:-translate-y-0.5 hover:border-primary/25"
              onClick={() => setSelectedProviderCode(provider.code)}
              data-testid={`provider-card-${provider.code}`}
            >
              <CardContent className="flex items-center gap-4 p-4">
                <ProviderLogoBadge provider={provider} className="h-14 w-14 rounded-2xl" testId={`provider-logo-img-${provider.slug || provider.code}`} />
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="truncate text-base font-semibold" data-testid={`provider-name-${provider.code}`}>{provider.name}</h3>
                      <p className="text-sm text-muted-foreground" data-testid={`provider-game-count-${provider.code}`}>{provider.gameCount} games</p>
                    </div>
                    <Building2 className="mt-1 h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {(provider.categories || []).slice(0, 3).map((category) => (
                      <Badge key={category} variant="outline" className="rounded-full border-border/60 px-2 py-0.5 text-[10px] capitalize">{category}</Badge>
                    ))}
                    {(provider.categories || []).length > 3 ? <Badge variant="outline" className="rounded-full border-border/60 px-2 py-0.5 text-[10px]">+{provider.categories.length - 3}</Badge> : null}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
