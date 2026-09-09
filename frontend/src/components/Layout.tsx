import { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Layout({ children }: { children: ReactNode }) {
  const { logout } = useAuth();

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3.5">
          <Link to="/stores" className="flex items-center gap-2">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 font-mono text-sm font-bold text-white">
              D
            </span>
            <span className="text-lg font-bold text-ink">DataLY</span>
          </Link>
          <button
            onClick={logout}
            className="text-sm font-medium text-slate-500 transition hover:text-slate-800"
          >
            تسجيل الخروج
          </button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-8">{children}</main>
    </div>
  );
}
