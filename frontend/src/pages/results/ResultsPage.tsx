import { ArrowLeft, Loader2, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { CentroidCard } from "@/components/analysis/CentroidCard";
import { ClusterScoreChart } from "@/components/analysis/ClusterScoreChart";
import { ConditioningSamplePanel } from "@/components/analysis/ConditioningSamplePanel";
import { CriterionHeatmap } from "@/components/analysis/CriterionHeatmap";
import { DualTrackComparisonPanel } from "@/components/analysis/DualTrackComparisonPanel";
import { FailureTagsTable } from "@/components/analysis/FailureTagsTable";
import { JudgePanelConfig } from "@/components/analysis/JudgePanelConfig";
import { MetadataTagsPanel } from "@/components/analysis/MetadataTagsPanel";
import { ModelShareChart } from "@/components/analysis/ModelShareChart";
import { RubricSection } from "@/components/analysis/RubricSection";
import { SilhouetteChart } from "@/components/analysis/SilhouetteChart";
import { WeightingComparison } from "@/components/analysis/WeightingComparison";
import { WinnerBanner } from "@/components/analysis/WinnerBanner";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  getAnalysis,
  getAnalysisLogs,
  getAnalysisStatus,
  runAnalysis,
} from "@/services/analysisApi";
import { getEvaluation } from "@/services/evaluationsApi";
import { getRubricByEvaluation } from "@/services/rubricsApi";
import type { Analysis, Evaluation, Rubric } from "@/types";

const POLL_INTERVAL = 3_000;

