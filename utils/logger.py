# utils/logger.py
# طباعة موحّدة بالطرفية فقط — بدون أي ملف يُحفظ على القرص، بطلب صاحب المشروع (كل
# تشغيلة مستقلة، ولا يريد ملفات تراكم تقدّم بين تشغيلة وأخرى بمرحلة الاختبار اليدوي هذي).

import logging


def get_logger(name: str = "dataly") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:  # تفادي تكرار الـ handlers لو اتنادت الدالة أكثر من مرة
        return logger

    logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    return logger
