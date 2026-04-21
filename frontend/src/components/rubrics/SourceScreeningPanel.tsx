import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

interface Props {
  screeningResult: Record<string, unknown> | null;
}

export function SourceScreeningPanel({ screeningResult }: Props) {
  const { t } = useTranslation();

  if (!screeningResult) return null;

  const rating = screeningResult.rating as string | undefined;
  const reason = screeningResult.reason as string | undefined;

  return (
    <Card className="p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.sourceScreening.title")}
      </p>
      {rating && (
        <p className="mb-1 text-sm font-medium text-foreground">
          {t(`fi.sourceScreening.rating`)}: {rating}
        </p>
      )}
      {reason && <p className="text-sm text-muted-foreground">{reason}</p>}
    </Card>
  );
}
