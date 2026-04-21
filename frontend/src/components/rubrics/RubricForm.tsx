import { Play } from "lucide-react";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Dialog, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { listCases } from "@/services/casesApi";
import { createRubric } from "@/services/rubricsApi";
import type { LegalCase, Rubric } from "@/types";

interface RubricFormProps {
  open: boolean;
  onClose: () => void;
  onCreated: (rubric: Rubric) => void;
}

export function RubricForm({ open, onClose, onCreated }: RubricFormProps) {
  const { t } = useTranslation();

  const [cases, setCases] = useState<LegalCase[]>([]);
  const [caseId, setCaseId] = useState("");
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    listCases().then(setCases);
  }, [open]);

  const trimmed = question.trim();
  const questionError =
    trimmed.length > 0 && trimmed.length < 30
      ? t("rubrics.form.questionTooShort")
      : trimmed.length > 1000
        ? t("rubrics.form.questionTooLong")
        : /(.)\1{6,}/.test(trimmed)
          ? t("rubrics.form.questionRepetitive")
          : null;

  const canSubmit = caseId && trimmed.length >= 30 && trimmed.length <= 1000 && !questionError;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    setLoading(true);
    setError(null);
    try {
      const created = await createRubric(caseId, question.trim());
      onCreated(created);
      handleClose();
    } catch {
      setError(t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setCaseId("");
    setQuestion("");
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} className="max-w-xl">
      <DialogTitle className="text-base">{t("rubrics.form.title")}</DialogTitle>
      <DialogDescription className="mb-3 text-xs">
        {t("rubrics.form.description")}
      </DialogDescription>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="space-y-1">
          <Label htmlFor="rubric-case" className="text-xs">
            {t("rubrics.form.caseLabel")}
          </Label>
          <select
            id="rubric-case"
            value={caseId}
            onChange={(e) => setCaseId(e.target.value)}
            required
            className="w-full rounded-md border border-input bg-background px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          >
            <option value="">{t("rubrics.form.casePlaceholder")}</option>
            {cases.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <Label htmlFor="rubric-question" className="text-xs">
            {t("rubrics.form.questionLabel")}
          </Label>
          <textarea
            id="rubric-question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            required
            rows={5}
            placeholder={t("rubrics.form.questionPlaceholder")}
            className={`w-full rounded-md border bg-background px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring ${questionError ? "border-destructive focus:ring-destructive" : "border-input"}`}
          />
          {questionError && <p className="text-xs text-destructive">{questionError}</p>}
        </div>

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
            {t("rubrics.form.submit")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
