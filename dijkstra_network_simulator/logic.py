
from typing import TypedDict, cast

import networkx as nx


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

    def compute(self) -> FlowTables:
        """Return routing table entries for each source router."""
        tables: FlowTables = {}
        for src in self.G.nodes:
            entries: list[FlowEntry] = []
            try:
                result = nx.single_source_dijkstra(self.G, src, weight="weight")
                lengths = cast(dict[str, float], result[0])
                paths = cast(dict[str, list[str]], result[1])
                for dst in sorted(self.G.nodes):
                    if dst == src:
                        continue
                    if dst not in paths:
                        entries.append(
                            {
                                "dst": dst,
                                "next_hop": "—",
                                "path": "unreachable",
                                "cost": "∞",
                            }
                        )
                    else:
                        path_nodes = paths[dst]
                        entries.append(
                            {
                                "dst": dst,
                                "next_hop": path_nodes[1] if len(path_nodes) > 1 else src,
                                "path": " → ".join(path_nodes),
                                "cost": lengths[dst],
                            }
                        )
            except Exception:
                # Keep behavior identical to the original implementation.
                pass
            tables[src] = entries
        return tables
