# -*- coding: utf-8 -*-
"""إنشاء المستخدم الإداري الوحيد — يُشغَّل مرة وحدة يدوياً بعد أول migration.
الاستخدام: python scripts/create_admin.py <email> <password>
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.user import User


def main():
    if len(sys.argv) != 3:
        print("الاستخدام: python scripts/create_admin.py <email> <password>")
        sys.exit(1)

    email, password = sys.argv[1], sys.argv[2]
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            print(f"المستخدم {email} موجود مسبقاً")
            return
        user = User(email=email, hashed_password=hash_password(password))
        db.add(user)
        db.commit()
        print(f"تم إنشاء المستخدم: {email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
