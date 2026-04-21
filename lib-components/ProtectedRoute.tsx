import React from 'react';
import { Navigate, Outlet, useParams } from 'react-router-dom';
// import { useAuth } from '../context/AuthContext'
import { Loader } from 'lucide-react';

const ROLE_RANK: Record<string, number> = { viewer: 1, editor: 2, admin: 3 };

function hasRole(userRole: string | undefined, requiredRole: string) {
  if (!userRole) return false;
  return (ROLE_RANK[userRole] ?? 0) >= (ROLE_RANK[requiredRole] ?? 99);
}

export interface ProtectedRouteUser {
  role?: string;
}

export interface ProtectedRouteProps {
  user?: ProtectedRouteUser | null;
  isLoading?: boolean;
  requiredRole?: string;
  loginPath?: string;
  fallbackPath?: string;
  loadingFallback?: React.ReactNode;
}

export function ProtectedRoute({
  user,
  isLoading = false,
  requiredRole,
  loginPath,
  fallbackPath,
  loadingFallback,
}: ProtectedRouteProps) {
  const { lang = 'en' } = useParams<{ lang: string }>();
  const resolvedLoginPath = loginPath ?? `/${lang}/login`;
  const resolvedFallbackPath = fallbackPath ?? `/${lang}`;

  if (isLoading) {
    if (loadingFallback) {
      return <>{loadingFallback}</>;
    }

    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!user) return <Navigate to={resolvedLoginPath} replace />;

  if (requiredRole && !hasRole(user.role, requiredRole)) {
    return <Navigate to={resolvedFallbackPath} replace />;
  }

  return <Outlet />;
}
