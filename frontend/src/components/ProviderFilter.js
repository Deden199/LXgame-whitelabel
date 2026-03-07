import React, { useEffect, useMemo, useState } from 'react';
import { Check, ChevronDown, ChevronLeft, ChevronRight, Grid3X3 } from 'lucide-react';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from './ui/command';
import { cn } from '../lib/utils';
import { ProviderLogoBadge, getProviderLogo } from './catalog/CatalogMedia';

export function ProviderLogo({ provider, className = 'h-8 w-8', testId }) {
  return <ProviderLogoBadge provider={provider} className={className} testId={testId} />;
}

export { getProviderLogo };
export const DEFAULT_PROVIDER_LOGOS = {};

function normalizeProvider(provider) {
  return {
    code: provider?.code || provider?.provider_code || provider?.slug || provider?.name,
    name: provider?.name || provider?.provider_name || provider?.code || provider?.provider_code || 'Unknown Provider',
    slug: provider?.slug || provider?.provider_slug || provider?.code?.toLowerCase?.() || provider?.provider_code?.toLowerCase?.(),
    logo_url: provider?.logo_url || provider?.logoUrl || provider?.provider_logo_url,
    gameCount: provider?.gameCount || provider?.count || 0,
    categories: provider?.categories || [],
    provider_code: provider?.provider_code || provider?.code,
  };
}

function ProviderHorizontalScroll({ providers, selected, onSelect, loading }) {
  const [showLeftArrow, setShowLeftArrow] = useState(false);
  const [showRightArrow, setShowRightArrow] = useState(false);
  const scrollRef = React.useRef(null);

  useEffect(() => {
    const update = () => {
      if (!scrollRef.current) return;
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
      setShowLeftArrow(scrollLeft > 4);
      setShowRightArrow(scrollLeft < scrollWidth - clientWidth - 4);
    };

    update();
    const node = scrollRef.current;
    node?.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      node?.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, [providers]);

  const scroll = (direction) => {
    scrollRef.current?.scrollBy({ left: direction === 'left' ? -180 : 180, behavior: 'smooth' });
  };

  if (loading) {
    return (
      <div className="provider-chips-row">
        {[...Array(5)].map((_, index) => (
          <div key={index} className="provider-chip-skeleton" />
        ))}
      </div>
    );
  }

  return (
    <div className="provider-filter-wrapper">
      {showLeftArrow && (
        <button
          type="button"
          className="provider-scroll-btn provider-scroll-left"
          onClick={() => scroll('left')}
          aria-label="Scroll providers left"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      )}
      <div ref={scrollRef} className="provider-chips-row">
        <button
          type="button"
          className={cn('provider-chip', selected === 'all' && 'provider-chip-active')}
          onClick={() => onSelect('all')}
          data-testid="games-provider-filter-item-all"
        >
          <Grid3X3 className="h-4 w-4" />
          <span>All</span>
        </button>
        {providers.map((rawProvider) => {
          const provider = normalizeProvider(rawProvider);
          const isSelected = selected === provider.code || selected === provider.slug;
          return (
            <button
              type="button"
              key={provider.code}
              onClick={() => onSelect(provider.code)}
              data-testid={`games-provider-filter-item-${provider.slug || provider.code}`}
              className={cn('provider-chip', isSelected && 'provider-chip-active')}
            >
              <ProviderLogo provider={provider} className="h-5 w-5" testId={`provider-logo-${provider.slug || provider.code}`} />
              <span className="provider-chip-name">{provider.name}</span>
              {provider.gameCount > 0 && (
                <span className="provider-chip-count">{provider.gameCount}</span>
              )}
            </button>
          );
        })}
      </div>
      {showRightArrow && (
        <button
          type="button"
          className="provider-scroll-btn provider-scroll-right"
          onClick={() => scroll('right')}
          aria-label="Scroll providers right"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

function ProviderDropdown({ providers, selected, onSelect, loading }) {
  const [open, setOpen] = useState(false);
  const providerList = useMemo(() => providers.map(normalizeProvider), [providers]);
  const selectedProvider = providerList.find((provider) => provider.code === selected || provider.slug === selected);

  const handleSelect = (value) => {
    onSelect(value);
    setOpen(false);
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn('h-10 min-w-[180px] justify-between rounded-full border-border/60 bg-card/70 text-sm', selected !== 'all' && 'border-primary/30 bg-primary/5')}
          data-testid="games-provider-filter-trigger"
        >
          <span className="flex min-w-0 items-center gap-2">
            {selected === 'all' ? (
              <>
                <Grid3X3 className="h-4 w-4" />
                <span>Provider: All</span>
              </>
            ) : (
              <>
                <ProviderLogo provider={selectedProvider || { name: selected }} className="h-6 w-6" testId={`provider-logo-${selected}`} />
                <span className="truncate">{selectedProvider?.name || selected}</span>
              </>
            )}
          </span>
          <ChevronDown className="h-4 w-4 opacity-60" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 border-border/60 bg-popover/95 p-0 backdrop-blur" align="start">
        <Command>
          <CommandInput placeholder="Search providers" data-testid="games-provider-filter-search" />
          <CommandList>
            <CommandEmpty>No providers found.</CommandEmpty>
            <CommandGroup heading="Providers">
              <CommandItem value="all providers" onSelect={() => handleSelect('all')} data-testid="games-provider-filter-item-all">
                <Grid3X3 className="h-4 w-4" />
                <span className="flex-1">All providers</span>
                {selected === 'all' ? <Check className="h-4 w-4 text-primary" /> : null}
              </CommandItem>
              {loading
                ? [...Array(6)].map((_, index) => (
                    <div key={index} className="mx-2 my-1 h-10 animate-pulse rounded-md bg-muted" />
                  ))
                : providerList.map((provider) => {
                    const isSelected = selected === provider.code || selected === provider.slug;
                    return (
                      <CommandItem
                        key={provider.code}
                        value={`${provider.name} ${provider.code}`}
                        onSelect={() => handleSelect(provider.code)}
                        data-testid={`games-provider-filter-item-${provider.slug || provider.code}`}
                      >
                        <ProviderLogo provider={provider} className="h-8 w-8" testId={`provider-logo-${provider.slug || provider.code}`} />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{provider.name}</p>
                          <p className="text-[11px] text-muted-foreground">{provider.gameCount} games</p>
                        </div>
                        {isSelected ? <Check className="h-4 w-4 text-primary" /> : null}
                      </CommandItem>
                    );
                  })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export default function ProviderFilter({ providers = [], selected = 'all', onSelect, loading = false, variant = 'dropdown' }) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const update = () => setIsMobile(window.innerWidth < 768);
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  const effectiveVariant = variant === 'auto' ? (isMobile ? 'scroll' : 'dropdown') : variant;

  if (effectiveVariant === 'scroll') {
    return <ProviderHorizontalScroll providers={providers} selected={selected} onSelect={onSelect} loading={loading} />;
  }

  return <ProviderDropdown providers={providers} selected={selected} onSelect={onSelect} loading={loading} />;
}
