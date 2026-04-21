import type { Evaluation, ModelInfo } from "@/types";

import { apiClient } from "./api";

export async function listAvailableModels(): Promise<ModelInfo[]> {
  const { data } = await apiClient.get<ModelInfo[]>("/evaluations/models");
  return data;
}

export async function createEvaluation(
  rubricId: string,
  modelNames: string[]
): Promise<Evaluation> {
  const { data } = await apiClient.post<Evaluation>("/evaluations", {
    rubric_id: rubricId,
    model_names: modelNames,
  });
  return data;
}

export async function listEvaluations(): Promise<Evaluation[]> {
  const { data } = await apiClient.get<Evaluation[]>("/evaluations");
  return data;
}

export async function getEvaluation(evaluationId: string): Promise<Evaluation> {
  const { data } = await apiClient.get<Evaluation>(`/evaluations/${evaluationId}`);
  return data;
}

export async function stopEvaluation(evaluationId: string): Promise<Evaluation> {
  const { data } = await apiClient.post<Evaluation>(`/evaluations/${evaluationId}/stop`);
  return data;
}

export async function rerunEvaluation(evaluationId: string): Promise<Evaluation> {
  const { data } = await apiClient.post<Evaluation>(`/evaluations/${evaluationId}/rerun`);
  return data;
}

export async function getEvaluationLogs(
  evaluationId: string,
  offset: number = 0
): Promise<{ lines: string[]; total: number }> {
  const { data } = await apiClient.get(`/evaluations/${evaluationId}/logs`, {
    params: { offset },
  });
  return data;
}
