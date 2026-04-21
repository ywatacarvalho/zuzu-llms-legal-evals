import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { RubricCriterion } from "@/types";

interface RubricCardProps {
  criteria: RubricCriterion[];
}

export function RubricCard({ criteria }: RubricCardProps) {
  const { t } = useTranslation();

  return (
    <Card className="p-4">
      <h3 className="mb-4 text-sm font-semibold text-foreground">
        {t("rubrics.criteria.title")}
      </h3>
      <ul className="space-y-3">
        {criteria.map((criterion) => (
          <li key={criterion.id} className="flex gap-4">
            <div className="flex w-14 shrink-0 flex-col items-center justify-start pt-0.5">
              <span className="text-lg font-bold text-primary">
                {Math.round(criterion.weight * 100)}%
              </span>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-foreground">{criterion.name}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                {criterion.description}
              </p>
            </div>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-right text-xs text-muted-foreground">
        {criteria.length} {t("rubrics.criteria.count")}
        {" · "}
        {t("rubrics.criteria.totalWeight")}{" "}
        {Math.round(criteria.reduce((s, c) => s + c.weight, 0) * 100)}%
      </p>
    </Card>
  );
}
