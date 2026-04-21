import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

interface SilhouetteChartProps {
  silhouette_scores_by_k: Record<string, number> | null;
  selectedK: number;
}

export function SilhouetteChart({ silhouette_scores_by_k, selectedK }: SilhouetteChartProps) {
  const { t } = useTranslation();

  if (!silhouette_scores_by_k || !Object.keys(silhouette_scores_by_k).length) return null;

  const data = Object.entries(silhouette_scores_by_k)
    .map(([k, score]) => ({ k: Number(k), score: Math.round(score * 1000) / 1000 }))
    .sort((a, b) => a.k - b.k);

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.silhouette.title")}
      </p>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -24, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis
            dataKey="k"
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "6px",
              fontSize: 12,
            }}
            formatter={(value: number) => [value.toFixed(3), "Silhouette"]}
            labelFormatter={(label) => `k = ${label}`}
          />
          <ReferenceLine
            x={selectedK}
            stroke="hsl(var(--primary))"
            strokeDasharray="4 2"
            label={{
              value: t("results.silhouette.selectedK"),
              position: "top",
              fontSize: 10,
              fill: "hsl(var(--primary))",
            }}
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="hsl(var(--primary))"
            strokeWidth={2}
            dot={{ r: 3, fill: "hsl(var(--primary))" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}
