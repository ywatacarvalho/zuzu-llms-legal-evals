import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

const HEADING_KEYS = [
  "source_benchmark_alignment",
  "controlling_doctrine_match",
  "gate_order_correctness",
  "trigger_test_accuracy",
  "exception_substitute_mapping",
  "fallback_doctrine_treatment",
  "factual_fidelity",
  "provenance_discipline",
] as const;

interface Props {
  comparison: Record<string, unknown> | null;
}

export function DraftComparisonPanel({ comparison }: Props) {
  const { t } = useTranslation();

  if (!comparison) return null;

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.draftComparison.title")}
      </p>
      <dl className="space-y-2">
        {HEADING_KEYS.map((key) => {
          const value = comparison[key];
          if (value === undefined || value === null) return null;
          return (
            <div key={key} className="rounded-md border p-2 text-sm">
              <dt className="mb-0.5 font-medium text-foreground">{key.replace(/_/g, " ")}</dt>
              <dd className="text-muted-foreground">
                {typeof value === "object" ? JSON.stringify(value) : String(value)}
              </dd>
            </div>
          );
        })}
      </dl>
    </Card>
  );
}
