import { useAuthStore } from "@/stores/authStore";
import type { User } from "@/types";

interface UseAuthReturn {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

export function useAuth(): UseAuthReturn {
  const { user, token, login, logout } = useAuthStore();

  return {
    user,
    token,
    isAuthenticated: token !== null,
    login,
    logout,
  };
}
