from typing import List, Dict, Any, Optional
import networkx as nx

from src.models.product import Product
from src.data_access.loader import load_products
from src.core.kg_builder import build_kg
from src.core.reasoning import find_alternatives
from src.core.visualize import visualize_search_path

class AppService:
    """High-level service used by Streamlit app."""

    def __init__(self) -> None:
        self.products: List[Product] = load_products()
        self.KG: nx.Graph = build_kg(self.products)

    def list_categories(self) -> List[str]:
        return sorted({p.category for p in self.products})

    def list_products_in_category(self, category: str) -> List[str]:
        return sorted([p.name for p in self.products if p.category == category])

    def get_results(
        self,
        product_name: str,
        max_price: Optional[float],
        required_tags: List[str],
        preferred_brand: Optional[str],
    ) -> Dict[str, Any]:
        return find_alternatives(
            self.KG,
            self.products,
            product_name,
            max_price,
            required_tags,
            preferred_brand,
        )

    def build_visualization(self, root_product, recs):
        return visualize_search_path(self.KG, root_product, recs)
