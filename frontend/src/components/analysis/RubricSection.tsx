import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

import { Card } from "@/components/ui/card";
import type { Rubric } from "@/types";

interface RubricSectionProps {
  rubric: Rubric;
  initialOpen?: boolean;
}

function RefinementSummary({ rubric }: { rubric: Rubric }) {
  const { t } = useTranslation();
  const meta = rubric.stopping_metadata;
  if (!meta) return null;

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Card className="p-3">
        <p className="mb-0.5 text-xs text-muted-foreground">{t("results.rubric.passes")}</p>
        <p className="text-lg font-bold text-foreground">{meta.passes_completed}</p>
      </Card>
      <Card className="p-3">
        <p className="mb-0.5 text-xs text-muted-foreground">{t("results.rubric.rejected")}</p>
        <p className="text-lg font-bold text-foreground">{meta.total_rejected}</p>
      </Card>
      <Card className="p-3">
        <p className="mb-0.5 text-xs text-muted-foreground">{t("results.rubric.stoppingReason")}</p>
        <p className="text-sm font-medium text-foreground">{meta.reason}</p>
      </Card>
    </div>
  );
}

function DecompositionTree({ tree }: { tree: Record<string, string[]> }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const entries = Object.entries(tree);
  if (!entries.length) return null;

  return (
    <div className="rounded-md border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("results.rubric.decomposition")}
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="space-y-2 border-t border-border px-4 pb-3 pt-2">
          {entries.map(([parent, children]) => (
            <div key={parent}>
              <p className="text-xs font-medium text-foreground">{parent}</p>
              <ul className="ml-4 mt-1 space-y-0.5">
                {children.map((child) => (
                  <li key={child} className="text-xs text-muted-foreground before:content-['→_']">
                    {child}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RefinementPassLog({ passes }: { passes: Rubric["refinement_passes"] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!passes?.length) return null;

  return (
    <div className="rounded-md border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("results.rubric.passLog")}
        </span>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>
      {open && (
        <div className="space-y-1 border-t border-border px-4 pb-3 pt-2">
          {passes.map((p) => (
            <div key={p.pass_number} className="flex items-center gap-3 text-xs">
              <span className="w-14 text-muted-foreground">Pass {p.pass_number}</span>
              <span className="text-green-600 dark:text-green-400">+{p.accepted} accepted</span>
              <span className="text-destructive">
                −{p.rejected_misalignment + p.rejected_redundancy} rejected
              </span>
              {p.decomposition_empty > 0 && (
                <span className="text-muted-foreground">{p.decomposition_empty} empty</span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function RubricSection({ rubric, initialOpen = false }: RubricSectionProps) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(initialOpen);

  if (!rubric) return null;

  return (
    <div className="rounded-lg border border-border">
      <button
        className="flex w-full items-center justify-between px-4 py-4 text-left"
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {t("results.rubric.title")}
        </p>
        {open ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {open && (
        <div className="space-y-4 border-t border-border px-4 pb-4 pt-3">
          {/* Criteria table */}
          {rubric.criteria?.length ? (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("results.rubric.title")} — {rubric.criteria.length} {t("rubrics.criteria.count")}
              </p>
              <div className="space-y-2">
                {[...rubric.criteria]
                  .sort((a, b) => b.weight - a.weight)
                  .map((c) => (
                    <div key={c.id} className="rounded-md border border-border p-3 text-xs">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-foreground">{c.name}</span>
                            {c.row_status && (
                              <span
                                className={`rounded-full px-1.5 py-0.5 text-[10px] font-medium ${c.row_status === "anchor" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" : "bg-muted text-muted-foreground"}`}
                              >
                                {c.row_status}
                              </span>
                            )}
                          </div>
                          <p className="mt-0.5 text-muted-foreground">{c.description}</p>
                          {c.golden_target_summary && (
                            <p className="mt-1.5 rounded-sm bg-primary/5 px-2 py-1 text-foreground">
                              <span className="font-medium">
                                {t("results.rubric.goldenTarget")}:{" "}
                              </span>
                              {c.golden_target_summary}
                            </p>
                          )}
                        </div>
                        <span className="shrink-0 font-semibold text-foreground">
                          {(c.weight * 100).toFixed(1)}%
                        </span>
                      </div>
                      {c.scoring_anchors && Object.keys(c.scoring_anchors).length > 0 && (
                        <div className="mt-2 overflow-x-auto rounded-sm border border-border">
                          <table className="w-full text-[10px]">
                            <thead className="bg-muted/40">
                              <tr>
                                {Object.keys(c.scoring_anchors)
                                  .sort()
                                  .map((k) => (
                                    <th
                                      key={k}
                                      className="px-2 py-1 text-center font-semibold text-muted-foreground"
                                    >
                                      {k}
                                    </th>
                                  ))}
                              </tr>
                            </thead>
                            <tbody>
                              <tr>
                                {Object.keys(c.scoring_anchors)
                                  .sort()
                                  .map((k) => (
                                    <td
                                      key={k}
                                      className="px-2 py-1 text-center text-muted-foreground"
                                    >
                                      {c.scoring_anchors![k]}
                                    </td>
                                  ))}
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      )}
                      {c.allowed_omissions && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {(Array.isArray(c.allowed_omissions)
                            ? c.allowed_omissions
                            : [c.allowed_omissions]
                          ).map((item, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-muted px-2 py-0.5 text-muted-foreground"
                            >
                              {item}
                            </span>
                          ))}
                        </div>
                      )}
                      {c.contradiction_flags && c.contradiction_flags.length > 0 && (
                        <div className="mt-1.5 flex flex-wrap gap-1">
                          {c.contradiction_flags.map((flag, i) => (
                            <span
                              key={i}
                              className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300"
                            >
                              {flag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
              </div>
            </div>
          ) : null}

          {/* Refinement summary */}
          {rubric.stopping_metadata && (
            <div>
              <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {t("results.rubric.refinement")}
              </p>
              <RefinementSummary rubric={rubric} />
            </div>
          )}

          {/* Decomposition tree */}
          {rubric.decomposition_tree && Object.keys(rubric.decomposition_tree).length > 0 && (
            <DecompositionTree tree={rubric.decomposition_tree} />
          )}

          {/* Refinement pass log */}
          <RefinementPassLog passes={rubric.refinement_passes} />
        </div>
      )}
    </div>
  );
}
