
import streamlit as st
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import os

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

# -----------------------------
# Load product data
# -----------------------------

@st.cache_data
def load_products() -> List[Product]:
    # Get the directory where app.py is located
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the full path to the json file
    json_path = os.path.join(current_dir, "products.json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Product(**item) for item in data]

products_data = load_products()
id_to_product = {p.product_id: p for p in products_data}
name_to_product_id = {p.name: p.product_id for p in products_data}

def get_product_by_name(name: str) -> Optional[Product]:
    pid = name_to_product_id.get(name)
    if pid is None:
        return None
    return id_to_product[pid]

# -----------------------------
# Rule-based reasoning (simplified version)
# -----------------------------

def exact_match_check(
    requested: Product,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str],
):
    if not requested.in_stock:
        return None, []

    if max_price is not None and requested.price > max_price:
        return None, []

    if not set(required_tags).issubset(set(requested.tags)):
        return None, []

    if preferred_brand is not None and requested.brand != preferred_brand:
        return None, []

    rule_tags = ["exact_match_available"]
    if preferred_brand is not None:
        rule_tags.append("preferred_brand_respected")
    if required_tags:
        rule_tags.append("all_required_tags_matched")

    return requested, rule_tags

RULE_EXPLANATIONS = {
    "exact_match_available": "The exact item you searched for is in stock and fits your filters.",
    "preferred_brand_respected": "Matches your preferred brand.",
    "same_brand_as_requested": "Same brand as the product you searched.",
    "different_brand_than_requested": "Different brand than the product you searched.",
    "all_required_tags_matched": "Matches all filter tags you selected.",
    "cheaper_option": "Cheaper than the product you searched.",
    "same_price_as_requested": "Same price as the product you searched.",
    "slightly_more_expensive": "Slightly more expensive than the product you searched.",
    "same_category": "Same category as the product you searched.",
    "similar_category": "Related category.",
}

def build_explanation(rule_tags: List[str], required_tags: List[str]) -> str:
    parts = []
    for tag in rule_tags:
        if tag in RULE_EXPLANATIONS:
            parts.append(RULE_EXPLANATIONS[tag])
    if required_tags and "all_required_tags_matched" in rule_tags:
        parts.append("Filter tags satisfied: " + ", ".join(required_tags) + ".")
    return " ".join(parts).strip()

def find_alternatives_catalog(
    requested_product_name: str,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str],
):
    import pandas as pd

    df = pd.DataFrame([p.__dict__ for p in products_data])

    requested = get_product_by_name(requested_product_name)
    if requested is None:
        return None, None, [], "Product not found in catalog."

    # Try exact match first
    exact, exact_rule_tags = exact_match_check(
        requested, max_price, required_tags, preferred_brand
    )
    if exact is not None:
        return requested, (exact, exact_rule_tags), [], "Exact product is available."

    # Candidate pool
    mask = df["in_stock"] == True
    if max_price is not None:
        mask &= df["price"] <= max_price

    if required_tags:
        def has_required(row_tags):
            return set(required_tags).issubset(set(row_tags))
        mask &= df["tags"].apply(has_required)

    # Exclude requested itself
    mask &= df["product_id"] != requested.product_id

    candidates = df[mask].copy()

    # Scoring
    scores = []
    for _, row in candidates.iterrows():
        score = 0.0
        rule_tags = []

        # Category importance
        if row["category"] == requested.category:
            score += 4.0
            rule_tags.append("same_category")
        else:
            score += 1.0
            rule_tags.append("similar_category")

        # Brand preference
        if row["brand"] == requested.brand:
            score += 2.0
            rule_tags.append("same_brand_as_requested")
        else:
            rule_tags.append("different_brand_than_requested")
        if preferred_brand is not None and row["brand"] == preferred_brand:
            score += 3.0
            rule_tags.append("preferred_brand_respected")

        # Tags
        if required_tags:
            rule_tags.append("all_required_tags_matched")

        # Price relation
        if row["price"] < requested.price:
            score += 1.0
            rule_tags.append("cheaper_option")
        elif row["price"] == requested.price:
            score += 0.5
            rule_tags.append("same_price_as_requested")
        else:
            score -= 0.2
            rule_tags.append("slightly_more_expensive")

        scores.append((row["product_id"], score, rule_tags))

    scores_sorted = sorted(scores, key=lambda x: x[1], reverse=True)
    top = scores_sorted[:3]
    alternatives = [(id_to_product[pid], rule_tags) for pid, _, rule_tags in top]

    if not alternatives:
        return requested, None, [], "Product is out of stock or filtered out, and no alternatives were found."

    return requested, None, alternatives, "Product is out of stock or does not meet filters. Showing alternatives."

