import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { RubricCriterion } from "@/types";

interface CriterionHeatmapProps {
  baseline_scores: Record<string, Record<string, number>> | null;
  criteria: RubricCriterion[] | null;
  winning_cluster: number | null;
}

function scoreColor(score: number): string {
  // Red (0) → Yellow (0.5) → Green (1)
  const r = score < 0.5 ? 220 : Math.round(220 - (score - 0.5) * 2 * 180);
  const g = score > 0.5 ? 160 : Math.round(score * 2 * 160);
  return `rgb(${r}, ${g}, 60)`;
}

export function CriterionHeatmap({
  baseline_scores,
  criteria,
  winning_cluster,
}: CriterionHeatmapProps) {
  const { t } = useTranslation();

  if (!baseline_scores || !criteria?.length) return null;

  const clusterIds = Object.keys(baseline_scores).sort(
    (a, b) =>
      (baseline_scores[b][criteria[0]?.id] ?? 0) - (baseline_scores[a][criteria[0]?.id] ?? 0)
  );

  const sortedCriteria = [...criteria].sort((a, b) => b.weight - a.weight);

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.heatmap.title")}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="pb-2 pr-3 text-left text-muted-foreground">
                {t("results.heatmap.cluster")}
              </th>
              {sortedCriteria.map((c) => (
                <th
                  key={c.id}
                  className="max-w-[80px] truncate px-1 pb-2 text-center text-muted-foreground"
                  title={c.name}
                >
                  {c.name.length > 12 ? `${c.name.slice(0, 12)}…` : c.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {clusterIds.map((cid) => {
              const isWinner = Number(cid) === winning_cluster;
              return (
                <tr key={cid} className={isWinner ? "outline outline-1 outline-primary/40" : ""}>
                  <td
                    className={`py-1 pr-3 font-medium ${isWinner ? "text-primary" : "text-foreground"}`}
                  >
                    {t("results.cluster.label")} {cid}
                    {isWinner && <span className="ml-1 text-[9px] text-primary">★</span>}
                  </td>
                  {sortedCriteria.map((c) => {
                    const score = baseline_scores[cid]?.[c.id] ?? 0;
                    return (
                      <td key={c.id} className="px-1 py-1 text-center">
                        <span
                          className="inline-block h-7 w-full min-w-[36px] rounded text-[10px] font-semibold leading-7 text-white shadow-sm"
                          style={{ backgroundColor: scoreColor(score) }}
                          title={`${c.name}: ${score.toFixed(2)}`}
                        >
                          {score.toFixed(2)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
