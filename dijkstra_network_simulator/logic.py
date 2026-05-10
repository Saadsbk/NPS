from typing import TypedDict, cast, Optional, Any
import heapq

import networkx as nx

class PathResult(TypedDict):
    shortest_distance: float
    second_shortest_distance: float
    shortest_path: Optional[list[str]]
    second_shortest_path: Optional[list[str]]

def single_source_second_shortest_path(G: nx.Graph, start: str) -> dict[str, PathResult]:
    INF: float = float("inf")
    dist: dict[str, list[float]] = {node: [INF, INF] for node in G.nodes}
    paths: dict[str, list[Optional[list[str]]]] = {node: [None, None] for node in G.nodes}

    dist[start][0] = 0
    paths[start][0] = [start]

    pq: list[tuple[float, str, list[str]]] = [(0, start, [start])]

    while pq:
        curr_dist, u, curr_path = heapq.heappop(pq)

        for v in G.neighbors(u):
            # Prevent cycles
            if v in curr_path:
                continue

            weight: float = float(G[u][v].get("weight", 1))
            new_dist: float = curr_dist + weight
            new_path: list[str] = curr_path + [v]

            # Case 1: New shortest
            if new_dist < dist[v][0]:
                dist[v][1] = dist[v][0]
                paths[v][1] = paths[v][0]

                dist[v][0] = new_dist
                paths[v][0] = new_path

                heapq.heappush(pq, (new_dist, v, new_path))
            
            # Case 2: New second shortest
            elif new_dist != dist[v][0] and new_dist < dist[v][1]:
                dist[v][1] = new_dist
                paths[v][1] = new_path

                heapq.heappush(pq, (new_dist, v, new_path))
    
    return {
        node: {
            "shortest_distance": dist[node][0],
            "second_shortest_distance": dist[node][1],
            "shortest_path": paths[node][0],
            "second_shortest_path": paths[node][1],
        }
        for node in G.nodes
    }

class FlowEntry(TypedDict):
    dst: str
    next_hop: str
    path: str
    cost: int | float | str

FlowTables = dict[str, list[FlowEntry]]

class SDNLogic:
    def __init__(self) -> None:
        self.G: nx.Graph = nx.Graph()

    def rebuild(self, routers: list[str], links: list[tuple[str, str, int]]) -> None:
        self.G.clear()
        for router_name in routers:
            self.G.add_node(router_name)
        for n1, n2, weight in links:
            self.G.add_edge(n1, n2, weight=weight)

    def compute(self) -> tuple[FlowTables, FlowTables]:
        """Return shortest and second shortest routing table entries for each source router."""
        shortest_tables: FlowTables = {}
        second_shortest_tables: FlowTables = {}
        INF = float("inf")
        for src in self.G.nodes:
            entries_short: list[FlowEntry] = []
            entries_second: list[FlowEntry] = []
            result = single_source_second_shortest_path(self.G, src)
            for dst in sorted(self.G.nodes):
                if dst == src:
                    continue
                
                # Shortest
                sp = result[dst]["shortest_path"]
                sd = result[dst]["shortest_distance"]
                if sp is None:
                    entries_short.append({"dst": dst, "next_hop": "—", "path": "unreachable", "cost": "∞"})
                else:
                    cost_str = sd if sd != INF else "∞"
                    entries_short.append({"dst": dst, "next_hop": sp[1] if len(sp) > 1 else src, "path": " --> ".join(sp), "cost": cost_str})
                    
                # Second shortest
                ssp = result[dst]["second_shortest_path"]
                ssd = result[dst]["second_shortest_distance"]
                if ssp is None:
                    entries_second.append({"dst": dst, "next_hop": "—", "path": "unreachable", "cost": "∞"})
                else:
                    cost_str2 = ssd if ssd != INF else "∞"
                    entries_second.append({"dst": dst, "next_hop": ssp[1] if len(ssp) > 1 else src, "path": " --> ".join(ssp), "cost": cost_str2})
            shortest_tables[src] = entries_short
            second_shortest_tables[src] = entries_second
        return shortest_tables, second_shortest_tables
