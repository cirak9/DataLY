import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/api";
import { InventoryLot, Store } from "../lib/types";
import Layout from "../components/Layout";

const DAY_MS = 1000 * 60 * 60 * 24;

type ExpiryStatus = "expired" | "soon" | "ok";

function expiryStatus(date: string | null): ExpiryStatus {
  if (!date) return "ok";
  const days = Math.floor((new Date(date).getTime() - Date.now()) / DAY_MS);
  if (days < 0) return "expired";
  if (days <= 30) return "soon";
  return "ok";
}

const EXPIRY_FILTER_LABEL: Record<"all" | ExpiryStatus, string> = {
  all: "كل الصلاحيات",
  expired: "منتهي",
  soon: "قريب الانتهاء (٣٠ يوم)",
  ok: "سليم",
};

function ExpiryBadge({ date }: { date: string | null }) {
  if (!date) {
    return <span className="text-xs text-slate-300">—</span>;
  }
  const days = Math.floor((new Date(date).getTime() - Date.now()) / DAY_MS);
  const formatted = new Date(date).toLocaleDateString("ar-LY", { dateStyle: "medium" });

  if (days < 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">منتهي</span>
        <span className="font-mono text-xs text-slate-400">{formatted}</span>
      </span>
    );
  }
  if (days <= 30) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
          بعد {days} يوم
        </span>
        <span className="font-mono text-xs text-slate-400">{formatted}</span>
      </span>
    );
  }
  return <span className="font-mono text-xs text-slate-500">{formatted}</span>;
}

export default function Inventory() {
  const { storeId } = useParams();
  const [search, setSearch] = useState("");
  const [expiryFilter, setExpiryFilter] = useState<"all" | ExpiryStatus>("all");
  const [categoryFilter, setCategoryFilter] = useState<number | "all">("all");

  const { data: store } = useQuery({
    queryKey: ["store", storeId],
    queryFn: async () => (await api.get<Store>(`/stores/${storeId}`)).data,
  });

  const { data: lots, isLoading } = useQuery({
    queryKey: ["inventory", storeId],
    queryFn: async () => (await api.get<InventoryLot[]>(`/stores/${storeId}/inventory`)).data,
  });

  // التصنيفات الموجودة فعلياً بمخزون هالمتجر بس — مو كل تصنيفات النظام، عشان القائمة
  // تبقى قصيرة ومفيدة بدل ما تعرض خيارات ما إلها وجود بهالمتجر أصلاً.
  const availableCategories = useMemo(() => {
    const map = new Map<number, { id: number; main: string; sub: string }>();
    for (const lot of lots ?? []) {
      if (lot.category) map.set(lot.category.id, lot.category);
    }
    return Array.from(map.values()).sort((a, b) => a.main.localeCompare(b.main, "ar"));
  }, [lots]);

  const filtered = useMemo(() => {
    if (!lots) return [];
    const q = search.trim().toLowerCase();
    return lots.filter((l) => {
      if (q && !(l.item_name?.toLowerCase().includes(q) || l.barcode.toLowerCase().includes(q))) return false;
      if (expiryFilter !== "all" && expiryStatus(l.expiration_date) !== expiryFilter) return false;
      if (categoryFilter !== "all" && l.category?.id !== categoryFilter) return false;
      return true;
    });
  }, [lots, search, expiryFilter, categoryFilter]);

  return (
    <Layout>
      <div className="mb-1 text-sm">
        <Link to="/stores" className="text-slate-400 hover:text-slate-600">
          المتاجر
        </Link>
        <span className="mx-1.5 text-slate-300">/</span>
        <span className="font-medium text-slate-600">{store?.name ?? "..."}</span>
      </div>

      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold text-ink">مخزون {store?.name}</h1>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="بحث بالاسم أو الباركود..."
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100 sm:w-64"
        />
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <select
          value={expiryFilter}
          onChange={(e) => setExpiryFilter(e.target.value as "all" | ExpiryStatus)}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
        >
          {(["all", "expired", "soon", "ok"] as const).map((v) => (
            <option key={v} value={v}>
              {EXPIRY_FILTER_LABEL[v]}
            </option>
          ))}
        </select>

        {availableCategories.length > 0 && (
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value === "all" ? "all" : Number(e.target.value))}
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
          >
            <option value="all">كل التصنيفات</option>
            {availableCategories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.main} / {c.sub}
              </option>
            ))}
          </select>
        )}

        {(expiryFilter !== "all" || categoryFilter !== "all") && (
          <button
            onClick={() => {
              setExpiryFilter("all");
              setCategoryFilter("all");
            }}
            className="text-xs font-medium text-slate-400 transition hover:text-slate-600"
          >
            ✕ مسح الفلاتر
          </button>
        )}
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">...جار التحميل</p>
      ) : !lots?.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          المخزون فاضي بعد — يتكوّن تلقائياً من دمج الفواتير.
        </div>
      ) : !filtered.length ? (
        <div className="rounded-xl border border-dashed border-slate-300 py-16 text-center text-sm text-slate-500">
          ما فيه أصناف تطابق البحث/الفلاتر.
        </div>
      ) : (
        <>
          {/* بطاقات للموبايل — جدول بخمسة أعمدة ما يتسع بعرض هاتف */}
          <div className="flex flex-col gap-3 sm:hidden">
            {filtered.map((lot) => (
              <div key={lot.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="mb-1 font-medium text-ink">{lot.item_name ?? "—"}</div>
                <div className="mb-2 font-mono text-xs text-slate-400">{lot.barcode}</div>
                {lot.category && (
                  <div className="mb-3 text-xs text-slate-400">
                    {lot.category.main} / {lot.category.sub}
                  </div>
                )}
                <div className="flex items-center justify-between text-xs">
                  <ExpiryBadge date={lot.expiration_date} />
                  <span className="font-mono text-slate-500">
                    {lot.quantity ?? "—"} × {lot.unit_cost ?? "—"}
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
                  <th className="px-4 py-3">الصنف</th>
                  <th className="px-4 py-3">التصنيف</th>
                  <th className="px-4 py-3">الباركود</th>
                  <th className="px-4 py-3">الصلاحية</th>
                  <th className="px-4 py-3">الكمية</th>
                  <th className="px-4 py-3">تكلفة الوحدة</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((lot) => (
                  <tr key={lot.id} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-3 font-medium text-ink">{lot.item_name ?? "—"}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-slate-500">
                      {lot.category ? `${lot.category.main} / ${lot.category.sub}` : "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-500">{lot.barcode}</td>
                    <td className="whitespace-nowrap px-4 py-3">
                      <ExpiryBadge date={lot.expiration_date} />
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                      {lot.quantity ?? "—"}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
                      {lot.unit_cost ?? "—"}
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