export function ResultsPage() {
  const { t } = useTranslation();
  const { evaluationId } = useParams<{ evaluationId: string }>();
  const navigate = useNavigate();

  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [rubric, setRubric] = useState<Rubric | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [judgeModels, setJudgeModels] = useState<string[]>([]);
  const logOffsetRef = useRef(0);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const startPolling = useCallback(() => {
    if (!evaluationId || pollRef.current) return;
    setRunning(true);
    setError(null);

    pollRef.current = setInterval(async () => {
      try {
        const [statusResp, logsResp] = await Promise.all([
          getAnalysisStatus(evaluationId),
          getAnalysisLogs(evaluationId, logOffsetRef.current),
        ]);

        if (logsResp.lines.length > 0) {
          setLogLines((prev) => [...prev, ...logsResp.lines]);
          logOffsetRef.current = logsResp.total;
        }

        if (statusResp.status === "done") {
          stopPolling();
          const result = await getAnalysis(evaluationId);
          setAnalysis(result);
          setRunning(false);
        } else if (statusResp.status === "failed") {
          stopPolling();
          setRunning(false);
          setError(t("results.runError"));
        }
      } catch {
        stopPolling();
        setRunning(false);
        setError(t("results.runError"));
      }
    }, POLL_INTERVAL);
  }, [evaluationId, stopPolling, t]);

  useEffect(() => {
    return () => stopPolling();
  }, [stopPolling]);

  useEffect(() => {
    if (!evaluationId) return;
    Promise.all([
      getEvaluation(evaluationId).catch(() => null),
      getAnalysis(evaluationId).catch(() => null),
      getRubricByEvaluation(evaluationId).catch(() => null),
      getAnalysisStatus(evaluationId).catch(() => null),
    ])
      .then(([ev, an, rb, st]) => {
        setEvaluation(ev);
        setAnalysis(an);
        setRubric(rb);
        if (!an && st?.status === "running") {
          startPolling();
        }
      })
      .finally(() => setLoading(false));
  }, [evaluationId, startPolling]);

  const handleRunAnalysis = async () => {
    if (!evaluationId) return;
    setRunning(true);
    setError(null);
    setLogLines([]);
    logOffsetRef.current = 0;
    try {
      await runAnalysis(evaluationId, judgeModels.length > 0 ? judgeModels : undefined);
      startPolling();
    } catch {
      setRunning(false);
      setError(t("results.runError"));
    }
  };

  const bestModelEntry = analysis?.model_shares
    ? Object.entries(analysis.model_shares).sort(([, a], [, b]) => b - a)[0]
    : null;

  const sortedClusters = analysis?.clusters
    ? [...analysis.clusters].sort((a, b) => {
        const sa = analysis.scores?.[String(a.cluster_id)] ?? 0;
        const sb = analysis.scores?.[String(b.cluster_id)] ?? 0;
        return sb - sa;
      })
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate("/results")}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          {t("results.list.title")}
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">{t("actions.loading")}</p>}

      {!loading && evaluation && (
        <>
          <div className="flex items-start justify-between gap-4">
            <PageHeader
              title={t("results.detail.title")}
              description={new Date(evaluation.created_at).toLocaleString()}
            />
            {!analysis && (
              <Button onClick={handleRunAnalysis} disabled={running}>
                {running ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Play className="mr-2 h-4 w-4" />
                )}
                {running ? t("results.detail.running") : t("results.detail.run")}
              </Button>
            )}
          </div>

          <Card className="p-4">
            <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              {t("evaluations.detail.question")}
            </p>
            <p className="text-sm leading-relaxed text-foreground">{evaluation.question}</p>
          </Card>

          {!analysis && !running && (
            <JudgePanelConfig selected={judgeModels} onChange={setJudgeModels} />
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          {running && (
            <Card className="p-6">
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    {t("results.detail.runningTitle")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {t("results.detail.runningSubtitle")}
                  </p>
                </div>
              </div>
              {logLines.length > 0 && (
                <pre className="mt-4 max-h-60 overflow-y-auto rounded bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
                  {logLines.join("\n")}
                </pre>
              )}
            </Card>
          )}

          {analysis && !running && (
            <div className="space-y-6">
              {/* Winner banner */}
              {bestModelEntry && (
                <WinnerBanner
                  bestModel={bestModelEntry[0]}
                  bestModelShare={bestModelEntry[1]}
                  winningCluster={analysis.winning_cluster ?? 0}
                  winningScore={analysis.scores?.[String(analysis.winning_cluster)] ?? 0}
                />
              )}

              {/* Summary stats */}
              <div className="grid gap-4 sm:grid-cols-3">
                <Card className="p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("results.stats.clusters")}
                  </p>
                  <p className="text-2xl font-bold text-foreground">{analysis.k}</p>
                </Card>
                <Card className="p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("results.stats.winningCluster")}
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {t("results.cluster.label")} {analysis.winning_cluster}
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("results.stats.topScore")}
                  </p>
                  <p className="text-2xl font-bold text-foreground">
                    {Math.round((analysis.scores?.[String(analysis.winning_cluster)] ?? 0) * 100)}
                    <span className="text-sm font-normal text-muted-foreground">%</span>
                  </p>
                </Card>
              </div>

              {/* Evaluated models pill list */}
              {evaluation.model_names?.length ? (
                <Card className="p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("results.models.title")}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {evaluation.model_names.map((m) => (
                      <span
                        key={m}
                        className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                </Card>
              ) : null}

              {/* Weighting comparison */}
              {analysis.weighting_comparison && (
                <WeightingComparison weighting_comparison={analysis.weighting_comparison} />
              )}

              {/* Charts row */}
              <div className="grid gap-6 lg:grid-cols-3">
                {analysis.model_shares && <ModelShareChart modelShares={analysis.model_shares} />}
                {analysis.scores && analysis.winning_cluster != null && (
                  <ClusterScoreChart
                    scores={analysis.scores}
                    winningCluster={analysis.winning_cluster}
                  />
                )}
                {analysis.silhouette_scores_by_k && (
                  <SilhouetteChart
                    silhouette_scores_by_k={analysis.silhouette_scores_by_k}
                    selectedK={analysis.k}
                  />
                )}
              </div>

              {/* Criterion heatmap */}
              {analysis.baseline_scores && rubric?.criteria && (
                <CriterionHeatmap
                  baseline_scores={analysis.baseline_scores}
                  criteria={rubric.criteria}
                  winning_cluster={analysis.winning_cluster}
                />
              )}

              {/* Judge panel summary */}
              {analysis.judge_panel && (analysis.judge_panel as { models?: string[] }).models && (
                <Card className="p-4">
                  <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {t("judgePanel.title")}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {(analysis.judge_panel as { models: string[] }).models.map((m) => (
                      <span
                        key={m}
                        className="rounded-full bg-muted px-3 py-1 text-xs font-medium text-muted-foreground"
                      >
                        {m.split("/").pop()}
                      </span>
                    ))}
                  </div>
                  {(analysis.judge_panel as { mode?: string }).mode === "multi_model_panel" && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {t("judgePanel.majorityStatus")}:{" "}
                      <span className="font-medium text-foreground">
                        {(analysis.zak_review_flag as { flag?: string })?.flag === "yes"
                          ? t("judgePanel.noMajority")
                          : t("judgePanel.majority")}
                      </span>
                    </p>
                  )}
                </Card>
              )}

              {/* Zak escalation banner */}
              {(analysis.zak_review_flag as { flag?: string })?.flag === "yes" && (
                <Card className="border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/20">
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                    {t("zak.title")}
                  </p>
                  <p className="mb-2 text-sm text-amber-700 dark:text-amber-300">
                    {t("zak.description")}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {(
                      (analysis.zak_review_flag as { disputed_centroids?: number[] })
                        .disputed_centroids ?? []
                    ).map((c) => (
                      <span
                        key={c}
                        className="rounded-full bg-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-800/40 dark:text-amber-300"
                      >
                        {t("results.cluster.label")} {c}
                      </span>
                    ))}
                  </div>
                </Card>
              )}

              {/* FI failure tags and structured metadata tags */}
              {analysis.failure_tags && <FailureTagsTable failureTags={analysis.failure_tags} />}
              {analysis.failure_tags && <MetadataTagsPanel tags={analysis.failure_tags} />}

              {/* Centroid cards */}
              <div>
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {t("results.centroids.title")}
                </p>
                <div className="space-y-4">
                  {sortedClusters.map((cluster) => (
                    <CentroidCard
                      key={cluster.cluster_id}
                      cluster={cluster}
                      score={analysis.scores?.[String(cluster.cluster_id)] ?? 0}
                      isWinner={cluster.cluster_id === analysis.winning_cluster}
                      composition={
                        analysis.centroid_composition?.[String(cluster.cluster_id)] ?? null
                      }
                      finalScore={
                        typeof analysis.final_scores === "object" &&
                        !Array.isArray(analysis.final_scores) &&
                        analysis.final_scores !== null
                          ? ((analysis.final_scores as Record<string, number>)[
                              String(cluster.cluster_id)
                            ] ?? null)
                          : null
                      }
                    />
                  ))}
                </div>
              </div>

              {/* Dual-track comparison */}
              <DualTrackComparisonPanel analysis={analysis} />

              {/* Rubric section */}
              {rubric && <RubricSection rubric={rubric} />}

              {/* Conditioning sample + provenance */}
              {rubric && <ConditioningSamplePanel rubric={rubric} />}
            </div>
          )}
        </>
      )}
    </div>
  );
}
