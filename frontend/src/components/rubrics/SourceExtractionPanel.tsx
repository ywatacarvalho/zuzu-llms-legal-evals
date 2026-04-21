import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

interface Props {
  sourceExtraction: Record<string, unknown> | null;
}

export function SourceExtractionPanel({ sourceExtraction }: Props) {
  const { t } = useTranslation();

  if (!sourceExtraction) return null;

  const entries = Object.entries(sourceExtraction).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.sourceExtraction.title")}
      </p>
      <dl className="space-y-1.5">
        {entries.map(([key, value]) => (
          <div key={key} className="grid grid-cols-[180px_1fr] gap-2 text-sm">
            <dt className="font-medium text-foreground">{key}</dt>
            <dd className="text-muted-foreground">{String(value)}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
