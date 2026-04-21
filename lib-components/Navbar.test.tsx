import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Navbar } from './Navbar';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: string | Record<string, unknown>) => {
      if (typeof opts === 'string') return opts;
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) return String(opts.defaultValue);
      return key;
    },
  }),
}));

vi.mock('react-country-flag', () => ({
  default: ({ countryCode }: { countryCode: string }) => (
    <span data-testid={`flag-${countryCode}`} />
  ),
}));

const wrap = (ui: React.ReactNode) => render(<MemoryRouter>{ui}</MemoryRouter>);

describe('Navbar', () => {
  it('renders brand name and suffix from props', () => {
    wrap(<Navbar brandNameFallback="Acme" brandSuffixFallback="Platform" />);
    expect(screen.getByText('Acme')).toBeInTheDocument();
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });

  it('renders provided nav links', () => {
    wrap(
      <Navbar
        links={[
          { key: 'nav.home', to: '/', labelFallback: 'Home' },
          { key: 'nav.about', to: '/about', labelFallback: 'About' },
        ]}
      />
    );
    expect(screen.getAllByText('Home').length).toBeGreaterThan(0);
    expect(screen.getAllByText('About').length).toBeGreaterThan(0);
  });

  it('renders no nav links when links prop is empty', () => {
    wrap(<Navbar links={[]} />);
    expect(screen.queryByRole('link', { name: /reports/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /publications/i })).not.toBeInTheDocument();
  });

  it('shows login link when not authenticated', () => {
    wrap(
      <Navbar userActions={{ isAuthenticated: false, loginLabelFallback: 'Sign In' }} />
    );
    expect(screen.getAllByText('Sign In').length).toBeGreaterThan(0);
  });

  it('shows dashboard link when authenticated', () => {
    wrap(
      <Navbar
        userActions={{ isAuthenticated: true, dashboardLabelFallback: 'My Dashboard' }}
      />
    );
    expect(screen.getAllByText('My Dashboard').length).toBeGreaterThan(0);
  });

  it('renders language switcher showing next language when onLanguageChange is provided', () => {
    wrap(
      <Navbar
        languages={[
          { code: 'en', label: 'EN', countryCode: 'US' },
          { code: 'pt', label: 'PT', countryCode: 'BR' },
        ]}
        currentLanguage="en"
        onLanguageChange={vi.fn()}
      />
    );
    // Shows the next language label (PT when current is EN)
    expect(screen.getByText('PT')).toBeInTheDocument();
  });

  it('does not render language switcher when onLanguageChange is absent', () => {
    wrap(
      <Navbar
        languages={[
          { code: 'en', label: 'EN', countryCode: 'US' },
          { code: 'pt', label: 'PT', countryCode: 'BR' },
        ]}
        currentLanguage="en"
      />
    );
    expect(screen.queryByText('PT')).not.toBeInTheDocument();
  });

  it('does not render language switcher when only one language is available', () => {
    wrap(
      <Navbar
        languages={[{ code: 'en', label: 'EN', countryCode: 'US' }]}
        currentLanguage="en"
        onLanguageChange={vi.fn()}
      />
    );
    expect(screen.queryByText('EN')).not.toBeInTheDocument();
  });
});
