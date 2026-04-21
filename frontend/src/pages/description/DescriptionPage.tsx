import {
  ArrowRight,
  BookOpen,
  Database,
  FileSearch,
  Layers,
  MessageSquare,
  Network,
  RefreshCw,
  Scale,
  Scissors,
  Trophy,
  Weight,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/PageHeader";
import { INTERNAL_MODELS } from "@/config/modelRegistry";
import { listAvailableModels } from "@/services/evaluationsApi";
import type { ModelInfo } from "@/types";

interface StageCardProps {
  id?: string;
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  accent?: "frank" | "rrd" | "dasha";
}

function StageCard({ id, icon, title, children, accent = "rrd" }: StageCardProps) {
  const border =
    accent === "frank"
      ? "border-l-primary"
      : accent === "rrd"
        ? "border-l-foreground/30"
        : "border-l-muted-foreground/30";
  return (
    <Card id={id} className={`scroll-mt-24 border-l-4 ${border}`}>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">{children}</CardContent>
    </Card>
  );
}

type StageLayer = "frank" | "rrd" | "dasha";

const STAGES = [
  { id: "stage-1", number: 1, titleKey: "description.stage1.title", layer: "frank" as StageLayer },
  { id: "stage-2", number: 2, titleKey: "description.stage2.title", layer: "frank" as StageLayer },
  { id: "stage-3", number: 3, titleKey: "description.stage3.title", layer: "rrd" as StageLayer },
  { id: "stage-4", number: 4, titleKey: "description.stage4.title", layer: "rrd" as StageLayer },
  { id: "stage-5", number: 5, titleKey: "description.stage5.title", layer: "rrd" as StageLayer },
  { id: "stage-6", number: 6, titleKey: "description.stage6.title", layer: "rrd" as StageLayer },
  { id: "stage-7", number: 7, titleKey: "description.stage7.title", layer: "rrd" as StageLayer },
  { id: "stage-8", number: 8, titleKey: "description.stage8.title", layer: "dasha" as StageLayer },
  { id: "stage-9", number: 9, titleKey: "description.stage9.title", layer: "dasha" as StageLayer },
  {
    id: "stage-10",
    number: 10,
    titleKey: "description.stage10.title",
    layer: "dasha" as StageLayer,
  },
];

const AUTHORS = ["carvalho", "chen", "hanlon", "liu", "syed", "tai"];

function MethodologyNav() {
  const { t } = useTranslation();

  const getStageClassName = (layer: StageLayer) => {
    if (layer === "frank") {
      return "border-primary/30 bg-primary/5 text-primary";
    }

    if (layer === "rrd") {
      return "border-border bg-muted/40 text-foreground";
    }

    return "border-muted-foreground/30 bg-background text-muted-foreground";
  };

  const scrollToStage = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="sticky top-0 z-10 rounded-md border border-border bg-background/95 p-3 shadow-sm backdrop-blur">
      <div className="mb-2 flex flex-wrap gap-2 text-[10px] font-semibold uppercase text-muted-foreground">
        <span>{t("description.stageNav.frank")}</span>
        <span className="text-muted-foreground/40">/</span>
        <span>{t("description.stageNav.rrd")}</span>
        <span className="text-muted-foreground/40">/</span>
        <span>{t("description.stageNav.dasha")}</span>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {STAGES.map((stage) => (
          <button
            key={stage.id}
            type="button"
            onClick={() => scrollToStage(stage.id)}
            className={`rounded-md border px-2 py-1 text-xs font-medium transition-colors hover:border-primary hover:text-primary ${getStageClassName(
              stage.layer
            )}`}
            aria-label={`${t("description.stageNav.goTo")} ${stage.number}: ${t(stage.titleKey)}`}
          >
            {t("description.stageNav.stage")} {stage.number}
          </button>
        ))}
      </div>
    </div>
  );
}

