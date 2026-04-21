import type { Analysis } from "@/types";

import { apiClient as api } from "./api";

export async function runAnalysis(evaluationId: string, judgeModels?: string[]): Promise<void> {
  const body = judgeModels && judgeModels.length > 0 ? { judge_models: judgeModels } : {};
  await api.post(`/analysis/${evaluationId}/run`, body);
}

export async function getAnalysis(evaluationId: string): Promise<Analysis> {
  const { data } = await api.get<Analysis>(`/analysis/${evaluationId}`);
  return data;
}

export async function getAnalysisStatus(
  evaluationId: string
): Promise<{ status: "done" | "running" | "failed" | "not_started" }> {
  const { data } = await api.get<{ status: "done" | "running" | "failed" | "not_started" }>(
    `/analysis/${evaluationId}/status`
  );
  return data;
}

export async function getAnalysisLogs(
  evaluationId: string,
  offset: number = 0
): Promise<{ lines: string[]; total: number }> {
  const { data } = await api.get<{ lines: string[]; total: number }>(
    `/analysis/${evaluationId}/logs`,
    { params: { offset } }
  );
  return data;
}
