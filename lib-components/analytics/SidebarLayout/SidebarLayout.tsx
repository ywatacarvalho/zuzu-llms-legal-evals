import React, { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { LogOut, Menu, X, ChevronRight, LucideIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';

export interface NavItemConfig {
  to: string;
  icon: LucideIcon;
  labelKey?: string;
  label?: string; // Fallback if no translation key
  end?: boolean;
}

export interface UserContextData {
  name: string;
  role: string;
  initials: string;
}

export interface SidebarLayoutProps {
  navigation?: NavItemConfig[];
  brandNameKey?: string;
  brandSubtitleKey?: string;
  user?: UserContextData;
  onLogout?: () => void;
  breadcrumbKey?: string;
  children: React.ReactNode;
}

function NavItem({ to, icon: Icon, labelKey, label, end = false, onClick }: NavItemConfig & { onClick?: () => void }) {
  const { t } = useTranslation('common');
  const displayLabel = labelKey ? t(labelKey, label ?? '') : label;

  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `relative flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all group overflow-hidden ${
          isActive
            ? 'text-primary-foreground'
            : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <motion.div
              layoutId="activeTab"
              className="absolute inset-0 bg-primary/20 border border-primary/30 rounded-lg"
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            />
          )}
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-1/2 bg-primary rounded-r-md" />
          )}
          <Icon className={`w-4 h-4 shrink-0 relative z-10 transition-colors ${isActive ? 'text-primary' : 'group-hover:text-foreground'}`} />
          <span className="relative z-10">{displayLabel}</span>
        </>
      )}
    </NavLink>
  );
}

export function SidebarLayout({
  navigation = [],
  brandNameKey = 'branding.name',
  brandSubtitleKey = 'branding.subtitle',
  user,
  onLogout,
  breadcrumbKey = 'nav.dashboard',
  children
}: SidebarLayoutProps) {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation('common');

  const Sidebar = (
    <nav className="flex flex-col h-full bg-background/50 backdrop-blur-xl">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-border">
        <p className="font-bold text-foreground tracking-tight text-sm">{t(brandNameKey)}</p>
        <p className="text-xs text-primary mt-0.5 font-medium">{t(brandSubtitleKey)}</p>
      </div>

      {/* Links */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5 scrollbar-hide">
        {navigation.map(item => (
          <NavItem key={item.to} {...item} onClick={() => setOpen(false)} />
        ))}
      </div>

      {/* User strip */}
      <div className="px-3 py-4 border-t border-border bg-gradient-to-t from-foreground/5 to-transparent dark:from-foreground/10">
        {user && (
          <div className="flex items-center gap-3 mb-3 pl-1">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0 shadow-lg shadow-primary/20 border border-primary/10">
              {user.initials}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-semibold text-foreground truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground uppercase tracking-wider">{user.role}</p>
            </div>
          </div>
        )}
        <button
          onClick={onLogout}
          className="w-full flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-xs font-medium text-muted-foreground bg-secondary/20 hover:bg-destructive/10 hover:text-destructive transition-colors border border-transparent hover:border-destructive/20"
        >
          <LogOut className="w-3.5 h-3.5" /> {t('auth.logout', 'Log out')}
        </button>
      </div>
    </nav>
  );

  return (
    <div className="h-full w-full bg-background flex overflow-hidden">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 shrink-0 flex-col border-r border-border z-20">
        {Sidebar}
      </aside>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden" 
              onClick={() => setOpen(false)} 
            />
            <motion.div 
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', bounce: 0, duration: 0.4 }}
              className="fixed inset-y-0 left-0 w-56 border-r border-border flex flex-col z-50 md:hidden bg-background"
            >
              {Sidebar}
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Decorative Background Glows */}
        <div className="absolute top-[-10%] right-[-5%] w-[30%] h-[30%] bg-primary/10 rounded-full blur-[120px] pointer-events-none" />
        
        {/* Top bar */}
        <header className="h-12 flex items-center gap-3 px-4 border-b border-border shrink-0 bg-background/80 backdrop-blur-md sticky top-0 z-30">
          <button
            className="md:hidden text-muted-foreground hover:text-foreground transition-colors"
            onClick={() => setOpen(true)}
            aria-label={t('nav.openMenu', 'Open menu')}
          >
            <Menu className="w-5 h-5" />
          </button>
          <ChevronRight className="w-4 h-4 text-muted-foreground hidden md:block" />
          <span className="text-sm font-medium text-muted-foreground hidden md:block">{t(breadcrumbKey, 'Dashboard')}</span>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-5 z-10 relative">
          {children}
        </main>
      </div>
    </div>
  );
}
