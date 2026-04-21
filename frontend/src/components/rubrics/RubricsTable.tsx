import { Eye } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { RubricStatusBadge } from "@/components/rubrics/RubricStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { Rubric } from "@/types";

interface RubricsTableProps {
  rubrics: Rubric[];
}

export function RubricsTable({ rubrics }: RubricsTableProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (rubrics.length === 0) {
    return (
      <div className="rounded-md border border-border py-12 text-center text-sm text-muted-foreground">
        {t("rubrics.table.empty")}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("rubrics.table.question")}</TableHead>
          <TableHead>{t("rubrics.table.criteria")}</TableHead>
          <TableHead>{t("rubrics.table.status")}</TableHead>
          <TableHead>{t("rubrics.table.createdAt")}</TableHead>
          <TableHead className="w-20">{t("cases.table.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rubrics.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="max-w-xs truncate font-medium">{r.question ?? "-"}</TableCell>
            <TableCell className="text-muted-foreground">{r.criteria?.length ?? 0}</TableCell>
            <TableCell>
              <RubricStatusBadge status={r.status} />
            </TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(r.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/rubrics/${r.id}`)}
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
