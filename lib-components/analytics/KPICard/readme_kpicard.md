# KPICard Component

## Overview
The `KPICard` component displays a single Key Performance Indicator metrics box. It is designed to sit gracefully at the top of an analytical dashboard, featuring glassmorphic effects, left-aligned coloured accents, and micro-hover animations using Framer Motion.

## Props
- `title` (string): The label for the metric (e.g., "Total Exposure").
- `value` (string | number): The primary data to display (e.g., "$50M").
- `subtitle` (string) _optional_: Additional context like comparative data or dates.
- `icon` (Lucide React component) _optional_: An icon rendered at the top right.
- `color` (string) _optional_: The theme color for the accent border and icon. Valid options are `blue`, `red`, `cyan`, `orange`, `green`. Default is `blue`.

## Usage
```jsx
import { DollarSign } from 'lucide-react';
import { KPICard } from './components/analytics/KPICard/KPICard';

function MyDashboardRow() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
      <KPICard 
        title="Total Revenue" 
        value="$903M" 
        subtitle="Up 2.4% from last quarter"
        icon={DollarSign}
        color="green"
      />
    </div>
  );
}
```
