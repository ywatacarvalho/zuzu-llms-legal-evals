import { Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { EvaluationForm } from "@/components/evaluations/EvaluationForm";
import { EvaluationsTable } from "@/components/evaluations/EvaluationsTable";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { listEvaluations } from "@/services/evaluationsApi";
import type { Evaluation } from "@/types";

export function EvaluationsPage() {
  const { t } = useTranslation();
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const fetchEvaluations = useCallback(() => {
    setLoading(true);
    setError(null);
    listEvaluations()
      .then(setEvaluations)
      .catch(() => setError(t("errors.generic")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    fetchEvaluations();
  }, [fetchEvaluations]);

  const handleCreated = (evaluation: Evaluation) => {
    setEvaluations((prev) => [evaluation, ...prev]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader title={t("evaluations.title")} description={t("evaluations.subtitle")} />
        <Button onClick={() => setFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("evaluations.new")}
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && (
        <div className="flex items-center gap-3">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchEvaluations}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            {t("actions.retry")}
          </Button>
        </div>
      )}
      {!loading && !error && <EvaluationsTable evaluations={evaluations} />}

      <EvaluationForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onCreated={handleCreated}
      />
    </div>
  );
}
