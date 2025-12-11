
import streamlit as st
import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import networkx as nx
from collections import deque
import matplotlib.pyplot as plt

# -----------------------------
# Data models
# -----------------------------

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

# -----------------------------
# Load products from JSON
# -----------------------------

@st.cache_data
def load_products() -> List[Product]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "products.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Product(**item) for item in data]

products_data = load_products()
id_to_product: Dict[str, Product] = {p.product_id: p for p in products_data}
name_to_product_id: Dict[str, str] = {p.name: p.product_id for p in products_data}

def get_product_by_name(name: str) -> Optional[Product]:
    pid = name_to_product_id.get(name)
    if pid is None:
        return None
    return id_to_product[pid]

# -----------------------------
# Knowledge Graph construction
# -----------------------------

CATEGORIES = ["Dairy", "Bakery", "Snacks", "Beverages", "Health"]

similar_categories: Dict[str, List[str]] = {
    "Dairy": ["Health", "Snacks"],
    "Bakery": ["Snacks", "Health"],
    "Snacks": ["Bakery", "Health"],
    "Beverages": ["Health"],
    "Health": ["Dairy", "Snacks", "Bakery", "Beverages"],
}

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

    # SIMILAR_TO pairs
    similar_pairs = [
        ("P001", "P003"), ("P002", "P026"), ("P009", "P011"),
        ("P012", "P028"), ("P015", "P016"), ("P018", "P019"),
        ("P021", "P022"), ("P023", "P024"), ("P027", "P028"),
        ("P029", "P026"),
    ]
    for a, b in similar_pairs:
        if a in id_to_product and b in id_to_product:
            KG.add_edge(f"product:{a}", f"product:{b}", edge_type="SIMILAR_TO")

    return KG

KG = build_kg(products_data)

# -----------------------------
# KG helpers
# -----------------------------

def product_to_node_id(product_id: str) -> str:
    return f"product:{product_id}"

def node_id_to_product(node_id: str) -> Optional[Product]:
    if not node_id.startswith("product:"):
        return None
    pid = node_id.split("product:")[-1]
    return id_to_product.get(pid)

def category_closeness(source_cat: str, target_cat: str) -> float:
    if source_cat == target_cat:
        return 1.0
    if target_cat in similar_categories.get(source_cat, []):
        return 0.7
    return 0.0

# -----------------------------
# BFS + scoring
# -----------------------------

RULE_EXPLANATIONS = {
    "exact_match_available": "The exact item is in stock and matches your filters.",
    "preferred_brand_respected": "Matches your preferred brand.",
    "same_brand_as_requested": "Same brand as the requested product.",
    "different_brand_than_requested": "Different brand than the requested product.",
    "all_required_tags_matched": "Matches all required tags.",
    "cheaper_option": "Cheaper than the requested product.",
    "same_price_as_requested": "Same price as the requested product.",
    "slightly_more_expensive": "Slightly more expensive.",
    "same_category": "Same category.",
    "similar_category": "Related category.",
    "closer_in_graph": "Close to the requested item in the knowledge graph.",
}

def build_explanation(rule_tags: List[str], required_tags: List[str]) -> str:
    parts = [RULE_EXPLANATIONS[t] for t in rule_tags if t in RULE_EXPLANATIONS]
    if required_tags and "all_required_tags_matched" in rule_tags:
        parts.append("Required tags: " + ", ".join(required_tags) + ".")
    return " ".join(parts).strip()

def check_exact_product_availability(
    product: Product,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str] = None,
) -> Tuple[Optional[Product], List[str]]:
    if preferred_brand is not None and product.brand != preferred_brand:
        return None, []
    if max_price is not None and product.price > max_price:
        return None, []
    if not product.in_stock:
        return None, []
    if not set(required_tags).issubset(set(product.tags)):
        return None, []
    tags = ["exact_match_available"]
    if preferred_brand is not None:
        tags.append("preferred_brand_respected")
    if required_tags:
        tags.append("all_required_tags_matched")
    return product, tags

def bfs_candidates_with_depth(requested: Product, max_depth: int = 2) -> Tuple[Dict[str, Tuple[Product,int]], int]:
    start = product_to_node_id(requested.product_id)
    visited = {start}
    queue = deque([(start, 0)])
    traversed = 0
    candidates: Dict[str, Tuple[Product,int]] = {}

    while queue:
        node, depth = queue.popleft()
        traversed += 1
        if depth >= max_depth:
            continue
        for nb in KG.neighbors(node):
            if nb in visited:
                continue
            visited.add(nb)
            queue.append((nb, depth + 1))
            if nb.startswith("product:") and nb != start:
                p = node_id_to_product(nb)
                if p:
                    prev = candidates.get(p.product_id)
                    if prev is None or depth + 1 < prev[1]:
                        candidates[p.product_id] = (p, depth + 1)

    return candidates, traversed

