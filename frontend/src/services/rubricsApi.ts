import type { Rubric, RubricApproveRequest, VariationOption } from "@/types";

import { apiClient } from "./api";

export async function createRubric(caseId: string, question: string): Promise<Rubric> {
  const { data } = await apiClient.post<Rubric>("/rubrics", {
    case_id: caseId,
    question,
  });
  return data;
}

export async function listRubrics(): Promise<Rubric[]> {
  const { data } = await apiClient.get<Rubric[]>("/rubrics");
  return data;
}

export async function listFrozenRubrics(): Promise<Rubric[]> {
  const { data } = await apiClient.get<Rubric[]>("/rubrics/frozen");
  return data;
}

export async function getRubric(rubricId: string): Promise<Rubric> {
  const { data } = await apiClient.get<Rubric>(`/rubrics/${rubricId}`);
  return data;
}

export async function getRubricLogs(
  rubricId: string,
  offset: number = 0
): Promise<{ lines: string[]; total: number }> {
  const { data } = await apiClient.get(`/rubrics/${rubricId}/logs`, {
    params: { offset },
  });
  return data;
}

export async function stopRubricBuild(rubricId: string): Promise<Rubric> {
  const { data } = await apiClient.post<Rubric>(`/rubrics/${rubricId}/stop`);
  return data;
}

export async function rerunRubric(rubricId: string): Promise<Rubric> {
  const { data } = await apiClient.post<Rubric>(`/rubrics/${rubricId}/rerun`);
  return data;
}

export async function getRubricByEvaluation(evaluationId: string): Promise<Rubric | null> {
  try {
    const { data } = await apiClient.get<Rubric>(`/rubrics/evaluation/${evaluationId}`);
    return data;
  } catch (err: unknown) {
    const status =
      err && typeof err === "object" && "response" in err
        ? (err as { response?: { status?: number } }).response?.status
        : undefined;
    if (status === 404) return null;
    throw err;
  }
}

export async function approveRubric(
  rubricId: string,
  body: RubricApproveRequest
): Promise<{ status: string; rubric_id: string }> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/approve`, body);
  return data;
}

export async function validateQuestion(rubricId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/validate-question`);
  return data;
}

export async function generateQuestion(rubricId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/generate-question`);
  return data;
}

export async function extractOnly(rubricId: string): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/extract-only`);
  return data;
}

export async function compareDraft(
  rubricId: string,
  draftText: string
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/compare-draft`, {
    draft_text: draftText,
  });
  return data;
}

export async function draftFailureModes(rubricId: string): Promise<Record<string, unknown>[]> {
  const { data } = await apiClient.post(`/rubrics/${rubricId}/draft-failure-modes`);
  return data;
}

export async function generateVariationMenu(rubricId: string): Promise<VariationOption[]> {
  const { data } = await apiClient.post<VariationOption[]>(`/rubrics/${rubricId}/variation-menu`);
  return data;
}

export async function selectVariation(
  rubricId: string,
  selectedLaneCode: string | null
): Promise<Rubric> {
  const { data } = await apiClient.post<Rubric>(`/rubrics/${rubricId}/select-variation`, {
    selected_lane_code: selectedLaneCode,
  });
  return data;
}
