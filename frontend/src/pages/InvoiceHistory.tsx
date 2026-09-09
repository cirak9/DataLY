import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { downloadInvoiceExport } from "../lib/download";
import { Invoice, Store } from "../lib/types";
import Layout from "../components/Layout";

export default function InvoiceHistory() {
  const { storeId } = useParams();
  const [downloadingId, setDownloadingId] = useState<number | null>(null);

  const { data: store } = useQuery({
    queryKey: ["store", storeId],
    queryFn: async () => (await api.get<Store>(`/stores/${storeId}`)).data,
  });

  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices", storeId],
    queryFn: async () => (await api.get<Invoice[]>(`/stores/${storeId}/invoices`)).data,
  });

  const exported = invoices?.filter((inv) => inv.status === "exported") ?? [];

  async function handleDownload(inv: Invoice) {
    setDownloadingId(inv.id);
    try {
      const name = `output_alsahl_${inv.original_filename?.replace(/\.[^.]+$/, "") ?? inv.id}.xlsx`;
      await downloadInvoiceExport(inv.id, name);
    } finally {
      setDownloadingId(null);
    }
  }

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{store?.name ?? "..."}</span>
      </div>

      <div className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-ink">سجل الفواتير المصدَّرة</h1>
        <Link
          to={`/stores/${storeId}/invoices`}
          className="text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          الفواتير الجارية ←
        </Link>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !exported.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          ما فيه فواتير مُصدَّرة بعد — الفواتير المكتملة (بعد التصدير) تظهر هنا.
        </div>
      ) : (
        <>
          {/* بطاقات للموبايل */}
          <div className="flex flex-col gap-3 sm:hidden">
            {exported.map((inv) => (
              <div key={inv.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="mb-1 flex items-start justify-between gap-3">
                  <span className="font-medium text-ink">{inv.original_filename ?? "—"}</span>
                  <button
                    onClick={() => handleDownload(inv)}
                    disabled={downloadingId === inv.id}
                    className="flex-shrink-0 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-60"
                  >
                    {downloadingId === inv.id ? "...جار التنزيل" : "📥 تنزيل"}
                  </button>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <span>{inv.supplier_name_raw ?? "—"}</span>
                  <span className="font-mono">
                    {new Date(inv.uploaded_at).toLocaleDateString("ar-LY", { dateStyle: "medium" })}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* جدول لعرض الشاشة الأكبر */}
          <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white sm:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-right text-xs font-medium text-slate-500">
                  <th className="px-4 py-3">الملف</th>
                  <th className="px-4 py-3">المورد</th>
                  <th className="px-4 py-3">تاريخ الرفع</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {exported.map((inv) => (
                  <tr key={inv.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-3 font-medium text-ink">{inv.original_filename ?? "—"}</td>
                    <td className="px-4 py-3 text-slate-500">{inv.supplier_name_raw ?? "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-400">
                      {new Date(inv.uploaded_at).toLocaleString("ar-LY", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-left">
                      <button
                        onClick={() => handleDownload(inv)}
                        disabled={downloadingId === inv.id}
                        className="rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-60"
                      >
                        {downloadingId === inv.id ? "...جار التنزيل" : "📥 تنزيل"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Layout>
  );
}
