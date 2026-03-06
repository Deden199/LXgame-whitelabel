import React, { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { BottomNav } from './BottomNav';
import { MobileAdminNav } from './MobileAdminNav';
import { useAuth } from '../../context/AuthContext';
import { cn } from '../../lib/utils';

export const Layout = ({ children }) => {
  const [sidebarExpanded, setSidebarExpanded] = useState(false);
  const { user } = useAuth();
  const location = useLocation();
  
  const isPlayer = user?.role === 'player';
  const isAdmin = user?.role === 'super_admin' || user?.role === 'tenant_admin';

  return (
    <div className="min-h-screen bg-background">
      {/* Noise overlay for texture */}
      <div className="noise-overlay" />
      
      {/* Desktop Sidebar - compact by default, expand on hover */}
      <Sidebar 
        isExpanded={sidebarExpanded}
        onMouseEnter={() => setSidebarExpanded(true)}
        onMouseLeave={() => setSidebarExpanded(false)}
      />

      {/* Main content area - TASK B3: Correct offset for larger sidebar */}
      <div 
        className={cn(
          "min-h-screen flex flex-col transition-all duration-200",
          // Default collapsed: 64px, expanded: 240px (xl: 260px)
          "lg:ml-[64px]",
          sidebarExpanded && "lg:ml-[240px] xl:ml-[260px]"
        )}
      >
        {/* Topbar */}
        <Topbar />

        {/* Page content - responsive padding */}
        <main className={cn(
          "flex-1",
          "px-2 py-2 sm:px-3 sm:py-3",
          "lg:px-6 lg:py-4 xl:px-8", // More padding on desktop
          (isPlayer || isAdmin) && "pb-28 lg:pb-4" // Extra bottom padding for mobile nav
        )}>
          {children}
        </main>

        {/* Player Footer */}
        {isPlayer && (
          <footer className="hidden lg:block text-center py-4 text-xs text-muted-foreground border-t border-border/30">
            Powered by <span className="font-semibold text-primary">LooxGame</span>
          </footer>
        )}
      </div>
      
      {/* Mobile Bottom Navigation - only for players */}
      {isPlayer && <BottomNav />}
      {isAdmin && <MobileAdminNav role={user?.role} />}
    </div>
  );
};
