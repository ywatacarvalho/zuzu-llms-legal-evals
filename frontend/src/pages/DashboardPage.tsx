import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { getDashboardStats } from "@/services/dashboardApi";
import type { DashboardStats } from "@/types";

interface KpiCardProps {
  title: string;
  value: number | string;
}

function KpiCard({ title, value }: KpiCardProps) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-bold text-foreground">{value}</p>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { t } = useTranslation("dashboard");
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, []);

  const display = (val: number) => (loading ? "—" : val);

  if (error) {
    return (
      <div>
        <PageHeader title={t("dashboard.title")} description={t("dashboard.subtitle")} />
        <p className="text-sm text-destructive">{t("dashboard.statsError")}</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title={t("dashboard.title")} description={t("dashboard.subtitle")} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard title={t("dashboard.kpi.totalCases")} value={display(stats?.total_cases ?? 0)} />
        <KpiCard
          title={t("dashboard.kpi.evaluationsRun")}
          value={display(stats?.evaluations_run ?? 0)}
        />
        <KpiCard
          title={t("dashboard.kpi.modelsEvaluated")}
          value={display(stats?.models_evaluated ?? 0)}
        />
        <KpiCard
          title={t("dashboard.kpi.avgClusters")}
          value={loading ? "—" : (stats?.avg_clusters ?? 0)}
        />
      </div>
    </div>
  );
}
