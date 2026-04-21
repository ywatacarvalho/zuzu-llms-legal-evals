import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { approveRubric } from "@/services/rubricsApi";
import type { Rubric } from "@/types";

interface Props {
  rubric: Rubric;
  onUpdate: (updated: Partial<Rubric>) => void;
}

export function FIReviewGate({ rubric, onUpdate }: Props) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { fi_status } = rubric;

  if (fi_status === "completed" || fi_status === null) return null;

  if (fi_status === "extracting" || fi_status === "approved") {
    return (
      <Card className="p-4">
        <p className="text-sm text-muted-foreground">{t("fi.reviewGate.pipelineRunning")}</p>
      </Card>
    );
  }

  if (fi_status === "rejected") {
    return (
      <Card className="border-destructive p-4">
        <p className="text-sm font-medium text-destructive">{t("fi.reviewGate.rejected")}</p>
        {rubric.review_notes && (
          <p className="mt-1 text-sm text-muted-foreground">{rubric.review_notes}</p>
        )}
      </Card>
    );
  }

  const handleAction = async (action: "approve" | "reject") => {
    setLoading(true);
    setError(null);
    try {
      await approveRubric(rubric.id, { action });
      onUpdate({ fi_status: action === "approve" ? "approved" : "rejected" });
    } catch {
      setError(t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("fi.reviewGate.title")}
      </p>
      <p className="mb-4 text-sm text-muted-foreground">{t("fi.reviewGate.description")}</p>

      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}

      <div className="flex gap-2">
        <Button size="sm" onClick={() => handleAction("approve")} disabled={loading}>
          {t("fi.reviewGate.approve")}
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => handleAction("reject")}
          disabled={loading}
        >
          {t("fi.reviewGate.reject")}
        </Button>
      </div>
    </Card>
  );
}
