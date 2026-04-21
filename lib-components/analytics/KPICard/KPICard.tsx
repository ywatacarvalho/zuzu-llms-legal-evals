import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
// These imports mock the standard shadcn/ui Card location in an Antigravity setup
// import { Card, CardContent } from "@/components/ui/card"
import { Card, CardContent } from '../../ui/card';

export interface KPICardProps {
  titleKey: string;
  titleFallback?: string;
  value: string | number;
  subtitleKey?: string;
  subtitleFallback?: string;
  icon?: LucideIcon;
  color?: 'blue' | 'red' | 'cyan' | 'orange' | 'green' | 'purple' | 'primary' | 'secondary' | 'destructive';
  delta?: string;
  loading?: boolean;
}

import { useTranslation } from 'react-i18next';

export function KPICard({ 
  titleKey, 
  titleFallback = 'Metric', 
  value, 
  subtitleKey, 
  subtitleFallback, 
  icon: Icon, 
  color = 'primary',
  delta,
  loading = false,
}: KPICardProps) {
  const { t } = useTranslation('common');

  // We abstract the border emphasis using dynamic utility concatenation, 
  // relying on standard css variable colors mapping to the app theme.
  const toneTokens: Record<string, string> = {
    blue: 'hsl(var(--chart-1))',
    red: 'hsl(var(--destructive))',
    cyan: 'hsl(var(--chart-2))',
    orange: 'hsl(var(--chart-4))',
    green: 'hsl(var(--chart-2))',
    purple: 'hsl(var(--chart-5))',
    primary: 'hsl(var(--primary))',
    secondary: 'hsl(var(--secondary-foreground))',
    destructive: 'hsl(var(--destructive))',
  };
  const toneColor = toneTokens[color] || 'hsl(var(--primary))';

  return (
    <Card
      className="relative overflow-hidden"
    >
    <motion.div
      whileHover={{ y: -2 }}
      className="flex items-center justify-between gap-3 py-3 px-4 pl-5"
    >
      {/* Accent Line */}
      <div className="absolute top-0 left-0 h-full w-1 border-l-4" style={{ backgroundColor: toneColor, borderColor: toneColor, opacity: 0.18 }} />
      
      <CardContent className="flex min-w-0 flex-1 items-center justify-between gap-3 p-0">
        <div className="flex min-w-0 flex-col justify-center">
          <p className="mb-0.5 truncate text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
            {t(titleKey, titleFallback)}
          </p>
          <div className="flex items-baseline gap-2">
            <h3 className="truncate text-xl font-bold leading-none tracking-tight">{loading ? t('common.loading', 'Loading...') : value}</h3>
            {delta && <span className="truncate text-xs font-medium" style={{ color: toneColor }}>{delta}</span>}
          </div>
          {(subtitleKey || subtitleFallback) && (
            <p className="mt-1 truncate text-[10px] text-muted-foreground">
              {subtitleKey ? t(subtitleKey, { defaultValue: subtitleFallback ?? '' }) : subtitleFallback}
            </p>
          )}
        </div>

        {Icon && (
          <div className="shrink-0 rounded-full border border-border/60 p-2" style={{ color: toneColor, backgroundColor: 'color-mix(in srgb, ' + toneColor + ' 12%, transparent)' }}>
            <Icon className="h-4 w-4 opacity-90" />
          </div>
        )}
      </CardContent>
    </motion.div>
    </Card>
  );
}
