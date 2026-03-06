import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { 
  Wallet, 
  Gamepad2, 
  TrendingUp,
  TrendingDown,
  Play,
  ArrowRight,
  Trophy,
  Flame,
  Sparkles,
  Star,
  ChevronRight,
  Gift
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';
import { convertAmount } from '../../lib/currency';

// Image component with error handling
const GameImage = ({ src, alt, className, style }) => {
  const [error, setError] = useState(false);
  
  if (error || !src) {
    return (
      <div 
        className={cn("bg-gradient-to-br from-muted to-card flex items-center justify-center", className)}
        style={style}
      >
        <Gamepad2 className="w-6 h-6 text-muted-foreground/30" />
      </div>
    );
  }
  
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      onError={() => setError(true)}
    />
  );
};

export default function PlayerDashboard() {
  const { api, user, tenant } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recentGames, setRecentGames] = useState([]);
  const [recentTx, setRecentTx] = useState([]);
  const [hotGames, setHotGames] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, recentRes, txRes, gamesRes] = await Promise.all([
        api.get('/player/stats').catch(() => ({ data: {} })),
        api.get('/player/recent-games').catch(() => ({ data: [] })),
        api.get('/transactions', { params: { limit: 5 } }),
        api.get('/games', { params: { tag: 'hot', limit: 8 } }).catch(() => ({ data: [] }))
      ]);
      setStats(statsRes.data);
      setRecentGames(recentRes.data);
      setRecentTx(txRes.data);
      setHotGames(gamesRes.data.slice(0, 8));
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  };

  const balance = user?.wallet_balance || 0;

  const formatTransactionAmount = (amount, txCurrency) => {
    const normalizedTxCurrency = String(txCurrency || 'IDR').toUpperCase();
    const convertedAmount = convertAmount(amount, { fromCurrency: normalizedTxCurrency, toCurrency: user?.preferred_currency || 'IDR' });
    return formatAppMoney(convertedAmount ?? amount);
  };

  // Branding settings from tenant
  const branding = tenant?.branding || {};
  const showHero = branding.show_hero !== false;
  const showCategories = branding.show_categories !== false;
  const showFeatured = branding.show_featured !== false;
  const heroUrl = branding.hero_url;

  if (loading) {
    return (
      <div className="space-y-3" data-testid="player-dashboard">
        <div className="h-24 rounded-lg bg-muted animate-pulse" />
        <div className="grid grid-cols-4 gap-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 rounded-md bg-muted animate-pulse" />
          ))}
        </div>
        <div className="h-40 rounded-lg bg-muted animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="player-dashboard">
      {/* Hero Banner - Premium with Layered Depth */}
      {showHero && (
      <div 
        className="relative overflow-hidden rounded-xl border border-border/40"
        style={{
          background: heroUrl 
            ? `linear-gradient(135deg, hsl(var(--background) / 0.85) 0%, hsl(var(--background) / 0.7) 100%), url(${heroUrl})`
            : 'linear-gradient(135deg, hsl(var(--primary) / 0.12) 0%, hsl(var(--card)) 40%, hsl(var(--accent) / 0.08) 100%)',
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          boxShadow: '0 4px 20px -4px hsl(var(--primary) / 0.15), inset 0 1px 0 hsl(var(--foreground) / 0.03)'
        }}
      >
        {/* Radial highlight layer */}
        <div 
          className="absolute inset-0 pointer-events-none"
          style={{
            background: 'radial-gradient(ellipse at 30% 20%, hsl(var(--primary) / 0.08) 0%, transparent 50%)'
          }}
        />
        {/* Subtle pattern overlay */}
        {!heroUrl && (
        <div 
          className="absolute inset-0 opacity-30 pointer-events-none"
          style={{
            backgroundImage: 'radial-gradient(circle at 2px 2px, hsl(var(--foreground) / 0.03) 1px, transparent 0)',
            backgroundSize: '24px 24px'
          }}
        />
        )}
        <div className="relative p-4 sm:p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-[10px] text-primary font-semibold uppercase tracking-wider mb-1"
                 style={{ textShadow: '0 0 20px hsl(var(--primary) / 0.3)' }}>
                Selamat Datang Kembali
              </p>
              <h1 className="text-lg sm:text-xl font-bold text-foreground">
                {user?.display_name?.split(' ')[0]}!
              </h1>
              <p className="text-xs text-muted-foreground mt-0.5">
                {tenant?.name}
              </p>
            </div>
            <div className="text-right min-w-0">
              <p className="text-[10px] text-muted-foreground">Saldo Anda</p>
              <p className={`text-xl sm:text-2xl font-bold text-primary ${MONEY_DISPLAY_CLASSES}`}
                 style={{ textShadow: '0 0 24px hsl(var(--primary) / 0.3)' }}
                 title={formatAppMoney(balance)}>
                {formatAppMoney(balance)}
              </p>
              <div className="flex gap-1.5 mt-2">
                <Button 
                  size="sm" 
                  className="h-7 px-3 text-[10px] shadow-md"
                  style={{ boxShadow: '0 2px 12px -2px hsl(var(--primary) / 0.4)' }}
                  onClick={() => navigate('/play/wallet')}
                >
                  <TrendingDown className="w-3 h-3 mr-1" />
                  Deposit
                </Button>
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="h-7 px-3 text-[10px]" 
                  onClick={() => navigate('/play/withdraw')}
                >
                  <TrendingUp className="w-3 h-3 mr-1" />
                  Tarik
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Quick Stats - Premium Row */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: 'Total Bet', value: stats?.total_bets || user?.total_bets || 0, icon: Gamepad2, color: 'text-yellow-500' },
          { label: 'Menang', value: stats?.total_wins || user?.total_wins || 0, icon: Trophy, color: 'text-green-500' },
          { label: 'Game', value: stats?.games_played || user?.games_played_count || 0, icon: Play, color: 'text-blue-500', isCount: true },
          { label: 'Bonus', value: 0, icon: Gift, color: 'text-purple-500' },
        ].map((stat, idx) => (
          <div 
            key={idx}
            className="bg-card rounded-xl border border-border/40 p-2 text-center min-w-0"
            style={{ 
              boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3), inset 0 1px 0 hsl(var(--foreground) / 0.02)',
              transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1)'
            }}
          >
            <stat.icon className={cn("w-4 h-4 mx-auto mb-1", stat.color)} />
            <p className={`text-xs font-bold ${MONEY_DISPLAY_CLASSES}`} title={stat.isCount ? stat.value : formatAppMoney(stat.value)}>
              {stat.isCount ? stat.value : formatAppMoney(stat.value)}
            </p>
            <p className="text-[9px] text-muted-foreground">{stat.label}</p>
          </div>
        ))}
      </div>

      {/* Category Quick Access - Premium Pills */}
      {showCategories && (
      <div className="scroll-container">
        {[
          { label: 'Slots', icon: Sparkles, color: 'bg-purple-500/15 text-purple-400 border-purple-500/20' },
          { label: 'Live', icon: Flame, color: 'bg-red-500/15 text-red-400 border-red-500/20' },
          { label: 'Table', icon: Gamepad2, color: 'bg-blue-500/15 text-blue-400 border-blue-500/20' },
          { label: 'Crash', icon: TrendingUp, color: 'bg-green-500/15 text-green-400 border-green-500/20' },
          { label: 'Jackpot', icon: Star, color: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20' },
        ].map((cat) => (
          <button
            key={cat.label}
            onClick={() => navigate(`/play/games?category=${cat.label.toLowerCase()}`)}
            className={cn(
              "flex flex-col items-center justify-center w-16 h-16 rounded-xl flex-shrink-0 border",
              cat.color,
              "hover:scale-105 active:scale-95 transition-transform duration-150"
            )}
            style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
          >
            <cat.icon className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">{cat.label}</span>
          </button>
        ))}
      </div>
      )}

      {/* Hot Games Section - Premium Cards */}
      {showFeatured && hotGames.length > 0 && (
        <div className="section-compact">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-1.5">
              <Flame className="w-4 h-4 text-red-500" />
              <h2 className="text-sm font-semibold">Hot Games</h2>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 px-2 text-[10px]"
              onClick={() => navigate('/play/games')}
            >
              Semua <ChevronRight className="w-3 h-3 ml-0.5" />
            </Button>
          </div>
          <div className="scroll-container">
            {hotGames.map((game) => (
              <div 
                key={game.id}
                className="w-[100px] sm:w-[110px] flex-shrink-0 cursor-pointer group"
                onClick={() => navigate('/play/games')}
              >
                <div 
                  className="aspect-[4/3] overflow-hidden bg-card relative"
                  style={{
                    borderRadius: '12px',
                    boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.4)',
                    border: '1px solid hsl(var(--border) / 0.3)',
                    transition: 'transform 200ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1)'
                  }}
                >
                  <GameImage
                    src={game.thumbnail_url}
                    alt={game.name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    style={{ borderRadius: '12px' }}
                  />
                  <div 
                    className="absolute inset-0 pointer-events-none"
                    style={{
                      background: 'linear-gradient(to top, hsl(var(--background) / 0.8) 0%, transparent 50%)',
                      borderRadius: '12px'
                    }}
                  />
                  <div className="absolute bottom-1.5 left-1.5 right-1.5">
                    <p className="text-[9px] text-white font-medium truncate drop-shadow-md">{game.name}</p>
                  </div>
                  {/* Play icon on hover */}
                  <div 
                    className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                    style={{ background: 'hsl(var(--background) / 0.5)', borderRadius: '12px' }}
                  >
                    <div className="w-8 h-8 rounded-full bg-primary/90 flex items-center justify-center shadow-lg">
                      <Play className="w-3.5 h-3.5 text-primary-foreground ml-0.5" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {/* Recent Games */}
        <div 
          className="bg-card rounded-xl border border-border/40 p-3"
          style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold flex items-center gap-1.5">
              <Gamepad2 className="w-3.5 h-3.5 text-primary" />
              Terakhir Dimainkan
            </h3>
            <Button 
              variant="ghost" 
              size="sm"
              className="h-5 px-1.5 text-[9px]"
              onClick={() => navigate('/play/games')}
            >
              Lihat <ArrowRight className="w-2.5 h-2.5 ml-0.5" />
            </Button>
          </div>
          {recentGames.length === 0 ? (
            <div className="empty-state-compact">
              <Gamepad2 />
              <p>Belum ada game</p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {recentGames.slice(0, 4).map((game, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 p-1.5 rounded-lg bg-muted/30 hover:bg-muted/50 cursor-pointer transition-colors duration-150"
                  onClick={() => navigate('/play/games')}
                >
                  <div className="w-10 h-8 rounded-lg overflow-hidden bg-muted flex-shrink-0">
                    <GameImage 
                      src={game.thumbnail_url} 
                      alt="" 
                      className="w-full h-full object-cover" 
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-medium truncate">{game.game_name}</p>
                    <p className="text-[8px] text-muted-foreground">
                      {new Date(game.last_played).toLocaleDateString('id-ID')}
                    </p>
                  </div>
                  <Play className="w-3 h-3 text-primary flex-shrink-0" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Transactions */}
        <div 
          className="bg-card rounded-xl border border-border/40 p-3"
          style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
        >
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold flex items-center gap-1.5">
              <Wallet className="w-3.5 h-3.5 text-primary" />
              Aktivitas Terakhir
            </h3>
            <Button 
              variant="ghost" 
              size="sm"
              className="h-5 px-1.5 text-[9px]"
              onClick={() => navigate('/play/history')}
            >
              Lihat <ArrowRight className="w-2.5 h-2.5 ml-0.5" />
            </Button>
          </div>
          {recentTx.length === 0 ? (
            <div className="empty-state-compact">
              <Wallet />
              <p>Belum ada transaksi</p>
            </div>
          ) : (
            <div className="space-y-1">
              {recentTx.slice(0, 4).map((tx, idx) => {
                const isPositive = ['deposit', 'win', 'bonus'].includes(tx.type);
                const typeMap = {
                  deposit: 'Deposit',
                  withdraw: 'Tarik',
                  bet: 'Bet',
                  win: 'Win',
                  bonus: 'Bonus'
                };
                return (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-1.5 rounded bg-muted/30"
                  >
                    <div className="flex items-center gap-2">
                      <div className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0",
                        isPositive ? "bg-green-500/10" : "bg-red-500/10"
                      )}>
                        {isPositive ? (
                          <TrendingUp className="w-3 h-3 text-green-500" />
                        ) : (
                          <TrendingDown className="w-3 h-3 text-red-400" />
                        )}
                      </div>
                      <div>
                        <p className="text-[10px] font-medium">{typeMap[tx.type] || tx.type}</p>
                        <p className="text-[8px] text-muted-foreground">
                          {new Date(tx.timestamp).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
                        </p>
                      </div>
                    </div>
                    <p className={cn(
                      "text-[10px] font-mono font-medium",
                      isPositive ? "text-green-500" : "text-red-400"
                    )}>
                      {isPositive ? '+' : '-'}{formatTransactionAmount(tx.amount, tx.currency)}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
