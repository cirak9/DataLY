# utils/logger.py
# سجل موحّد يكتب لملف logs/dataly.log بالإضافة للطباعة العادية بالطرفية.
# يحل تحدي "غياب سجل أخطاء دائم" — قبل كذا كل شي كان print() يضيع بعد إغلاق الطرفية.

import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def get_logger(name: str = "dataly") -> logging.Logger:
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)

    if logger.handlers:  # تفادي تكرار الـ handlers لو اتنادت الدالة أكثر من مرة
        return logger

    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, "dataly.log"), encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    return logger
