import { useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

// حساب ديمو عام — بيانات معروفة ومنشورة أصلاً بـREADME المشروع، مو سرّية.
// مشترك بين كل الزوار ومُقيّد بمتجر تجريبي واحد فقط (عزل الملكية بالباك إند).
const DEMO_EMAIL = "demo@dataly.app";
const DEMO_PASSWORD = "DataLY-Demo-2026";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function doLogin(loginEmail: string, loginPassword: string) {
    setError(null);
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
      navigate("/stores");
    } catch {
      setError("بريد أو كلمة مرور غلط");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    await doLogin(email, password);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-600 font-mono text-xl font-bold text-white">
            D
          </span>
          <h1 className="text-2xl font-bold text-ink">DataLY</h1>
          <p className="text-sm text-slate-500">لوحة تحكم معالجة الفواتير</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">البريد الإلكتروني</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">كلمة المرور</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          {error && <p className="text-sm font-medium text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? "...جار الدخول" : "دخول"}
          </button>

          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span className="h-px flex-1 bg-slate-200" />
            أو
            <span className="h-px flex-1 bg-slate-200" />
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => doLogin(DEMO_EMAIL, DEMO_PASSWORD)}
            className="rounded-lg border border-brand-200 bg-brand-50 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-100 disabled:opacity-60"
          >
            🔎 جرّب الديمو بدون تسجيل
          </button>
        </form>
      </div>
    </div>
  );
}
