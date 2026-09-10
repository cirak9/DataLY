from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_invoice
from app.core.db import get_db
from app.models.export import AlsahlExport
from app.models.invoice import Invoice
from app.schemas.export import AlsahlExportOut
from app.services import export_service
from app.services.export_service import ExportError

router = APIRouter(tags=["export"], dependencies=[Depends(get_current_user)])


@router.post("/invoices/{invoice_id}/export", response_model=AlsahlExportOut, status_code=status.HTTP_201_CREATED)
def export_invoice(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    try:
        return export_service.export_invoice(db, invoice)
    except ExportError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/invoices/{invoice_id}/export/download")
def download_latest_export(invoice: Invoice = Depends(get_owned_invoice), db: Session = Depends(get_db)):
    export = (
        db.query(AlsahlExport)
        .filter(AlsahlExport.invoice_id == invoice.id)
        .order_by(AlsahlExport.exported_at.desc())
        .first()
    )
    if not export:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ما فيه ملف تصدير لهذي الفاتورة بعد")

    # يُعاد بناء الملف من قاعدة البيانات مباشرة بدل قراءته من القرص — قرص Render
    # المجاني مؤقت وينمسح بإعادة النشر/التشغيل، فملف export.file_path قد لا يكون
    # موجوداً فعلياً حتى لو سجل التصدير موجود بقاعدة البيانات.
    file_bytes = export_service.build_export_bytes(db, invoice)

    return Response(
        content=file_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="output_alsahl.xlsx"'},
    )
