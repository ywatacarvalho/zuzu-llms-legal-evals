import { useTranslation } from "react-i18next";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { Card } from "@/components/ui/card";

const COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-5))",
  "hsl(var(--primary))",
];

interface ModelShareChartProps {
  modelShares: Record<string, number>;
}

export function ModelShareChart({ modelShares }: ModelShareChartProps) {
  const { t } = useTranslation();

  const data = Object.entries(modelShares)
    .sort(([, a], [, b]) => b - a)
    .map(([model, share]) => ({
      name: model,
      value: Math.round(share * 100),
    }));

  return (
    <Card className="p-4">
      <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.modelShare.title")}
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={95}
            paddingAngle={3}
            dataKey="value"
            label={({ name, value }: { name: string; value: number }) =>
              `${name.split("/").pop() ?? name} ${value}%`
            }
            labelLine={false}
          >
            {data.map((_, index) => (
              <Cell key={index} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value: number) => [`${value}%`, t("results.modelShare.share")]} />
          <Legend
            formatter={(value: string) => <span className="text-xs text-foreground">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </Card>
  );
}
