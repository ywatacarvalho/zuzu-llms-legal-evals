import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { useAuth } from "@/hooks/useAuth";
import { CaseDetailPage } from "@/pages/cases/CaseDetailPage";
import { CasesPage } from "@/pages/cases/CasesPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { EvaluationDetailPage } from "@/pages/evaluations/EvaluationDetailPage";
import { EvaluationsPage } from "@/pages/evaluations/EvaluationsPage";
import { LoginPage } from "@/pages/LoginPage";
import { DescriptionPage } from "@/pages/description/DescriptionPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { ResultsListPage } from "@/pages/results/ResultsListPage";
import { ResultsPage } from "@/pages/results/ResultsPage";
import { RubricDetailPage } from "@/pages/rubrics/RubricDetailPage";
import { RubricsPage } from "@/pages/rubrics/RubricsPage";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="cases" element={<CasesPage />} />
        <Route path="cases/:caseId" element={<CaseDetailPage />} />
        <Route path="rubrics" element={<RubricsPage />} />
        <Route path="rubrics/:rubricId" element={<RubricDetailPage />} />
        <Route path="evaluations" element={<EvaluationsPage />} />
        <Route path="evaluations/:evaluationId" element={<EvaluationDetailPage />} />
        <Route path="results" element={<ResultsListPage />} />
        <Route path="results/:evaluationId" element={<ResultsPage />} />
        <Route path="description" element={<DescriptionPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
