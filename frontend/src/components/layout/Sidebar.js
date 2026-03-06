import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  Users,
  Gamepad2,
  Receipt,
  Palette,
  Building2,
  Wallet,
  Crown,
  Waves,
  ArrowUpRight,
  ArrowDownRight,
  Shield,
  ChevronRight,
  Key,
  BarChart3,
  AlertTriangle,
  Settings,
  PiggyBank
} from 'lucide-react';

const SuperAdminNavItems = [
  { to: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/admin/tenants', icon: Building2, label: 'Operator' },
  { to: '/admin/transactions', icon: Receipt, label: 'Transaksi' },
  { to: '/admin/themes', icon: Palette, label: 'Tema' },
];

const TenantAdminNavItems = [
  { to: '/tenant', icon: LayoutDashboard, label: 'Beranda', exact: true },
  { to: '/tenant/players', icon: Users, label: 'Pemain' },
  { to: '/tenant/games', icon: Gamepad2, label: 'Permainan' },
  { to: '/tenant/transactions', icon: Receipt, label: 'Transaksi' },
  { to: '/tenant/finance', icon: PiggyBank, label: 'Finance & Risk' },
  { to: '/tenant/withdrawals', icon: Wallet, label: 'Penarikan' },
  { to: '/tenant/bank-accounts', icon: Building2, label: 'Deposit Bank Accounts' },
  { to: '/tenant/deposits', icon: ArrowDownRight, label: 'Deposit Approvals' },
  { to: '/tenant/reports', icon: BarChart3, label: 'Laporan' },
  { to: '/tenant/api-keys', icon: Key, label: 'API Keys' },
  { to: '/tenant/risk', icon: AlertTriangle, label: 'Risk' },
  { to: '/tenant/branding', icon: Palette, label: 'Branding' },
  { to: '/tenant/settings', icon: Settings, label: 'Settings' },
];

const PlayerNavItems = [
  { to: '/play/dashboard', icon: LayoutDashboard, label: 'Home', exact: true },
  { to: '/play/games', icon: Gamepad2, label: 'Games' },
  { to: '/play/providers', icon: Building2, label: 'Provider' },
  { to: '/play/wallet', icon: ArrowDownRight, label: 'Deposit' },
  { to: '/play/withdraw', icon: ArrowUpRight, label: 'Withdraw' },
  { to: '/play/history', icon: Receipt, label: 'History' },
  { to: '/play/responsible-gaming', icon: Shield, label: 'Akun' },
];

export const Sidebar = ({ isExpanded, onMouseEnter, onMouseLeave }) => {
  const { user, tenant } = useAuth();
  const location = useLocation();

  const navItems = user?.role === 'super_admin' 
    ? SuperAdminNavItems 
    : user?.role === 'tenant_admin'
    ? TenantAdminNavItems
    : PlayerNavItems;

  const LogoIcon = tenant?.theme_preset === 'midnight_blue' ? Waves : Crown;
  const isPlayer = user?.role === 'player';

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-50 h-full border-r transition-all duration-200 ease-out",
        "hidden lg:flex flex-col",
        // TASK B2 - Sidebar background
        isPlayer 
          ? "bg-card/85 backdrop-blur-md border-border/50" 
          : "bg-card/95 backdrop-blur-md border-border",
        // TASK B2 - Width 240px default, 260px xl
        isExpanded ? "w-[240px] xl:w-[260px]" : "w-[64px]"
      )}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Logo Area - TASK B2: Taller header area to match topbar */}
      <div className={cn(
        "flex items-center",
        "h-12 lg:h-[76px]", // Match topbar height
        isPlayer ? "border-b border-border/40" : "border-b border-border",
        isExpanded ? "px-4 gap-3" : "justify-center"
      )}>
        <div className={cn(
          "rounded-xl flex items-center justify-center flex-shrink-0",
          isPlayer ? "bg-primary/10" : "bg-primary/15",
          isExpanded ? "w-10 h-10" : "w-9 h-9"
        )}>
          <LogoIcon className={cn(
            "text-primary",
            isExpanded ? "w-5 h-5" : "w-4 h-4"
          )} />
        </div>
        {isExpanded && (
          <div className="flex flex-col min-w-0">
            <span className="font-bold text-sm text-foreground truncate">
              {tenant?.name || 'Platform'}
            </span>
            <span className={cn(
              "text-[10px] uppercase tracking-wider",
              isPlayer ? "text-muted-foreground/70" : "text-muted-foreground"
            )}>
              {user?.role?.replace('_', ' ')}
            </span>
          </div>
        )}
      </div>

      {/* Navigation - TASK B2: Larger nav items 48-56px height */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 scrollbar-hide">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive = item.exact 
              ? location.pathname === item.to 
              : location.pathname.startsWith(item.to);
            
            return (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  className={cn(
                    "flex items-center gap-3 rounded-xl relative",
                    "transition-all duration-200 ease-out",
                    // TASK B2 - Nav item height 48-56px (py-3.5 = ~52px total)
                    isExpanded ? "px-3 py-3.5" : "px-2 py-3.5 justify-center",
                    // Font size: text-base, font-medium
                    "text-sm font-medium",
                    // Active/hover states
                    isActive
                      ? isPlayer 
                        ? "bg-primary/15 text-primary border border-primary/20 shadow-sm" 
                        : "bg-primary/20 text-primary"
                      : isPlayer 
                        ? "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                        : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                  )}
                  style={{
                    boxShadow: isActive && !isPlayer ? '0 2px 12px -4px hsl(var(--primary) / 0.35)' : undefined
                  }}
                  title={!isExpanded ? item.label : undefined}
                >
                  {/* Active indicator bar */}
                  {isActive && (
                    <span 
                      className={cn(
                        "absolute left-0 top-1/2 -translate-y-1/2 rounded-r-full bg-primary",
                        isPlayer ? "w-[3px] h-6" : "w-[3px] h-7"
                      )}
                      style={{ boxShadow: '2px 0 10px -2px hsl(var(--primary) / 0.6)' }}
                    />
                  )}
                  {/* TASK B2 - Icon size naik */}
                  <item.icon className={cn(
                    "flex-shrink-0 transition-transform duration-200",
                    "w-5 h-5",
                    !isActive && "group-hover:scale-105"
                  )} />
                  {isExpanded && (
                    <span className="truncate">{item.label}</span>
                  )}
                </NavLink>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* User Area - scaled up */}
      <div className={cn(
        "py-3 px-2",
        isPlayer ? "border-t border-border/40" : "border-t border-border",
        !isExpanded && "flex justify-center"
      )}>
        <div className={cn(
          "flex items-center gap-3",
          !isExpanded && "justify-center"
        )}>
          <div className={cn(
            "rounded-full flex items-center justify-center flex-shrink-0",
            isPlayer ? "bg-primary/15" : "bg-primary/20",
            isExpanded ? "w-9 h-9" : "w-8 h-8"
          )}>
            <span className={cn(
              "font-bold text-primary",
              isExpanded ? "text-sm" : "text-xs"
            )}>
              {user?.display_name?.charAt(0) || 'U'}
            </span>
          </div>
          {isExpanded && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground truncate">
                {user?.display_name}
              </p>
              <p className="text-[10px] text-muted-foreground truncate">
                {user?.email?.split('@')[0]}
              </p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
