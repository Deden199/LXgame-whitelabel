import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AlertCircle, ChevronLeft, ChevronRight, Clock, Flame, Gamepad2, Loader2, Play, RefreshCw, Search, Sparkles, Star, TriangleAlert, X, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../../context/AuthContext';
import { useCurrency } from '../../hooks/useCurrency';
import { cn } from '../../lib/utils';
import { Alert, AlertDescription, AlertTitle } from '../../components/ui/alert';
import { Button } from '../../components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import HeroBanner from '../../components/HeroBanner';
import PromoTicker from '../../components/PromoTicker';
import ProviderFilter from '../../components/ProviderFilter';
import { EmptyIllustration, GameThumbnail, ProviderLogoBadge } from '../../components/catalog/CatalogMedia';

const CATEGORY_ICONS = {
  all: Gamepad2,
  slots: Sparkles,
  live: Zap,
  table: Gamepad2,
  arcade: Flame,
  crash: TriangleAlert,
  fishing: Star,
  sports: Flame,
  lottery: Star,
  poker: Zap,
  other: Gamepad2,
};

const INITIAL_FETCH_ERROR = { games: '', metadata: '' };
const GAMES_PER_PAGE = 30;
const RECENTLY_PLAYED_KEY = 'looxgame_recently_played';
const MAX_RECENT_GAMES = 10;

