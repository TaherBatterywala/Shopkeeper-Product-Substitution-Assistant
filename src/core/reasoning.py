from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import networkx as nx

from src.models.product import Product, Recommendation
from src.core.kg_builder import SIMILAR_CATEGORIES
from src.utils.logger import logger

def product_to_node_id(product_id: str) -> str:
    return f"product:{product_id}"

def node_id_to_product(node_id: str, id_to_product: Dict[str, Product]) -> Optional[Product]:
    if not node_id.startswith("product:"):
        return None
    pid = node_id.split("product:")[-1]
    return id_to_product.get(pid)

def category_closeness(source_cat: str, target_cat: str) -> float:
    if source_cat == target_cat:
        return 1.0
    if target_cat in SIMILAR_CATEGORIES.get(source_cat, []):
        return 0.7
    return 0.0

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

def bfs_candidates_with_depth(
    KG: nx.Graph,
    requested: Product,
    id_to_product: Dict[str, Product],
    max_depth: int = 2,
) -> Tuple[Dict[str, Tuple[Product,int]], int]:
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
                p = node_id_to_product(nb, id_to_product)
                if p:
                    prev = candidates.get(p.product_id)
                    if prev is None or depth + 1 < prev[1]:
                        candidates[p.product_id] = (p, depth + 1)

    logger.info(f"BFS traversed {traversed} nodes, found {len(candidates)} candidate products")
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
    KG: nx.Graph,
    products: List[Product],
    requested_product_name: str,
    max_price: Optional[float],
    required_tags: List[str],
    preferred_brand: Optional[str],
    max_alternatives: int = 3,
) -> Dict[str, Any]:
    id_to_product = {p.product_id: p for p in products}
    name_to_product_id = {p.name: p.product_id for p in products}

    res: Dict[str, Any] = {
        "requested": None,
        "exact_match": None,
        "alternatives": [],
        "message": "",
        "traversed_nodes": 0,
    }

    pid = name_to_product_id.get(requested_product_name)
    if pid is None:
        res["message"] = "Product not found."
        return res

    requested = id_to_product[pid]
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

    candidates_with_depth, traversed = bfs_candidates_with_depth(KG, requested, id_to_product, max_depth=2)
    res["traversed_nodes"] = traversed

    scored: List[Recommendation] = []
    for _, (cand, depth) in candidates_with_depth.items():
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
