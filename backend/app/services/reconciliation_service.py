from datetime import datetime, timezone

from rapidfuzz import fuzz, process
from sqlalchemy.orm import Session

from app.core_logic.reconciliation import (
    CONFLICT_THRESHOLD,
    FUZZY_MATCH_THRESHOLD,
    size_conflict_reason,
)
from app.models.catalog import ProductCatalog
from app.models.inventory import InventoryLot
from app.models.invoice import Invoice, InvoiceItem
from app.models.reconciliation import ReconciliationMatch
from app.models.session import IntakeSession


class ReconciliationError(Exception):
    """يُرفع لما محاولة تسوية/قرار تخالف حالة الجلسة أو التسوية."""
    pass


def _build_reference_index(db: Session, store_id: int) -> dict[str, dict]:
    """
    بديل combined_master بـfusion/reconciliation.py: product_catalog (فهرس مشترك بين
    كل المتاجر، بديل master_items.xlsx) له الأولوية، ثم مخزون هذا المتجر السابق
    (inventory_lots، بديل old_inventory.xlsx عبر load_old_inventory_as_master) — بس
    لصنف مو موجود أصلاً بـproduct_catalog، نفس ترتيب drop_duplicates(keep="first") الأصلي.
    """
    index: dict[str, dict] = {}

    lots = db.query(InventoryLot).filter(InventoryLot.store_id == store_id).all()
    for lot in lots:
        if lot.barcode not in index:
            index[lot.barcode] = {"name": lot.item_name or "", "category_id": None}

    for row in db.query(ProductCatalog).all():
        index[row.barcode] = {"name": row.canonical_name, "category_id": row.category_id}

    return index


def generate_matches(db: Session, invoice: Invoice) -> list[ReconciliationMatch]:
    """
    بديل reconcile_dataframes(): يقارن اسم كل صنف بالفاتورة مقابل مصدرين (نفس القاعدة
    الأصلية بالأولوية)، بالاعتماد على الباركود اللي عبّاه التاجر بجلسة الاستلام. كل
    تطابق يُحفظ كـReconciliationMatch بحالة pending — **ولا تطابق يُطبَّق تلقائياً
    إطلاقاً، مهما كانت نسبة التشابه**، بانتظار قرار بشري عبر decide_match(). لو ما
    فيه ولا تطابق (لا باركود معروف ولا تشابه اسم كافٍ)، الفاتورة تنتقل مباشرة لـ
    status=reconciled — ما فيه شي ينتظر قرار أصلاً.
    """
    session = db.query(IntakeSession).filter(IntakeSession.invoice_id == invoice.id).first()
    if not session or session.status != "complete":
        raise ReconciliationError("لازم تكمل جلسة الاستلام أولاً قبل التسوية.")

    already = (
        db.query(ReconciliationMatch)
        .join(InvoiceItem, ReconciliationMatch.invoice_item_id == InvoiceItem.id)
        .filter(InvoiceItem.invoice_id == invoice.id)
        .first()
    )
    if already:
        raise ReconciliationError("التسوية تمت أصلاً لهذي الفاتورة.")

    reference = _build_reference_index(db, invoice.store_id)
    known_names = [v["name"] for v in reference.values() if v["name"]]
    barcode_by_item = {si.invoice_item_id: si.barcode for si in session.items}

    matches: list[ReconciliationMatch] = []
    for item in invoice.items:
        current_name = item.item_name
        barcode = barcode_by_item.get(item.id)

        if barcode and barcode in reference:
            ref = reference[barcode]
            similarity = fuzz.WRatio(current_name, ref["name"]) if ref["name"] else 0.0
            reason = size_conflict_reason(current_name, ref["name"]) if ref["name"] else ""
            if not reason and ref["name"] and similarity < CONFLICT_THRESHOLD:
                reason = "الاسم مختلف كثيرًا نصيًا عن الاسم المعتمد"
            match = ReconciliationMatch(
                invoice_item_id=item.id,
                match_method="barcode",
                matched_barcode=barcode,
                suggested_name=ref["name"] or None,
                suggested_category_id=ref["category_id"],
                similarity_score=round(similarity, 1),
                warning_reason=reason or None,
            )
            db.add(match)
            matches.append(match)

        elif not barcode and known_names:
            # لا باركود بالمرة → fallback: مطابقة تقريبية للاسم فقط (نادر عملياً — الجلسة
            # تشترط باركود قبل الاكتمال أصلاً، هذا مسار احتياطي بحت)
            best = process.extractOne(current_name, known_names, scorer=fuzz.WRatio)
            if best and best[1] >= FUZZY_MATCH_THRESHOLD:
                matched_name = best[0]
                matched_ref = next(v for v in reference.values() if v["name"] == matched_name)
                match = ReconciliationMatch(
                    invoice_item_id=item.id,
                    match_method="fuzzy_name",
                    matched_barcode=None,
                    suggested_name=matched_name,
                    suggested_category_id=matched_ref["category_id"],
                    similarity_score=round(best[1], 1),
                    warning_reason=size_conflict_reason(current_name, matched_name) or None,
                )
                db.add(match)
                matches.append(match)
        # باركود موجود بس مو بقاعدة المقارنة → يُترك كما هو، بدون أي تسجيل أو اقتراح

    if not matches:
        invoice.status = "reconciled"

    db.commit()
    for m in matches:
        db.refresh(m)
    return matches


def decide_match(
    db: Session, match: ReconciliationMatch, decision: str, manual_name: str | None, decided_by_id: int | None
) -> ReconciliationMatch:
    """
    يطبّق قرار بشري واحد — approve (يعتمد الاسم/التصنيف المقترح)، reject (يبقي اسم
    الفاتورة كما هو)، أو manual (اسم يكتبه المستخدم بنفسه، يُطبَّق على هذي الفاتورة
    بس). لما آخر تطابق pending بالفاتورة يتقرر، الفاتورة تنتقل تلقائياً لـstatus=reconciled
    — بديل الحلقة التفاعلية resolve_matches_interactively() اللي كانت تعالج كل
    التطابقات بجلسة طرفية واحدة متزامنة؛ هون كل قرار طلب HTTP منفصل، فالإنهاء التلقائي
    يصير لما آخر واحد يتقرر بدل نهاية حلقة for.
    """
    if match.decision != "pending":
        raise ReconciliationError("هذا التطابق تقرر مصيره أصلاً.")

    item = db.get(InvoiceItem, match.invoice_item_id)

    if decision == "approve":
        item.item_name = match.suggested_name
        if match.suggested_category_id:
            item.category_id = match.suggested_category_id
        match.decision = "approved"
    elif decision == "reject":
        match.decision = "rejected"
    elif decision == "manual":
        name = (manual_name or "").strip()
        if not name:
            raise ReconciliationError("لازم تكتب الاسم اليدوي.")
        item.item_name = name
        match.manual_name = name
        match.decision = "manual"
    else:
        raise ReconciliationError(f"قرار غير معروف: {decision} — لازم يكون approve أو reject أو manual.")

    match.decided_by = decided_by_id
    match.decided_at = datetime.now(timezone.utc)
    db.flush()

    remaining_pending = (
        db.query(ReconciliationMatch)
        .join(InvoiceItem, ReconciliationMatch.invoice_item_id == InvoiceItem.id)
        .filter(InvoiceItem.invoice_id == item.invoice_id, ReconciliationMatch.decision == "pending")
        .count()
    )
    if remaining_pending == 0:
        invoice = db.get(Invoice, item.invoice_id)
        invoice.status = "reconciled"

    db.commit()
    db.refresh(match)
    return match