def score_candidate(
    requested: Product,
    candidate: Product,
    depth: int,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str],
) -> Tuple[Optional[float], List[str]]:
    rule_tags: List[str] = []

    if not candidate.in_stock:
        return None, []
    if max_price is not None and candidate.price > max_price:
        return None, []
    if not set(required_tags).issubset(set(candidate.tags)):
        return None, []

    score = 0.0

    cat_score = category_closeness(requested.category, candidate.category)
    score += cat_score * 4.0
    if cat_score == 1.0:
        rule_tags.append("same_category")
    elif cat_score > 0:
        rule_tags.append("similar_category")

    if preferred_brand is not None:
        if candidate.brand == preferred_brand:
            score += 3.0
            rule_tags.append("preferred_brand_respected")
        else:
            score -= 0.5
            rule_tags.append("different_brand_than_requested")
    else:
        if candidate.brand == requested.brand:
            score += 2.0
            rule_tags.append("same_brand_as_requested")
        else:
            rule_tags.append("different_brand_than_requested")

    if candidate.price < requested.price:
        score += 1.0
        rule_tags.append("cheaper_option")
    elif candidate.price == requested.price:
        score += 0.5
        rule_tags.append("same_price_as_requested")
    else:
        score -= 0.2
        rule_tags.append("slightly_more_expensive")

    score += max(0, (3 - depth)) * 0.5
    rule_tags.append("closer_in_graph")

    if required_tags:
        rule_tags.append("all_required_tags_matched")

    return score, rule_tags

def find_alternatives(
    requested_product_name: str,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str],
    max_alternatives: int = 3,
) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "requested": None,
        "exact_match": None,
        "alternatives": [],
        "message": "",
        "traversed_nodes": 0,
    }

    requested = get_product_by_name(requested_product_name)
    if requested is None:
        res["message"] = "Product not found."
        return res

    res["requested"] = requested

    exact, exact_tags = check_exact_product_availability(
        requested, max_price, required_tags, preferred_brand
    )
    if exact is not None:
        res["exact_match"] = {
            "product": exact,
            "rule_tags": exact_tags,
            "explanation": build_explanation(exact_tags, required_tags),
        }

    candidates_with_depth, traversed = bfs_candidates_with_depth(requested, max_depth=2)
    res["traversed_nodes"] = traversed

    scored: List[Recommendation] = []
    for pid, (cand, depth) in candidates_with_depth.items():
        s, tags = score_candidate(
            requested, cand, depth, max_price, required_tags, preferred_brand
        )
        if s is None:
            continue
        expl = build_explanation(tags, required_tags)
        scored.append(Recommendation(product=cand, score=s, rule_tags=tags, explanation=expl))

    scored.sort(key=lambda r: r.score, reverse=True)
    top = scored[:max_alternatives]

    if not top:
        if exact is not None:
            res["message"] = "Exact product is available, but no better alternatives were found."
        else:
            res["message"] = "No alternatives found matching constraints."
    else:
        if exact is not None:
            res["message"] = "Exact product is available. Showing additional alternatives."
        else:
            res["message"] = "Alternatives found."
        res["alternatives"] = top

    return res

# -----------------------------
# Visualization: shortest paths
# -----------------------------

def visualize_search_path(root_product: Product, recs: List[Recommendation]) -> Optional[plt.Figure]:
    if not recs:
        return None

    root_id = product_to_node_id(root_product.product_id)
    target_ids = [product_to_node_id(r.product.product_id) for r in recs]

    nodes = {root_id}
    edges = set()

    for tid in target_ids:
        try:
            path = nx.shortest_path(KG, source=root_id, target=tid)
        except nx.NetworkXNoPath:
            continue
        for i in range(len(path) - 1):
            a, b = path[i], path[i+1]
            nodes.add(a); nodes.add(b)
            edges.add((a, b))

    if not edges:
        return None

    sub = KG.edge_subgraph(list(edges)).copy()

    plt.figure(figsize=(10, 6))
    shells = [
        [root_id],
        [n for n in nodes if n not in [root_id] + target_ids],
        target_ids,
    ]
    pos = nx.shell_layout(sub, nlist=shells)

    # Node colors: white nodes so dark text is readable
    colors = []
    for n in sub.nodes():
        if n == root_id:
            colors.append("#ffe680")   # light yellow for requested
        elif n in target_ids:
            colors.append("#b3ffb3")   # light green for recommended
        else:
            t = sub.nodes[n].get("node_type")
            if t == "category":
                colors.append("#cfe2ff")
            elif t == "brand":
                colors.append("#ffd6a5")
            elif t == "attribute":
                colors.append("#ffccd5")
            else:
                colors.append("#f0f0f0")

    nx.draw_networkx_nodes(sub, pos, node_size=650, node_color=colors, edgecolors="#000000")
    nx.draw_networkx_edges(sub, pos, alpha=0.7, width=1.5, edge_color="#bbbbbb")

    # Black font on light nodes
    labels = {n: sub.nodes[n].get("name", n) for n in sub.nodes()}
    nx.draw_networkx_labels(sub, pos, labels=labels, font_size=8, font_color="#000000")

    # Dark background for contrast
    ax = plt.gca()
    ax.set_facecolor("#050b16")           # dark navy background inside plot
    plt.title(f"Paths from '{root_product.name}' to recommended items", fontsize=10, color="#ffffff")
    plt.axis("off")
    return plt

