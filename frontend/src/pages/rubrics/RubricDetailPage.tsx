import { ArrowLeft, RefreshCw, Square } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { ConditioningSamplePanel } from "@/components/analysis/ConditioningSamplePanel";
import { RubricSection } from "@/components/analysis/RubricSection";
import { ControllerCardPanel } from "@/components/rubrics/ControllerCardPanel";
import { DoctrinePackBadge } from "@/components/rubrics/DoctrinePackBadge";
import { FailureModesPanel } from "@/components/rubrics/FailureModesPanel";
import { FIReviewGate } from "@/components/rubrics/FIReviewGate";
import { GoldAnswerPanel } from "@/components/rubrics/GoldAnswerPanel";
import { GoldPacketMappingPanel } from "@/components/rubrics/GoldPacketMappingPanel";
import { ModeActionsPanel } from "@/components/rubrics/ModeActionsPanel";
import { QuestionAnalysisPanel } from "@/components/rubrics/QuestionAnalysisPanel";
import { RubricLogConsole } from "@/components/rubrics/RubricLogConsole";
import { SelfAuditPanel } from "@/components/rubrics/SelfAuditPanel";
import { SourceExtractionPanel } from "@/components/rubrics/SourceExtractionPanel";
import { SourceScreeningPanel } from "@/components/rubrics/SourceScreeningPanel";
import { VariationMenuGate } from "@/components/rubrics/VariationMenuGate";
import { VariationRubricPanel } from "@/components/rubrics/VariationRubricPanel";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { RubricStatusBadge } from "@/components/rubrics/RubricStatusBadge";
import { getRubric, rerunRubric, stopRubricBuild } from "@/services/rubricsApi";
import type { Rubric } from "@/types";

const POLL_INTERVAL_MS = 4000;

export function RubricDetailPage() {
  const { t } = useTranslation();
  const { rubricId } = useParams<{ rubricId: string }>();
  const navigate = useNavigate();

  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [logKey, setLogKey] = useState(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRubric = useCallback(async () => {
    if (!rubricId) return;
    try {
      const data = await getRubric(rubricId);
      setRubric(data);
      if (data.status !== "building" && pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    } catch {
      setError(t("errors.generic"));
      if (pollRef.current) clearInterval(pollRef.current);
    }
  }, [rubricId, t]);

  useEffect(() => {
    fetchRubric().finally(() => setLoading(false));
  }, [fetchRubric]);

  const isBuilding = rubric?.status === "building";
  const isAwaitingInput =
    rubric?.fi_status === "awaiting_review" || rubric?.fi_status === "variation_pending";

  useEffect(() => {
    if (isBuilding || isAwaitingInput) {
      pollRef.current = setInterval(fetchRubric, POLL_INTERVAL_MS);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [isBuilding, isAwaitingInput, fetchRubric]);

  const handleStop = async () => {
    if (!rubric) return;
    setActionLoading(true);
    try {
      const updated = await stopRubricBuild(rubric.id);
      setRubric(updated);
    } catch {
      setError(t("errors.generic"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleRerun = async () => {
    if (!rubric) return;
    setActionLoading(true);
    setError(null);
    try {
      const updated = await rerunRubric(rubric.id);
      setRubric(updated);
      setLogKey((k) => k + 1);
    } catch {
      setError(t("errors.generic"));
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/rubrics")}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          {t("rubrics.title")}
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      {rubric && (
        <>
          <div className="flex items-start justify-between">
            <PageHeader
              title={t("rubrics.detail.title")}
              description={new Date(rubric.created_at).toLocaleString()}
            />
            <div className="flex gap-2">
              {isBuilding && (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleStop}
                  disabled={actionLoading}
                >
                  <Square className="mr-1.5 h-3.5 w-3.5" />
                  {t("rubrics.detail.stop")}
                </Button>
              )}
              {rubric.status === "failed" && (
                <Button variant="outline" size="sm" onClick={handleRerun} disabled={actionLoading}>
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                  {t("rubrics.detail.rerun")}
                </Button>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("rubrics.detail.status")}
              </p>
              <RubricStatusBadge status={rubric.status} />
            </Card>

            <Card className="p-4">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("rubrics.detail.criteria")}
              </p>
              <p className="text-2xl font-bold text-foreground">{rubric.criteria?.length ?? 0}</p>
            </Card>
          </div>

          <Card className="p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("rubrics.detail.question")}
            </p>
            <p className="text-sm leading-relaxed text-foreground">{rubric.question}</p>
          </Card>

          {(isBuilding || rubric.status === "failed") && (
            <RubricLogConsole key={logKey} rubricId={rubric.id} active={isBuilding} />
          )}

          {rubric.fi_status && (
            <FIReviewGate
              rubric={rubric}
              onUpdate={(updated) => setRubric((r) => (r ? { ...r, ...updated } : r))}
            />
          )}

          <VariationMenuGate rubric={rubric} onComplete={fetchRubric} />

          {!rubric.source_extraction && !isBuilding && (
            <ModeActionsPanel
              rubric={rubric}
              onUpdate={(updated) => setRubric((r) => (r ? { ...r, ...updated } : r))}
            />
          )}

          <SourceScreeningPanel screeningResult={rubric.screening_result} />
          <SourceExtractionPanel sourceExtraction={rubric.source_extraction} />

          {(rubric.doctrine_pack || rubric.routing_metadata) && (
            <DoctrinePackBadge
              doctrinePack={rubric.doctrine_pack}
              routingMetadata={rubric.routing_metadata}
            />
          )}

          <GoldPacketMappingPanel goldPacketMapping={rubric.gold_packet_mapping} />
          <FailureModesPanel failureModes={rubric.predicted_failure_modes} />
          <GoldAnswerPanel goldAnswer={rubric.gold_answer} />
          <ControllerCardPanel rubric={rubric} />
          <SelfAuditPanel selfAuditResult={rubric.self_audit_result} />
          <QuestionAnalysisPanel questionAnalysis={rubric.question_analysis} />

          {rubric.is_frozen && (
            <>
              <RubricSection rubric={rubric} initialOpen />
              <VariationRubricPanel rubric={rubric} />
              <ConditioningSamplePanel rubric={rubric} initialOpen />
            </>
          )}
        </>
      )}
    </div>
  );
}
