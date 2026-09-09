# نفس utils/logger.py بالأداة الأصلية — طباعة موحّدة بالطرفية بس، بدون ملف على القرص.
import logging


def get_logger(name: str = "dataly") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)
    return logger
