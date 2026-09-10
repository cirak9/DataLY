import { useState, FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [storeName, setStoreName] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(storeName, phoneNumber, password);
      navigate("/stores");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "تعذّر إنشاء الحساب — حاول من جديد");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center gap-3">
          <span className="grid h-12 w-12 place-items-center rounded-xl bg-brand-600 font-mono text-xl font-bold text-white">
            D
          </span>
          <h1 className="text-2xl font-bold text-ink">تسجيل متجر جديد</h1>
          <p className="text-sm text-slate-500">اسم المتجر ورقم الهاتف بس — يفتح حسابك فوراً</p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">اسم المتجر</label>
            <input
              type="text"
              value={storeName}
              onChange={(e) => setStoreName(e.target.value)}
              required
              autoFocus
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">رقم الهاتف</label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
              dir="ltr"
              className="rounded-lg border border-slate-300 px-3 py-2 text-left text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-slate-700">كلمة المرور</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
            <p className="text-xs text-slate-400">6 أحرف على الأقل</p>
          </div>

          {error && <p className="text-sm font-medium text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="mt-1 rounded-lg bg-brand-600 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {loading ? "...جار إنشاء الحساب" : "إنشاء الحساب"}
          </button>

          <p className="text-center text-sm text-slate-500">
            عندك حساب فعلاً؟{" "}
            <Link to="/login" className="font-semibold text-brand-600 hover:text-brand-700">
              سجّل الدخول
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
