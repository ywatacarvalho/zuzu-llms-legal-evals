# Charts Components

## Overview
This folder contains highly stylized chart wrappers using `recharts`. They are pre-configured to match the premium dark-mode aesthetic of the analytics dashboards, including glowing tooltips, smooth animations, and glassmorphic container backgrounds.

## Available Components

### `DonutChart`
A circular statistical graphic, divided into slices to illustrate numerical proportion.

**Props:**
- `data` (Array): E.g., `[{ name: 'Stage 1', value: 400 }, ...]`
- `colors` (Array) _optional_: Custom hex array for the slices.
- `title` (string) _optional_: Label displayed at the top.

### `BarChart`
A chart that presents categorical data with rectangular bars with heights proportional to the values that they represent.

**Props:**
- `data` (Array): E.g., `[{ category: 'Retail', value: 800 }, ...]`
- `xAxisKey` (string): The object key used for the X-axis label (e.g., `'category'`)
- `barKey` (string): The object key used for the actual value (e.g., `'value'`)
- `title` (string) _optional_
- `color` (string) _optional_: The hex code for the bar color. Default is `blue`.
- `showGrid` (boolean) _optional_: Checkered background grid. Default is `true`.

## Usage
```jsx
import { DonutChart, BarChart } from './components/analytics/Charts/DonutChart';

const donutData = [
  { name: 'Stage 1', value: 400 },
  { name: 'Stage 2', value: 300 },
];

function AnalyticsCharts() {
  return (
    <div className="grid grid-cols-2 gap-4">
      <DonutChart data={donutData} title="PPE By Stage" />
      <BarChart data={donutData} xAxisKey="name" barKey="value" title="Segment History" />
    </div>
  );
}
```