// Helper to manage recently played games in localStorage
const getRecentlyPlayed = () => {
  try {
    const stored = localStorage.getItem(RECENTLY_PLAYED_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
};

const addToRecentlyPlayed = (game) => {
  try {
    const current = getRecentlyPlayed();
    const filtered = current.filter(g => g.id !== game.id);
    const updated = [{ 
      id: game.id, 
      name: game.name, 
      thumbnail_url: game.thumbnail_url,
      provider_code: game.provider_code,
      provider_name: game.provider_name,
      category: game.category,
      playedAt: Date.now() 
    }, ...filtered].slice(0, MAX_RECENT_GAMES);
    localStorage.setItem(RECENTLY_PLAYED_KEY, JSON.stringify(updated));
    return updated;
  } catch {
    return [];
  }
};

const GameCard = React.memo(function GameCard({ game, onLaunch, index = 0, blockedReason = '', compact = false }) {
  const providerLabel = game.provider_name || game.provider_code || 'Provider';
  const isBlocked = Boolean(blockedReason) || game.is_enabled === false || game.is_active === false;
  const badges = [
    game.is_hot ? { key: 'hot', label: 'Hot', className: 'bg-primary/15 text-primary border border-primary/25' } : null,
    game.is_new ? { key: 'new', label: 'New', className: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' } : null,
    game.is_popular ? { key: 'popular', label: 'Popular', className: 'bg-sky-500/10 text-sky-300 border border-sky-500/20' } : null,
  ].filter(Boolean);

  const handleClick = () => {
    if (isBlocked) {
      toast.error(blockedReason || 'This game is temporarily unavailable.');
      return;
    }
    onLaunch(game);
  };

  const loadingPriority = index < 8 ? 'eager' : 'lazy';

  return (
    <button
      type="button"
      className={cn('game-card cursor-pointer text-left', isBlocked && 'opacity-75 saturate-75')}
      onClick={handleClick}
      data-testid={`game-card-${game.id}`}
      data-index={Math.min(index, 11)}
    >
      <div className="relative aspect-[16/10] overflow-hidden rounded-t-[14px]">
        <GameThumbnail
          game={game}
          className="game-card-image h-full w-full object-cover"
          imageTestId={`game-thumbnail-img-${game.id}`}
          fallbackTestId={`game-thumbnail-fallback-${game.id}`}
          loading={loadingPriority}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
        <div className="game-card-overlay">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/90 shadow-lg">
            <Play className="ml-0.5 h-4 w-4 text-primary-foreground" />
          </div>
          <span className="mt-2 text-xs font-medium text-white/95">Play</span>
        </div>
        {!compact && badges.length > 0 ? (
          <div className="absolute right-2 top-2 flex flex-col gap-1">
            {badges.map((badge) => (
              <span
                key={badge.key}
                className={cn('rounded-md px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide', badge.className)}
                data-testid={`game-badge-${badge.key}-${game.id}`}
              >
                {badge.label}
              </span>
            ))}
          </div>
        ) : null}
        {isBlocked ? (
          <span className="absolute left-2 top-2 rounded-full border border-border/60 bg-background/85 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Unavailable
          </span>
        ) : null}
        <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between gap-2 rounded-full bg-black/55 px-2.5 py-1.5 backdrop-blur-sm">
          <div className="flex min-w-0 items-center gap-2">
            <ProviderLogoBadge provider={game} className="h-5 w-5 rounded-full border-white/10" testId={`provider-logo-img-${game.id}`} />
            <span className="truncate text-[11px] font-medium text-white/90">{providerLabel}</span>
          </div>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-white/70">{game.category}</span>
        </div>
      </div>
      <div className="game-card-title">
        <p className="line-clamp-2 text-sm font-medium text-foreground/95">{game.name}</p>
      </div>
    </button>
  );
});

// Search Autocomplete Component
function SearchAutocomplete({ value, onChange, onSelect, games, loading }) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const inputRef = useRef(null);
  const listRef = useRef(null);

  const suggestions = useMemo(() => {
    if (!value || value.length < 2) return [];
    const searchLower = value.toLowerCase();
    return games
      .filter(g => g.name.toLowerCase().includes(searchLower))
      .slice(0, 8);
  }, [value, games]);

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusedIndex(prev => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusedIndex(prev => Math.max(prev - 1, -1));
    } else if (e.key === 'Enter' && focusedIndex >= 0) {
      e.preventDefault();
      onSelect(suggestions[focusedIndex]);
      setShowSuggestions(false);
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  useEffect(() => {
    setFocusedIndex(-1);
  }, [value]);

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        ref={inputRef}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setShowSuggestions(true);
        }}
        onFocus={() => setShowSuggestions(true)}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        onKeyDown={handleKeyDown}
        placeholder="Search games..."
        className="h-10 rounded-full border-border/60 bg-card/70 pl-10 pr-10"
        data-testid="games-search-input"
        autoComplete="off"
      />
      {value ? (
        <button 
          type="button" 
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors" 
          onClick={() => { onChange(''); setShowSuggestions(false); }}
        >
          <X className="h-4 w-4" />
        </button>
      ) : null}
      
      {/* Autocomplete Dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <div 
          ref={listRef}
          className="search-autocomplete-dropdown"
          data-testid="search-autocomplete"
        >
          {suggestions.map((game, idx) => (
            <button
              key={game.id}
              type="button"
              className={cn(
                'search-autocomplete-item',
                focusedIndex === idx && 'search-autocomplete-item-focused'
              )}
              onClick={() => {
                onSelect(game);
                setShowSuggestions(false);
              }}
              onMouseEnter={() => setFocusedIndex(idx)}
            >
              <GameThumbnail 
                game={game} 
                className="h-10 w-16 rounded-lg object-cover flex-shrink-0" 
              />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-foreground truncate">{game.name}</p>
                <p className="text-xs text-muted-foreground">{game.provider_name || game.provider_code}</p>
              </div>
              <span className="text-[10px] uppercase text-muted-foreground bg-muted/50 px-2 py-0.5 rounded-full">
                {game.category}
              </span>
            </button>
          ))}
        </div>
      )}
      
      {/* Loading indicator */}
      {loading && value && (
        <div className="absolute right-10 top-1/2 -translate-y-1/2">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

// Recently Played Section
function RecentlyPlayedSection({ recentGames, allGames, onLaunch }) {
  const listRef = useRef(null);
  
  // Hydrate recent games with full data from allGames
  const hydratedRecent = useMemo(() => {
    return recentGames
      .map(recent => {
        const fullGame = allGames.find(g => g.id === recent.id);
        return fullGame || recent;
      })
      .filter(Boolean);
  }, [recentGames, allGames]);

  if (hydratedRecent.length === 0) return null;

  const scroll = (direction) => {
    listRef.current?.scrollBy({ left: direction * 200, behavior: 'smooth' });
  };

  return (
    <section className="horizontal-game-section" data-testid="section-recently-played">
      <div className="horizontal-section-header">
        <div className="flex items-center gap-2">
          <div className="section-icon-wrapper recently-played-icon">
            <Clock className="h-4 w-4 text-sky-400" />
          </div>
          <div>
            <h2 className="section-title">Recently Played</h2>
            <p className="section-subtitle">{hydratedRecent.length} games</p>
          </div>
        </div>
        <div className="hidden items-center gap-1.5 md:flex">
          <Button variant="outline" size="icon" className="h-7 w-7 rounded-full" onClick={() => scroll(-1)}>
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="icon" className="h-7 w-7 rounded-full" onClick={() => scroll(1)}>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div ref={listRef} className="horizontal-game-list">
        {hydratedRecent.map((game, index) => (
          <div key={game.id} className="horizontal-game-card-wrapper">
            <GameCard game={game} onLaunch={onLaunch} index={index} compact />
          </div>
        ))}
      </div>
    </section>
  );
}

function HorizontalGameSection({ title, icon: Icon, games, loading, onLaunch }) {
  const listRef = useRef(null);
  const scroll = (direction) => {
    listRef.current?.scrollBy({ left: direction * 280, behavior: 'smooth' });
  };

  return (
    <section className="horizontal-game-section" data-testid={`section-${title.toLowerCase().replace(/\s+/g, '-')}`}>
      <div className="horizontal-section-header">
        <div className="flex items-center gap-2">
          <div className="section-icon-wrapper">
            <Icon className="h-4 w-4 text-primary" />
          </div>
          <div>
            <h2 className="section-title">{title}</h2>
            <p className="section-subtitle">{games.length} games</p>
          </div>
        </div>
        <div className="hidden items-center gap-1.5 md:flex">
          <Button variant="outline" size="icon" className="h-7 w-7 rounded-full" onClick={() => scroll(-1)}>
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <Button variant="outline" size="icon" className="h-7 w-7 rounded-full" onClick={() => scroll(1)}>
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div ref={listRef} className="horizontal-game-list">
        {loading
          ? [...Array(6)].map((_, index) => (
              <div key={index} className="horizontal-game-card-wrapper">
                <Skeleton className="aspect-[16/10] rounded-xl" />
                <Skeleton className="mt-2 h-4 w-4/5" />
              </div>
            ))
          : games.map((game, index) => (
              <div key={game.id} className="horizontal-game-card-wrapper">
                <GameCard game={game} onLaunch={onLaunch} index={index} />
              </div>
            ))}
      </div>
    </section>
  );
}

export default function PlayerGamesPage() {
  const { api, user } = useAuth();
  const { formatAppMoney } = useCurrency();
  const [searchParams] = useSearchParams();
  const [games, setGames] = useState([]);
  const [providers, setProviders] = useState([]);
  const [categories, setCategories] = useState([]);
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const [debouncedSearch, setDebouncedSearch] = useState(searchParams.get('search') || '');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [providerFilter, setProviderFilter] = useState('all');
  const [tagFilter, setTagFilter] = useState('');
  const [loadingGames, setLoadingGames] = useState(true);
  const [loadingMeta, setLoadingMeta] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [fetchError, setFetchError] = useState(INITIAL_FETCH_ERROR);
  const [showGameDialog, setShowGameDialog] = useState(false);
  const [selectedGame, setSelectedGame] = useState(null);
  const [launchPreview, setLaunchPreview] = useState(null);
  const [launchingGameId, setLaunchingGameId] = useState('');
  const [recentlyPlayed, setRecentlyPlayed] = useState([]);
  
  // Infinite scroll state
  const [displayedCount, setDisplayedCount] = useState(GAMES_PER_PAGE);
  const [hasMore, setHasMore] = useState(true);
  const loadMoreRef = useRef(null);

  // Load recently played on mount
  useEffect(() => {
    setRecentlyPlayed(getRecentlyPlayed());
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedSearch(searchInput.trim()), 200);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  // Reset displayed count when filters change
  useEffect(() => {
    setDisplayedCount(GAMES_PER_PAGE);
    setHasMore(true);
  }, [categoryFilter, providerFilter, tagFilter, debouncedSearch]);

  const fetchMetadata = useCallback(async () => {
    setLoadingMeta(true);
    setFetchError((current) => ({ ...current, metadata: '' }));
    try {
      const [providersResponse, categoriesResponse] = await Promise.all([
        api.get('/providers'),
        api.get('/games/categories'),
      ]);
      setProviders(providersResponse.data || []);
      setCategories(categoriesResponse.data || []);
    } catch (error) {
      console.error('Failed to load metadata', error);
      setFetchError((current) => ({ ...current, metadata: error.response?.data?.detail || 'Failed to load providers and categories.' }));
    } finally {
      setLoadingMeta(false);
    }
  }, [api]);

  const fetchGames = useCallback(async () => {
    setLoadingGames(true);
    setFetchError((current) => ({ ...current, games: '' }));
    try {
      const params = {};
      if (categoryFilter !== 'all') params.category = categoryFilter;
      if (providerFilter !== 'all') params.provider = providerFilter;
      if (tagFilter) params.tag = tagFilter;
      if (debouncedSearch) params.search = debouncedSearch;
      const response = await api.get('/games', { params });
      setGames(response.data || []);
    } catch (error) {
      console.error('Failed to load games', error);
      setFetchError((current) => ({ ...current, games: error.response?.data?.detail || 'Failed to load games.' }));
    } finally {
      setLoadingGames(false);
    }
  }, [api, categoryFilter, providerFilter, tagFilter, debouncedSearch]);

  useEffect(() => {
    fetchMetadata();
  }, [fetchMetadata]);

  useEffect(() => {
    fetchGames();
  }, [fetchGames]);

  // Infinite scroll observer
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !loadingGames) {
          loadMoreGames();
        }
      },
      { threshold: 0.1, rootMargin: '100px' }
    );

    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loadingMore, loadingGames, displayedCount, games.length]);

  const loadMoreGames = useCallback(() => {
    if (displayedCount >= games.length) {
      setHasMore(false);
      return;
    }
    
    setLoadingMore(true);
    // Simulate small delay for smooth UX
    setTimeout(() => {
      setDisplayedCount(prev => Math.min(prev + GAMES_PER_PAGE, games.length));
      setLoadingMore(false);
    }, 300);
  }, [displayedCount, games.length]);

  const providerLookup = useMemo(() => {
    const lookup = new Map();
    providers.forEach((provider) => {
      lookup.set(provider.code, provider);
      lookup.set(provider.slug, provider);
    });
    return lookup;
  }, [providers]);

  const hydratedGames = useMemo(
    () => games.map((game) => ({ ...providerLookup.get(game.provider_code), ...game })),
    [games, providerLookup]
  );

  // Games to display (infinite scroll)
  const displayedGames = useMemo(
    () => hydratedGames.slice(0, displayedCount),
    [hydratedGames, displayedCount]
  );

  const hotGames = useMemo(() => hydratedGames.filter((game) => game.is_hot).slice(0, 12), [hydratedGames]);
  const newGames = useMemo(() => hydratedGames.filter((game) => game.is_new).slice(0, 12), [hydratedGames]);
  const popularGames = useMemo(() => hydratedGames.filter((game) => game.is_popular).slice(0, 12), [hydratedGames]);

  const pageCountLabel = useMemo(() => {
    const totalCategory = categories.find((category) => category.name === 'all')?.count || hydratedGames.length;
    if (hydratedGames.length === totalCategory) return `${totalCategory.toLocaleString()} games`;
    return `Showing ${hydratedGames.length.toLocaleString()} of ${totalCategory.toLocaleString()} games`;
  }, [categories, hydratedGames.length]);

  const clearFilters = () => {
    setSearchInput('');
    setCategoryFilter('all');
    setProviderFilter('all');
    setTagFilter('');
  };

  const launchGame = async (game) => {
    // Add to recently played
    const updatedRecent = addToRecentlyPlayed(game);
    setRecentlyPlayed(updatedRecent);
    
    setLaunchingGameId(game.id);
    try {
      const response = await api.post(`/games/${game.id}/launch`);
      setLaunchPreview(response.data || null);
      if (response.data?.launch_url) {
        window.open(response.data.launch_url, '_blank', 'noopener,noreferrer');
        toast.success(`${game.name} opened in a new tab.`);
      } else {
        setSelectedGame(game);
        setShowGameDialog(true);
        toast.success(`${game.name} is ready.`);
      }
    } catch (error) {
      const detail = error.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : detail?.message || 'Game launch is temporarily unavailable.';
      toast.error(message);
      setSelectedGame(game);
      setLaunchPreview(detail || error.response?.data || null);
      setShowGameDialog(true);
    } finally {
      setLaunchingGameId('');
    }
  };

  // Handle autocomplete selection
  const handleAutocompleteSelect = (game) => {
    setSearchInput(game.name);
    launchGame(game);
  };

  const isDefaultView = !searchInput && categoryFilter === 'all' && providerFilter === 'all' && !tagFilter;

  return (
    <div className="player-content-container space-y-4" data-testid="player-games-page">
      <section className="games-filter-section" data-testid="games-filter-section">
        {/* Header row */}
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="min-w-0">
            <h1 className="text-xl lg:text-2xl font-semibold tracking-tight" data-testid="games-page-title">Games</h1>
            <p className="text-xs lg:text-sm text-muted-foreground truncate" data-testid="games-result-count">{pageCountLabel}</p>
          </div>
          <Button variant="outline" size="sm" className="h-9 lg:h-10 rounded-full flex-shrink-0" onClick={() => { fetchMetadata(); fetchGames(); }} data-testid="games-refresh-button">
            <RefreshCw className="h-3.5 w-3.5 lg:mr-2" />
            <span className="hidden lg:inline">Refresh</span>
          </Button>
        </div>

        {/* Search bar with autocomplete */}
        <div className="mb-3">
          <SearchAutocomplete
            value={searchInput}
            onChange={setSearchInput}
            onSelect={handleAutocompleteSelect}
            games={hydratedGames}
            loading={loadingGames}
          />
        </div>

        {/* Provider filter - horizontal scroll */}
        <div className="mb-3">
          <ProviderFilter providers={providers} selected={providerFilter} onSelect={setProviderFilter} loading={loadingMeta} variant="scroll" />
        </div>

        {/* Category chips */}
        <div className="filter-chips-row mb-2">
          {categories.map((category) => {
            const Icon = CATEGORY_ICONS[category.name] || Gamepad2;
            const active = categoryFilter === category.name;
            return (
              <button
                key={category.name}
                type="button"
                className={cn('filter-chip', active && 'filter-chip-active')}
                onClick={() => setCategoryFilter(category.name)}
                data-testid={`games-category-chip-${category.name}`}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="capitalize">{category.name}</span>
                <span className="filter-chip-count">{category.count}</span>
              </button>
            );
          })}
        </div>

        {/* Tag filters + clear */}
        <div className="flex items-center gap-2 flex-wrap">
          {[
            { value: 'hot', label: 'Hot', icon: Flame },
            { value: 'new', label: 'New', icon: Sparkles },
            { value: 'popular', label: 'Popular', icon: Star },
          ].map((tag) => (
            <button
              key={tag.value}
              type="button"
              className={cn('tag-chip', tagFilter === tag.value && 'tag-chip-active')}
              onClick={() => setTagFilter(tagFilter === tag.value ? '' : tag.value)}
              data-testid={`games-tag-chip-${tag.value}`}
            >
              <tag.icon className="h-3 w-3" />
              <span>{tag.label}</span>
            </button>
          ))}
          {!isDefaultView ? (
            <button type="button" className="tag-chip tag-chip-clear" onClick={clearFilters} data-testid="games-clear-filters-button">
              <X className="h-3 w-3" />
              <span>Clear</span>
            </button>
          ) : null}
        </div>
      </section>

      <PromoTicker />

      {fetchError.metadata ? (
        <Alert variant="destructive" data-testid="games-error-state">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Couldn't load filters</AlertTitle>
          <AlertDescription>{fetchError.metadata}</AlertDescription>
        </Alert>
      ) : null}

      {/* Recently Played Section - show on default view */}
      {isDefaultView && recentlyPlayed.length > 0 && !loadingGames ? (
        <RecentlyPlayedSection 
          recentGames={recentlyPlayed} 
          allGames={hydratedGames} 
          onLaunch={launchGame} 
        />
      ) : null}

      {isDefaultView ? <HeroBanner games={hydratedGames.slice(0, 12)} onLaunch={launchGame} /> : null}

      {isDefaultView ? (
        <>
          {hotGames.length > 0 || loadingGames ? <HorizontalGameSection title="Hot Games" icon={Flame} games={hotGames} loading={loadingGames} onLaunch={launchGame} /> : null}
          {newGames.length > 0 || loadingGames ? <HorizontalGameSection title="New Games" icon={Sparkles} games={newGames} loading={loadingGames} onLaunch={launchGame} /> : null}
          {popularGames.length > 0 || loadingGames ? <HorizontalGameSection title="Popular Games" icon={Star} games={popularGames} loading={loadingGames} onLaunch={launchGame} /> : null}
        </>
      ) : null}

      <section className="space-y-3" data-testid="games-grid-section">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">All games</h2>
            <p className="text-xs text-muted-foreground">
              {displayedGames.length < hydratedGames.length 
                ? `Showing ${displayedGames.length} of ${hydratedGames.length} games`
                : `${hydratedGames.length} games`
              }
            </p>
          </div>
          {loadingGames ? <Loader2 className="h-4 w-4 animate-spin text-primary" /> : null}
        </div>

        {fetchError.games ? (
          <Alert variant="destructive" data-testid="games-error-state">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Couldn't load games</AlertTitle>
            <AlertDescription className="space-y-3">
              <p>{fetchError.games}</p>
              <Button variant="outline" size="sm" onClick={fetchGames} data-testid="games-retry-button">Retry</Button>
            </AlertDescription>
          </Alert>
        ) : loadingGames ? (
          <div className="games-grid" data-testid="games-loading-skeleton">
            {[...Array(12)].map((_, index) => (
              <div key={index} className="space-y-2">
                <Skeleton className="aspect-[16/10] rounded-xl" />
                <Skeleton className="h-4 w-4/5" />
              </div>
            ))}
          </div>
        ) : hydratedGames.length === 0 ? (
          <div className="solid-card flex flex-col items-start gap-2 rounded-2xl p-6" data-testid="games-empty-state">
            <EmptyIllustration />
            <h3 className="text-base font-semibold">No games found</h3>
            <p className="text-sm text-muted-foreground">Try a different search, category, or provider.</p>
            <Button variant="outline" onClick={clearFilters} data-testid="games-clear-filters-button">Clear filters</Button>
          </div>
        ) : (
          <>
            <div className="games-grid">
              {displayedGames.map((game, index) => (
                <div key={game.id} className="game-card-animate" data-index={Math.min(index, 11)}>
                  <GameCard game={game} onLaunch={launchGame} index={index} />
                </div>
              ))}
            </div>
            
            {/* Infinite scroll trigger */}
            {hasMore && displayedCount < hydratedGames.length && (
              <div ref={loadMoreRef} className="infinite-scroll-trigger">
                {loadingMore ? (
                  <div className="flex items-center justify-center gap-2 py-6">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    <span className="text-sm text-muted-foreground">Loading more games...</span>
                  </div>
                ) : (
                  <div className="flex justify-center py-4">
                    <Button variant="outline" size="sm" onClick={loadMoreGames} className="rounded-full">
                      Load more games
                    </Button>
                  </div>
                )}
              </div>
            )}
            
            {/* End of list indicator */}
            {!hasMore && hydratedGames.length > GAMES_PER_PAGE && (
              <p className="text-center text-xs text-muted-foreground py-4">
                You've reached the end • {hydratedGames.length} games
              </p>
            )}
          </>
        )}
      </section>

      <Dialog open={showGameDialog} onOpenChange={setShowGameDialog}>
        <DialogContent className="max-w-lg border-border/60 bg-card/95 backdrop-blur">
          <DialogHeader>
            <DialogTitle>{selectedGame?.name || 'Game launch status'}</DialogTitle>
            <DialogDescription>{selectedGame?.provider_name || 'Provider'}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="overflow-hidden rounded-2xl border border-border/50 bg-muted/30">
              <div className="aspect-[16/10] overflow-hidden">
                {selectedGame ? (
                  <GameThumbnail game={selectedGame} className="h-full w-full object-cover" imageTestId="launch-preview-thumbnail" fallbackTestId="launch-preview-thumbnail-fallback" />
                ) : null}
              </div>
            </div>
            {launchPreview?.launch_url ? (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Launch ready</AlertTitle>
                <AlertDescription>
                  <p className="mb-3 break-all text-xs text-muted-foreground">{launchPreview.launch_url}</p>
                  <Button onClick={() => window.open(launchPreview.launch_url, '_blank', 'noopener,noreferrer')}>Open game</Button>
                </AlertDescription>
              </Alert>
            ) : (
              <Alert variant="destructive">
                <TriangleAlert className="h-4 w-4" />
                <AlertTitle>Launch unavailable</AlertTitle>
                <AlertDescription>
                  {typeof launchPreview === 'string'
                    ? launchPreview
                    : launchPreview?.detail || launchPreview?.message || 'This game could not be launched right now.'}
                </AlertDescription>
              </Alert>
            )}
            <div className="rounded-xl border border-border/50 bg-muted/20 p-4 text-sm text-muted-foreground">
              <p><span className="font-medium text-foreground">Wallet balance:</span> {formatAppMoney(user?.wallet_balance || 0)}</p>
              <p className="mt-2"><span className="font-medium text-foreground">Launch path:</span> Seamless provider contract</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
