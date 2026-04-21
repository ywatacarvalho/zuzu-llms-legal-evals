import React from 'react';
import { BarChart as RechartsBarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useTranslation } from 'react-i18next';

export interface ChartData {
  [key: string]: string | number;
}

export interface BarChartProps {
  data: ChartData[];
  xAxisKey: string;
  barKey: string;
  titleKey?: string;
  titleFallback?: string;
  color?: string; // Expecting CSS variable format like 'var(--primary)' or tailwind class text-primary
  showGrid?: boolean;
}

export function BarChart({ 
  data, 
  xAxisKey, 
  barKey, 
  titleKey, 
  titleFallback,
  color = 'hsl(var(--primary))', 
  showGrid = true 
}: BarChartProps) {
  const { t } = useTranslation('common');
  
  return (
    <div className="w-full h-[280px] p-3 bg-background border border-border rounded-xl shadow-sm flex flex-col">
      {titleKey && (
        <h4 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest mb-2 pl-1">
          {t(titleKey, titleFallback ?? '')}
        </h4>
      )}
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <RechartsBarChart
            data={data}
            margin={{ top: 5, right: 10, left: -20, bottom: 5 }}
            barSize={24}
          >
            {showGrid && (
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            )}
            <XAxis 
              dataKey={xAxisKey} 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} 
              dy={10}
            />
            <YAxis 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} 
              tickFormatter={(value) => value >= 1000 ? `${(value / 1000).toFixed(1)}k` : value}
            />
            <Tooltip 
              cursor={{ fill: 'hsl(var(--secondary))' }}
              contentStyle={{ 
                backgroundColor: 'hsl(var(--background))', 
                borderColor: 'hsl(var(--border))', 
                borderRadius: '8px', 
                color: 'hsl(var(--foreground))',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)'
              }}
              itemStyle={{ color: color, fontWeight: 'bold' }}
            />
            <Bar 
              dataKey={barKey} 
              radius={[4, 4, 0, 0]}
              isAnimationActive={true}
              animationDuration={1000}
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={color} 
                />
              ))}
            </Bar>
          </RechartsBarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
