import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Invoice, InvoiceItem } from "../lib/types";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";

function EditableCell({
  value,
  onSave,
  align = "right",
  mono = false,
}: {
  value: string | number;
  onSave: (v: string) => void;
  align?: "right" | "left";
  mono?: boolean;
}) {
  const [draft, setDraft] = useState(String(value));

  return (
    <input
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        if (draft !== String(value)) onSave(draft);
      }}
      className={`w-full min-w-0 rounded border border-transparent bg-transparent px-2 py-1 text-sm outline-none transition hover:border-slate-200 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100 ${
        mono ? "font-mono" : ""
      } ${align === "left" ? "text-left" : "text-right"}`}
    />
  );
}

export default function InvoiceReview() {
  const { invoiceId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [cleanError, setCleanError] = useState<string | null>(null);
  const [sessionError, setSessionError] = useState<string | null>(null);

  const { data: invoice } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
  });

  const { data: items, isLoading } = useQuery({
    queryKey: ["invoice-items", invoiceId],
    queryFn: async () => (await api.get<InvoiceItem[]>(`/invoices/${invoiceId}/items`)).data,
    enabled: invoice?.status !== "uploaded",
  });

  const clean = useMutation({
    mutationFn: () => api.post(`/invoices/${invoiceId}/clean`),
    onSuccess: () => {
      setCleanError(null);
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["invoice-items", invoiceId] });
    },
    onError: (err: any) => setCleanError(err?.response?.data?.detail ?? "فشل التنظيف"),
  });

  const updateItem = useMutation({
    mutationFn: ({ itemId, field, value }: { itemId: number; field: string; value: string }) =>
      api.patch(`/invoices/${invoiceId}/items/${itemId}`, { [field]: value }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["invoice-items", invoiceId] }),
  });

  const startSession = useMutation({
    mutationFn: () => api.post(`/invoices/${invoiceId}/session`),
    onSuccess: () => navigate(`/invoices/${invoiceId}/session`),
    onError: (err: any) => setSessionError(err?.response?.data?.detail ?? "تعذّر بدء جلسة الاستلام"),
  });

  if (!invoice) return <Layout><p className="text-sm text-slate-500">...جار التحميل</p></Layout>;

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to={`/stores/${invoice.store_id}/invoices`} className="text-slate-400 hover:text-slate-600">
          الفواتير
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{invoice.original_filename}</span>
      </div>

      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-ink">مراجعة الفاتورة</h1>
          <StatusBadge status={invoice.status} />
        </div>

        {invoice.status === "uploaded" ? (
          <button
            onClick={() => clean.mutate()}
            disabled={clean.isPending}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {clean.isPending ? "...جار التنظيف" : "نظّف الفاتورة"}
          </button>
        ) : (
          <button
            onClick={() => startSession.mutate()}
            disabled={startSession.isPending || invoice.status !== "cleaned"}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {startSession.isPending ? "...جار البدء" : "التالي: جلسة الاستلام ←"}
          </button>
        )}
      </div>

      {cleanError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {cleanError}
        </div>
      )}
      {sessionError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {sessionError}
        </div>
      )}

      {invoice.status === "uploaded" ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          الفاتورة مرفوعة بس لسا ما اتنظّفت — اضغط "نظّف الفاتورة" فوق.
        </div>
      ) : isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-right text-xs font-medium text-slate-500">
                <th className="px-3 py-3">الصنف</th>
                <th className="px-3 py-3">التصنيف</th>
                <th className="px-3 py-3">الكمية</th>
                <th className="px-3 py-3">العبوة</th>
                <th className="px-3 py-3">تكلفة الوحدة</th>
                <th className="px-3 py-3">الإجمالي</th>
              </tr>
            </thead>
            <tbody>
              {items?.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 last:border-0">
                  <td className="min-w-[220px] px-1 py-1">
                    <EditableCell
                      value={item.item_name}
                      onSave={(v) => updateItem.mutate({ itemId: item.id, field: "item_name", value: v })}
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-500">
                    {item.category ? `${item.category.main} / ${item.category.sub}` : "—"}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-600">
                    {item.quantity_pieces}
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-600">
                    {item.per_box ?? <span className="text-slate-300">—</span>}
                  </td>
                  <td className="min-w-[110px] px-1 py-1">
                    <EditableCell
                      value={item.unit_cost ?? 0}
                      mono
                      onSave={(v) => updateItem.mutate({ itemId: item.id, field: "unit_cost", value: v })}
                    />
                  </td>
                  <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-600">
                    {item.total_price ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  );
}
