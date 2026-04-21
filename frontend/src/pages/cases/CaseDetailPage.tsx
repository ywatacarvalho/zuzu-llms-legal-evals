import { ArrowLeft } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { getCase } from "@/services/casesApi";
import type { LegalCase } from "@/types";

export function CaseDetailPage() {
  const { t } = useTranslation();
  const { caseId } = useParams<{ caseId: string }>();
  const navigate = useNavigate();

  const [legalCase, setLegalCase] = useState<LegalCase | null>(null);
  const [loadingCase, setLoadingCase] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;

    getCase(caseId)
      .then(setLegalCase)
      .catch(() => setError(t("errors.generic")))
      .finally(() => setLoadingCase(false));
  }, [caseId, t]);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/cases")}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          {t("cases.title")}
        </Button>
      </div>

      {loadingCase && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {legalCase && (
        <>
          <PageHeader title={legalCase.title} description={legalCase.filename} />

          <Card className="p-4">
            <h3 className="mb-3 text-sm font-semibold text-foreground">
              {t("cases.detail.extractedText")}
            </h3>
            {legalCase.raw_text ? (
              <pre className="max-h-[50vh] overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-muted-foreground">
                {legalCase.raw_text}
              </pre>
            ) : (
              <p className="text-sm text-muted-foreground">{t("cases.detail.noText")}</p>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
