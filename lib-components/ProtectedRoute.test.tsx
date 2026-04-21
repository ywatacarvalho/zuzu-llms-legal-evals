import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { ProtectedRoute, ProtectedRouteProps } from './ProtectedRoute';

function buildRouter(props: ProtectedRouteProps, initialPath = '/en/app') {
  return createMemoryRouter(
    [
      {
        path: '/:lang/app',
        element: <ProtectedRoute {...props} />,
        children: [{ index: true, element: <div>Protected Content</div> }],
      },
      { path: '/:lang/login', element: <div>Login Page</div> },
      { path: '/:lang', element: <div>Home Page</div> },
    ],
    { initialEntries: [initialPath] }
  );
}

describe('ProtectedRoute', () => {
  it('renders children when user is authenticated', () => {
    render(<RouterProvider router={buildRouter({ user: { role: 'viewer' } })} />);
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('redirects to login when user is absent', () => {
    render(<RouterProvider router={buildRouter({ user: undefined })} />);
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('shows loading spinner when isLoading is true and no loadingFallback', () => {
    render(<RouterProvider router={buildRouter({ user: undefined, isLoading: true })} />);
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders custom loadingFallback when isLoading is true', () => {
    render(
      <RouterProvider
        router={buildRouter({
          user: undefined,
          isLoading: true,
          loadingFallback: <div>Please wait...</div>,
        })}
      />
    );
    expect(screen.getByText('Please wait...')).toBeInTheDocument();
  });

  it('redirects to fallback when user role is insufficient', () => {
    render(
      <RouterProvider
        router={buildRouter({ user: { role: 'viewer' }, requiredRole: 'admin' })}
      />
    );
    expect(screen.getByText('Home Page')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('renders children when user role exactly meets required role', () => {
    render(
      <RouterProvider
        router={buildRouter({ user: { role: 'editor' }, requiredRole: 'editor' })}
      />
    );
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('renders children when user role exceeds required role', () => {
    render(
      <RouterProvider
        router={buildRouter({ user: { role: 'admin' }, requiredRole: 'editor' })}
      />
    );
    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('uses custom loginPath for unauthenticated redirect', () => {
    const router = createMemoryRouter(
      [
        {
          path: '/app',
          element: <ProtectedRoute user={undefined} loginPath="/custom-login" />,
          children: [{ index: true, element: <div>Protected Content</div> }],
        },
        { path: '/custom-login', element: <div>Custom Login</div> },
      ],
      { initialEntries: ['/app'] }
    );
    render(<RouterProvider router={router} />);
    expect(screen.getByText('Custom Login')).toBeInTheDocument();
  });
});
