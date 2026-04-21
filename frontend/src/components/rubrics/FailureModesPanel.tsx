import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface FailureMode {
  code?: string;
  label?: string;
  description?: string;
  severity?: string;
}

interface Props {
  failureModes: Record<string, unknown>[] | null;
}

const SEVERITY_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  high: "destructive",
  medium: "secondary",
  low: "outline",
};

export function FailureModesPanel({ failureModes }: Props) {
  const { t } = useTranslation();

  if (!failureModes || failureModes.length === 0) return null;

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.failureModes.title")}
      </p>
      <ul className="space-y-3">
        {(failureModes as FailureMode[]).map((fm, i) => (
          <li key={fm.code ?? i} className="rounded-md border p-3">
            <div className="mb-1 flex items-center gap-2">
              {fm.code && (
                <span className="font-mono text-xs text-muted-foreground">{fm.code}</span>
              )}
              {fm.label && <span className="text-sm font-medium text-foreground">{fm.label}</span>}
              {fm.severity && (
                <Badge
                  variant={SEVERITY_VARIANT[fm.severity] ?? "outline"}
                  className="ml-auto text-xs"
                >
                  {fm.severity}
                </Badge>
              )}
            </div>
            {fm.description && <p className="text-sm text-muted-foreground">{fm.description}</p>}
          </li>
        ))}
      </ul>
    </Card>
  );
}
