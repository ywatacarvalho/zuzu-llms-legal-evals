import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RechartsTooltip, Legend } from 'recharts';
import { useTranslation } from 'react-i18next';

export interface DonutData {
  name: string;
  value: number;
}

export interface DonutChartProps {
  data: DonutData[];
  colors?: string[]; // CSS values
  titleKey?: string;
  titleFallback?: string;
}

export function DonutChart({ 
  data, 
  colors = ['hsl(var(--chart-1))', 'hsl(var(--chart-2))', 'hsl(var(--chart-3))', 'hsl(var(--chart-4))', 'hsl(var(--chart-5))'], 
  titleKey,
  titleFallback
}: DonutChartProps) {
  const { t } = useTranslation('common');

  return (
    <div className="w-full h-[280px] p-3 bg-background border border-border rounded-xl shadow-sm flex flex-col">
      {(titleKey || titleFallback) && (
        <h4 className="text-muted-foreground text-[10px] font-bold uppercase tracking-widest mb-1 pl-1">
          {titleKey ? t(titleKey, titleFallback ?? '') : titleFallback}
        </h4>
      )}
      <div className="flex-1 w-full min-h-0 relative">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius="60%"
              outerRadius="80%"
              paddingAngle={5}
              dataKey="value"
              stroke="none"
              isAnimationActive={true}
              animationBegin={0}
              animationDuration={800}
              animationEasing="ease-out"
            >
              {data.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={colors[index % colors.length]} 
                />
              ))}
            </Pie>
            <RechartsTooltip 
              contentStyle={{ 
                backgroundColor: 'hsl(var(--background))', 
                borderColor: 'hsl(var(--border))', 
                borderRadius: '8px', 
                color: 'hsl(var(--foreground))',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)'
              }}
              itemStyle={{ color: 'hsl(var(--foreground))', fontWeight: '500' }}
            />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle" 
              wrapperStyle={{ fontSize: '11px', color: 'hsl(var(--muted-foreground))', paddingTop: '4px' }} 
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
