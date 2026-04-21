import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X, LayoutDashboard, LogIn } from 'lucide-react';
import { useTranslation } from 'react-i18next';
// Mock import for AuthContext
// import { useAuth } from '../context/AuthContext';
import ReactCountryFlag from 'react-country-flag';
import { Button } from './ui/button';

export interface NavbarLanguageConfig {
  code: string;
  label: string;
  countryCode?: string;
}

export interface NavLinkConfig {
  key: string;
  to: string;
  labelFallback?: string;
}

export interface NavbarUserActions {
  isAuthenticated?: boolean;
  dashboardPath?: string;
  loginPath?: string;
  dashboardLabelKey?: string;
  dashboardLabelFallback?: string;
  loginLabelKey?: string;
  loginLabelFallback?: string;
}

export interface NavbarProps {
  links?: NavLinkConfig[];
  currentPath?: string;
  homePath?: string;
  brandNameKey?: string;
  brandNameFallback?: string;
  brandSuffixKey?: string;
  brandSuffixFallback?: string;
  languages?: NavbarLanguageConfig[];
  currentLanguage?: string;
  onLanguageChange?: (language: string) => void;
  userActions?: NavbarUserActions;
  headerActions?: React.ReactNode;
}

const DEFAULT_LANGUAGES: NavbarLanguageConfig[] = [
  { code: 'en', label: 'EN', countryCode: 'US' },
  { code: 'pt', label: 'PT', countryCode: 'BR' },
  { code: 'es', label: 'ES', countryCode: 'ES' },
];

export function Navbar({
  links = [],
  currentPath = '/',
  homePath = '/',
  brandNameKey = 'branding.companyName',
  brandNameFallback = '',
  brandSuffixKey = 'branding.companySuffix',
  brandSuffixFallback = '',
  languages = DEFAULT_LANGUAGES,
  currentLanguage,
  onLanguageChange,
  userActions,
  headerActions,
}: NavbarProps) {
  const { t } = useTranslation('common');
  const [open, setOpen] = useState(false);

  const activeLanguage = currentLanguage ?? languages[0]?.code ?? 'en';
  const isAuthenticated = userActions?.isAuthenticated ?? false;
  const dashboardPath = userActions?.dashboardPath ?? '/dashboard';
  const loginPath = userActions?.loginPath ?? '/login';

  // Close drawer on route change
  useEffect(() => { setOpen(false); }, [currentPath]);

  const LangToggle = ({ className = '' }: { className?: string }) => {
    if (!onLanguageChange || languages.length <= 1) {
      return null;
    }

    const currentIndex = Math.max(languages.findIndex((language) => language.code === activeLanguage), 0);
    const targetLanguage = languages[(currentIndex + 1) % languages.length];
    const flagCode = targetLanguage.countryCode;
    
    return (
      <Button
        onClick={() => onLanguageChange(targetLanguage.code)}
        variant="outline"
        size="sm"
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border text-sm font-semibold text-muted-foreground hover:text-foreground hover:border-border/80 transition-colors ${className}`}
        aria-label={t('nav.switchLanguage', { defaultValue: `Switch to ${targetLanguage.label}` })}
      >
        {flagCode && (
          <ReactCountryFlag
            countryCode={flagCode}
            svg
            style={{ width: '1.2em', height: '1.2em', borderRadius: '2px' }}
          />
        )}
        {targetLanguage.label}
      </Button>
    );
  };

  const renderActionLink = (mobile = false) => {
    if (isAuthenticated) {
      return (
        <Link
          to={dashboardPath}
          className={`flex items-center gap-2 ${mobile ? 'px-3 py-3 rounded-xl' : 'px-4 py-2 rounded-full'} bg-secondary text-secondary-foreground text-sm font-medium hover:bg-secondary/80 transition-colors`}
        >
          <LayoutDashboard className="w-4 h-4" />
          {t(userActions?.dashboardLabelKey ?? 'nav.dashboard', userActions?.dashboardLabelFallback ?? 'Dashboard')}
        </Link>
      );
    }

    return (
      <Link
        to={loginPath}
        className={`flex items-center gap-1.5 ${mobile ? 'px-3 py-3 rounded-xl text-sm font-medium hover:bg-secondary/50' : 'px-3 py-2 rounded-lg text-sm'} text-muted-foreground hover:text-foreground transition-colors`}
      >
        <LogIn className="w-4 h-4" />
        {t(userActions?.loginLabelKey ?? 'auth.login', userActions?.loginLabelFallback ?? 'Login')}
      </Link>
    );
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      {/* ── Main bar ── */}
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <Link to={homePath} className="text-xl font-bold tracking-tight shrink-0 text-foreground">
          {t(brandNameKey, brandNameFallback)} <span className="text-primary font-light">{t(brandSuffixKey, brandSuffixFallback)}</span>
        </Link>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-6 text-sm font-medium">
          {links.map(link => (
            <Link
              key={link.to}
              to={link.to}
              className={`transition-colors ${currentPath === link.to ? 'text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
            >
              {t(link.key, link.labelFallback ?? '')}
            </Link>
          ))}
          {headerActions}
          <LangToggle />
          {renderActionLink()}
        </div>

        {/* Hamburger — mobile only */}
        <Button
          className="md:hidden text-muted-foreground hover:text-foreground transition-colors p-1"
          onClick={() => setOpen((o) => !o)}
          aria-label={open ? t('nav.closeMenu', 'Close menu') : t('nav.openMenu', 'Open menu')}
          variant="ghost"
          size="icon"
        >
          {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
        </Button>
      </div>

      {/* ── Mobile drawer ── */}
      {open && (
        <div className="md:hidden border-t border-border bg-background/95 backdrop-blur-md">
          <div className="px-6 py-4 flex flex-col gap-1">
            {links.map(link => (
              <Link
                key={link.to}
                to={link.to}
                className={`py-3 px-4 rounded-xl text-sm font-medium transition-colors ${
                  currentPath === link.to
                    ? 'bg-secondary text-secondary-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/50'
                }`}
              >
                {t(link.key, link.labelFallback ?? '')}
              </Link>
            ))}
            <div className="flex items-center gap-3 mt-3">
              {renderActionLink(true)}
              {headerActions}
              <LangToggle />
            </div>
          </div>
        </div>
      )}
    </nav>
  );
}
