import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { Rubric, RubricCriterion } from "@/types";

const DELTA_COLORS: Record<string, string> = {
  cosmetic: "bg-muted text-muted-foreground",
  localized_factual: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300",
  ambiguity_sensitive: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300",
  doctrinally_material: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
};

interface Props {
  rubric: Rubric;
}

export function VariationRubricPanel({ rubric }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!rubric.dual_rubric_mode || !rubric.variation_criteria) return null;

  const varCriteria = Array.isArray(rubric.variation_criteria)
    ? (rubric.variation_criteria as RubricCriterion[])
    : [];

  return (
    <Card className="overflow-hidden">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("variation.variationRubricTitle")}
        </span>
        <span className="flex items-center gap-2">
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
            {rubric.selected_lane_code}
          </span>
          {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </span>
      </button>
      {open && (
        <div className="border-t border-border">
          {varCriteria.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-3 py-2 text-left font-semibold text-muted-foreground">
                      {t("results.heatmap.criterion")}
                    </th>
                    <th className="px-3 py-2 text-left font-semibold text-muted-foreground">
                      Description
                    </th>
                    <th className="px-3 py-2 text-right font-semibold text-muted-foreground">
                      Weight
                    </th>
                    <th className="px-3 py-2 text-left font-semibold text-muted-foreground">
                      {t("variation.changeType")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {varCriteria.map((c) => {
                    const deltaType = (c as RubricCriterion & { delta_type?: string }).delta_type;
                    return (
                      <tr key={c.id} className="border-t border-border">
                        <td className="px-3 py-2 font-medium text-foreground">{c.name}</td>
                        <td className="px-3 py-2 text-muted-foreground">{c.description}</td>
                        <td className="px-3 py-2 text-right font-semibold text-foreground">
                          {(c.weight * 100).toFixed(1)}%
                        </td>
                        <td className="px-3 py-2">
                          {deltaType && (
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${DELTA_COLORS[deltaType] ?? "bg-muted text-muted-foreground"}`}
                            >
                              {deltaType}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">
              {t("variation.noVariationCriteria")}
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
