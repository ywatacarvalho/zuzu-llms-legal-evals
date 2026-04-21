import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ModelSelector } from "@/components/evaluations/ModelSelector";
import { Button } from "@/components/ui/button";
import { Dialog, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { createEvaluation, listAvailableModels } from "@/services/evaluationsApi";
import { listFrozenRubrics } from "@/services/rubricsApi";
import type { Evaluation, ModelInfo, Rubric } from "@/types";

interface EvaluationFormProps {
  open: boolean;
  onClose: () => void;
  onCreated: (evaluation: Evaluation) => void;
}

export function EvaluationForm({ open, onClose, onCreated }: EvaluationFormProps) {
  const { t } = useTranslation();

  const [rubrics, setRubrics] = useState<Rubric[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [rubricId, setRubricId] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    Promise.all([listFrozenRubrics(), listAvailableModels()]).then(([r, m]) => {
      setRubrics(r);
      setModels(m);
    });
  }, [open]);

  const selectedRubric = rubrics.find((r) => r.id === rubricId);

  const canSubmit = rubricId && selectedModels.length >= 2 && selectedModels.length <= 5;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      const created = await createEvaluation(rubricId, selectedModels);
      onCreated(created);
      handleClose();
    } catch {
      setError(t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setRubricId("");
    setSelectedModels([]);
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} className="max-w-xl">
      <DialogTitle className="text-base">{t("evaluations.form.title")}</DialogTitle>
      <DialogDescription className="mb-3 text-xs">
        {t("evaluations.form.description")}
      </DialogDescription>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="eval-rubric" className="text-xs">
            {t("evaluations.form.rubricLabel")}
          </Label>
          <select
            id="eval-rubric"
            value={rubricId}
            onChange={(e) => setRubricId(e.target.value)}
            required
            className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">{t("evaluations.form.rubricPlaceholder")}</option>
            {rubrics.map((r) => (
              <option key={r.id} value={r.id}>
                {r.question ? r.question.slice(0, 80) : r.id}
              </option>
            ))}
          </select>
        </div>

        {selectedRubric && (
          <div className="rounded-md border border-border bg-muted/30 p-2">
            <p className="text-xs text-muted-foreground">
              {selectedRubric.criteria?.length ?? 0} {t("evaluations.form.criteriaCount")}
            </p>
          </div>
        )}

        <ModelSelector models={models} selected={selectedModels} onChange={setSelectedModels} />

        {error && <p className="text-xs text-destructive">{error}</p>}

        <div className="flex justify-end gap-2 pt-1">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleClose}
            disabled={loading}
          >
            {t("actions.cancel")}
          </Button>
          <Button type="submit" size="sm" disabled={!canSubmit || loading}>
            <Play className="mr-1.5 h-3.5 w-3.5" />
            {t("evaluations.form.submit")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
