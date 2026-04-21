import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Dialog, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uploadCase } from "@/services/casesApi";
import type { LegalCase } from "@/types";

interface CaseUploadDialogProps {
  open: boolean;
  onClose: () => void;
  onUploaded: (newCase: LegalCase) => void;
}

export function CaseUploadDialog({ open, onClose, onUploaded }: CaseUploadDialogProps) {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFile(e.target.files?.[0] ?? null);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const created = await uploadCase(file, title.trim() || undefined);
      onUploaded(created);
      handleClose();
    } catch {
      setError(t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setTitle("");
    setFile(null);
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose}>
      <DialogTitle>{t("cases.uploadDialog.title")}</DialogTitle>
      <DialogDescription>{t("cases.uploadDialog.description")}</DialogDescription>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="case-file">{t("cases.uploadDialog.fileLabel")}</Label>
          <Input
            id="case-file"
            ref={fileRef}
            type="file"
            accept="application/pdf"
            onChange={handleFileChange}
            required
            className="cursor-pointer"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="case-title">{t("cases.uploadDialog.titleLabel")}</Label>
          <Input
            id="case-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t("cases.uploadDialog.titlePlaceholder")}
          />
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={handleClose} disabled={loading}>
            {t("actions.cancel")}
          </Button>
          <Button type="submit" disabled={!file || loading}>
            <Upload className="mr-2 h-4 w-4" />
            {t("actions.upload")}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
