import React from 'react';
import { motion } from 'framer-motion';
import { LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';

export interface ActivityItem {
  id: string | number;
  icon?: LucideIcon;
  color?: string; // Tailwind class like text-primary
  titleKey?: string;
  title?: string;
  timestamp: string;
  descriptionKey?: string;
  description?: string;
  badgeKey?: string;
  badge?: string;
}

export interface ActivityFeedProps {
  activities?: ActivityItem[];
  titleKey?: string;
  titleFallback?: string;
}

export function ActivityFeed({ 
  activities = [],
  titleKey,
  titleFallback = "Recent Activity" 
}: ActivityFeedProps) {
  const { t } = useTranslation('common');

  return (
    <div className="bg-card border border-border rounded-2xl p-6 h-full flex flex-col shadow-sm text-card-foreground">
      <h3 className="text-lg font-semibold tracking-tight mb-6">
        {titleKey ? t(titleKey, titleFallback) : titleFallback}
      </h3>
      
      <div className="flex-1 overflow-y-auto pr-4 scrollbar-hide relative">
        {/* Continuous vertical line */}
        <div className="absolute left-[19px] top-4 bottom-4 w-px bg-border" />
        
        <div className="space-y-6">
          {activities.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div 
                key={item.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="relative flex gap-4 group"
              >
                {/* Node */}
                <div className="relative z-10">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-4 border-card ${item.color || 'bg-primary/20 text-primary'}`}>
                    {Icon ? <Icon className="w-4 h-4" /> : <div className="w-2 h-2 rounded-full bg-current" />}
                  </div>
                </div>
                
                {/* Content */}
                <div className="flex-1 pt-1.5 pb-2">
                  <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1 mb-1">
                    <p className="text-sm font-medium">
                      {item.titleKey ? t(item.titleKey, item.title ?? '') : item.title}
                    </p>
                    <span className="text-xs font-mono text-muted-foreground shrink-0">
                      {item.timestamp}
                    </span>
                  </div>
                  {(item.descriptionKey || item.description) && (
                    <p className="text-sm text-muted-foreground leading-relaxed">
                      {item.descriptionKey ? t(item.descriptionKey, item.description ?? '') : item.description}
                    </p>
                  )}
                  {(item.badgeKey || item.badge) && (
                    <span className="inline-block mt-2 text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border border-border bg-muted/50 text-muted-foreground">
                      {item.badgeKey ? t(item.badgeKey, item.badge ?? '') : item.badge}
                    </span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
