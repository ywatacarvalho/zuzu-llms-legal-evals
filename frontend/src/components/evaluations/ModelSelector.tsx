import { useTranslation } from "react-i18next";

import type { ModelInfo } from "@/types";

interface ModelSelectorProps {
  models: ModelInfo[];
  selected: string[];
  onChange: (selected: string[]) => void;
}

const MIN_MODELS = 2;
const MAX_MODELS = 5;

export function ModelSelector({ models, selected, onChange }: ModelSelectorProps) {
  const { t } = useTranslation();

  const toggle = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter((s) => s !== id));
    } else if (selected.length < MAX_MODELS) {
      onChange([...selected, id]);
    }
  };

  const providers = [...new Set(models.map((m) => m.provider))];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-foreground">
          {t("evaluations.form.selectModels")}
        </span>
        <span
          className={`text-xs font-medium ${
            selected.length >= MIN_MODELS ? "text-primary" : "text-muted-foreground"
          }`}
        >
          {selected.length}/{MAX_MODELS} {t("evaluations.form.selected")}
        </span>
      </div>

      {providers.map((provider) => (
        <div key={provider}>
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {provider}
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {models
              .filter((m) => m.provider === provider)
              .map((model) => {
                const isSelected = selected.includes(model.id);
                const isDisabled = !isSelected && selected.length >= MAX_MODELS;
                return (
                  <button
                    key={model.id}
                    type="button"
                    onClick={() => toggle(model.id)}
                    disabled={isDisabled}
                    className={`rounded-md border px-2.5 py-1.5 text-left text-xs transition-colors ${
                      isSelected
                        ? "border-primary bg-primary/10 text-primary"
                        : isDisabled
                          ? "cursor-not-allowed border-border bg-muted/30 text-muted-foreground opacity-50"
                          : "border-border bg-background text-foreground hover:border-primary/50 hover:bg-accent"
                    }`}
                  >
                    {model.name}
                  </button>
                );
              })}
          </div>
        </div>
      ))}
    </div>
  );
}
