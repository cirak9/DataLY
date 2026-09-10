import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import Layout from "../components/Layout";

type Confidence = "high" | "medium" | "low";

interface OcrCandidateItem {
  id: number;
  sourceImage: number;
  itemName: string;
  quantity: number;
  unitCost: number;
  barcode: string;
  confidence: Confidence;
}

// بيانات تجريبية فقط — تحاكي شكل مخرجات OCR (اسم + كمية + سعر + باركود اختياري،
// مع درجة ثقة لكل صنف ورقم الصورة المصدر لدعم دمج عدة صور بفاتورة واحدة).
// تُستبدل ببيانات حقيقية من POST /invoices/{id}/ocr-extract لما تُفعَّل خدمة Tesseract.
const SAMPLE_ITEMS: OcrCandidateItem[] = [
  { id: 1, sourceImage: 1, itemName: "زيت ذرة 1.5 لتر", quantity: 12, unitCost: 8.75, barcode: "6221031202019", confidence: "high" },
  { id: 2, sourceImage: 1, itemName: "معجون طماطم 400غ", quantity: 24, unitCost: 2.4, barcode: "6221031202026", confidence: "high" },
  { id: 3, sourceImage: 1, itemName: "أرز مصري كيس 5كغ", quantity: 6, unitCost: 21.5, barcode: "", confidence: "medium" },
  { id: 4, sourceImage: 2, itemName: "سكر أبيض كيس 1كغ", quantity: 40, unitCost: 3.1, barcode: "6221031202033", confidence: "high" },
  { id: 5, sourceImage: 2, itemName: "عدس أحمر1كغ", quantity: 18, unitCost: 4.65, barcode: "", confidence: "low" },
  { id: 6, sourceImage: 2, itemName: "شاي أخضر ٥٠ ظرف", quantity: 10, unitCost: 6.2, barcode: "", confidence: "low" },
];

const CONFIDENCE_LABEL: Record<Confidence, string> = {
  high: "ثقة عالية",
  medium: "ثقة متوسطة",
  low: "تحتاج مراجعة",
};

const CONFIDENCE_STYLE: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-red-50 text-red-700 border-red-200",
};

function ConfidenceBadge({ level }: { level: Confidence }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${CONFIDENCE_STYLE[level]}`}>
      {CONFIDENCE_LABEL[level]}
    </span>
  );
}

let nextId = 1000;

export default function OcrReviewPreview() {
  const [items, setItems] = useState<OcrCandidateItem[]>(SAMPLE_ITEMS);
  const [confirmed, setConfirmed] = useState(false);

  const imageCount = useMemo(() => new Set(items.map((i) => i.sourceImage)).size, [items]);
  const totalValue = useMemo(() => items.reduce((sum, i) => sum + i.quantity * i.unitCost, 0), [items]);
  const lowConfidenceCount = items.filter((i) => i.confidence === "low").length;

  function updateField(id: number, field: keyof OcrCandidateItem, value: string) {
    setItems((prev) =>
      prev.map((item) => {
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
    setItems((prev) => prev.filter((i) => i.id !== id));
  }

  function addManualRow() {
    setItems((prev) => [
      ...prev,
      { id: nextId++, sourceImage: 0, itemName: "", quantity: 1, unitCost: 0, barcode: "", confidence: "high" },
    ]);
  }

  const canConfirm = items.length > 0 && items.every((i) => i.itemName.trim() && i.quantity > 0 && i.unitCost >= 0);

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">معاينة شاشة المراجعة (OCR)</span>
      </div>

      <div className="mb-4 flex items-center gap-3">
        <h1 className="text-2xl font-bold text-ink">مراجعة الأصناف المستخرجة</h1>
      </div>

      <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        🧪 معاينة تصميم — الأصناف تحت بيانات تجريبية تحاكي شكل مخرجات OCR، مو من فاتورة
        حقيقية. هالشاشة بتُربط بخدمة استخراج النص (Tesseract) لما تُفعَّل بنيتها التحتية؛
        الهدف الآن اختبار تجربة المراجعة والتعديل قبل الاعتماد.
      </div>

      {confirmed ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-6 py-8 text-center">
          <p className="mb-2 text-lg font-bold text-emerald-800">تم الاعتماد ✓</p>
          <p className="mx-auto max-w-md text-sm leading-relaxed text-emerald-700">
            بالنسخة الحقيقية، هالخطوة بتحفظ الأصناف المعتمدة كـ invoice_items وتنقل حالة
            الفاتورة إلى "منظّفة" — بنفس نقطة البداية اللي تدخل منها الآن بعد "نظّف
            الفاتورة"، وتكمل بنفس المسار: جلسة استلام ← تسوية ← دمج ← تصدير.
          </p>
          <button
            onClick={() => setConfirmed(false)}
            className="mt-4 rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
          >
            رجوع للمراجعة
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

          {/* بطاقات للموبايل */}
          <div className="flex flex-col gap-3 sm:hidden">
            {items.map((item) => (
              <div
                key={item.id}
                className={`rounded-xl border bg-white p-4 ${
                  item.confidence === "low" ? "border-red-200" : "border-slate-200"
                }`}
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
                  {item.sourceImage > 0 && (
                    <span className="text-[11px] text-slate-400">من الصورة {item.sourceImage}</span>
                  )}
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
                  <tr
                    key={item.id}
                    className={`border-b border-slate-100 last:border-0 ${
                      item.confidence === "low" ? "bg-red-50/40" : ""
                    }`}
                  >
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
              onClick={() => setConfirmed(true)}
              disabled={!canConfirm}
              className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              اعتماد ودخول للمعالجة ←
            </button>
          </div>
        </>
      )}
    </Layout>
  );
}
