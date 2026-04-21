import { Eye } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { LegalCase } from "@/types";

interface CasesTableProps {
  cases: LegalCase[];
}

export function CasesTable({ cases }: CasesTableProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  if (cases.length === 0) {
    return (
      <div className="rounded-md border border-border py-12 text-center text-sm text-muted-foreground">
        {t("cases.table.empty")}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("cases.table.title")}</TableHead>
          <TableHead>{t("cases.table.filename")}</TableHead>
          <TableHead>{t("cases.table.uploadedAt")}</TableHead>
          <TableHead className="w-20">{t("cases.table.actions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {cases.map((c) => (
          <TableRow key={c.id}>
            <TableCell className="font-medium">{c.title}</TableCell>
            <TableCell className="text-muted-foreground">{c.filename}</TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(c.created_at).toLocaleDateString()}
            </TableCell>
            <TableCell>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate(`/cases/${c.id}`)}
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
