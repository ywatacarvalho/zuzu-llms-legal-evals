import type { DashboardStats } from "@/types";

import { apiClient as api } from "./api";

export async function getDashboardStats(): Promise<DashboardStats> {
  const { data } = await api.get<DashboardStats>("/dashboard/stats");
  return data;
}
