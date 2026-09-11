import { useState, FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { CategoryWithKeywords } from "../lib/types";
import Layout from "../components/Layout";

function CategoryCard({ category }: { category: CategoryWithKeywords }) {
  const queryClient = useQueryClient();
  const [newKeyword, setNewKeyword] = useState("");
  const [isWholeWord, setIsWholeWord] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["categories"] });

  const addKeyword = useMutation({
    mutationFn: () =>
      api.post(`/categories/${category.id}/keywords`, { keyword: newKeyword.trim(), is_whole_word: isWholeWord }),
    onSuccess: () => {
      setNewKeyword("");
      setError(null);
      invalidate();
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "فشلت إضافة الكلمة"),
  });

  const removeKeyword = useMutation({
    mutationFn: (keywordId: number) => api.delete(`/categories/${category.id}/keywords/${keywordId}`),
    onSuccess: invalidate,
  });

  const deleteCategory = useMutation({
    mutationFn: () => api.delete(`/categories/${category.id}`),
    onSuccess: invalidate,
    onError: (err: any) => setError(err?.response?.data?.detail ?? "فشل حذف التصنيف"),
  });

  function handleAddKeyword(e: FormEvent) {
    e.preventDefault();
    if (!newKeyword.trim()) return;
    addKeyword.mutate();
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <div className="font-semibold text-ink">{category.main}</div>
          <div className="text-xs text-slate-400">{category.sub}</div>
        </div>
        <button
          onClick={() => {
            if (confirm(`حذف تصنيف "${category.main} / ${category.sub}"؟`)) deleteCategory.mutate();
          }}
          disabled={deleteCategory.isPending}
          className="shrink-0 rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-500"
          aria-label="حذف التصنيف"
        >
          🗑
        </button>
      </div>

      <div className="mb-3 flex flex-wrap gap-1.5">
        {category.keywords.length === 0 && <span className="text-xs text-slate-300">بلا كلمات مفتاحية يدوية</span>}
        {category.keywords.map((kw) => (
          <span
            key={kw.id}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600"
          >
            {kw.keyword}
            {kw.is_whole_word && <span className="text-slate-400" title="كلمة كاملة فقط">°</span>}
            <button
              onClick={() => removeKeyword.mutate(kw.id)}
              className="text-slate-400 transition hover:text-red-500"
              aria-label="حذف الكلمة"
            >
              ✕
            </button>
          </span>
        ))}
      </div>

      <form onSubmit={handleAddKeyword} className="flex items-center gap-2">
        <input
          value={newKeyword}
          onChange={(e) => setNewKeyword(e.target.value)}
          placeholder="+ كلمة مفتاحية جديدة"
          className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2.5 py-1.5 text-xs outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        />
        <label className="flex shrink-0 items-center gap-1 text-xs text-slate-500">
          <input type="checkbox" checked={isWholeWord} onChange={(e) => setIsWholeWord(e.target.checked)} />
          كلمة كاملة
        </label>
        <button
          type="submit"
          disabled={addKeyword.isPending || !newKeyword.trim()}
          className="shrink-0 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-200 disabled:opacity-50"
        >
          إضافة
        </button>
      </form>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export default function Categories() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [main, setMain] = useState("");
  const [sub, setSub] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);

  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get<CategoryWithKeywords[]>("/categories")).data,
  });

  const createCategory = useMutation({
    mutationFn: () => api.post("/categories", { main: main.trim(), sub: sub.trim() }),
    onSuccess: () => {
      setMain("");
      setSub("");
      setShowForm(false);
      setCreateError(null);
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err: any) => setCreateError(err?.response?.data?.detail ?? "فشل إنشاء التصنيف"),
  });

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    createCategory.mutate();
  }

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">إدارة التصنيفات</span>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">التصنيفات</h1>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          {showForm ? "إلغاء" : "+ تصنيف جديد"}
        </button>
      </div>

      <p className="mb-6 text-sm text-slate-500">
        فهرس مشترك بين كل المتاجر — الكلمات المفتاحية المُضافة هنا تُستخدم فعلياً عند
        تصنيف أصناف الفواتير الجديدة تلقائياً، فوق خوارزمية التخمين المدمجة بالنظام.
      </p>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="mb-6 flex flex-wrap items-end gap-3 rounded-xl border border-slate-200 bg-white p-4"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">التصنيف الرئيسي</label>
            <input
              value={main}
              onChange={(e) => setMain(e.target.value)}
              required
              placeholder="مواد غذائية"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-500">التصنيف الفرعي</label>
            <input
              value={sub}
              onChange={(e) => setSub(e.target.value)}
              required
              placeholder="مكملات غذائية"
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            />
          </div>
          <button
            type="submit"
            disabled={createCategory.isPending}
            className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
          >
            {createCategory.isPending ? "..." : "إضافة"}
          </button>
          {createError && <p className="w-full text-xs text-red-600">{createError}</p>}
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !categories?.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          ما فيه تصنيفات بعد.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {categories.map((c) => (
            <CategoryCard key={c.id} category={c} />
          ))}
        </div>
      )}
    </Layout>
  );
}
