# SidebarLayout Component

## Overview
A highly polished, reusable fixed-sidebar application layout. Built with sleek glassmorphism, Framer Motion route transition highlighting, and native mobile responsiveness (hamburger menu and overlay drawer).

## Props
- `navigation` (Array): An array of objects defining your links: `{ to: string, icon: LucideIcon, label: string, end?: boolean }`
- `brandName` (string): Primary text top left.
- `brandSubtitle` (string): Accent text below brand name.
- `user` (Object): Display details for the bottom left strip `{ name, role, initials }`.
- `onLogout` (Function): Handler for the logout button.
- `logoutLabel` (string): Localized logout text.
- `breadcrumb` (string | Node): Content to render in the top bar.

## Usage
Wrap your central application `Outlet` inside this layout within your Router layout layer:

```jsx
import { SidebarLayout } from './components/analytics/SidebarLayout/SidebarLayout';
import { Home, Settings } from 'lucide-react';
import { Outlet } from 'react-router-dom';

function MyAdminLayout() {
  const navLinks = [
    { to: '/dashboard', icon: Home, label: 'Overview', end: true },
    { to: '/dashboard/settings', icon: Settings, label: 'Settings' }
  ];

  return (
    <SidebarLayout 
      navigation={navLinks}
      brandName="My Premium App"
      user={{ name: 'Alex', role: 'admin', initials: 'A' }}
    >
      <Outlet />
    </SidebarLayout>
  );
}
```