# -----------------------------
# UI Layout (store-like)
# -----------------------------

st.set_page_config(layout="wide", page_title="General Store - Product Finder")

# Custom minimal styling to look less like a form
st.markdown(
    """
    <style>
    .product-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .product-title {
        font-weight: 600;
        font-size: 16px;
        margin-bottom: 4px;
    }
    .product-meta {
        font-size: 13px;
        color: #555555;
    }
    .product-price {
        font-size: 14px;
        font-weight: 600;
        color: #1a7f37;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🛒 General Store Catalog")

# Sidebar filters (like Amazon filters)
with st.sidebar:
    st.header("Filters")

    max_price_input = st.slider(
        "Maximum price (₹)",
        min_value=0,
        max_value=200,
        value=0,
        step=5,
        help="Set 0 for no maximum limit.",
    )
    max_price_val = max_price_input if max_price_input > 0 else None

    all_tags = sorted({tag for p in products_data for tag in p.tags})
    required_tags = st.multiselect(
        "Filter by tags (optional)",
        options=all_tags,
        default=[],
        help="Tags are used internally for filtering; they are not shown in the product name.",
    )

    brands = sorted({p.brand for p in products_data})
    preferred_brand = st.selectbox(
        "Preferred brand (optional)",
        options=["(no preference)"] + brands,
    )
    preferred_brand_val = None if preferred_brand == "(no preference)" else preferred_brand

# Main search area
col_left, col_right = st.columns([2, 3])

with col_left:
    st.subheader("Search product")
    product_names = sorted(name_to_product_id.keys())

    # Simulate Amazon-type search: text input with suggestions
    search_text = st.text_input("Type product name", "")

    if search_text:
        matched_names = [
            name for name in product_names if search_text.lower() in name.lower()
        ]
    else:
        matched_names = product_names

    selected_name = st.selectbox(
        "Select from catalog",
        matched_names,
        index=0 if matched_names else None,
        key="product_select",
    )

    search_button = st.button("Search")

with col_right:
    st.subheader("Product & alternatives")

    if search_button and selected_name:
        requested, exact_info, alternatives, message = find_alternatives_catalog(
            requested_product_name=selected_name,
            max_price=max_price_val,
            required_tags=required_tags,
            preferred_brand=preferred_brand_val,
        )

        st.write(message)

        if requested:
            st.markdown("**Searched product**")
            with st.container():
                st.markdown(
                    f"""
                    <div class="product-card">
                        <div class="product-title">{requested.name}</div>
                        <div class="product-meta">
                            Category: {requested.category} | Brand: {requested.brand}
                        </div>
                        <div class="product-price">₹{requested.price}</div>
                        <div class="product-meta">In stock: {requested.in_stock}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if exact_info:
            exact, rule_tags = exact_info
            explanation = build_explanation(rule_tags, required_tags)
            st.success("Exact item available")
            st.markdown("**You can buy this item:**")
            st.markdown(
                f"""
                <div class="product-card">
                    <div class="product-title">{exact.name}</div>
                    <div class="product-meta">
                        Category: {exact.category} | Brand: {exact.brand}
                    </div>
                    <div class="product-price">₹{exact.price}</div>
                    <div class="product-meta">In stock: {exact.in_stock}</div>
                    <div class="product-meta"><b>Why suggested:</b> {explanation}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif alternatives:
            st.markdown("**Alternative options**")
            for alt, rule_tags in alternatives:
                explanation = build_explanation(rule_tags, required_tags)
                st.markdown(
                    f"""
                    <div class="product-card">
                        <div class="product-title">{alt.name}</div>
                        <div class="product-meta">
                            Category: {alt.category} | Brand: {alt.brand}
                        </div>
                        <div class="product-price">₹{alt.price}</div>
                        <div class="product-meta">In stock: {alt.in_stock}</div>
                        <div class="product-meta"><b>Why suggested:</b> {explanation}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            if search_button:
                st.warning("No suitable alternatives found with current filters.")
