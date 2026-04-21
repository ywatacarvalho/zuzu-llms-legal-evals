import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { extractOnly } from "@/services/rubricsApi";
import type { FIStatus, Rubric } from "@/types";

interface Props {
  rubric: Rubric;
  onUpdate: (updated: Partial<Rubric>) => void;
}

export function ModeActionsPanel({ rubric, onUpdate }: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExtractOnly = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await extractOnly(rubric.id);
      onUpdate({
        screening_result: result.screening_result as Record<string, unknown> | null,
        source_extraction: result.source_extraction as Record<string, unknown> | null,
        routing_metadata: result.routing_metadata as Record<string, unknown> | null,
        doctrine_pack: result.doctrine_pack as string | null,
      });
    } catch {
      setError(t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  const showExtractOnly = !rubric.source_extraction;
  const isExtracting = (rubric.fi_status as FIStatus) === "extracting";
  const isAwaiting = (rubric.fi_status as FIStatus) === "awaiting_review";

  return (
    <Card className="p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.modeActions.title")}
      </p>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      {isExtracting && (
        <p className="text-sm text-muted-foreground">{t("fi.modeActions.extracting")}</p>
      )}

      {isAwaiting && (
        <p className="text-sm text-muted-foreground">{t("fi.modeActions.awaitingReview")}</p>
      )}

      {showExtractOnly && !isExtracting && (
        <Button size="sm" onClick={handleExtractOnly} disabled={loading}>
          {t("fi.modeActions.runExtract")}
        </Button>
      )}
    </Card>
  );
}
