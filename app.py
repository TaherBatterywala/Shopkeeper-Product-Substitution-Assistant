import streamlit as st
from src.pipelines.app_service import AppService

service = AppService()

st.set_page_config(layout="wide", page_title="Smart Catalog Assistant")

# ---------- Global CSS ----------
st.markdown("""
<style>
body, .main, .stApp {
    background-color: #050b16;
    color: #e0e6f0;
}
.block-container {
    padding-top: 2.8rem;
    padding-bottom: 1.5rem;
}

/* Hero area */
.hero-title {
    font-size: 30px;
    font-weight: 800;
    background: linear-gradient(90deg, #5ab0ff, #9f7bff);
    -webkit-background-clip: text;
    color: transparent;
}
.hero-subtitle {
    font-size: 14px;
    color: #9ca7c6;
}

/* Product cards */
.product-card {
    border: 1px solid #1f2a3a;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 12px;
    background: radial-gradient(circle at top left, #1a2740 0%, #050b16 55%);
    box-shadow: 0 4px 10px rgba(0,0,0,0.7);
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}
.product-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0,0,0,0.9);
    border-color: #4f82ff;
}
.product-title {
    font-weight: 700;
    font-size: 17px;
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

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
}
.badge-category {
    background: rgba(93, 156, 255, 0.16);
    color: #78aaff;
    border: 1px solid rgba(93, 156, 255, 0.4);
}
.badge-stock {
    background: rgba(69, 214, 154, 0.16);
    color: #45d69a;
    border: 1px solid rgba(69, 214, 154, 0.4);
}
.badge-alt-index {
    background: rgba(255, 200, 97, 0.16);
    color: #ffc861;
    border: 1px solid rgba(255, 200, 97, 0.4);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.3rem;
}
.stTabs [data-baseweb="tab"] {
    background-color: #081321;
    padding: 0.4rem 0.9rem;
    border-radius: 999px;
    color: #c0c6dd;
    font-size: 13px;
    font-weight: 500;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, #1b3b6f, #3560b3);
    color: #ffffff !important;
}

/* Buttons */
.stButton button {
    background: linear-gradient(90deg, #1b3b6f, #274a8a);
    color: #ffffff;
    border-radius: 999px;
    border: 1px solid #3b6ac9;
    padding: 0.4rem 1.2rem;
}
.stButton button:hover {
    background: linear-gradient(90deg, #274a8a, #3560b3);
    border-color: #4f82ff;
}

/* Expander */
.stExpander {
    border: 1px solid #1f2a3a;
    border-radius: 8px;
    background-color: #081321;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #050b16;
}
</style>
""", unsafe_allow_html=True)

# ---------- Hero header ----------
st.markdown('<div class="hero-title">Smart Catalog & Substitution Assistant</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">'
    'Search any product in the store, check availability, and see curated graph‑based alternatives '
    'with transparent reasoning.</div>',
    unsafe_allow_html=True
)
st.write("")

# ---------- Layout: two columns ----------
left_col, right_col = st.columns([1, 1.5])

with left_col:
    st.subheader("Choose product")

    # Primary: category + product
    categories = service.list_categories()
    cat = st.selectbox("Category", categories, key="category_main")
    product_names = service.list_products_in_category(cat)
    selected_name = st.selectbox("Product", product_names, key="product_main")

    st.write("")
    search_clicked = st.button("✨ Check stock & alternatives")

    st.markdown("---")
    st.markdown("**Filters (optional)**")

    max_price_input = st.slider("Max Price (₹)", 0, 250, 0, 5, key="max_price_main")
    max_price_val = max_price_input if max_price_input > 0 else None

    all_tags = sorted({tag for p in service.products for tag in p.tags})
    required_tags = st.multiselect("Required Tags", options=all_tags, default=[], key="tags_main")

    brands = sorted({p.brand for p in service.products})
    preferred_brand = st.selectbox(
        "Preferred Brand",
        ["(no preference)"] + brands,
        key="brand_main",
    )
    preferred_brand_val = None if preferred_brand == "(no preference)" else preferred_brand

with right_col:
    tab_main, tab_graph = st.tabs(["Product & alternatives", "Reasoning graph"])

    if search_clicked:
        result = service.get_results(
            selected_name, max_price_val, required_tags, preferred_brand_val
        )
        requested = result["requested"]

        with tab_main:
            st.subheader("Product & alternatives")
            st.info(result["message"])

            # Requested product card
            if requested:
                stock_badge = (
                    "<span class='badge badge-stock'>In stock</span>"
                    if requested.in_stock
                    else "<span class='badge badge-stock' style='opacity:0.6'>Out of stock</span>"
                )
                st.markdown(
                    f"""
                    <div class="product-card">
                        <div class="product-title">{requested.name}</div>
                        <div class="product-meta">
                            <span class="badge badge-category">{requested.category}</span>
                            {stock_badge}
                        </div>
                        <div class="product-price">₹{requested.price}</div>
                        <div class="product-meta">Brand: {requested.brand}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # If requested is out of stock, show explicit message
                if not requested.in_stock:
                    st.warning("This product is currently out of stock. Please review the suggested alternatives below.")

            # If exact match is available and also passes filters
            if result["exact_match"]:
                em = result["exact_match"]["product"]
                st.markdown("**You can buy this exact item:**")
                st.markdown(
                    f"""
                    <div class="product-card">
                        <div class="product-title">{em.name}</div>
                        <div class="product-meta">
                            <span class="badge badge-category">{em.category}</span>
                            <span class="badge badge-stock">In stock</span>
                        </div>
                        <div class="product-price">₹{em.price}</div>
                        <div class="product-meta">Brand: {em.brand}</div>
                        <div class="product-meta"><b>Why suggested:</b> {result["exact_match"]["explanation"]}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Alternatives, always shown under the product section
            st.markdown("### Recommended alternatives")
            if result["alternatives"]:
                for idx, rec in enumerate(result["alternatives"], start=1):
                    p = rec.product
                    alt_stock_badge = (
                        "<span class='badge badge-stock'>In stock</span>"
                        if p.in_stock
                        else "<span class='badge badge-stock' style='opacity:0.6'>Out of stock</span>"
                    )
                    st.markdown(
                        f"""
                        <div class="product-card">
                            <div class="product-title">{p.name}</div>
                            <div class="product-meta">
                                <span class="badge badge-alt-index">Alt #{idx}</span>
                                <span class="badge badge-category">{p.category}</span>
                                {alt_stock_badge}
                            </div>
                            <div class="product-price">₹{p.price}</div>
                            <div class="product-meta">
                                Brand: {p.brand}
                            </div>
                            <div class="product-meta"><b>Why suggested:</b> {rec.explanation}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            else:
                st.write("No alternative suggestions with the current filters.")

        with tab_graph:
            st.subheader("Knowledge Graph reasoning")
            if result["requested"] and result["alternatives"]:
                fig = service.build_visualization(result["requested"], result["alternatives"])
                if fig:
                    st.pyplot(fig)
            else:
                st.write("No paths to visualize (no alternatives for this query).")
    else:
        with tab_main:
            st.markdown("Start by selecting a product on the left and clicking **“Check stock & alternatives”**.")
        with tab_graph:
            st.write("The reasoning graph will appear here after you run a query.")
