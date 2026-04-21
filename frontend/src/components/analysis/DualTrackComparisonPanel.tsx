import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Analysis } from "@/types";

interface RankEntry {
  model: string;
  base_rank: number;
  variation_rank: number;
  delta: number;
}

interface Props {
  analysis: Analysis;
}

function buildRankTable(variation_scores: Record<string, unknown>): RankEntry[] {
  const vs = variation_scores as {
    base_ranking?: Record<string, number>;
    variation_ranking?: Record<string, number>;
  };
  if (!vs.base_ranking || !vs.variation_ranking) return [];
  const models = Object.keys(vs.base_ranking);
  return models
    .map((m) => ({
      model: m,
      base_rank: vs.base_ranking![m],
      variation_rank: vs.variation_ranking![m],
      delta: vs.base_ranking![m] - vs.variation_ranking![m],
    }))
    .sort((a, b) => a.base_rank - b.base_rank);
}

export function DualTrackComparisonPanel({ analysis }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!analysis.variation_scores) return null;

  const rows = buildRankTable(analysis.variation_scores as Record<string, unknown>);

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("dualTrack.title")}
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="border-t border-border px-4 pb-4 pt-3">
          {rows.length > 0 ? (
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-muted-foreground">
                      {t("dualTrack.model")}
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-muted-foreground">
                      {t("dualTrack.baseRank")}
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-muted-foreground">
                      {t("dualTrack.varRank")}
                    </th>
                    <th className="px-3 py-2 text-center font-semibold text-muted-foreground">
                      {t("dualTrack.delta")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr key={r.model} className="border-t border-border">
                      <td className="px-3 py-2 font-medium text-foreground">
                        {r.model.split("/").pop()}
                      </td>
                      <td className="px-3 py-2 text-center text-muted-foreground">{r.base_rank}</td>
                      <td className="px-3 py-2 text-center text-muted-foreground">
                        {r.variation_rank}
                      </td>
                      <td className="px-3 py-2 text-center font-semibold">
                        <span
                          className={
                            r.delta > 0
                              ? "text-green-600 dark:text-green-400"
                              : r.delta < 0
                                ? "text-destructive"
                                : "text-muted-foreground"
                          }
                        >
                          {r.delta > 0 ? `+${r.delta}` : r.delta}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t("dualTrack.noData")}</p>
          )}
        </div>
      )}
    </div>
  );
}
