import React, { useState, useMemo, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Calendar, RefreshCw, Activity, Filter, ChevronDown, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { calcDailyReturns, stdDev, calculateMaxDrawdown } from './mathUtils';

// --- Types ---
export interface SeriesConfig {
  key: string;
  name: string;
  color?: string; // CSS color string
}

export interface PerformanceDataRow {
  date: string;
  [key: string]: number | string;
}

export interface PerformanceAnalyzerProps {
  data: PerformanceDataRow[];
  seriesConfig: SeriesConfig[];
  riskFreeRate?: number;
  titleKey?: string;
  titleFallback?: string;
}

export function PerformanceAnalyzer({ 
  data = [], 
  seriesConfig = [], 
  riskFreeRate = 0.02,
  titleKey,
  titleFallback = "Normalized Price Performance"
}: PerformanceAnalyzerProps) {
  const { t } = useTranslation('common');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [activeSeries, setActiveSeries] = useState<string[]>([]);
  const [showStats, setShowStats] = useState(true);

  useEffect(() => {
    if (data.length > 0) {
      setStartDate(data[0].date as string);
      setEndDate(data[data.length - 1].date as string);
    }
    setActiveSeries(seriesConfig.map(s => s.key));
  }, [data, seriesConfig]);

  const toggleAll = (check: boolean) => {
    if (check) setActiveSeries(seriesConfig.map(s => s.key));
    else setActiveSeries([]);
  };

  const toggleSeries = (key: string) => {
    setActiveSeries(prev => 
      prev.includes(key) ? prev.filter(k => k !== key) : [...prev, key]
    );
  };

  const processedData = useMemo(() => {
    if (!data.length || !startDate || !endDate) return { chartData: [], stats: [] };
    
    const startIndex = data.findIndex(d => d.date >= startDate);
    const endIndex = data.findLastIndex(d => d.date <= endDate);
    if (startIndex === -1 || endIndex === -1 || startIndex >= endIndex) return { chartData: [], stats: [] };
    
    const windowData = data.slice(startIndex, endIndex + 1);
    const basePrices: Record<string, number> = {};
    activeSeries.forEach(key => { basePrices[key] = windowData[0][key] as number; });

    const chartData = windowData.map(row => {
      const normalizedRow: Record<string, any> = { date: row.date };
      activeSeries.forEach(key => {
        normalizedRow[key] = basePrices[key] ? (row[key] as number) / basePrices[key] : null;
      });
      return normalizedRow;
    });

    const statsObj = activeSeries.map(key => {
      const prices = windowData.map(r => r[key] as number).filter(v => v != null);
      if (prices.length < 2) return null;

      const returns = calcDailyReturns(prices);
      const tradingDays = returns.length;
      const years = tradingDays / 252;
      
      const totalReturn = (prices[prices.length - 1] / prices[0]) - 1;
      const annReturn = years > 0 ? Math.pow(1 + totalReturn, 1 / years) - 1 : 0;
      
      const dailyVol = stdDev(returns);
      const annVol = dailyVol * Math.sqrt(252);
      
      const sharpe = annVol > 0 ? (annReturn - riskFreeRate) / annVol : 0;
      const maxDrawdown = calculateMaxDrawdown(prices);

      return {
        key,
        name: seriesConfig.find(s => s.key === key)?.name,
        color: seriesConfig.find(s => s.key === key)?.color,
        totalReturn: totalReturn * 100,
        annReturn: annReturn * 100,
        annVol: annVol * 100,
        sharpe: sharpe,
        drawdown: maxDrawdown * 100
      };
    }).filter(Boolean);

    return { chartData, stats: statsObj };
  }, [data, startDate, endDate, activeSeries, seriesConfig, riskFreeRate]);

  return (
    <div className="flex flex-col gap-6 bg-card text-card-foreground p-6 rounded-2xl border border-border shadow-sm">
      
      {/* --- HEADER CONTROLS --- */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-border pb-4">
        <h2 className="text-xl font-bold flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          {titleKey ? t(titleKey, titleFallback) : titleFallback}
        </h2>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-muted/20 border border-border rounded-lg px-3 py-1.5 focus-within:border-primary/50 transition-colors">
            <Calendar className="w-4 h-4 text-muted-foreground" />
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)}
              className="bg-transparent text-sm text-foreground focus:outline-none placeholder-muted-foreground" 
            />
          </div>
          <span className="text-muted-foreground text-sm">{t('common.to', 'to')}</span>
          <div className="flex items-center gap-2 bg-muted/20 border border-border rounded-lg px-3 py-1.5 focus-within:border-primary/50 transition-colors">
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)}
              className="bg-transparent text-sm text-foreground focus:outline-none placeholder-muted-foreground" 
            />
          </div>
          <button 
            onClick={() => {
              setStartDate(data[0]?.date as string);
              setEndDate(data[data.length - 1]?.date as string);
            }}
            className="flex items-center gap-2 px-3 py-1.5 bg-muted/20 hover:bg-muted border border-border rounded-lg text-sm text-foreground transition-colors"
          >
            <RefreshCw className="w-4 h-4" /> {t('common.reset', 'Reset')}
          </button>
        </div>
      </div>

      {/* --- CHART --- */}
      <div className="h-[400px] w-full">
        {processedData.chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={processedData.chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis 
                dataKey="date" 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={11} 
                tickMargin={10} 
                tickFormatter={(val) => val.substring(0, 7)}
              />
              <YAxis 
                stroke="hsl(var(--muted-foreground))" 
                fontSize={11} 
                tickFormatter={(val) => val.toFixed(1)}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px', color: 'hsl(var(--card-foreground))' }}
                itemStyle={{ fontSize: '13px' }}
                labelStyle={{ color: 'hsl(var(--muted-foreground))', fontSize: '12px', marginBottom: '4px' }}
                formatter={(val: number) => [val.toFixed(3), 'Base=1']}
              />
              {activeSeries.map(key => {
                const conf = seriesConfig.find(s => s.key === key);
                return (
                  <Line 
                    key={key} 
                    type="monotone" 
                    dataKey={key} 
                    name={conf?.name} 
                    stroke={conf?.color || 'hsl(var(--primary))'} 
                    strokeWidth={2} 
                    dot={false}
                    activeDot={{ r: 4, strokeWidth: 0, fill: 'hsl(var(--background))' }}
                  />
                );
              })}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground text-sm">
            {t('chart.noData', 'No data available for the selected dates.')}
          </div>
        )}
      </div>

      {/* --- SERIES SELECTION --- */}
      <div className="bg-muted/10 border border-border rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Filter className="w-4 h-4" /> {t('chart.seriesSelection', 'Series Selection')}
          </p>
          <div className="flex gap-2">
            <button onClick={() => toggleAll(true)} className="text-xs px-2 py-1 bg-primary/10 text-primary hover:bg-primary/20 rounded border border-primary/20 transition-colors flex items-center gap-1">
              <Check className="w-3 h-3" /> {t('common.checkAll', 'Check All')}
            </button>
            <button onClick={() => toggleAll(false)} className="text-xs px-2 py-1 bg-muted/20 text-muted-foreground hover:text-foreground rounded border border-border transition-colors">
              {t('common.uncheckAll', 'Uncheck All')}
            </button>
          </div>
        </div>
        <div className="flex flex-wrap gap-4">
          {seriesConfig.map(s => {
            const isActive = activeSeries.includes(s.key);
            return (
              <label key={s.key} className="flex items-center gap-2 cursor-pointer group">
                <div onClick={() => toggleSeries(s.key)} className={`w-4 h-4 rounded-[4px] border border-border flex items-center justify-center transition-colors ${isActive ? 'bg-primary border-primary text-primary-foreground' : 'group-hover:border-primary/50'}`}>
                  {isActive && <Check className="w-3 h-3" />}
                </div>
                <span onClick={() => toggleSeries(s.key)} className="text-sm text-muted-foreground select-none group-hover:text-foreground transition-colors">{s.name}</span>
                <span className="w-2.5 h-2.5 rounded-full ml-1" style={{ backgroundColor: s.color || 'hsl(var(--primary))' }} />
              </label>
            );
          })}
        </div>
      </div>

      {/* --- STATISTICS TABLE --- */}
      <div className="border border-border rounded-xl overflow-hidden bg-muted/10">
        <button 
          onClick={() => setShowStats(!showStats)}
          className="w-full px-5 py-3 flex items-center justify-between bg-muted/5 hover:bg-muted/10 transition-colors"
        >
          <p className="text-sm font-semibold text-foreground flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            {t('chart.performanceStats', 'Selected Time Range Performance Statistics')}
          </p>
          <ChevronDown className={`w-4 h-4 text-muted-foreground transition-transform ${showStats ? 'rotate-180' : ''}`} />
        </button>
        
        <AnimatePresence>
          {showStats && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden"
            >
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-muted-foreground border-b border-border bg-muted/20">
                    <tr>
                      <th className="px-5 py-3 font-medium">{t('chart.measure', 'Measure')}</th>
                      {processedData.stats.map((s: any) => (
                        <th key={s.key} className="px-5 py-3 font-medium text-right" style={{ color: s.color || 'hsl(var(--primary))' }}>
                          {s.name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {[
                      { label: t('chart.totalReturn', "Total Return (%)"), key: "totalReturn" },
                      { label: t('chart.annReturn', "Annual Mean Return (%)"), key: "annReturn" },
                      { label: t('chart.annVol', "Annual Volatility (%)"), key: "annVol" },
                      { label: t('chart.sharpe', "Sharpe Ratio"), key: "sharpe", noPercent: true },
                      { label: t('chart.maxDrawdown', "Maximum Drawdown (%)"), key: "drawdown" }
                    ].map((row) => (
                      <tr key={row.key} className="hover:bg-muted/5 transition-colors">
                        <td className="px-5 py-3 text-foreground font-medium">{row.label}</td>
                        {processedData.stats.map((s: any) => (
                          <td key={`${s.key}-${row.key}`} className={`px-5 py-3 text-right font-mono ${s[row.key] < 0 ? 'text-destructive' : 'text-foreground'}`}>
                            {row.noPercent 
                              ? s[row.key].toFixed(4)
                              : `${s[row.key] > 0 ? '+' : ''}${s[row.key].toFixed(2)}%`}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

    </div>
  );
}
