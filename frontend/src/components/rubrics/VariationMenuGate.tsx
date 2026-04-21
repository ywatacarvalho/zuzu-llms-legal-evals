import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { generateVariationMenu, selectVariation } from "@/services/rubricsApi";
import type { Rubric, VariationLaneCode, VariationOption } from "@/types";

interface Props {
  rubric: Rubric;
  onComplete: () => void;
}

export function VariationMenuGate({ rubric, onComplete }: Props) {
  const { t } = useTranslation();
  const [state, setState] = useState<"idle" | "loading" | "choosing" | "confirming">("idle");
  const [options, setOptions] = useState<VariationOption[]>([]);
  const [picked, setPicked] = useState<VariationLaneCode>(null);
  const [error, setError] = useState<string | null>(null);

  if (rubric.fi_status !== "variation_pending") return null;

  const handleGenerate = async () => {
    setState("loading");
    setError(null);
    try {
      const menu = await generateVariationMenu(rubric.id);
      setOptions(menu);
      setState("choosing");
    } catch {
      setError(t("errors.generic"));
      setState("idle");
    }
  };

  const handleSkip = async () => {
    setState("confirming");
    try {
      await selectVariation(rubric.id, null);
      onComplete();
    } catch {
      setError(t("errors.generic"));
      setState("idle");
    }
  };

  const handleSelect = async (code: VariationLaneCode) => {
    setState("confirming");
    try {
      await selectVariation(rubric.id, code);
      onComplete();
    } catch {
      setError(t("errors.generic"));
      setState("choosing");
    }
  };

  return (
    <Card className="p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("variation.title")}
      </p>
      <p className="mb-4 text-sm text-muted-foreground">{t("variation.description")}</p>
      {error && <p className="mb-3 text-sm text-destructive">{error}</p>}

      {state === "idle" && (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleSkip}>
            {t("variation.skip")}
          </Button>
          <Button size="sm" onClick={handleGenerate}>
            {t("variation.generate")}
          </Button>
        </div>
      )}

      {state === "loading" && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t("variation.generating")}
        </div>
      )}

      {(state === "choosing" || state === "confirming") && options.length > 0 && (
        <div className="space-y-3">
          {options.map((opt) => (
            <div
              key={opt.lane_code}
              className={`rounded-md border p-3 text-sm transition-colors ${picked === opt.lane_code ? "border-primary bg-primary/5" : "border-border"}`}
            >
              <div className="mb-2 flex items-center justify-between gap-2">
                <span className="font-semibold text-foreground">
                  {opt.lane_code} — {opt.label}
                </span>
                <Button
                  size="sm"
                  variant={picked === opt.lane_code ? "default" : "outline"}
                  disabled={state === "confirming"}
                  onClick={() => setPicked(opt.lane_code)}
                >
                  {picked === opt.lane_code ? t("variation.selected") : t("variation.select")}
                </Button>
              </div>
              <p className="mb-1 text-muted-foreground">
                <span className="font-medium text-foreground">{t("variation.whatChanges")}: </span>
                {opt.what_changes}
              </p>
              <p className="mb-1 text-muted-foreground">
                <span className="font-medium text-foreground">{t("variation.whyItFits")}: </span>
                {opt.why_it_fits}
              </p>
              <p className="text-amber-600 dark:text-amber-400">
                <span className="font-medium">{t("variation.mainRedFlag")}: </span>
                {opt.main_red_flag}
              </p>
            </div>
          ))}
          <div className="flex gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              disabled={state === "confirming"}
              onClick={handleSkip}
            >
              {t("variation.skip")}
            </Button>
            <Button
              size="sm"
              disabled={!picked || state === "confirming"}
              onClick={() => picked && handleSelect(picked)}
            >
              {state === "confirming" ? (
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
              ) : null}
              {t("variation.confirm")}
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
}
