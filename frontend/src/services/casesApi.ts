import type { LegalCase } from "@/types";

import { apiClient } from "./api";

export async function uploadCase(file: File, title?: string): Promise<LegalCase> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);

  const { data } = await apiClient.post<LegalCase>("/cases", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listCases(): Promise<LegalCase[]> {
  const { data } = await apiClient.get<LegalCase[]>("/cases");
  return data;
}

export async function getCase(caseId: string): Promise<LegalCase> {
  const { data } = await apiClient.get<LegalCase>(`/cases/${caseId}`);
  return data;
}