function InternalModelsTable() {
  const { t } = useTranslation();
  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.modelId")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.name")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.provider")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.role")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.style")}
            </th>
          </tr>
        </thead>
        <tbody>
          {INTERNAL_MODELS.map((m) => (
            <tr key={m.id} className="border-b border-border last:border-0">
              <td className="px-3 py-1.5 font-mono">{m.id}</td>
              <td className="px-3 py-1.5">{m.name}</td>
              <td className="px-3 py-1.5">{m.provider}</td>
              <td className="px-3 py-1.5">{t(m.roleKey)}</td>
              <td className="px-3 py-1.5">{t(m.styleKey)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function ComparisonModelsTable({ models }: { models: ModelInfo[] }) {
  const { t } = useTranslation();

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border bg-muted/50">
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.modelId")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.name")}
            </th>
            <th className="px-3 py-2 text-left font-medium text-foreground">
              {t("description.modelRegistry.provider")}
            </th>
          </tr>
        </thead>
        <tbody>
          {models.map((m) => (
            <tr key={m.id} className="border-b border-border last:border-0">
              <td className="px-3 py-1.5 font-mono">{m.id}</td>
              <td className="px-3 py-1.5">{m.name}</td>
              <td className="px-3 py-1.5">{m.provider}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface SubSectionProps {
  label: string;
  children: React.ReactNode;
}

function SubSection({ label, children }: SubSectionProps) {
  return (
    <div className="rounded-md bg-muted/40 p-3">
      <p className="mb-1 text-xs font-semibold text-foreground">{label}</p>
      <div>{children}</div>
    </div>
  );
}

function AuthorsCard() {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("description.authors.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-muted-foreground">
        <p>{t("description.authors.note")}</p>
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border bg-muted/50">
                <th className="px-3 py-2 text-left font-medium text-foreground">
                  {t("description.authors.name")}
                </th>
                <th className="px-3 py-2 text-left font-medium text-foreground">
                  {t("description.authors.affiliation")}
                </th>
              </tr>
            </thead>
            <tbody>
              {AUTHORS.map((author) => (
                <tr key={author} className="border-b border-border last:border-0">
                  <td className="px-3 py-1.5 font-medium text-foreground">
                    {t(`description.authors.people.${author}.name`)}
                  </td>
                  <td className="px-3 py-1.5">
                    {t(`description.authors.people.${author}.affiliation`)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

export function DescriptionPage() {
  const { t } = useTranslation();
  const iconCls = "h-4 w-4 shrink-0 text-primary";
  const [comparisonModels, setComparisonModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState(false);

  const fetchComparisonModels = useCallback(() => {
    setModelsLoading(true);
    setModelsError(false);
    listAvailableModels()
      .then(setComparisonModels)
      .catch(() => setModelsError(true))
      .finally(() => setModelsLoading(false));
  }, []);

  useEffect(() => {
    fetchComparisonModels();
  }, [fetchComparisonModels]);

  return (
    <div className="space-y-6">
      <PageHeader title={t("description.title")} description={t("description.subtitle")} />

      {/* Introduction */}
      <Card>
        <CardContent className="space-y-4 pt-6 text-sm text-muted-foreground">
          <p>{t("description.intro")}</p>
          <p>{t("description.twoLayers")}</p>
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
              <p className="mb-1 text-xs font-semibold text-primary">
                {t("description.layerFrank")}
              </p>
              <p className="text-xs">{t("description.layerFrankDesc")}</p>
            </div>
            <div className="rounded-md border border-primary/30 bg-primary/5 p-3">
              <p className="mb-1 text-xs font-semibold text-foreground">
                {t("description.layerCore")}
              </p>
              <p className="text-xs">{t("description.layerCoreDesc")}</p>
            </div>
            <div className="rounded-md border border-muted-foreground/30 bg-muted/40 p-3">
              <p className="mb-1 text-xs font-semibold text-muted-foreground">
                {t("description.layerDownstream")}
              </p>
              <p className="text-xs">{t("description.layerDownstreamDesc")}</p>
            </div>
          </div>
          <p>{t("description.pipelineNote")}</p>
        </CardContent>
      </Card>

      <AuthorsCard />

      <MethodologyNav />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("description.modelRegistry.title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-5 text-sm text-muted-foreground">
          <p>{t("description.modelRegistry.p1")}</p>
          <p>{t("description.modelRegistry.p2")}</p>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-foreground">
              {t("description.modelRegistry.internal")}
            </p>
            <InternalModelsTable />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold text-foreground">
              {t("description.modelRegistry.comparison")}
            </p>
            {modelsLoading && <p className="text-xs">{t("actions.loading")}</p>}
            {modelsError && (
              <div className="flex items-center gap-3">
                <p className="text-xs text-destructive">{t("description.modelRegistry.error")}</p>
                <Button variant="outline" size="sm" onClick={fetchComparisonModels}>
                  <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                  {t("actions.retry")}
                </Button>
              </div>
            )}
            {!modelsLoading && !modelsError && <ComparisonModelsTable models={comparisonModels} />}
            <p className="text-xs italic">{t("description.modelRegistry.comparisonNote")}</p>
          </div>
        </CardContent>
      </Card>

      <div className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
        {STAGES.map((stage) => (
          <span key={stage.id} className="flex items-center gap-1">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary">
              {stage.number}
            </span>
            {stage.number < 10 && <ArrowRight className="h-3 w-3 text-muted-foreground/50" />}
          </span>
        ))}
      </div>

      {/* Stage 1 */}
      <StageCard
        id="stage-1"
        icon={<FileSearch className={iconCls} />}
        title={t("description.stage1.title")}
        accent="frank"
      >
        <p>{t("description.stage1.p1")}</p>
        <p>{t("description.stage1.p2")}</p>
      </StageCard>

      {/* Stage 2 */}
      <StageCard
        id="stage-2"
        icon={<BookOpen className={iconCls} />}
        title={t("description.stage2.title")}
        accent="frank"
      >
        <p>{t("description.stage2.p1")}</p>
        <p>{t("description.stage2.p2")}</p>
        <SubSection label={t("description.stage2.screening")}>
          {t("description.stage2.screeningDesc")}
        </SubSection>
        <SubSection label={t("description.stage2.routing")}>
          {t("description.stage2.routingDesc")}
        </SubSection>
        <SubSection label={t("description.stage2.controller")}>
          {t("description.stage2.controllerDesc")}
        </SubSection>
        <SubSection label={t("description.stage2.review")}>
          {t("description.stage2.reviewDesc")}
        </SubSection>
      </StageCard>

      {/* Stage 3 */}
      <StageCard
        id="stage-3"
        icon={<MessageSquare className={iconCls} />}
        title={t("description.stage3.title")}
      >
        <p>{t("description.stage3.p1")}</p>
        <p>{t("description.stage3.p2")}</p>
        <p className="text-xs font-semibold text-foreground">
          {t("description.modelRegistry.internal")}
        </p>
        <InternalModelsTable />
        <p className="text-xs italic">{t("description.stage3.modelNote")}</p>
      </StageCard>

      {/* Stage 4 */}
      <StageCard
        id="stage-4"
        icon={<Network className={iconCls} />}
        title={t("description.stage4.title")}
      >
        <p>{t("description.stage4.p1")}</p>
        <p>{t("description.stage4.p2")}</p>
        <div className="rounded-md border border-primary/20 bg-primary/5 p-3 text-xs italic">
          {t("description.stage4.deviation")}
        </div>
      </StageCard>

      {/* Stage 5 */}
      <StageCard
        id="stage-5"
        icon={<BookOpen className={iconCls} />}
        title={t("description.stage5.title")}
      >
        <p>{t("description.stage5.p1")}</p>
        <p>{t("description.stage5.p2")}</p>
      </StageCard>

      {/* Stage 6 */}
      <StageCard
        id="stage-6"
        icon={<Scissors className={iconCls} />}
        title={t("description.stage6.title")}
      >
        <p>{t("description.stage6.p1")}</p>
        <SubSection label={t("description.stage6.decomposition")}>
          {t("description.stage6.decompositionDesc")}
        </SubSection>
        <SubSection label={t("description.stage6.misalignment")}>
          {t("description.stage6.misalignmentDesc")}
        </SubSection>
        <SubSection label={t("description.stage6.redundancy")}>
          {t("description.stage6.redundancyDesc")}
        </SubSection>
        <SubSection label={t("description.stage6.stopping")}>
          {t("description.stage6.stoppingDesc")}
        </SubSection>
      </StageCard>

      {/* Stage 7 */}
      <StageCard
        id="stage-7"
        icon={<Weight className={iconCls} />}
        title={t("description.stage7.title")}
      >
        <p>{t("description.stage7.p1")}</p>
        <p>{t("description.stage7.p2")}</p>
        <SubSection label={t("description.stage7.karthic")}>
          {t("description.stage7.karthicDesc")}
        </SubSection>
        <SubSection label={t("description.stage7.variation")}>
          {t("description.stage7.variationDesc")}
        </SubSection>
      </StageCard>

      {/* Stage 8 */}
      <StageCard
        id="stage-8"
        icon={<Database className={iconCls} />}
        title={t("description.stage8.title")}
        accent="dasha"
      >
        <p>{t("description.stage8.p1")}</p>
        <p>{t("description.stage8.p2")}</p>
        <SubSection label={t("description.stage8.exclusion")}>
          {t("description.stage8.exclusionDesc")}
        </SubSection>
      </StageCard>

      {/* Stage 9 */}
      <StageCard
        id="stage-9"
        icon={<Layers className={iconCls} />}
        title={t("description.stage9.title")}
        accent="dasha"
      >
        <p>{t("description.stage9.p1")}</p>
        <p>{t("description.stage9.p2")}</p>
        <p className="text-xs font-semibold text-foreground">
          {t("description.stage9.weightsLabel")}
        </p>
        <ul className="ml-4 list-disc space-y-1">
          <li>{t("description.stage9.uniform")}</li>
          <li>{t("description.stage9.heuristic")}</li>
          <li>{t("description.stage9.whitened")}</li>
        </ul>
        <SubSection label={t("description.stage9.tagsLabel")}>
          {t("description.stage9.tagsDesc")}
        </SubSection>
        <SubSection label={t("description.stage9.dualTrackLabel")}>
          {t("description.stage9.dualTrackDesc")}
        </SubSection>
        <SubSection label={t("description.stage9.judgePanelLabel")}>
          {t("description.stage9.judgePanelDesc")}
        </SubSection>
      </StageCard>

      {/* Stage 10 */}
      <StageCard
        id="stage-10"
        icon={<Trophy className={iconCls} />}
        title={t("description.stage10.title")}
        accent="dasha"
      >
        <p>{t("description.stage10.p1")}</p>
        <p>{t("description.stage10.p2")}</p>
      </StageCard>

      {/* Control model note */}
      <StageCard icon={<Scale className={iconCls} />} title={t("description.controlModel.title")}>
        <p>{t("description.controlModel.p1")}</p>
      </StageCard>
    </div>
  );
}
