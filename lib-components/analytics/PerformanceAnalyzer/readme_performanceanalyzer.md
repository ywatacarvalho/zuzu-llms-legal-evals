# PerformanceAnalyzer Component

## Overview
A hyper-advanced, self-calculating financial time-series analyzer. Recreates classic corporate "Normalized Price Performance" dashboards using sleek dark-mode React paradigms. 

It handles raw unnormalized daily pricing data, automatically normalizes it dynamically based on user-defined date inputs, and **mathematically calculates** risk statistics (Sharpe Ratio, Annualized Volatility, Max Drawdown) on the fly for the selected viewing window!

## Key Features
- **Dynamic Normalization:** Base = 1 logic is calculated instantly when dates drag.
- **Series Filtering:** Elegant UI controls for multiline charting selection.
- **On-The-Fly Statistics Engine:** Computes Mean Returns, Standard Deviation, and Maximum Drawdowns natively in JS without needing continuous backend roundtrips.

## Props
- `data` (Array): Array of records. Example: `[{ date: '2023-01-01', asx: 4300, aex: 500 }, ...]`
- `seriesConfig` (Array): Map keys to human labels and colors. Example: `[{ key: 'asx', name: 'ASX 200', color: '#3b82f6' }]`
- `riskFreeRate` (Number): Used for Sharpe. Default `0.02`.

## Usage
```jsx
// Simply feed it raw daily closing prices!
import { PerformanceAnalyzer } from './components/analytics/PerformanceAnalyzer/PerformanceAnalyzer';

<PerformanceAnalyzer 
  data={myHistoricalPricingArray} 
  seriesConfig={[
    { key: 'ibov', name: 'IBOVESPA', color: '#10b981' },
    { key: 'sp500', name: 'S&P 500', color: '#f43f5e' }
  ]}
/>
```
