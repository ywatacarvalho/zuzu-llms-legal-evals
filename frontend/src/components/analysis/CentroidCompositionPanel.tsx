import { useTranslation } from "react-i18next";

import type { CentroidComposition } from "@/types";

interface Props {
  composition: CentroidComposition | null | undefined;
}

export function CentroidCompositionPanel({ composition }: Props) {
  const { t } = useTranslation();

  if (!composition) return null;

  return (
    <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {t("centroidComposition.title")}
      </p>
      <div className="mb-2 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>
          <span className="font-medium text-foreground">
            {t("centroidComposition.totalResponses")}:{" "}
          </span>
          {composition.cluster_size_total}
        </span>
        <span>
          <span className="font-medium text-foreground">
            {t("centroidComposition.representedModels")}:{" "}
          </span>
          {composition.represented_model_count}
        </span>
        <span>
          <span className="font-medium text-foreground">
            {t("centroidComposition.dominantModel")}:{" "}
          </span>
          {composition.dominant_model_name.split("/").pop()} (
          {Math.round(composition.dominant_model_share * 100)}%)
        </span>
      </div>
      <div className="space-y-1.5">
        {composition.model_breakdown.map((entry) => (
          <div key={entry.model_name} className="flex items-center gap-2 text-xs">
            <span className="w-28 shrink-0 truncate text-muted-foreground" title={entry.model_name}>
              {entry.model_name.split("/").pop()}
            </span>
            <div className="flex-1 overflow-hidden rounded-full bg-muted">
              <div
                className="h-1.5 rounded-full bg-primary/60"
                style={{ width: `${Math.round(entry.answer_share * 100)}%` }}
              />
            </div>
            <span className="w-8 shrink-0 text-right font-medium text-foreground">
              {Math.round(entry.answer_share * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
