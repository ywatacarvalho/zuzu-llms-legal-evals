import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { TrendingUp } from 'lucide-react';
import { KPICard } from './KPICard';

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: string | Record<string, unknown>) => {
      if (typeof opts === 'string') return opts;
      if (opts && typeof opts === 'object' && 'defaultValue' in opts) return String(opts.defaultValue);
      return key;
    },
  }),
}));

vi.mock('framer-motion', async () => {
  const { forwardRef, createElement } = await import('react');
  return {
    motion: {
      div: forwardRef((props: any, ref: any) => createElement('div', { ...props, ref })),
    },
    AnimatePresence: ({ children }: any) => children,
  };
});

describe('KPICard', () => {
  it('renders title and value', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="$1,200" />);
    expect(screen.getByText('Revenue')).toBeInTheDocument();
    expect(screen.getByText('$1,200')).toBeInTheDocument();
  });

  it('shows loading text when loading=true and hides value', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="$1,200" loading />);
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByText('$1,200')).not.toBeInTheDocument();
  });

  it('renders positive delta when provided', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="100" delta="+12%" />);
    expect(screen.getByText('+12%')).toBeInTheDocument();
  });

  it('renders negative delta when provided', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="100" delta="-5%" />);
    expect(screen.getByText('-5%')).toBeInTheDocument();
  });

  it('does not render delta element when delta is absent', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="100" />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('renders subtitleFallback when provided', () => {
    render(
      <KPICard
        titleKey="kpi.revenue"
        titleFallback="Revenue"
        value="100"
        subtitleFallback="vs last month"
      />
    );
    expect(screen.getByText('vs last month')).toBeInTheDocument();
  });

  it('renders icon svg when icon prop is provided', () => {
    render(<KPICard titleKey="kpi.revenue" titleFallback="Revenue" value="100" icon={TrendingUp} />);
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('renders all tone variants without crashing', () => {
    const tones = [
      'blue', 'red', 'cyan', 'orange', 'green',
      'purple', 'primary', 'secondary', 'destructive',
    ] as const;
    for (const color of tones) {
      const { unmount } = render(
        <KPICard titleKey="t" titleFallback={color} value="1" color={color} />
      );
      expect(screen.getByText(color)).toBeInTheDocument();
      unmount();
    }
  });
});
