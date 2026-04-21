import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";

interface Props {
  doctrinePack: string | null;
  routingMetadata?: Record<string, unknown> | null;
}

export function DoctrinePackBadge({ doctrinePack, routingMetadata }: Props) {
  const { t } = useTranslation();

  if (!doctrinePack) return null;

  const confidence = routingMetadata?.confidence as string | undefined;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.doctrinePack.title")}:
      </span>
      <Badge variant="secondary">{doctrinePack}</Badge>
      {confidence && (
        <Badge variant="outline" className="text-xs">
          {t("fi.doctrinePack.confidence")}: {confidence}
        </Badge>
      )}
    </div>
  );
}
