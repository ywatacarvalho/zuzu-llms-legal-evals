import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import type { CentroidComposition, ClusterResult, OverlayResult } from "@/types";
import { CentroidCompositionPanel } from "./CentroidCompositionPanel";
import { CentroidResponseRenderer } from "./CentroidResponseRenderer";
import { OverlayCapsPanel } from "./OverlayCapsPanel";

const PREVIEW_CHARS = 400;

interface CentroidCardProps {
  cluster: ClusterResult;
  score: number;
  isWinner: boolean;
  composition?: CentroidComposition | null;
  overlay?: OverlayResult | null;
  finalScore?: number | null;
}

export function CentroidCard({
  cluster,
  score,
  isWinner,
  composition,
  overlay,
  finalScore,
}: CentroidCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const text = cluster.centroid_response_text?.trim() ?? "";
  const isLong = text.length > PREVIEW_CHARS;
  const displayText = expanded || !isLong ? text : `${text.slice(0, PREVIEW_CHARS)}...`;
  const displayScore = finalScore ?? score;
  const scorePct = Math.min(
    100,
    Math.max(0, Math.round(displayScore * (finalScore != null ? 1 : 100)))
  );

  const modelEntries = cluster.model_counts
    ? Object.entries(cluster.model_counts).sort(([, a], [, b]) => b - a)
    : [];

  return (
    <Card
      className={`overflow-hidden ${isWinner ? "border-primary/60 ring-1 ring-primary/20" : ""}`}
    >
      {isWinner && <div className="h-1 bg-primary" />}

      <div className="p-4">
        {/* Header row */}
        <div className="mb-2 flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-foreground">
              {t("results.cluster.label")} {cluster.cluster_id}
            </span>
            {isWinner && (
              <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary">
                {t("results.cluster.winner")}
              </span>
            )}
          </div>
          <div className="shrink-0 text-right">
            <span className="text-2xl font-bold text-foreground">{scorePct}</span>
            <span className="text-sm font-normal text-muted-foreground">
              {finalScore != null ? "" : "%"}
            </span>
            <p className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {finalScore != null ? t("overlay.finalScore") : t("results.cluster.score")}
            </p>
            {finalScore != null && (
              <p className="text-[10px] text-muted-foreground">
                {t("results.cluster.score")}: {Math.round(score * 100)}%
              </p>
            )}
          </div>
        </div>

        {/* Score progress bar */}
        <div className="mb-3 h-1.5 overflow-hidden rounded-full bg-muted">
          <div
            className={`h-full rounded-full transition-all ${isWinner ? "bg-primary" : "bg-muted-foreground/40"}`}
            style={{ width: `${scorePct}%` }}
          />
        </div>

        {/* Stats row: response count + model breakdown */}
        <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="text-xs text-muted-foreground">
            {t("results.cluster.responseCount", { count: cluster.response_indices.length })}
          </span>
          {modelEntries.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {modelEntries.map(([model, count]) => (
                <span
                  key={model}
                  title={model}
                  className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                >
                  {model.split("/").pop()}: {count}
                </span>
              ))}
            </div>
          )}
        </div>

        <CentroidCompositionPanel composition={composition ?? cluster.composition} />
        <OverlayCapsPanel overlay={overlay ?? cluster.overlay} />

        {/* Centroid response text */}
        <div>
          <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {t("results.cluster.centroidResponse")}
          </p>
          <div className="rounded-md border border-border bg-muted/35 p-4">
            {text ? (
              <CentroidResponseRenderer text={displayText} />
            ) : (
              <p className="text-sm text-muted-foreground">{t("results.cluster.emptyCentroid")}</p>
            )}
            {isLong && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 h-7 px-2 text-xs"
                onClick={() => setExpanded((e) => !e)}
              >
                {expanded ? (
                  <>
                    <ChevronUp className="mr-1 h-3 w-3" />
                    {t("results.cluster.showLess")}
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-1 h-3 w-3" />
                    {t("results.cluster.showMore")}
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
