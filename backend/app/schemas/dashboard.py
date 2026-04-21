from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_cases: int
    evaluations_run: int
    models_evaluated: int
    avg_clusters: float
