import { PropsWithChildren } from 'react';
import { cn } from '../lib/cn';

export function Card({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('rounded-xl border border-border bg-card text-card-foreground shadow-sm', className)}>{children}</div>;
}

export function CardHeader({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('flex flex-col space-y-1.5 p-4', className)}>{children}</div>;
}

export function CardTitle({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('text-sm font-semibold tracking-tight', className)}>{children}</div>;
}

export function CardDescription({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('text-sm text-muted-foreground', className)}>{children}</div>;
}

export function CardContent({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('p-4 pt-0', className)}>{children}</div>;
}

export function CardFooter({ className, children }: PropsWithChildren<{ className?: string }>) {
  return <div className={cn('flex items-center p-4 pt-0', className)}>{children}</div>;
}
