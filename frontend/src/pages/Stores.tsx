import { useState, FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { Store } from "../lib/types";
import Layout from "../components/Layout";

export default function Stores() {
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [showForm, setShowForm] = useState(false);

  const { data: stores, isLoading } = useQuery({
    queryKey: ["stores"],
    queryFn: async () => (await api.get<Store[]>("/stores")).data,
  });

  const createStore = useMutation({
    mutationFn: (payload: { name: string; code: string }) => api.post("/stores", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["stores"] });
      setName("");
      setCode("");
      setShowForm(false);
    },
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createStore.mutate({ name, code });
  }

  return (
    <Layout>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">المتاجر</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          {showForm ? "إلغاء" : "+ متجر جديد"}
        </button>
      </div>

      <Link
        to="/ocr-preview"
        className="mb-6 inline-flex items-center gap-1.5 rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-500 transition hover:border-brand-400 hover:text-brand-600"
      >
        🧪 معاينة: شاشة مراجعة/اعتماد OCR (تجريبي)
      </Link>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">اسم المتجر</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="سوبر ماركت النجمة"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">الكود</label>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              placeholder="store_1"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-mono outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <button
            type="submit"
            disabled={createStore.isPending}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
          >
            {createStore.isPending ? "..." : "إضافة"}
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !stores?.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          مافيش متاجر بعد — أضف أول متجر عشان تبدأ.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {stores.map((store) => (
            <Link
              key={store.id}
              to={`/stores/${store.id}/invoices`}
              className="group rounded-xl border border-slate-200 bg-white p-5 transition hover:border-brand-300 hover:shadow-sm"
            >
              <div className="mb-1 font-semibold text-ink group-hover:text-brand-700">
                {store.name}
              </div>
              <div className="font-mono text-xs text-slate-400">{store.code}</div>
            </Link>
          ))}
        </div>
      )}
    </Layout>
  );
}
