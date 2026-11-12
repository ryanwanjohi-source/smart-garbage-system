"""Route optimization (proposal §3.3.3.3).
Builds a complete distance graph over bins needing collection and returns a
greedy nearest-neighbour visit order plus total distance (km).
"""
import math
import networkx as nx

# Depot: Nairobi CBD collection yard (tune to the pilot site)
DEPOT = (-1.2921, 36.8219)


def haversine(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def optimize_route(bin_points, depot=DEPOT):
    """bin_points: [(bin_id, lat, lng), ...] -> (ordered bin_ids, total_km)."""
    nodes = ["depot"] + [bid for bid, _, _ in bin_points]
    coords = {"depot": depot, **{bid: (la, lo) for bid, la, lo in bin_points}}
    G = nx.complete_graph(nodes)
    for u, v in G.edges():
        G[u][v]["weight"] = haversine(coords[u], coords[v])

    # greedy nearest neighbour starting at depot
    unvisited = set(nodes) - {"depot"}
    order, current, total = [], "depot", 0.0
    while unvisited:
        nxt = min(unvisited, key=lambda n: G[current][n]["weight"])
        total += G[current][nxt]["weight"]
        order.append(nxt)
        unvisited.remove(nxt)
        current = nxt
    total += G[current]["depot"]["weight"]  # return leg
    return order, total


if __name__ == "__main__":
    demo = [(1, -1.2864, 36.8172), (2, -1.2841, 36.8219), (3, -1.2921, 36.8300)]
    print(optimize_route(demo))
