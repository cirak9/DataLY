import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Invoice, ReconciliationMatch } from "../lib/types";
import Layout from "../components/Layout";
import StatusBadge from "../components/StatusBadge";

const DECISION_LABELS: Record<string, string> = {
  approved: "اعتُمد الاسم المقترح",
  rejected: "أُبقي الاسم الأصلي",
  manual: "تسمية يدوية",
};

function MatchCard({
  match,
  invoiceId,
}: {
  match: ReconciliationMatch;
  invoiceId: string;
}) {
  const queryClient = useQueryClient();
  const [manualMode, setManualMode] = useState(false);
  const [manualName, setManualName] = useState(match.item_name);
  const [error, setError] = useState<string | null>(null);

  const decide = useMutation({
    mutationFn: (payload: { decision: string; manual_name?: string }) =>
      api.post(`/reconciliation-matches/${match.id}/decide`, payload),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["matches", invoiceId] });
      queryClient.invalidateQueries({ queryKey: ["invoice", invoiceId] });
    },
    onError: (err: any) => setError(err?.response?.data?.detail ?? "تعذّر تسجيل القرار"),
  });

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center justify-between">
        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
          {match.match_method === "barcode" ? "تطابق بالباركود" : "تطابق بالاسم التقريبي"}
        </span>
        {match.similarity_score != null && (
          <span className="font-mono text-xs text-slate-400">تشابه {match.similarity_score.toFixed(0)}%</span>
        )}
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-xs font-medium text-slate-400">بالفاتورة</p>
          <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-ink">{match.item_name}</p>
        </div>
        <div>
          <p className="mb-1 text-xs font-medium text-brand-600">المقترح</p>
          <p className="rounded-lg bg-brand-50 px-3 py-2 text-sm font-medium text-brand-800">
            {match.suggested_name}
          </p>
        </div>
      </div>

      {match.warning_reason && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          ⚠️ {match.warning_reason}
        </div>
      )}

      {error && <p className="mb-3 text-xs font-medium text-red-600">{error}</p>}

      {manualMode ? (
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            value={manualName}
            onChange={(e) => setManualName(e.target.value)}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
            placeholder="اكتب الاسم الصحيح..."
          />
          <div className="flex gap-2">
            <button
              onClick={() => decide.mutate({ decision: "manual", manual_name: manualName })}
              disabled={decide.isPending || !manualName.trim()}
              className="rounded-lg bg-ink px-4 py-2 text-sm font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
            >
              تأكيد
            </button>
            <button
              onClick={() => setManualMode(false)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 transition hover:bg-slate-50"
            >
              إلغاء
            </button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => decide.mutate({ decision: "approve" })}
            disabled={decide.isPending}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-60"
          >
            ✓ موافقة على المقترح
          </button>
          <button
            onClick={() => decide.mutate({ decision: "reject" })}
            disabled={decide.isPending}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
          >
            ✕ رفض — إبقاء الأصلي
          </button>
          <button
            onClick={() => setManualMode(true)}
            disabled={decide.isPending}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50 disabled:opacity-60"
          >
            ✎ تسمية يدوية
          </button>
        </div>
      )}
    </div>
  );
}

export default function InvoiceReconciliation() {
  const { invoiceId } = useParams();

  const { data: invoice } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
  });

  const { data: matches, isLoading } = useQuery({
    queryKey: ["matches", invoiceId],
    queryFn: async () =>
      (await api.get<ReconciliationMatch[]>(`/invoices/${invoiceId}/reconciliation-matches`)).data,
  });

  if (!invoice || isLoading) {
    return <Layout><p className="text-sm text-slate-500">...جار التحميل</p></Layout>;
  }

  const pending = matches?.filter((m) => m.decision === "pending") ?? [];
  const decided = matches?.filter((m) => m.decision !== "pending") ?? [];
  const isDone = pending.length === 0;

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
        <h1 className="text-2xl font-bold text-ink">تسوية الأصناف</h1>
        <StatusBadge status={invoice.status} />
      </div>

      {isDone && (
        <div className="mb-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-center">
          <p className="mb-1 text-sm font-semibold text-emerald-700">
            {matches?.length ? "🎉 كل التطابقات اتقررت" : "ما فيه تطابقات تحتاج مراجعة"}
          </p>
          <p className="mb-3 text-xs text-emerald-600">الفاتورة جاهزة للدمج والتصدير.</p>
          <Link
            to={`/invoices/${invoiceId}/export`}
            className="inline-block rounded-lg bg-emerald-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700"
          >
            التالي: الدمج والتصدير ←
          </Link>
        </div>
      )}

      {pending.length > 0 && (
        <div className="mb-8">
          <p className="mb-3 text-sm font-semibold text-slate-700">
            بانتظار المراجعة ({pending.length})
          </p>
          <div className="flex flex-col gap-4">
            {pending.map((m) => (
              <MatchCard key={m.id} match={m} invoiceId={invoiceId!} />
            ))}
          </div>
        </div>
      )}

      {decided.length > 0 && (
        <div>
          <p className="mb-3 text-sm font-semibold text-slate-500">تم البت فيها ({decided.length})</p>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
            {decided.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between border-b border-slate-100 px-4 py-3 text-sm last:border-0"
              >
                {/* item_name يعكس القيمة الحالية بعد القرار (الباك إند يحدّثها فعلياً) —
                    مو الاسم الأصلي بالفاتورة، فعرضه لحاله كافٍ وغير مضلّل بعد اتخاذ القرار. */}
                <span className="text-ink">{m.item_name}</span>
                <span className="text-xs text-slate-400">{DECISION_LABELS[m.decision] ?? m.decision}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Layout>
  );
}
