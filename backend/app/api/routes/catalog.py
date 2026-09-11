from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.catalog import Category, CategoryKeyword
from app.schemas.catalog import CategoryCreate, CategoryOut, KeywordCreate

# لا عزل ملكية هنا عمداً — التصنيفات وكلماتها المفتاحية فهرس مشترك بين كل الحسابات،
# نفس فلسفة /suppliers وproduct_catalog (راجع backend/README.md). أي مستخدم مسجّل
# دخول يقدر يدير التصنيفات، مو بس صاحب متجر معيّن.
router = APIRouter(tags=["catalog"], dependencies=[Depends(get_current_user)])


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return db.query(Category).order_by(Category.main, Category.sub).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    main, sub = payload.main.strip(), payload.sub.strip()
    if not main or not sub:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="الاسم الرئيسي والفرعي مطلوبان")
    if db.query(Category).filter(Category.main == main, Category.sub == sub).first():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="هذا التصنيف موجود أصلاً")

    category = Category(main=main, sub=sub)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="التصنيف غير موجود")
    try:
        db.delete(category)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ما يمكن حذف تصنيف مستخدَم بأصناف حالية"
        )


@router.post(
    "/categories/{category_id}/keywords", response_model=CategoryOut, status_code=status.HTTP_201_CREATED
)
def add_keyword(category_id: int, payload: KeywordCreate, db: Session = Depends(get_db)):
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="التصنيف غير موجود")

    keyword = payload.keyword.strip()
    if not keyword:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="الكلمة المفتاحية مطلوبة")

    db.add(CategoryKeyword(category_id=category.id, keyword=keyword, is_whole_word=payload.is_whole_word))
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}/keywords/{keyword_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_keyword(category_id: int, keyword_id: int, db: Session = Depends(get_db)):
    keyword = (
        db.query(CategoryKeyword)
        .filter(CategoryKeyword.id == keyword_id, CategoryKeyword.category_id == category_id)
        .first()
    )
    if not keyword:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="الكلمة المفتاحية غير موجودة")
    db.delete(keyword)
    db.commit()
