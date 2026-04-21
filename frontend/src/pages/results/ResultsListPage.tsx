import { BarChart2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { listEvaluations } from "@/services/evaluationsApi";
import { EvaluationStatus, type Evaluation } from "@/types";

export function ResultsListPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResults = useCallback(() => {
    setLoading(true);
    setError(null);
    listEvaluations()
      .then((all) => setEvaluations(all.filter((e) => e.status === EvaluationStatus.Done)))
      .catch(() => setError(t("errors.generic")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  return (
    <div className="space-y-6">
      <PageHeader title={t("results.list.title")} description={t("results.list.subtitle")} />

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && (
        <div className="flex items-center gap-3">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchResults}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            {t("actions.retry")}
          </Button>
        </div>
      )}

      {!loading && !error && evaluations.length === 0 && (
        <p className="text-sm text-muted-foreground">{t("results.list.empty")}</p>
      )}

      {evaluations.length > 0 && (
        <div className="space-y-2">
          {evaluations.map((ev) => (
            <div
              key={ev.id}
              className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card p-4"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{ev.question}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {new Date(ev.created_at).toLocaleString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={ev.status} />
                <Button size="sm" onClick={() => navigate(`/results/${ev.id}`)}>
                  <BarChart2 className="mr-1.5 h-3.5 w-3.5" />
                  {t("results.list.viewResults")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
