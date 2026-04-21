import { Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { CaseUploadDialog } from "@/components/cases/CaseUploadDialog";
import { CasesTable } from "@/components/cases/CasesTable";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/PageHeader";
import { listCases } from "@/services/casesApi";
import type { LegalCase } from "@/types";

export function CasesPage() {
  const { t } = useTranslation();
  const [cases, setCases] = useState<LegalCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  const fetchCases = useCallback(() => {
    setLoading(true);
    setError(null);
    listCases()
      .then(setCases)
      .catch(() => setError(t("errors.generic")))
      .finally(() => setLoading(false));
  }, [t]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const handleUploaded = (newCase: LegalCase) => {
    setCases((prev) => [newCase, ...prev]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <PageHeader title={t("cases.title")} description={t("cases.subtitle")} />
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t("cases.upload")}
        </Button>
      </div>

      {loading && <div className="text-sm text-muted-foreground">{t("actions.loading")}</div>}

      {error && (
        <div className="flex items-center gap-3">
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="outline" size="sm" onClick={fetchCases}>
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            {t("actions.retry")}
          </Button>
        </div>
      )}

      {!loading && !error && <CasesTable cases={cases} />}

      <CaseUploadDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onUploaded={handleUploaded}
      />
    </div>
  );
}
