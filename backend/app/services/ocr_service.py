import base64
import os

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core_logic.ocr_extractor import PROMPT, OcrParseError, parse_extraction_response
from app.core_logic.validators import InvoiceValidationError
from app.models.invoice import Invoice, InvoiceItem
from app.schemas.ocr import OcrConfirmItem
from app.services import catalog_service

SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class OcrNotConfiguredError(Exception):
    pass


def _ocr_images_dir(store_id: int, invoice_id: int) -> str:
    d = os.path.join(settings.storage_dir, "ocr_images", str(store_id), str(invoice_id))
    os.makedirs(d, exist_ok=True)
    return d


def create_ocr_invoice(db: Session, store_id: int, files: list[tuple[str, bytes]]) -> Invoice:
    """
    ينشئ فاتورة method=3 (صور OCR) ويحفظ الصور الخام على القرص — نفس فلسفة الفواتير
    العادية (الملف الخام يبقى، الاستخراج خطوة منفصلة قابلة لإعادة المحاولة). دعم عدة
    صور بنفس الفاتورة عمداً — التاجر يصوّر فاتورة طويلة بأكثر من صورة.
    """
    if not files:
        raise InvoiceValidationError("ارفع صورة واحدة على الأقل")

    for filename, _ in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_IMAGE_EXT:
            raise InvoiceValidationError(
                f"نوع الملف غير مدعوم ({ext}) — الصيغ المدعومة: jpg, jpeg, png, webp, gif"
            )

    invoice = Invoice(
        store_id=store_id,
        method=3,
        status="uploaded",
        original_filename=f"{len(files)} صور" if len(files) > 1 else files[0][0],
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    images_dir = _ocr_images_dir(store_id, invoice.id)
    for i, (filename, content) in enumerate(files, start=1):
        ext = os.path.splitext(filename)[1].lower()
        with open(os.path.join(images_dir, f"{i:02d}{ext}"), "wb") as f:
            f.write(content)

    return invoice


def _stored_image_paths(invoice: Invoice) -> list[str]:
    d = _ocr_images_dir(invoice.store_id, invoice.id)
    return [os.path.join(d, name) for name in sorted(os.listdir(d))]


def extract_items(db: Session, invoice: Invoice) -> list[dict]:
    """
    يرسل الصور المحفوظة لـClaude Vision ويرجّع الأصناف المستخرَجة بدون حفظها —
    المراجعة/التعديل/الاعتماد يصير بالواجهة، والحفظ الفعلي بـconfirm_items() بس.
    """
    if invoice.method != 3:
        raise InvoiceValidationError("هالفاتورة مو من نوع صور OCR")
    if invoice.status != "uploaded":
        raise InvoiceValidationError("الاستخراج يصير مرة وحدة، والفاتورة تجاوزت هالمرحلة")
    if not settings.anthropic_api_key:
        raise OcrNotConfiguredError("خدمة OCR غير مُفعَّلة — مفتاح Anthropic API غير مُعدّ بعد")

    paths = _stored_image_paths(invoice)
    if not paths:
        raise InvoiceValidationError("ما فيه صور محفوظة لهالفاتورة")

    from anthropic import Anthropic  # استيراد مؤجَّل — يتجنّب كلفة الاستيراد لو الخدمة مو مفعّلة أصلاً

    client = Anthropic(api_key=settings.anthropic_api_key)

    image_blocks = []
    for path in paths:
        media_type = MEDIA_TYPES.get(os.path.splitext(path)[1].lower(), "image/jpeg")
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        image_blocks.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}})

    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=4096,
        messages=[{"role": "user", "content": [*image_blocks, {"type": "text", "text": PROMPT}]}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")

    try:
        return parse_extraction_response(text)
    except OcrParseError as e:
        raise InvoiceValidationError(str(e)) from e


def confirm_items(db: Session, invoice: Invoice, items: list[OcrConfirmItem]) -> Invoice:
    """
    نقطة "الاعتماد" الفعلية — تحوّل الأصناف المراجَعة/المعدَّلة يدوياً إلى invoice_items
    حقيقية وتنقل الفاتورة لحالة "cleaned"، بنفس نقطة الدخول اللي تكمل منها الفواتير
    العادية (جلسة استلام ← تسوية ← دمج ← تصدير) — لا فرق بعد هالخطوة.
    """
    if invoice.method != 3:
        raise InvoiceValidationError("هالفاتورة مو من نوع صور OCR")
    if invoice.status != "uploaded":
        raise InvoiceValidationError("الفاتورة اتّعمدت مسبقاً أو تجاوزت هالمرحلة")
    if not items:
        raise InvoiceValidationError("ما فيه أصناف لاعتمادها")

    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()

    for order, item in enumerate(items, start=1):
        category_id = catalog_service.get_category_id(db, item.item_name, barcode=item.barcode)
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                item_order=order,
                item_name=item.item_name,
                category_id=category_id,
                quantity_pieces=item.quantity,
                unit_cost=item.unit_cost,
                total_price=round(item.quantity * item.unit_cost, 3),
                barcode=item.barcode,
            )
        )

    invoice.status = "cleaned"
    db.commit()
    db.refresh(invoice)
    return invoice
