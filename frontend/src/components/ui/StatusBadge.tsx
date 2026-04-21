import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";
import { EvaluationStatus } from "@/types";

interface StatusBadgeProps {
  status: EvaluationStatus;
}

const STATUS_VARIANT: Record<EvaluationStatus, BadgeProps["variant"]> = {
  [EvaluationStatus.Pending]: "secondary",
  [EvaluationStatus.RubricBuilding]: "warning",
  [EvaluationStatus.RubricFrozen]: "warning",
  [EvaluationStatus.Running]: "warning",
  [EvaluationStatus.Done]: "success",
  [EvaluationStatus.Failed]: "destructive",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { t } = useTranslation();

  return <Badge variant={STATUS_VARIANT[status]}>{t(`status.${status}`)}</Badge>;
}
