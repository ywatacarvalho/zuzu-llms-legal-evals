import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

interface Props {
  goldAnswer: string | null;
}

export function GoldAnswerPanel({ goldAnswer }: Props) {
  const { t } = useTranslation();

  if (!goldAnswer) return null;

  return (
    <Card className="p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.goldAnswer.title")}
      </p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">{goldAnswer}</p>
    </Card>
  );
}
