from dataclasses import dataclass, field
from typing import List

@dataclass
class Product:
    product_id: str
    name: str
    category: str
    brand: str
    price: float
    in_stock: bool
    tags: List[str] = field(default_factory=list)

@dataclass
class Recommendation:
    product: Product
    score: float
    rule_tags: List[str]
    explanation: str
