import React, { useMemo, useState } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { ImageOff, Puzzle } from 'lucide-react';
import { cn } from '../../lib/utils';

const backendBase = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/$/, '');

export function providerAssetUrl(provider) {
  const code = provider?.code || provider?.provider_code || provider?.slug || provider?.provider_slug || provider?.name || 'provider';
  return `${backendBase}/api/assets/providers/${String(code).toLowerCase().replace(/_/g, '-')}.svg`;
}

export function gameAssetUrl(game) {
  const providerCode = game?.provider_code || game?.provider_slug || game?.provider_id || 'game';
  const gameCode = game?.game_code || game?.game_launch_id || game?.external_game_id || game?.id || 'game';
  return `${backendBase}/api/assets/games/${String(providerCode).toLowerCase().replace(/_/g, '-')}/${String(gameCode).toLowerCase().replace(/[^a-z0-9_-]+/gi, '-')}.svg`;
}

export function getProviderLogo(provider) {
  return provider?.provider_logo_url || provider?.logo_url || provider?.logoUrl || providerAssetUrl(provider);
}

export function getGameThumbnail(game) {
  return game?.thumbnail_url || gameAssetUrl(game);
}

export function getInitials(value) {
  const text = String(value || '')
    .replace(/[^a-zA-Z0-9\s]/g, ' ')
    .trim();
  if (!text) return '??';
  const parts = text.split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0] || ''}${parts[1][0] || ''}`.toUpperCase();
}

export function ProviderLogoBadge({ provider, className = 'h-10 w-10', imageClassName, fallbackClassName, testId }) {
  const [imgError, setImgError] = useState(false);
  const logoUrl = getProviderLogo(provider);
  const label = provider?.name || provider?.provider_name || provider?.code || provider?.provider_code || 'Provider';
  const initials = useMemo(() => getInitials(label), [label]);

  return (
    <Avatar className={cn('rounded-xl border border-border/50 bg-card/80', className)} data-testid={testId}>
      {!imgError && logoUrl ? (
        <AvatarImage
          src={logoUrl}
          alt={label}
          loading="lazy"
          decoding="async"
          onError={() => setImgError(true)}
          className={cn('object-cover', imageClassName)}
        />
      ) : null}
      <AvatarFallback className={cn('bg-muted/70 text-foreground/80 font-semibold', fallbackClassName)}>
        {initials}
      </AvatarFallback>
    </Avatar>
  );
}

export function GameThumbnail({
  game,
  className = 'w-full h-full object-cover',
  wrapperClassName = 'w-full h-full',
  imageTestId,
  fallbackTestId,
}) {
  const primarySrc = getGameThumbnail(game);
  const fallbackSrc = gameAssetUrl(game);
  const [currentSrc, setCurrentSrc] = useState(primarySrc);
  const [imgError, setImgError] = useState(false);
  const providerLabel = game?.provider_name || game?.provider_code || 'Game';

  React.useEffect(() => {
    setCurrentSrc(primarySrc);
    setImgError(false);
  }, [primarySrc]);

  if (!currentSrc || imgError) {
    return (
      <div
        className={cn('img-placeholder flex h-full w-full flex-col items-center justify-center gap-2 rounded-[inherit]', wrapperClassName)}
        data-testid={fallbackTestId}
      >
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-background/30 border border-white/10">
          <ImageOff className="h-4 w-4 text-white/75" />
        </div>
        <div className="px-3 text-center">
          <p className="text-xs font-semibold text-white/90 line-clamp-2">{game?.name || 'Game'}</p>
          <p className="mt-1 text-[10px] uppercase tracking-wide text-white/60">{providerLabel}</p>
        </div>
      </div>
    );
  }

  return (
    <img
      src={currentSrc}
      alt={game?.name || 'Game thumbnail'}
      className={cn(className)}
      loading="lazy"
      decoding="async"
      onError={() => {
        if (currentSrc !== fallbackSrc) {
          setCurrentSrc(fallbackSrc);
          return;
        }
        setImgError(true);
      }}
      data-testid={imageTestId}
    />
  );
}

export function EmptyIllustration({ className = 'h-10 w-10' }) {
  return <Puzzle className={cn('text-primary/80', className)} />;
}
