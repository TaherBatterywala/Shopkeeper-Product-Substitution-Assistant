# SHOPKEEPER PRODUCT SUBSTITUTION ASSISTANT

[![Live Demo](https://img.shields.io/badge/Live%20App-Click%20Here-success?style=for-the-badge)](https://shopkeeper-assistant.streamlit.app/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20App-ff4b4b?style=for-the-badge&logo=streamlit)](https://streamlit.io)
[![NetworkX](https://img.shields.io/badge/NetworkX-Knowledge%20Graph-2088FF?style=for-the-badge)](https://networkx.org)

---

## Project Overview

This repository contains a **Streamlit web application** that helps a shopkeeper suggest **alternative products** when a requested item is unavailable. The system uses a **Knowledge Graph (KG)** plus **rule-based reasoning** (graph search + scoring rules + human-readable explanations) instead of flat lists or black‑box ML models.

Given a selected product and optional filters (max price, product tags, preferred brand), the app:

- Checks whether the **exact product** is available under the selected constraints.
- Traverses a **product–category–brand–attribute** Knowledge Graph using a bounded **Breadth‑First Search (BFS)** to collect nearby products.
- Applies a **scoring function** that rewards category similarity, brand match, cheaper price, and graph proximity while respecting all constraints.
- Returns a ranked list of **recommended alternatives**, each with a short **“Why suggested”** explanation and an accompanying **reasoning graph** that visually shows how the alternative is connected to the original item.

---

## Knowledge Graph Design

The Knowledge Graph is implemented using **NetworkX** and built directly from JSON catalog data.

### Node Types

- `product:<product_id>`  
  - Attributes: `name`, `category`, `brand`, `price`, `in_stock`, `tags`.
- `category:<category_name>`  
  - Example: `Dairy`, `Bakery`, `Snacks`, `Beverages`, `Health`.
- `brand:<brand_name>`  
  - Example: `Amul`, `Mother Dairy`, `Britannia`, `Lays`, etc.
- `attr:<tag_name>`  
  - Example: `veg_only`, `high_protein`, `low_fat`, `lactose_free`, `gluten_free`, `breakfast_item`, `evening_snack`.

### Edge Types

- `product → category` via `IS_A`  
  - Connects each product to its main category.
- `product → brand` via `HAS_BRAND`  
  - Connects products from the same brand.
- `product → attribute` via `HAS_ATTRIBUTE`  
  - Connects products to properties / usage tags like `high_protein`, `healthy_snack`, etc.
- `product ↔ product` via `SIMILAR_TO`  
  - Manually curated similarity pairs between closely related SKUs (e.g., different milk or bread variants) to improve graph connectivity.

### Category Similarity

A small lookup table defines **similar categories** for softer matching:

- `Dairy` is similar to `Health`, `Snacks`.
- `Bakery` is similar to `Snacks`, `Health`.
- `Snacks` is similar to `Bakery`, `Health`.
- `Beverages` is similar to `Health`.
- `Health` is similar to all of the above.

This is used to compute a **category closeness** value:

- Same category → closeness `1.0`.
- Similar category → closeness `0.7`.
- Otherwise → `0.0`.

The closeness feeds directly into the scoring function.

---

## Search & Reasoning Logic

### Candidate Search (Graph BFS)

1. Convert the requested product to its graph node: `product:<product_id>`.  
2. Run a **bounded BFS** (e.g. depth ≤ 2 or 3) from this node over the KG.
3. Whenever a product node (other than the start node) is discovered, add it as a candidate and record the **minimum depth** at which it was seen.
4. Track the number of nodes visited to get a sense of search effort.

This yields a candidate pool of graph‑local products that share category, brand, attributes, or are connected via `SIMILAR_TO` links.

### Hard Constraint Handling

Before scoring each candidate, the system applies hard filters:

- `in_stock == True`.  
- If `max_price` is set, require `candidate.price ≤ max_price`.  
- All `required_tags` must be present in `candidate.tags`.  
- For the **exact match** flow, if a `preferred_brand` is specified, the requested product must match it to qualify as an exact, buyable item.

Candidates failing any of these checks are removed and never scored.

### Scoring Rules

Each candidate that passes the constraints receives a score based on interpretable rules:

- **Category closeness**  
  - Same category: `+4.0` and tag `same_category`.  
  - Similar category: `+0.7 * 4.0` and tag `similar_category`.
- **Brand logic**  
  - Matches user’s preferred brand: `+3.0`, tag `preferred_brand_respected`.  
  - If no explicit preference, same brand as requested: `+2.0`, tag `same_brand_as_requested`.  
  - Different brand: small penalty and tag `different_brand_than_requested`.
- **Price relationship**  
  - Cheaper than requested: `+1.0`, tag `cheaper_option`.  
  - Same price: `+0.5`, tag `same_price_as_requested`.  
  - Slightly more expensive: `-0.2`, tag `slightly_more_expensive`.
- **Graph proximity**  
  - Reward closer nodes with `(3 - depth) * 0.5` and add tag `closer_in_graph`.

If `required_tags` were specified, the tag `all_required_tags_matched` is added to highlight this in explanations.

### Explanation Rule Mechanism

A dictionary maps **rule tags → human explanation fragments**, for example:

- `same_category` → “Same category.”
- `similar_category` → “Related category.”
- `preferred_brand_respected` → “Matches your preferred brand.”
- `same_brand_as_requested` → “Same brand as original product.”
- `cheaper_option` → “Cheaper option than the requested item.”
- `closer_in_graph` → “Highly related in the knowledge graph.”
- `all_required_tags_matched` → “Matches all your selected tags.”

For each candidate, all applicable tags are collected and transformed into a concise **“Why suggested”** explanation string. This mechanism makes it easy to extend the system: adding a new rule only requires adding its tag and explanation.

---

## App Features

### User Workflow

1. **Choose Product**
   - Select a category from the dropdown.
   - Select a product within that category.
   - Click **“Check stock & alternatives”**.

2. **Optional Filters**
   - **Max Price (₹)** slider to enforce a price ceiling.
   - **Required Tags** multi-select to demand specific properties (e.g., `high_protein`, `gluten_free`, `low_fat`).
   - **Preferred Brand** dropdown to prioritize a particular brand.

3. **Results Display (Product & Alternatives)**
   - Card for the **requested product** (always shown), including category badge, stock badge, price, and brand.
   - If the requested product is out of stock, an explicit message appears:
     - “This product is currently out of stock. Please review the suggested alternatives below.”
   - If an **exact match** is available under the given filters, a dedicated card highlights that it can be purchased directly, with its explanation.
   - A **ranked list of recommended alternatives** is shown underneath, each with:
     - Alternative index (Alt #1, Alt #2, …)
     - Category and stock badges
     - Price and brand
     - A textual explanation generated from the rule tags.

4. **Reasoning Graph**
   - A separate tab renders a **subgraph** containing the **shortest paths** from the requested product to each recommended product using NetworkX + Matplotlib.
   - Requested product, recommended products, and intermediate nodes (categories / brands / attributes) are colored distinctly, making it easy to see connections like “same brand”, “shares tag `high_protein`”, or “belongs to similar categories”.

---

## Project Structure

```text
Shopkeeper-Product-Substitution-Assistant/
├── app.py                           
├── README.md                  
├── requirements.txt 
│
├── data/
│   ├── products.json                  
│   ├── categories.json                
│   └── attributes.json      
│
├── src/
│   ├── __init__.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── paths.py                 
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── product.py               
│   │
│   ├── data_access/
│   │   ├── __init__.py
│   │   └── loader.py               
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── kg_builder.py           
│   │   ├── reasoning.py             
│   │   └── visualize.py           
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                  
│   │   └── exceptions.py              
│   │
│   └── pipelines/
│       ├── __init__.py
│       └── app_service.py             
│
└── notebooks/
    └── book.ipynb                     # Prototype notebook used for experiments

```

---

## Example Design Highlights

### KG modeling
Products are richly described with category, brand, and tags, and connected by interpretable edge types (`IS_A`, `HAS_BRAND`, `HAS_ATTRIBUTE`, `SIMILAR_TO`).

### Search approach
Bounded BFS finds candidates in the local neighborhood of the requested item.  
Shortest path computation powers the explanation graph, making the reasoning step transparent.

### Constraint handling
Availability, price limits, brand preferences, and tag requirements are treated as hard constraints to guarantee that all shown options respect user filters.

### Rule tags & explanations
Each ranking decision is decomposed into explicit rule tags which are mapped to human-readable text, producing concise explanations for each suggestion.

---

## Key Technologies & Libraries

- **Web UI:** Streamlit  
- **Graph Representation & Search:** NetworkX (graph, BFS, shortest paths)
- **Visualization:** Matplotlib for graph rendering in the app  
- **Data Handling:** JSON catalog files (`products.json`, `categories.json`, `attributes.json`) loaded via Python `os` paths for portability.

---

Thank you for taking the time to review this project. 🙏🏻