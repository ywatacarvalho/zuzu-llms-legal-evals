import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

// Internal judge models — must never overlap with comparison pool.
// Agent 3 may expose GET /analysis/judge-models; update this list when that endpoint is ready.
const JUDGE_MODELS = [
  "deepseek-ai/DeepSeek-V3",
  "deepseek-ai/DeepSeek-R1",
  "Qwen/Qwen2.5-7B-Instruct-Turbo",
  "meta-llama/Llama-3.3-70B-Instruct-Turbo",
] as const;

const MAX_JUDGES = 3;

interface Props {
  selected: string[];
  onChange: (models: string[]) => void;
}

export function JudgePanelConfig({ selected, onChange }: Props) {
  const { t } = useTranslation();

  const toggle = (model: string) => {
    if (selected.includes(model)) {
      onChange(selected.filter((m) => m !== model));
    } else if (selected.length < MAX_JUDGES) {
      onChange([...selected, model]);
    }
  };

  return (
    <Card className="p-4">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("judgePanel.title")}
      </p>
      <p className="mb-3 text-xs text-muted-foreground">{t("judgePanel.description")}</p>
      <div className="flex flex-wrap gap-2">
        {JUDGE_MODELS.map((model) => {
          const isSelected = selected.includes(model);
          const atMax = !isSelected && selected.length >= MAX_JUDGES;
          return (
            <Button
              key={model}
              variant={isSelected ? "default" : "outline"}
              size="sm"
              disabled={atMax}
              onClick={() => toggle(model)}
              title={atMax ? t("judgePanel.maxWarning") : undefined}
            >
              {model.split("/").pop()}
            </Button>
          );
        })}
      </div>
      {selected.length > 0 && (
        <p className="mt-2 text-xs text-muted-foreground">
          {t("judgePanel.selected", { count: selected.length })}
        </p>
      )}
    </Card>
  );
}
