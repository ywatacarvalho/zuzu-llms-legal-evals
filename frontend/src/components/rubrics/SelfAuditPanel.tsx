import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface Props {
  selfAuditResult: Record<string, unknown> | null;
}

export function SelfAuditPanel({ selfAuditResult }: Props) {
  const { t } = useTranslation();

  if (!selfAuditResult) return null;

  const classification = selfAuditResult.classification as string | undefined;
  const entries = Object.entries(selfAuditResult).filter(([k]) => k !== "classification");

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("fi.selfAudit.title")}
        </p>
        {classification && <Badge variant="secondary">{classification}</Badge>}
      </div>
      {entries.length > 0 && (
        <dl className="space-y-1.5">
          {entries.map(([key, value]) => (
            <div key={key} className="grid grid-cols-[180px_1fr] gap-2 text-sm">
              <dt className="font-medium text-foreground">{key}</dt>
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
