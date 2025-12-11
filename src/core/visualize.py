from typing import List, Optional
import matplotlib.pyplot as plt
import networkx as nx

from src.models.product import Product, Recommendation
from src.core.reasoning import product_to_node_id

def visualize_search_path(KG: nx.Graph, root_product: Product, recs: List[Recommendation]) -> Optional[plt.Figure]:
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
            a, b = path[i], path[i + 1]
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

    colors = []
    for n in sub.nodes():
        if n == root_id:
            colors.append("#ffe680")   # requested
        elif n in target_ids:
            colors.append("#b3ffb3")   # alternatives
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

    labels = {n: sub.nodes[n].get("name", n) for n in sub.nodes()}
    nx.draw_networkx_labels(sub, pos, labels=labels, font_size=8, font_color="#000000")

    ax = plt.gca()
    ax.set_facecolor("#050b16")
    plt.title(f"Paths from '{root_product.name}' to recommended items", fontsize=10, color="#ffffff")
    plt.axis("off")
    return plt
