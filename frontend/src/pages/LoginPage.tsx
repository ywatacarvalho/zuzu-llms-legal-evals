import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { branding } from "@/config/branding";
import { useAuth } from "@/hooks/useAuth";
import { apiClient } from "@/services/api";
import type { User } from "@/types";

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export function LoginPage() {
  const { t } = useTranslation();
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const { data: tokenData } = await apiClient.post<LoginResponse>("/auth/login", {
        email,
        password,
      });
      // Temporarily store token so the /me request can attach it
      localStorage.setItem("auth_token", tokenData.access_token);
      const { data: userData } = await apiClient.get<User>("/auth/me");
      login(tokenData.access_token, userData);
      navigate("/");
    } catch (err: unknown) {
      const status =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : undefined;
      setError(status === 401 ? t("auth.invalidCredentials") : t("errors.generic"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="animate-fade-in w-full max-w-sm space-y-6 rounded-lg border border-border bg-card p-8 shadow-xl shadow-black/5">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-bold text-foreground">{branding.appName}</h1>
          <p className="text-sm text-muted-foreground">{branding.appTagline}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">{t("auth.email")}</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button type="submit" className="w-full" disabled={loading}>
            {t("auth.login")}
          </Button>
        </form>
      </div>
    </div>
  );
}
