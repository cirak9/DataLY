import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { IntakeSession, Invoice } from "../lib/types";
import Layout from "../components/Layout";

export default function InvoiceSession() {
  const { invoiceId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [draft, setDraft] = useState({ barcode: "", expiration_date: "", sale_price: "" });
  const [completeError, setCompleteError] = useState<string | null>(null);

  const { data: invoice } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
  });

  const { data: session, isLoading } = useQuery({
    queryKey: ["session", invoiceId],
    queryFn: async () => (await api.get<IntakeSession>(`/invoices/${invoiceId}/session`)).data,
  });

  const items = session?.items ?? [];
  const active = items.find((i) => i.id === activeId) ?? items[0];

  useEffect(() => {
    if (!active) return;
    setActiveId(active.id);
    setDraft({
      barcode: active.barcode ?? "",
      expiration_date: active.expiration_date ?? "",
      sale_price: active.sale_price != null ? String(active.sale_price) : "",
    });
  }, [active?.id]);

  const isMethod2 = session?.method === 2;

  const saveItem = useMutation({
    mutationFn: (payload: { barcode: string; expiration_date: string; sale_price: string }) => {
      const salePrice = payload.sale_price === "" ? null : Number(payload.sale_price);
      // بالطريقة الثانية الباركود/الصلاحية مقفولين من الباك إند — حتى إرسالهم بنفس
      // القيمة الأصلية يُرفض 422 (يتحقق من وجود المفتاح، مو من تغيّر القيمة).
      const body = isMethod2
        ? { sale_price: salePrice }
        : {
            barcode: payload.barcode,
            expiration_date: payload.expiration_date === "" ? null : payload.expiration_date,
            sale_price: salePrice,
          };
      return api.patch(`/sessions/${session!.id}/items/${active!.id}`, body);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["session", invoiceId] }),
  });

  const complete = useMutation({
    mutationFn: () => api.post(`/sessions/${session!.id}/complete`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
      navigate(`/invoices/${invoiceId}/reconciliation`);
    },
    onError: (err: any) => setCompleteError(err?.response?.data?.detail ?? "تعذّر إكمال الجلسة"),
  });

  function saveAndGo(dir: 1 | -1) {
    if (!active) return;
    saveItem.mutate(draft);
    const idx = items.findIndex((i) => i.id === active.id);
    const next = items[idx + dir];
    if (next) setActiveId(next.id);
  }

  if (isLoading || !invoice) {
    return <Layout><p className="text-sm text-slate-500">...جار التحميل</p></Layout>;
  }

  if (!session) {
    return (
      <Layout>
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          ما فيه جلسة استلام لهذي الفاتورة بعد.{" "}
          <Link to={`/invoices/${invoiceId}/review`} className="font-medium text-brand-600">
            ارجع لشاشة المراجعة
          </Link>
        </div>
      </Layout>
    );
  }

  const doneCount = items.filter((i) => i.is_complete).length;
  const allDone = doneCount === items.length && items.length > 0;
  const isLocked = session.status === "complete";

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to={`/stores/${invoice.store_id}/invoices`} className="text-slate-400 hover:text-slate-600">
          الفواتير
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{invoice.original_filename}</span>
      </div>

      <div className="mb-2 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-ink">جلسة استلام التاجر</h1>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
            isMethod2 ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-800"
          }`}
        >
          {isMethod2 ? "الطريقة الثانية — إدخال سريع" : "الطريقة الأولى — إدخال يدوي"}
        </span>
      </div>

      <div className="mb-6">
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-brand-600 transition-all"
            style={{ width: `${items.length ? (doneCount / items.length) * 100 : 0}%` }}
          />
        </div>
        <p className="mt-1.5 text-xs text-slate-500">
          {doneCount} من {items.length} صنف مكتمل
        </p>
      </div>

      {completeError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {completeError}
        </div>
      )}

      {isLocked && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          الجلسة مكتملة — تم التسليم للتسوية تلقائياً.{" "}
          <Link to={`/invoices/${invoiceId}/reconciliation`} className="font-semibold underline">
            روح للتسوية ←
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 md:grid-cols-[240px_1fr]">
        {/* sidebar */}
        <div className="order-2 max-h-[420px] overflow-y-auto rounded-xl border border-slate-200 bg-white md:order-1">
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveId(item.id)}
              className={`flex w-full items-center gap-2 border-b border-slate-100 px-3 py-2.5 text-right text-sm transition last:border-0 ${
                item.id === active?.id ? "bg-brand-50 font-medium text-brand-700" : "hover:bg-slate-50"
              }`}
            >
              <span
                className={`grid h-4 w-4 flex-shrink-0 place-items-center rounded-full text-[10px] ${
                  item.is_complete ? "bg-emerald-500 text-white" : "border border-slate-300"
                }`}
              >
                {item.is_complete ? "✓" : ""}
              </span>
              <span className="truncate">{item.item_name}</span>
            </button>
          ))}
        </div>

        {/* active item card */}
        <div className="order-1 rounded-xl border border-slate-200 bg-white p-6 md:order-2">
          {active && (
            <>
              <p className="mb-1 text-xs text-slate-400">
                صنف {items.findIndex((i) => i.id === active.id) + 1} من {items.length}
              </p>
              <h2 className="mb-1 text-xl font-bold text-ink">{active.item_name}</h2>
              {active.unit_cost != null && (
                <p className="mb-6 inline-block rounded-lg bg-amber-50 px-3 py-1 font-mono text-sm font-semibold text-amber-700">
                  تكلفة الوحدة: {active.unit_cost.toFixed(3)}
                </p>
              )}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-slate-700">الباركود</label>
                  {isMethod2 ? (
                    <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-500">
                      {active.barcode || "—"}
                    </p>
                  ) : (
                    <input
                      value={draft.barcode}
                      onChange={(e) => setDraft((d) => ({ ...d, barcode: e.target.value }))}
                      disabled={isLocked}
                      placeholder="امسح الباركود..."
                      className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
                    />
                  )}
                </div>

                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-slate-700">الصلاحية</label>
                  {isMethod2 ? (
                    <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 font-mono text-sm text-slate-500">
                      {active.expiration_date || "—"}
                    </p>
                  ) : (
                    <input
                      type="date"
                      value={draft.expiration_date}
                      onChange={(e) => setDraft((d) => ({ ...d, expiration_date: e.target.value }))}
                      disabled={isLocked}
                      className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
                    />
                  )}
                </div>

                <div className="flex flex-col gap-1.5 sm:col-span-2">
                  <label className="text-sm font-medium text-slate-700">سعر البيع</label>
                  <input
                    type="number"
                    step="0.001"
                    value={draft.sale_price}
                    onChange={(e) => setDraft((d) => ({ ...d, sale_price: e.target.value }))}
                    disabled={isLocked}
                    placeholder="أدخل سعر البيع..."
                    className="rounded-lg border border-slate-300 px-3 py-2 font-mono text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:bg-slate-50"
                  />
                </div>
              </div>

              {!isLocked && (
                <div className="mt-6 flex gap-2">
                  <button
                    onClick={() => saveAndGo(-1)}
                    disabled={items.findIndex((i) => i.id === active.id) === 0}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-40"
                  >
                    ◀ السابق
                  </button>
                  <button
                    onClick={() => saveItem.mutate(draft)}
                    className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
                  >
                    💾 حفظ
                  </button>
                  <button
                    onClick={() => saveAndGo(1)}
                    disabled={items.findIndex((i) => i.id === active.id) === items.length - 1}
                    className="flex-1 rounded-lg bg-brand-600 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-40"
                  >
                    حفظ والتالي ▶
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {!isLocked && allDone && (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-center">
          <p className="mb-3 text-sm font-semibold text-emerald-700">🎉 اكتملت جميع الأصناف</p>
          <button
            onClick={() => complete.mutate()}
            disabled={complete.isPending}
            className="rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
          >
            {complete.isPending ? "...جار الإكمال" : "إكمال الجلسة ←"}
          </button>
        </div>
      )}
    </Layout>
  );
}
