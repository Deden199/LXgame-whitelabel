import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import {
  Search,
  LogOut,
  User,
  Wallet,
  ChevronDown,
  Bell,
  Settings
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';

export const Topbar = () => {
  const { user, tenant, logout } = useAuth();
  const { formatAppMoney } = useCurrency();
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState('');
  
  const isPlayer = user?.role === 'player';
  const balance = user?.wallet_balance || 0;
  const activeSessionId = window.sessionStorage.getItem('active_session_id');

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchValue.trim() && isPlayer) {
      navigate(`/play/games?search=${encodeURIComponent(searchValue)}`);
    }
  };

  return (
    // TASK B1 - Desktop header 72-84px height
    <header className={cn(
      "sticky top-0 z-30 bg-card/80 backdrop-blur-md border-b border-border",
      "h-12 lg:h-[76px]" // Taller on desktop
    )}>
      <div className={cn(
        "h-full flex items-center gap-2",
        "px-2 sm:px-3",
        "lg:px-6 xl:px-8", // More padding on desktop
        "lg:max-w-[1400px] lg:mx-auto" // Align with content max-width
      )}>
        {/* Search - Player only, scaled up for desktop */}
        {isPlayer && (
          <form onSubmit={handleSearch} className="hidden sm:flex flex-1 max-w-xs lg:max-w-md">
            <div className="relative w-full">
              <Search className={cn(
                "absolute left-2 lg:left-3 top-1/2 -translate-y-1/2 text-muted-foreground",
                "w-3.5 h-3.5 lg:w-4 lg:h-4"
              )} />
              <Input
                type="search"
                placeholder="Cari game..."
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                className={cn(
                  "bg-muted/50 border-0 focus-visible:ring-1",
                  "h-8 pl-8 pr-3 text-xs",
                  "lg:h-11 lg:pl-10 lg:pr-4 lg:text-sm lg:rounded-xl" // Bigger on desktop
                )}
              />
            </div>
          </form>
        )}
        
        {/* Spacer */}
        <div className="flex-1" />
        
        {/* Wallet Balance - Player only, premium style on desktop */}
        {isPlayer && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/play/wallet')}
            className={cn(
              "gap-1.5 font-medium bg-primary/10 hover:bg-primary/20 text-primary",
              "h-8 px-2 text-xs",
              "lg:h-11 lg:px-4 lg:text-sm lg:rounded-xl lg:border lg:border-primary/20" // Premium desktop style
            )}
          >
            <Wallet className="w-3.5 h-3.5 lg:w-4 lg:h-4" />
            <span className="font-mono">{formatAppMoney(balance)}</span>
          </Button>
        )}
        
        {/* Notifications - scaled for desktop */}
        <Button variant="ghost" size="icon" className={cn(
          "h-8 w-8",
          "lg:h-11 lg:w-11 lg:rounded-xl lg:border lg:border-border/50"
        )}>
          <Bell className="w-4 h-4 lg:w-5 lg:h-5 text-muted-foreground" />
        </Button>

        {/* User Menu - scaled for desktop */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className={cn(
              "gap-1.5",
              "h-8 px-2",
              "lg:h-11 lg:px-3 lg:rounded-xl lg:border lg:border-border/50"
            )}>
              <div className={cn(
                "rounded-full bg-primary/20 flex items-center justify-center",
                "w-6 h-6",
                "lg:w-8 lg:h-8"
              )}>
                <span className={cn(
                  "font-bold text-primary",
                  "text-[10px]",
                  "lg:text-xs"
                )}>
                  {user?.display_name?.charAt(0) || 'U'}
                </span>
              </div>
              <ChevronDown className="w-3 h-3 lg:w-4 lg:h-4 text-muted-foreground hidden sm:block" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48 lg:w-56">
            <div className="px-2 py-1.5 lg:px-3 lg:py-2 space-y-1">
              <p className="text-xs lg:text-sm font-medium truncate">{user?.display_name}</p>
              <p className="text-[10px] lg:text-xs text-muted-foreground truncate">{user?.email}</p>
              {isPlayer && (
                <>
                  <p className="text-[10px] text-muted-foreground break-all">player_id: {user?.id}</p>
                  <p className="text-[10px] text-muted-foreground break-all">session_id: {activeSessionId || '-'}</p>
                </>
              )}
            </div>
            <DropdownMenuSeparator />
            {isPlayer && (
              <>
                <DropdownMenuItem onClick={() => navigate('/play/wallet')} className="text-xs lg:text-sm">
                  <Wallet className="w-3.5 h-3.5 lg:w-4 lg:h-4 mr-2" />
                  Wallet
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => navigate('/play/responsible-gaming')} className="text-xs lg:text-sm">
                  <Settings className="w-3.5 h-3.5 lg:w-4 lg:h-4 mr-2" />
                  Settings
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem onClick={handleLogout} className="text-xs lg:text-sm text-destructive">
              <LogOut className="w-3.5 h-3.5 lg:w-4 lg:h-4 mr-2" />
              Keluar
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};
