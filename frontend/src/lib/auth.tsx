import { createContext, useContext, useState, ReactNode } from "react";
import { api } from "./api";

interface AuthContextValue {
  isAuthenticated: boolean;
  login: (identifier: string, password: string) => Promise<void>;
  register: (storeName: string, phoneNumber: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(
    () => !!localStorage.getItem("dataly_token")
  );

  async function login(identifier: string, password: string) {
    const { data } = await api.post("/auth/login", { identifier, password });
    localStorage.setItem("dataly_token", data.access_token);
    setIsAuthenticated(true);
  }

  async function register(storeName: string, phoneNumber: string, password: string) {
    const { data } = await api.post("/auth/register", {
      store_name: storeName,
      phone_number: phoneNumber,
      password,
    });
    localStorage.setItem("dataly_token", data.access_token);
    setIsAuthenticated(true);
  }

  function logout() {
    localStorage.removeItem("dataly_token");
    setIsAuthenticated(false);
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth يُستخدم بس داخل AuthProvider");
  return ctx;
}
