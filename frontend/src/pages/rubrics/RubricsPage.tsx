import { Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { RubricForm } from "@/components/rubrics/RubricForm";
import { RubricsTable } from "@/components/rubrics/RubricsTable";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { listRubrics } from "@/services/rubricsApi";
import type { Rubric } from "@/types";

export function RubricsPage() {
  const { t } = useTranslation();
  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const fetchRubrics = useCallback(() => {
    setLoading(true);
    setError(null);
    listRubrics()
      .then(setRubrics)
      .catch(() => setError(t("errors.generic")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    fetchRubrics();
  }, [fetchRubrics]);

  const handleCreated = (rubric: Rubric) => {
    setRubrics((prev) => [rubric, ...prev]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader title={t("rubrics.title")} description={t("rubrics.subtitle")} />
        <Button onClick={() => setFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("rubrics.new")}
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && (
        <div className="flex items-center gap-3">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchRubrics}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            {t("actions.retry")}
          </Button>
        </div>
      )}
      {!loading && !error && <RubricsTable rubrics={rubrics} />}

      <RubricForm open={formOpen} onClose={() => setFormOpen(false)} onCreated={handleCreated} />
    </div>
  );
}
