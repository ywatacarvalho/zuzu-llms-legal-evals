import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";
import type { RubricStatus } from "@/types";

interface RubricStatusBadgeProps {
  status: RubricStatus;
}

const STATUS_VARIANT: Record<RubricStatus, BadgeProps["variant"]> = {
  building: "warning",
  frozen: "success",
  failed: "destructive",
};

export function RubricStatusBadge({ status }: RubricStatusBadgeProps) {
  const { t } = useTranslation();

  return <Badge variant={STATUS_VARIANT[status]}>{t(`rubricStatus.${status}`)}</Badge>;
}
