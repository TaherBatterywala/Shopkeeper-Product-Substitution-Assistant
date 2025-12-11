from typing import List, Dict
import networkx as nx
from src.models.product import Product
from src.utils.logger import logger

CATEGORIES = ["Dairy", "Bakery", "Snacks", "Beverages", "Health"]

SIMILAR_CATEGORIES: Dict[str, List[str]] = {
    "Dairy": ["Health", "Snacks"],
    "Bakery": ["Snacks", "Health"],
    "Snacks": ["Bakery", "Health"],
    "Beverages": ["Health"],
    "Health": ["Dairy", "Snacks", "Bakery", "Beverages"],
}

SIMILAR_PAIRS = [
    ("P001", "P003"), ("P002", "P026"), ("P009", "P011"),
    ("P012", "P028"), ("P015", "P016"), ("P018", "P019"),
    ("P021", "P022"), ("P023", "P024"), ("P027", "P028"),
    ("P029", "P026"),
]

def build_kg(products: List[Product]) -> nx.Graph:
    KG = nx.Graph()

    # Categories
    for cat in CATEGORIES:
        KG.add_node(f"category:{cat}", node_type="category", name=cat)

    # Brands and attributes
    brands = sorted({p.brand for p in products})
    attributes = sorted({tag for p in products for tag in p.tags})

    for brand in brands:
        KG.add_node(f"brand:{brand}", node_type="brand", name=brand)

    for attr in attributes:
        KG.add_node(f"attr:{attr}", node_type="attribute", name=attr)

    # Products
    for p in products:
        pid = f"product:{p.product_id}"
        KG.add_node(
            pid,
            node_type="product",
            name=p.name,
            product_id=p.product_id,
            category=p.category,
            brand=p.brand,
            price=p.price,
            in_stock=p.in_stock,
            tags=p.tags,
        )
        KG.add_edge(pid, f"category:{p.category}", edge_type="IS_A")
        KG.add_edge(pid, f"brand:{p.brand}", edge_type="HAS_BRAND")
        for tag in p.tags:
            KG.add_edge(pid, f"attr:{tag}", edge_type="HAS_ATTRIBUTE")

    # SIMILAR_TO edges
    product_ids = {p.product_id for p in products}
    for a, b in SIMILAR_PAIRS:
        if a in product_ids and b in product_ids:
            KG.add_edge(f"product:{a}", f"product:{b}", edge_type="SIMILAR_TO")

    logger.info(f"KG built: {KG.number_of_nodes()} nodes, {KG.number_of_edges()} edges")
    return KG
