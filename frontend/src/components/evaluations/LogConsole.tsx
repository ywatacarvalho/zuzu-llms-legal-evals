import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import { getEvaluationLogs } from "@/services/evaluationsApi";

interface LogConsoleProps {
  evaluationId: string;
  active: boolean;
}

const POLL_MS = 2000;
const MAX_VISIBLE_LINES = 2000;

/** Classify a log line for color coding. */
function lineColor(line: string): string {
  if (/\[ERROR\]|FATAL|fatal|error/i.test(line)) return "text-red-400";
  if (/\[WARN\]|warn|429|413/i.test(line)) return "text-yellow-400";
  if (/\[Stage\s?\d|stage\s?\d/i.test(line)) return "text-cyan-400 font-semibold";
  if (/\[analysis\]/i.test(line)) return "text-cyan-400 font-semibold";
  if (/\[call\s?\d|retry|rotating|cooldown/i.test(line)) return "text-orange-300";
  if (/complete|done|finished/i.test(line)) return "text-emerald-400";
  if (/ledger|cost|token/i.test(line)) return "text-violet-400";
  return "text-green-400";
}

export function LogConsole({ evaluationId, active }: LogConsoleProps) {
  const { t } = useTranslation();
  const [lines, setLines] = useState<string[]>([]);
  const offsetRef = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  const fetchLogs = useCallback(async () => {
    try {
      const { lines: newLines, total } = await getEvaluationLogs(evaluationId, offsetRef.current);
      if (newLines.length > 0) {
        setLines((prev) => {
          const combined = [...prev, ...newLines];
          return combined.length > MAX_VISIBLE_LINES
            ? combined.slice(combined.length - MAX_VISIBLE_LINES)
            : combined;
        });
        offsetRef.current = total;
      }
    } catch {
      // silently ignore -- log polling is best-effort
    }
  }, [evaluationId]);

  useEffect(() => {
    fetchLogs();
    if (active) {
      timerRef.current = setInterval(fetchLogs, POLL_MS);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [evaluationId, active, fetchLogs]);

  // Stop polling once active turns false but do one final fetch
  useEffect(() => {
    if (!active && timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
      fetchLogs();
    }
  }, [active, fetchLogs]);

  useEffect(() => {
    if (autoScroll) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [lines, autoScroll]);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setAutoScroll(atBottom);
  }, []);

  return (
    <Card className="p-4">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {t("evaluations.detail.pipelineLog")}
        <span className="ml-2 font-normal normal-case text-muted-foreground/60">
          {lines.length > 0 ? `(${lines.length} lines)` : ""}
        </span>
      </p>
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-80 overflow-y-auto rounded-md bg-black/90 p-3 font-mono text-[11px] leading-relaxed"
      >
        {lines.length === 0 ? (
          <span className="text-muted-foreground">{t("evaluations.detail.logWaiting")}</span>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={`whitespace-pre-wrap break-all ${lineColor(line)}`}>
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </Card>
  );
}
