import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

interface Props {
  failureTags: Record<string, unknown> | null;
}

export function FailureTagsTable({ failureTags }: Props) {
  const { t } = useTranslation();

  if (!failureTags) return null;

  const entries = Object.entries(failureTags);
  if (entries.length === 0) return null;

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.failureTags.title")}
      </p>
      <div className="flex flex-wrap gap-2">
        {entries.map(([tag, value]) => (
          <Badge key={tag} variant="secondary" className="text-xs">
            {tag}
            {value !== true && value !== null ? `: ${String(value)}` : ""}
          </Badge>
        ))}
      </div>
    </Card>
  );
}
