import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { Rubric } from "@/types";

interface Props {
  rubric: Rubric;
}

const KEY_FIELDS: Array<{ key: string; label: string }> = [
  { key: "doctrine_pack", label: "controllerCard.doctrinePack" },
  { key: "selected_lane_code", label: "controllerCard.laneCode" },
  { key: "workflow_source_case_name", label: "controllerCard.sourceCase" },
  { key: "workflow_source_case_citation", label: "controllerCard.sourceCitation" },
  { key: "case_citation_verification_mode", label: "controllerCard.verificationMode" },
];

export function ControllerCardPanel({ rubric }: Props) {
  const { t } = useTranslation();
  const [showFull, setShowFull] = useState(false);

  if (!rubric.controller_card) return null;

  const prominentValues: Record<string, unknown> = {
    doctrine_pack: rubric.doctrine_pack,
    selected_lane_code: rubric.selected_lane_code ?? "none",
    workflow_source_case_name: rubric.workflow_source_case_name,
    workflow_source_case_citation: rubric.workflow_source_case_citation,
    case_citation_verification_mode: String(rubric.case_citation_verification_mode),
  };

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("controllerCard.title")}
      </p>
      <dl className="grid gap-2 sm:grid-cols-2">
        {KEY_FIELDS.map(({ key, label }) => (
          <div key={key} className="rounded-md bg-muted/50 p-2 text-sm">
            <dt className="mb-0.5 text-xs font-medium text-muted-foreground">{t(label)}</dt>
            <dd className="font-medium text-foreground">
              {prominentValues[key] != null ? String(prominentValues[key]) : "—"}
            </dd>
          </div>
        ))}
      </dl>
      <button
        className="mt-3 flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        onClick={() => setShowFull((v) => !v)}
        type="button"
      >
        {showFull ? (
          <>
            <ChevronUp className="h-3 w-3" />
            {t("controllerCard.hideFull")}
          </>
        ) : (
          <>
            <ChevronDown className="h-3 w-3" />
            {t("controllerCard.showFull")}
          </>
        )}
      </button>
      {showFull && (
        <pre className="mt-2 max-h-80 overflow-auto rounded-md bg-muted/40 p-3 text-[11px] leading-relaxed text-muted-foreground">
          {JSON.stringify(rubric.controller_card, null, 2)}
        </pre>
      )}
    </Card>
  );
}
