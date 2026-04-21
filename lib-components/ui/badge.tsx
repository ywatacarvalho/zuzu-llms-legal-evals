import { PropsWithChildren } from 'react';
import { cn } from '../lib/cn';

export function Badge({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <span className={cn('inline-flex items-center rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground', className)}>{children}</span>;
}