# -----------------------------
# UI layout (dark blue theme)
# -----------------------------

st.set_page_config(layout="wide", page_title="General Store - Product Finder")

st.markdown("""
    <style>
    body, .main, .stApp {
        background-color: #050b16;
        color: #e0e6f0;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
    }
    .product-card {
        border: 1px solid #1f2a3a;
        border-radius: 10px;
        padding: 14px;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #0b1626, #152338);
        box-shadow: 0 2px 6px rgba(0,0,0,0.6);
    }
    .product-title {
        font-weight: 700;
        font-size: 16px;
        margin-bottom: 4px;
        color: #ffffff;
    }
    .product-price {
        font-size: 15px;
        font-weight: 600;
        color: #4fe3c1;
    }
    .product-meta {
        font-size: 13px;
        color: #d0d6e0;
    }
    .stMarkdown, .stText, .stSelectbox label, .stSlider label {
        color: #e0e6f0 !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #0b1626;
        color: #e0e6f0;
    }
    .stSlider > div > div > div {
        background-color: #1b3b6f;
    }
    .stButton button {
        background: linear-gradient(90deg, #1b3b6f, #274a8a);
        color: #ffffff;
        border-radius: 8px;
        border: 1px solid #3b6ac9;
    }
    .stButton button:hover {
        background: linear-gradient(90deg, #274a8a, #3560b3);
        border-color: #4f82ff;
    }
    .stExpander {
        border: 1px solid #1f2a3a;
        border-radius: 8px;
        background-color: #081321;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 Smart Catalog & Substitution Assistant")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    max_price_input = st.slider("Max Price (₹)", 0, 250, 0, 5)
    max_price_val = max_price_input if max_price_input > 0 else None

    all_tags = sorted({tag for p in products_data for tag in p.tags})
    required_tags = st.multiselect("Required Tags (optional)", options=all_tags, default=[])

    brands = sorted({p.brand for p in products_data})
    preferred_brand = st.selectbox("Preferred Brand (optional)", ["(no preference)"] + brands)
    preferred_brand_val = None if preferred_brand == "(no preference)" else preferred_brand

# Product selection
cat = st.selectbox("Category", CATEGORIES)
cat_products = sorted([p for p in products_data if p.category == cat], key=lambda x: x.name)
selected_name = st.selectbox("Product", [p.name for p in cat_products])

if st.button("Check stock & alternatives"):
    result = find_alternatives(
        selected_name, max_price_val, required_tags, preferred_brand_val
    )

    st.write("---")
    st.subheader("Result")
    st.info(result["message"])

    requested = result["requested"]

    # Exact
    if result["exact_match"]:
        em = result["exact_match"]["product"]
        st.markdown(f"""
        <div class="product-card">
            <div class="product-title">Exact product: {em.name}</div>
            <div class="product-price">₹{em.price}</div>
            <div class="product-meta">
                Brand: {em.brand} | In stock: {em.in_stock}
            </div>
            <div class="product-meta"><b>Why suggested:</b> {result["exact_match"]["explanation"]}</div>
        </div>
        """, unsafe_allow_html=True)

    # Alternatives
    if result["alternatives"]:
        st.markdown("### Alternatives")
        for rec in result["alternatives"]:
            p = rec.product
            st.markdown(f"""
            <div class="product-card">
                <div class="product-title">{p.name}</div>
                <div class="product-price">₹{p.price}</div>
                <div class="product-meta">
                    Brand: {p.brand} | In stock: {p.in_stock}
                </div>
                <div class="product-meta"><b>Why suggested:</b> {rec.explanation}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("No alternative suggestions.")

    with st.expander("Knowledge Graph reasoning (paths used)"):
        if requested and result["alternatives"]:
            fig = visualize_search_path(requested, result["alternatives"])
            if fig:
                st.pyplot(fig)
        else:
            st.write("No paths to visualize.")
