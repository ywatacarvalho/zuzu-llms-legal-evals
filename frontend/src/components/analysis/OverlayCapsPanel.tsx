import { useTranslation } from "react-i18next";

import type { OverlayResult } from "@/types";

interface Props {
  overlay: OverlayResult | null | undefined;
}

export function OverlayCapsPanel({ overlay }: Props) {
  const { t } = useTranslation();

  if (!overlay) return null;

  const hasPenalties = overlay.penalties_applied.length > 0;
  const delta = overlay.subtotal - overlay.final_score;
  const deltaColor = delta === 0 ? "text-green-600 dark:text-green-400" : "text-destructive";

  return (
    <div className="mt-3 rounded-md border border-border bg-muted/20 p-3">
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {t("overlay.title")}
      </p>
      <div className="mb-2 flex flex-wrap gap-2 text-xs">
        {hasPenalties ? (
          overlay.penalties_applied.map((p) => (
            <span
              key={p.code}
              className="rounded-full bg-destructive/10 px-2 py-0.5 font-medium text-destructive"
              title={p.label}
            >
              {p.code} −{p.points} {t("overlay.deducted")}
            </span>
          ))
        ) : (
          <span className="text-muted-foreground">{t("overlay.noPenalties")}</span>
        )}
      </div>
      {overlay.cap_status.applied && (
        <p className="mb-2 text-xs text-amber-600 dark:text-amber-400">
          {t("overlay.cap")}: {overlay.cap_status.cap_code}
        </p>
      )}
      <div className="flex items-baseline gap-2 text-xs">
        <span className="text-muted-foreground">
          {t("overlay.subtotal")}: {overlay.subtotal.toFixed(1)}
        </span>
        <span className="text-muted-foreground">→</span>
        <span className={`font-semibold ${deltaColor}`}>
          {t("overlay.finalScore")}: {overlay.final_score.toFixed(1)}
        </span>
        {delta > 0 && <span className={`text-[10px] ${deltaColor}`}>(−{delta.toFixed(1)})</span>}
      </div>
    </div>
  );
}
