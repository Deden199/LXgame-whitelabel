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
    <div className="min-h-screen overflow-x-hidden bg-background">
      <div className="noise-overlay" />
      <Sidebar 
        isExpanded={sidebarExpanded}
        onMouseEnter={() => setSidebarExpanded(true)}
        onMouseLeave={() => setSidebarExpanded(false)}
      />

      <div 
        className={cn(
          'min-h-screen flex flex-col transition-all duration-200',
          'lg:ml-[64px]',
          sidebarExpanded && 'lg:ml-[240px] xl:ml-[260px]'
        )}
      >
        <Topbar />

        <main className={cn(
          'relative z-0 flex-1 overflow-x-hidden',
          'px-2 py-2 sm:px-3 sm:py-3',
          'lg:px-6 lg:py-4 xl:px-8',
          (isPlayer || isAdmin) && 'pb-32 lg:pb-6'
        )}>
          {children}
        </main>

        {isPlayer && (
          <footer className="hidden lg:block text-center py-4 text-xs text-muted-foreground border-t border-border/30">
            Powered by <span className="font-semibold text-primary">LooxGame</span>
          </footer>
        )}
      </div>
      
      {isPlayer && <BottomNav />}
      {isAdmin && <MobileAdminNav role={user?.role} />}
    </div>
  );
};
