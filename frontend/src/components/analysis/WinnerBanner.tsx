import { Trophy } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";

interface WinnerBannerProps {
  bestModel: string;
  bestModelShare: number;
  winningCluster: number;
  winningScore: number;
}

export function WinnerBanner({
  bestModel,
  bestModelShare,
  winningCluster,
  winningScore,
}: WinnerBannerProps) {
  const { t } = useTranslation();

  return (
    <Card className="border-primary/30 bg-gradient-to-r from-primary/5 via-primary/10 to-primary/5 p-6">
      <div className="flex items-start gap-4">
        <div className="rounded-xl bg-primary/10 p-3">
          <Trophy className="h-7 w-7 text-primary" />
        </div>
        <div className="flex-1">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t("results.winner.label")}
          </p>
          <p className="text-2xl font-bold text-foreground">{bestModel}</p>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("results.winner.clusterShare", {
              pct: Math.round(bestModelShare * 100),
              cluster: winningCluster,
            })}
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            {t("results.winner.clusterScore")}
          </p>
          <p className="text-3xl font-bold text-primary">
            {Math.round(winningScore * 100)}
            <span className="text-base font-normal text-muted-foreground">%</span>
          </p>
        </div>
      </div>
    </Card>
  );
}
