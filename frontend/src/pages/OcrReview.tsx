import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { Invoice, OcrExtractedItem, OcrExtractResponse } from "../lib/types";
import Layout from "../components/Layout";

type Confidence = "high" | "medium" | "low";

interface ReviewItem {
  id: number;
  sourceImage: number;
  itemName: string;
  quantity: number;
  unitCost: number;
  barcode: string;
  confidence: Confidence;
}

const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "ثقة عالية",
  medium: "ثقة متوسطة",
  low: "تحتاج مراجعة",
};

const CONFIDENCE_STYLE: Record<Confidence, string> = {
  high: "bg-emerald-600 text-white",
  medium: "bg-amber-500 text-white",
  low: "bg-red-600 text-white",
};

const CONFIDENCE_ICON: Record<Confidence, string> = { high: "✓", medium: "◐", low: "⚠" };

function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-bold ${CONFIDENCE_STYLE[level]}`}>
      <span>{CONFIDENCE_ICON[level]}</span>
      {CONFIDENCE_LABEL[level]}
    </span>
  );
}

function toReviewItems(items: OcrExtractedItem[]): ReviewItem[] {
  return items.map((item, i) => ({
    id: i + 1,
    sourceImage: item.source_image,
    itemName: item.item_name,
    quantity: item.quantity,
    unitCost: item.unit_cost,
    barcode: item.barcode ?? "",
    confidence: item.confidence,
  }));
}

let nextManualId = 100000;

export default function OcrReview() {
  const { invoiceId } = useParams();
  const navigate = useNavigate();
  const [items, setItems] = useState<ReviewItem[] | null>(null);
  const [confirmError, setConfirmError] = useState<string | null>(null);

  const { data: invoice } = useQuery({
    queryKey: ["invoice", invoiceId],
    queryFn: async () => (await api.get<Invoice>(`/invoices/${invoiceId}`)).data,
  });

  const extract = useMutation({
    mutationFn: async () => (await api.post<OcrExtractResponse>(`/invoices/${invoiceId}/ocr-extract`)).data,
    onSuccess: (data) => setItems(toReviewItems(data.items)),
  });

  const confirm = useMutation({
    mutationFn: () =>
      api.post(`/invoices/${invoiceId}/ocr-confirm`, {
        items: (items ?? []).map((i) => ({
          item_name: i.itemName,
          quantity: i.quantity,
          unit_cost: i.unitCost,
          barcode: i.barcode || null,
        })),
      }),
    onSuccess: () => navigate(`/invoices/${invoiceId}/review`),
    onError: (err: any) => setConfirmError(err?.response?.data?.detail ?? "تعذّر اعتماد الأصناف"),
  });

  const imageCount = useMemo(
    () => (items ? new Set(items.map((i) => i.sourceImage).filter((n) => n > 0)).size : 0),
    [items]
  );
  const totalValue = useMemo(() => (items ?? []).reduce((sum, i) => sum + i.quantity * i.unitCost, 0), [items]);
  const lowConfidenceCount = (items ?? []).filter((i) => i.confidence === "low").length;

  function updateField(id: number, field: "itemName" | "quantity" | "unitCost" | "barcode", value: string) {
    setItems((prev) =>
      (prev ?? []).map((item) => {
        if (item.id !== id) return item;
        if (field === "quantity" || field === "unitCost") {
          const num = Number(value);
          return { ...item, [field]: Number.isFinite(num) ? num : item[field] };
        }
        return { ...item, [field]: value };
      })
    );
  }

  function removeRow(id: number) {
    setItems((prev) => (prev ?? []).filter((i) => i.id !== id));
  }

  function addManualRow() {
    setItems((prev) => [
      ...(prev ?? []),
      { id: nextManualId++, sourceImage: 0, itemName: "", quantity: 1, unitCost: 0, barcode: "", confidence: "high" },
    ]);
  }

  const canConfirm = !!items?.length && items.every((i) => i.itemName.trim() && i.quantity > 0 && i.unitCost >= 0);

  if (!invoice) return <Layout><p className="text-sm text-slate-500">...جار التحميل</p></Layout>;

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to={`/stores/${invoice.store_id}/invoices`} className="text-slate-400 hover:text-slate-600">
          الفواتير
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">مراجعة استخراج OCR</span>
      </div>

      <h1 className="mb-6 text-2xl font-bold text-ink">مراجعة الأصناف المستخرجة</h1>

      {invoice.status !== "uploaded" ? (
        <div className="rounded-xl border border-slate-200 bg-white px-6 py-8 text-center text-sm text-slate-500">
          هالفاتورة اتّعمدت مسبقاً أو تجاوزت مرحلة المراجعة.{" "}
          <Link to={`/invoices/${invoice.id}/review`} className="font-medium text-brand-600 hover:underline">
            روح لشاشة المراجعة العادية ←
          </Link>
        </div>
      ) : items === null ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center">
          {extract.isError && (
            <div className="mx-auto mb-4 max-w-md rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {(extract.error as any)?.response?.data?.detail ?? "فشل استخراج الأصناف من الصور"}
            </div>
          )}
          <button
            onClick={() => extract.mutate()}
            disabled={extract.isPending}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:opacity-60"
          >
            {extract.isPending ? "...جار الاستخراج" : extract.isError ? "أعد المحاولة" : "ابدأ الاستخراج (OCR)"}
          </button>
        </div>
      ) : (
        <>
          <div className="mb-4 flex flex-wrap items-center gap-3 text-xs text-slate-500">
            <span className="rounded-full bg-slate-100 px-3 py-1">📷 {imageCount} صورة مصدر</span>
            <span className="rounded-full bg-slate-100 px-3 py-1">{items.length} صنف</span>
            {lowConfidenceCount > 0 && (
              <span className="rounded-full border border-red-200 bg-red-50 px-3 py-1 text-red-700">
                {lowConfidenceCount} صنف يحتاج مراجعة دقيقة
              </span>
            )}
          </div>

          {confirmError && (
            <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {confirmError}
            </div>
          )}

          {/* بطاقات للموبايل */}
          <div className="flex flex-col gap-3 sm:hidden">
            {items.map((item) => (
              <div
                key={item.id}
                className={`rounded-xl border bg-white p-4 ${item.confidence === "low" ? "border-red-200" : "border-slate-200"}`}
              >
                <div className="mb-2 flex items-start justify-between gap-2">
                  <input
                    value={item.itemName}
                    placeholder="اسم الصنف"
                    onChange={(e) => updateField(item.id, "itemName", e.target.value)}
                    className="w-full rounded border border-transparent bg-transparent px-1 py-0.5 text-right font-medium text-ink outline-none focus:border-slate-200 focus:ring-2 focus:ring-brand-100"
                  />
                  <button
                    onClick={() => removeRow(item.id)}
                    className="shrink-0 rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-500"
                    aria-label="حذف الصنف"
                  >
                    ✕
                  </button>
                </div>
                <div className="mb-3 flex items-center gap-2">
                  <ConfidenceBadge level={item.confidence} />
                  {item.sourceImage > 0 && <span className="text-[11px] text-slate-400">من الصورة {item.sourceImage}</span>}
                </div>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <label className="rounded-lg bg-slate-50 py-2">
                    <div className="mb-0.5 text-slate-400">الكمية</div>
                    <input
                      value={item.quantity}
                      onChange={(e) => updateField(item.id, "quantity", e.target.value)}
                      className="w-full rounded border-none bg-transparent text-center font-mono text-ink outline-none"
                    />
                  </label>
                  <label className="rounded-lg bg-slate-50 py-2">
                    <div className="mb-0.5 text-slate-400">سعر الوحدة</div>
                    <input
                      value={item.unitCost}
                      onChange={(e) => updateField(item.id, "unitCost", e.target.value)}
                      className="w-full rounded border-none bg-transparent text-center font-mono text-ink outline-none"
                    />
                  </label>
                  <div className="rounded-lg bg-slate-50 py-2">
                    <div className="text-slate-400">الإجمالي</div>
                    <div className="mt-0.5 font-mono text-ink">{(item.quantity * item.unitCost).toFixed(2)}</div>
                  </div>
                </div>
                <label className="mt-3 flex items-center justify-between gap-2 text-xs">
                  <span className="text-slate-400">الباركود</span>
                  <input
                    value={item.barcode}
                    placeholder="—"
                    onChange={(e) => updateField(item.id, "barcode", e.target.value)}
                    className="w-40 rounded border border-slate-200 px-2 py-1 text-center font-mono text-ink outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
                  />
                </label>
              </div>
            ))}
          </div>

          {/* جدول لعرض الشاشة الأكبر */}
          <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white sm:block">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-right text-xs font-medium text-slate-500">
                  <th className="px-3 py-3">الصنف</th>
                  <th className="px-3 py-3">المصدر</th>
                  <th className="px-3 py-3">الثقة</th>
                  <th className="px-3 py-3">الكمية</th>
                  <th className="px-3 py-3">سعر الوحدة</th>
                  <th className="px-3 py-3">الإجمالي</th>
                  <th className="px-3 py-3">الباركود</th>
                  <th className="px-3 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className={`border-b border-slate-100 last:border-0 ${item.confidence === "low" ? "bg-red-50/40" : ""}`}>
                    <td className="min-w-[200px] px-1 py-1">
                      <input
                        value={item.itemName}
                        placeholder="اسم الصنف"
                        onChange={(e) => updateField(item.id, "itemName", e.target.value)}
                        className="w-full min-w-0 rounded border border-transparent bg-transparent px-2 py-1 text-sm outline-none transition hover:border-slate-200 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                      />
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-xs text-slate-400">
                      {item.sourceImage > 0 ? `صورة ${item.sourceImage}` : "يدوي"}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3">
                      <ConfidenceBadge level={item.confidence} />
                    </td>
                    <td className="min-w-[80px] px-1 py-1">
                      <input
                        value={item.quantity}
                        onChange={(e) => updateField(item.id, "quantity", e.target.value)}
                        className="w-full min-w-0 rounded border border-transparent bg-transparent px-2 py-1 text-right font-mono text-sm outline-none transition hover:border-slate-200 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                      />
                    </td>
                    <td className="min-w-[100px] px-1 py-1">
                      <input
                        value={item.unitCost}
                        onChange={(e) => updateField(item.id, "unitCost", e.target.value)}
                        className="w-full min-w-0 rounded border border-transparent bg-transparent px-2 py-1 text-right font-mono text-sm outline-none transition hover:border-slate-200 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                      />
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 font-mono text-xs text-slate-600">
                      {(item.quantity * item.unitCost).toFixed(2)}
                    </td>
                    <td className="min-w-[130px] px-1 py-1">
                      <input
                        value={item.barcode}
                        placeholder="—"
                        onChange={(e) => updateField(item.id, "barcode", e.target.value)}
                        className="w-full min-w-0 rounded border border-transparent bg-transparent px-2 py-1 text-right font-mono text-sm outline-none transition hover:border-slate-200 focus:border-brand-400 focus:bg-white focus:ring-2 focus:ring-brand-100"
                      />
                    </td>
                    <td className="px-2 py-1 text-center">
                      <button
                        onClick={() => removeRow(item.id)}
                        className="rounded p-1 text-slate-300 transition hover:bg-red-50 hover:text-red-500"
                        aria-label="حذف الصنف"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-3 flex justify-start">
            <button
              onClick={addManualRow}
              className="rounded-lg border border-dashed border-slate-300 px-4 py-2 text-sm font-medium text-slate-500 transition hover:border-brand-400 hover:text-brand-600"
            >
              + إضافة صنف يدوي (لو فاته OCR)
            </button>
          </div>

          <div className="sticky bottom-4 mt-6 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-lg sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-slate-600">
              الإجمالي التقديري: <span className="font-mono font-semibold text-ink">{totalValue.toFixed(2)}</span>
              {lowConfidenceCount > 0 && (
                <span className="mr-2 text-xs text-red-600">— راجع الأصناف المعلَّمة بالأحمر قبل الاعتماد</span>
              )}
            </div>
            <button
              onClick={() => confirm.mutate()}
              disabled={!canConfirm || confirm.isPending}
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {confirm.isPending ? "...جار الاعتماد" : "اعتماد ودخول للمعالجة ←"}
            </button>
          </div>
        </>
      )}
    </Layout>
  );
}
