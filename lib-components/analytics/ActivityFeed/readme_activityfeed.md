# ActivityFeed Component

## Overview
A sleek, vertical timeline component perfect for Audit Logs, User Session tracking, or System Logs. Features a continuous vertical track with customizable, glowing event nodes.

## Props
- `activities` (Array of Objects): The events to render. Each object can contain: `{ id, icon: LucideIcon, title, description, timestamp, badge, color: string }`. Color should be a pair of tailwind classes (e.g. `bg-red-500/20 text-red-400`).
- `title` (string): Header title. Defaults to `"Recent Activity"`.

## Usage
```jsx
import { ActivityFeed } from './components/analytics/ActivityFeed/ActivityFeed';
import { UserPlus, Settings } from 'lucide-react';

const logs = [
  { 
    id: 1, 
    icon: UserPlus, 
    title: "New User Registered", 
    description: "Alex Ywata created an admin account.", 
    timestamp: "10:42 AM", 
    color: "bg-green-500/20 text-green-400" 
  }
];

<ActivityFeed activities={logs} />
```
