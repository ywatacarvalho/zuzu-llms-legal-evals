import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Card } from "@/components/ui/card";

interface ClusterScoreChartProps {
  scores: Record<string, number>;
  winningCluster: number;
}

export function ClusterScoreChart({ scores, winningCluster }: ClusterScoreChartProps) {
  const { t } = useTranslation();

  const data = Object.entries(scores)
    .sort(([a], [b]) => Number(a) - Number(b))
    .map(([clusterId, score]) => ({
      cluster: `${t("results.cluster.label")} ${clusterId}`,
      score: Math.round(score * 100),
      id: Number(clusterId),
    }));

  return (
    <Card className="p-4">
      <p className="mb-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.clusterScores.title")}
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="cluster" tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} />
          <YAxis
            domain={[0, 100]}
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
          />
          <Tooltip formatter={(value: number) => [`${value}%`, t("results.clusterScores.score")]} />
          <Bar dataKey="score" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.id === winningCluster ? "hsl(var(--chart-1))" : "hsl(var(--chart-2))"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}
