import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { WeightingModeResult } from "@/types";

interface WeightingComparisonProps {
  weighting_comparison: Record<string, WeightingModeResult> | null;
}

const MODES = ["uniform", "heuristic", "whitened_uniform"] as const;

function topModel(shares: Record<string, number>): [string, number] {
  const entries = Object.entries(shares);
  if (!entries.length) return ["n/a", 0];
  return entries.sort(([, a], [, b]) => b - a)[0] as [string, number];
}

export function WeightingComparison({ weighting_comparison }: WeightingComparisonProps) {
  const { t } = useTranslation();

  if (!weighting_comparison) return null;

  const modeKeys = MODES.filter((m) => m in weighting_comparison);
  if (!modeKeys.length) return null;

  const winningClusters = modeKeys.map((m) => weighting_comparison[m].winning_cluster);
  const allSameWinner = winningClusters.every((c) => c === winningClusters[0]);

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.weighting.title")}
      </p>
      <div className="grid gap-3 sm:grid-cols-3">
        {modeKeys.map((mode) => {
          const data = weighting_comparison[mode];
          const [top, share] = topModel(data.model_shares);
          const isDisagreement =
            !allSameWinner &&
            data.winning_cluster !== weighting_comparison[modeKeys[0]].winning_cluster;

          const modeLabel =
            mode === "uniform"
              ? t("results.weighting.uniform")
              : mode === "heuristic"
                ? t("results.weighting.heuristic")
                : t("results.weighting.whitened");

          return (
            <div
              key={mode}
              className={`rounded-md border p-3 ${isDisagreement ? "border-destructive/40 bg-destructive/5" : "border-border bg-muted/20"}`}
            >
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                {modeLabel}
              </p>
              <p className="text-xs text-muted-foreground">
                {t("results.weighting.winningCluster")}
              </p>
              <p className="mb-1 text-sm font-semibold text-foreground">
                {t("results.cluster.label")} {data.winning_cluster}
                {isDisagreement && (
                  <span className="ml-1 text-[10px] text-destructive">
                    {t("results.weighting.disagreement")}
                  </span>
                )}
              </p>
              <p className="text-xs text-muted-foreground">{t("results.weighting.topModel")}</p>
              <p className="truncate text-sm font-medium text-foreground">{top}</p>
              <p className="mt-0.5 text-xs text-muted-foreground">{Math.round(share * 100)}%</p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
