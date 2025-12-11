import json
from typing import List, Dict, Any
from src.config.paths import PRODUCTS_PATH, CATEGORIES_PATH, ATTRIBUTES_PATH
from src.models.product import Product
from src.utils.exceptions import DataLoadError
from src.utils.logger import logger

def _load_json(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"File not found: {path}")
        raise DataLoadError(f"File not found: {path}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}")
        raise DataLoadError(f"Invalid JSON in {path}") from e

def load_products() -> List[Product]:
    raw = _load_json(PRODUCTS_PATH)
    products = [Product(**item) for item in raw]
    logger.info(f"Loaded {len(products)} products from {PRODUCTS_PATH}")
    return products

def load_categories() -> Dict[str, Any]:
    data = _load_json(CATEGORIES_PATH)
    return {item["name"]: item for item in data}

def load_attributes() -> List[str]:
    data = _load_json(ATTRIBUTES_PATH)
    return [item["name"] for item in data]
