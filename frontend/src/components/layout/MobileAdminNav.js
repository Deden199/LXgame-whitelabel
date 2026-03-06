import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { LayoutDashboard, Gamepad2, Users, Receipt, Settings, MoreHorizontal, Wallet, BarChart3, Key, AlertTriangle } from 'lucide-react';
import { cn } from '../../lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';

const adminNavItems = [
  { to: '/admin/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/admin/tenants', icon: Users, label: 'Tenants' },
  { to: '/admin/transactions', icon: Receipt, label: 'Transactions' },
  { to: '/admin/themes', icon: Settings, label: 'Settings' },
];

const tenantNavItems = [
  { to: '/tenant', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/tenant/games', icon: Gamepad2, label: 'Games' },
  { to: '/tenant/withdrawals', icon: Wallet, label: 'Withdrawals' },
  { to: '/tenant/players', icon: Users, label: 'Players' },
  { to: '/tenant/reports', icon: BarChart3, label: 'Reports' },
  { to: '/tenant/api-keys', icon: Key, label: 'API Keys' },
  { to: '/tenant/risk', icon: AlertTriangle, label: 'Risk' },
  { to: '/tenant/settings', icon: Settings, label: 'Settings' },
];

export const MobileAdminNav = ({ role }) => {
  const location = useLocation();
  const navItems = role === 'super_admin' ? adminNavItems : tenantNavItems;
  const primaryItems = navItems.slice(0, 4);
  const overflowItems = navItems.slice(4);
  const isRouteActive = (route) => location.pathname === route || location.pathname.startsWith(`${route}/`);
  const hasOverflowActiveRoute = overflowItems.some((item) => isRouteActive(item.to));

  return (
    <nav className="mobile-admin-nav lg:hidden" data-testid="mobile-admin-nav">
      <div className="mobile-admin-nav-inner">
        {primaryItems.map((item) => {
          const isActive = isRouteActive(item.to);
          return (
            <NavLink key={item.to} to={item.to} className={cn('mobile-admin-nav-item', isActive && 'active')}>
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}

        {!!overflowItems.length && (
          <DropdownMenu>
            <DropdownMenuTrigger className={cn('mobile-admin-nav-item', hasOverflowActiveRoute && 'active')} aria-label="More admin menu">
              <MoreHorizontal className="w-4 h-4" />
              <span>More</span>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="end" className="w-52 mb-2">
              {overflowItems.map((item) => (
                <DropdownMenuItem key={item.to} asChild>
                  <NavLink to={item.to} className="w-full">
                    {item.label}
                  </NavLink>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </nav>
  );
};
