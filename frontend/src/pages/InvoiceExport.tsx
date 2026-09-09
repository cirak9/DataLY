import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { AlsahlExport, Invoice, MergeResult } from "../lib/types";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";

const EARLY_STATUSES = new Set(["uploaded", "cleaned", "session_pending", "session_complete"]);

function StepNumber({ n, done, active }: { n: number; done: boolean; active: boolean }) {
  return (
    <span
      className={`grid h-7 w-7 flex-shrink-0 place-items-center rounded-full text-sm font-bold ${
        done ? "bg-emerald-500 text-white" : active ? "bg-brand-600 text-white" : "bg-slate-200 text-slate-500"
      }`}
    >
      {done ? "✓" : n}
    </span>
  );
}

export default function InvoiceExport() {
  const { invoiceId } = useParams();
  const queryClient = useQueryClient();
  const [mergeSummary, setMergeSummary] = useState<{ lots: number; catalog: number } | null>(null);
  const [lastExportAt, setLastExportAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const { data: invoice } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
  });

  const merge = useMutation({
    mutationFn: async () => (await api.post<MergeResult>(`/invoices/${invoiceId}/merge`)).data,
    onSuccess: (result) => {
      setError(null);
      setMergeSummary({ lots: result.lots_upserted, catalog: result.catalog_entries_learned });
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "تعذّر الدمج"),
  });

  const doExport = useMutation({
    mutationFn: async () => (await api.post<AlsahlExport>(`/invoices/${invoiceId}/export`)).data,
    onSuccess: (result) => {
      setError(null);
      setLastExportAt(result.exported_at);
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "تعذّر التصدير"),
  });

  async function handleDownload() {
    setDownloading(true);
    setError(null);
    try {
      const res = await api.get(`/invoices/${invoiceId}/export/download`, { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `output_alsahl_${invoice?.original_filename?.replace(/\.[^.]+$/, "") ?? invoiceId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setError("تعذّر تنزيل الملف");
    } finally {
      setDownloading(false);
    }
  }

  if (!invoice) return <Layout><p className="text-sm text-slate-500">...جار التحميل</p></Layout>;

  if (EARLY_STATUSES.has(invoice.status)) {
    return (
      <Layout>
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          لازم تكمل التسوية أولاً قبل الدمج والتصدير.{" "}
          <Link to={`/invoices/${invoiceId}/reconciliation`} className="font-medium text-brand-600">
            روح للتسوية
          </Link>
        </div>
      </Layout>
    );
  }

  const isMerged = invoice.status === "merged" || invoice.status === "exported";
  const isExported = invoice.status === "exported" || lastExportAt !== null;

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to={`/stores/${invoice.store_id}/invoices`} className="text-slate-400 hover:text-slate-600">
          الفواتير
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{invoice.original_filename}</span>
      </div>

      <div className="mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-ink">الدمج والتصدير</h1>
        <StatusBadge status={invoice.status} />
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex flex-col gap-4">
        {/* الخطوة 1: الدمج */}
        <div className="rounded-xl border border-slate-200 bg-white p-5">
          <div className="mb-3 flex items-center gap-3">
            <StepNumber n={1} done={isMerged} active={true} />
            <h2 className="font-semibold text-ink">الدمج بالمخزون التراكمي</h2>
          </div>
          <p className="mb-4 text-sm text-slate-500">
            يحدّث مخزون المتجر (اللوتات حسب الباركود/الصلاحية) ويعلّم فهرس الأصناف المشترك بالباركودات الجديدة.
          </p>

          {isMerged ? (
            mergeSummary ? (
              <div className="flex gap-6 rounded-lg bg-emerald-50 px-4 py-3 text-sm">
                <span className="text-emerald-700">
                  <strong className="font-mono">{mergeSummary.lots}</strong> لوت مخزون تحدّث
                </span>
                <span className="text-emerald-700">
                  <strong className="font-mono">{mergeSummary.catalog}</strong> صنف جديد بالفهرس المشترك
                </span>
              </div>
            ) : (
              <p className="text-sm font-medium text-emerald-600">تم الدمج مسبقاً ✓</p>
            )
          ) : (
            <button
              onClick={() => merge.mutate()}
              disabled={merge.isPending}
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
            >
              {merge.isPending ? "...جار الدمج" : "دمج الآن"}
            </button>
          )}
        </div>

        {/* الخطوة 2: التصدير */}
        <div className={`rounded-xl border border-slate-200 bg-white p-5 ${!isMerged ? "opacity-50" : ""}`}>
          <div className="mb-3 flex items-center gap-3">
            <StepNumber n={2} done={isExported} active={isMerged} />
            <h2 className="font-semibold text-ink">تصدير ملف السهل</h2>
          </div>
          <p className="mb-4 text-sm text-slate-500">
            يولّد ملف Excel جاهز للاستيراد المباشر بشاشة "فاتورة مشتريات" بمنظومة السهل.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => doExport.mutate()}
              disabled={!isMerged || doExport.isPending}
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-40"
            >
              {doExport.isPending ? "...جار التوليد" : isExported ? "توليد نسخة جديدة" : "تصدير الآن"}
            </button>

            {isExported && (
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="rounded-lg border border-emerald-300 bg-emerald-50 px-5 py-2.5 text-sm font-semibold text-emerald-700 transition hover:bg-emerald-100 disabled:opacity-60"
              >
                {downloading ? "...جار التنزيل" : "📥 تنزيل آخر ملف"}
              </button>
            )}
          </div>

          {lastExportAt && (
            <p className="mt-3 text-xs text-slate-400">
              آخر تصدير: {new Date(lastExportAt).toLocaleString("ar-LY", { dateStyle: "medium", timeStyle: "short" })}
            </p>
          )}
        </div>
      </div>
    </Layout>
  );
}
