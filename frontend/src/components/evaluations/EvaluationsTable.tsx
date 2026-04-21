import { Eye } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Evaluation } from "@/types";

interface EvaluationsTableProps {
  evaluations: Evaluation[];
}

export function EvaluationsTable({ evaluations }: EvaluationsTableProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (evaluations.length === 0) {
    return (
      <div className="rounded-md border border-border py-12 text-center text-sm text-muted-foreground">
        {t("evaluations.table.empty")}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("evaluations.table.question")}</TableHead>
          <TableHead>{t("evaluations.table.models")}</TableHead>
          <TableHead>{t("evaluations.table.responses")}</TableHead>
          <TableHead>{t("evaluations.table.status")}</TableHead>
          <TableHead>{t("evaluations.table.createdAt")}</TableHead>
          <TableHead className="w-20">{t("cases.table.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {evaluations.map((e) => (
          <TableRow key={e.id}>
            <TableCell className="max-w-xs truncate font-medium">{e.question}</TableCell>
            <TableCell className="text-muted-foreground">
              {e.model_names?.length ?? 0} {t("evaluations.table.modelsCount")}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {e.response_count}
              {e.model_names?.length ? ` / ${e.model_names.length * 40}` : ""}
            </TableCell>
            <TableCell>
              <StatusBadge status={e.status} />
            </TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(e.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/evaluations/${e.id}`)}
                aria-label={t("actions.view")}
              >
                <Eye className="h-4 w-4" />
              </Button>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
