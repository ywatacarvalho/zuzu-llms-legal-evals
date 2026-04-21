import { ArrowLeft, BarChart2, RefreshCw, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { LogConsole } from "@/components/evaluations/LogConsole";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { getEvaluation, rerunEvaluation, stopEvaluation } from "@/services/evaluationsApi";
import { EvaluationStatus, type Evaluation } from "@/types";

const POLL_INTERVAL_MS = 4000;
const RESPONSES_PER_MODEL = 40;

export function EvaluationDetailPage() {
  const { t } = useTranslation();
  const { evaluationId } = useParams<{ evaluationId: string }>();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [logKey, setLogKey] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchEvaluation = async () => {
    if (!evaluationId) return;
    try {
      const data = await getEvaluation(evaluationId);
      setEvaluation(data);
      const isTerminal =
        data.status === EvaluationStatus.Done || data.status === EvaluationStatus.Failed;
      if (isTerminal && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      setError(t("errors.generic"));
      if (pollRef.current) clearInterval(pollRef.current);
    }
  };

  useEffect(() => {
    fetchEvaluation().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [evaluationId]);

  const isActive = evaluation?.status === EvaluationStatus.Running;

  useEffect(() => {
    if (isActive) {
      pollRef.current = setInterval(fetchEvaluation, POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive]);

  const handleStop = async () => {
    if (!evaluation) return;
    setActionLoading(true);
    try {
      const updated = await stopEvaluation(evaluation.id);
      setEvaluation(updated);
    } catch {
      setError(t("errors.generic"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRerun = async () => {
    if (!evaluation) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await rerunEvaluation(evaluation.id);
      setEvaluation(updated);
      setLogKey((k) => k + 1);
    } catch {
      setError(t("errors.generic"));
    } finally {
      setActionLoading(false);
    }
  };

  const totalResponses = (evaluation?.model_names?.length ?? 0) * RESPONSES_PER_MODEL;
  const progressPct =
    evaluation && totalResponses > 0
      ? Math.min(100, Math.round((evaluation.response_count / totalResponses) * 100))
      : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/evaluations")}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          {t("evaluations.title")}
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {evaluation && (
        <>
          <div className="flex items-start justify-between">
            <PageHeader
              title={t("evaluations.detail.title")}
              description={new Date(evaluation.created_at).toLocaleString()}
            />
            <div className="flex gap-2">
              {isActive && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleStop}
                  disabled={actionLoading}
                >
                  <Square className="mr-1.5 h-3.5 w-3.5" />
                  {t("evaluations.detail.stop")}
                </Button>
              )}
              {(evaluation.status === EvaluationStatus.Done ||
                evaluation.status === EvaluationStatus.Failed) && (
                <Button variant="outline" size="sm" onClick={handleRerun} disabled={actionLoading}>
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                  {t("evaluations.detail.rerun")}
                </Button>
              )}
              {evaluation.status === EvaluationStatus.Done && (
                <Button size="sm" onClick={() => navigate(`/results/${evaluation.id}`)}>
                  <BarChart2 className="mr-1.5 h-3.5 w-3.5" />
                  {t("evaluations.detail.viewResults")}
                </Button>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("evaluations.detail.status")}
              </p>
              <StatusBadge status={evaluation.status} />
            </Card>

            <Card className="p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("evaluations.detail.responses")}
              </p>
              <p className="text-2xl font-bold text-foreground">
                {evaluation.response_count}
                {totalResponses > 0 && (
                  <span className="text-sm font-normal text-muted-foreground">
                    {" "}
                    / {totalResponses}
                  </span>
                )}
              </p>
              {isActive && (
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="animate-shimmer h-full rounded-full"
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              )}
            </Card>
          </div>

          <Card className="p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("evaluations.detail.question")}
            </p>
            <p className="text-sm leading-relaxed text-foreground">{evaluation.question}</p>
          </Card>

          <Card className="p-4">
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("evaluations.detail.models")}
            </p>
            <div className="flex flex-wrap gap-2">
              {evaluation.model_names?.map((m) => (
                <span
                  key={m}
                  className="rounded-full border border-border bg-muted/50 px-3 py-1 text-xs text-foreground"
                >
                  {m}
                </span>
              ))}
            </div>
          </Card>

          {(isActive || evaluation.status === EvaluationStatus.Failed) && (
            <LogConsole key={logKey} evaluationId={evaluation.id} active={isActive} />
          )}
        </>
      )}
    </div>
  );
}
