import logging
import os

LOG_LEVEL = os.environ.get("SHOPKEEPER_LOG_LEVEL", "INFO").upper()

logger = logging.getLogger("shopkeeper")
if not logger.handlers:
    logger.setLevel(LOG_LEVEL)
    ch = logging.StreamHandler()
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")
    ch.setFormatter(fmt)
    logger.addHandler(ch)
