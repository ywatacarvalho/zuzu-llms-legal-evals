import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { Module0Metadata } from "@/types";

const MODULE0_KEYS: Array<keyof Module0Metadata> = [
  "bottom_line_outcome",
  "outcome_correctness",
  "reasoning_alignment",
  "jurisdiction_assumption",
  "controlling_doctrine_named",
];

const MODULE0_LABELS: Record<keyof Module0Metadata, string> = {
  bottom_line_outcome: "module0.bottomLine",
  outcome_correctness: "module0.outcomeCorrectness",
  reasoning_alignment: "module0.reasoningAlignment",
  jurisdiction_assumption: "module0.jurisdictionAssumption",
  controlling_doctrine_named: "module0.controllingDoctrine",
};

const CORRECTNESS_COLORS: Record<string, string> = {
  correct: "text-green-600 dark:text-green-400",
  partial: "text-amber-600 dark:text-amber-400",
  incorrect: "text-destructive",
  unclear: "text-muted-foreground",
};

const ALIGNMENT_COLORS: Record<string, string> = {
  aligned: "text-green-600 dark:text-green-400",
  partial: "text-amber-600 dark:text-amber-400",
  misaligned: "text-destructive",
};

interface Props {
  tags: Record<string, unknown> | null;
}

function isModule0(tags: Record<string, unknown>): tags is Record<keyof Module0Metadata, unknown> {
  return MODULE0_KEYS.some((k) => k in tags);
}

export function MetadataTagsPanel({ tags }: Props) {
  const { t } = useTranslation();

  if (!tags) return null;
  const entries = Object.entries(tags).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  const structured = isModule0(tags);

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {structured ? t("module0.title") : t("fi.metadataTags.title")}
      </p>
      {structured ? (
        <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {MODULE0_KEYS.filter((k) => tags[k] != null).map((k) => {
            const val = String(tags[k]);
            const colorClass =
              k === "outcome_correctness"
                ? (CORRECTNESS_COLORS[val] ?? "")
                : k === "reasoning_alignment"
                  ? (ALIGNMENT_COLORS[val] ?? "")
                  : "";
            return (
              <div key={k} className="rounded-md bg-muted/50 p-2 text-sm">
                <dt className="mb-0.5 text-xs font-medium text-muted-foreground">
                  {t(MODULE0_LABELS[k])}
                </dt>
                <dd className={`font-medium ${colorClass || "text-foreground"}`}>{val}</dd>
              </div>
            );
          })}
        </dl>
      ) : (
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {entries.map(([key, value]) => (
            <div key={key} className="rounded-md bg-muted/50 p-2 text-sm">
              <dt className="mb-0.5 font-medium text-foreground">{key}</dt>
              <dd className="text-muted-foreground">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </Card>
  );
}
