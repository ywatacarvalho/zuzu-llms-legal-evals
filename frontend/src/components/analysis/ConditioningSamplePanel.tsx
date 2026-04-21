import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { Rubric } from "@/types";

interface ConditioningSamplePanelProps {
  rubric: Rubric;
  initialOpen?: boolean;
}

function ConditioningCard({ index, text }: { index: number; text: string }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const preview = 300;
  const isLong = text.length > preview;
  const display = expanded || !isLong ? text : `${text.slice(0, preview)}…`;

  return (
    <Card className="p-3">
      <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        {t("results.conditioning.centroid")} {index + 1}
      </p>
      <p className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">{display}</p>
      {isLong && (
        <button
          className="mt-1 flex items-center gap-1 text-[11px] text-primary"
          onClick={() => setExpanded((v) => !v)}
          type="button"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              {t("results.cluster.showLess")}
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              {t("results.cluster.showMore")}
            </>
          )}
        </button>
      )}
    </Card>
  );
}

function SetupResponsesSummary({ responses }: { responses: Rubric["setup_responses"] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!responses?.length) return null;

  const countByModel = responses.reduce<Record<string, number>>((acc, r) => {
    acc[r.model] = (acc[r.model] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="rounded-md border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("results.conditioning.setupResponses")} ({responses.length})
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="space-y-1 border-t border-border px-4 pb-3 pt-2">
          {Object.entries(countByModel).map(([model, count]) => (
            <div key={model} className="flex items-center justify-between text-xs">
              <span className="text-foreground">{model}</span>
              <span className="text-muted-foreground">
                {count} {t("results.conditioning.setupCount")}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ConditioningSamplePanel({
  rubric,
  initialOpen = false,
}: ConditioningSamplePanelProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(initialOpen);

  const hasSample = rubric.conditioning_sample?.length;
  const hasRef = rubric.strong_reference_text || rubric.weak_reference_text;
  if (!hasSample && !hasRef && !rubric.setup_responses?.length) return null;

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-4 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("results.conditioning.title")}
        </p>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div className="space-y-4 border-t border-border px-4 pb-4 pt-3">
          {/* Conditioning centroids */}
          {rubric.conditioning_sample?.length ? (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("results.conditioning.title")} — {rubric.conditioning_sample.length} centroids
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {rubric.conditioning_sample.map((text, i) => (
                  <ConditioningCard key={i} index={i} text={text} />
                ))}
              </div>
            </div>
          ) : null}

          {/* Reference pair */}
          {hasRef && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("results.conditioning.referencePair")}
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {rubric.strong_reference_text && (
                  <Card className="p-3">
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-green-600 dark:text-green-400">
                      {t("results.conditioning.strong")}
                    </p>
                    <p className="line-clamp-6 whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                      {rubric.strong_reference_text}
                    </p>
                  </Card>
                )}
                {rubric.weak_reference_text && (
                  <Card className="p-3">
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-destructive">
                      {t("results.conditioning.weak")}
                    </p>
                    <p className="line-clamp-6 whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                      {rubric.weak_reference_text}
                    </p>
                  </Card>
                )}
              </div>
            </div>
          )}

          {/* Setup responses */}
          <SetupResponsesSummary responses={rubric.setup_responses} />
        </div>
      )}
    </div>
  );
}
