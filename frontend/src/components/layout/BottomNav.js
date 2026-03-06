import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '../../lib/utils';
import {
  Home,
  Gamepad2,
  Wallet,
  History,
  Menu,
  User
} from 'lucide-react';

const navItems = [
  { to: '/play/dashboard', icon: Home, label: 'Home' },
  { to: '/play/games', icon: Gamepad2, label: 'Games' },
  { to: '/play/wallet', icon: Wallet, label: 'Wallet' },
  { to: '/play/history', icon: History, label: 'History' },
  { to: '/play/responsible-gaming', icon: User, label: 'Akun' },
];

export const BottomNav = () => {
  const location = useLocation();

  return (
    <nav className="bottom-nav lg:hidden" data-testid="bottom-nav">
      <div className="flex items-center justify-around">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to || 
            (item.to === '/play/games' && location.pathname === '/play');
          
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "bottom-nav-item",
                isActive && "active"
              )}
              data-testid={`bottom-nav-${item.label.toLowerCase()}`}
            >
              <item.icon />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
};
