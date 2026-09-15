"""Graph-based black-box UQ measures from the existing NLI similarity matrix.

Implements the remaining measures from Lin et al. (TMLR 2024) /
Kuhn et al. (ICLR 2023) on the per-question semantic equivalence graph
(bidirectional entailment >= 0.5 -> edge):

    num_sets      number of connected components (semantic sets)
    degree_matrix trace of the graph Laplacian = sum of node degrees
    eigv          sum of eigenvalues of the graph Laplacian
    eccentricity  maximum node eccentricity (max shortest-path distance)

Note: for a graph Laplacian, sum of eigenvalues == trace == sum of degrees,
so degree_matrix and eigv coincide by construction; both are reported for
completeness.

NO new NLI computation: the pairwise entailment matrix is read from
results/semantic_entropy.jsonl (already persisted by score_semantic_entropy.py).

Outputs:
    results/graph_methods.jsonl

Usage:
    python scoring/score_graph_methods.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import uq_common as uq


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, node: int) -> int:
        while self.parent[node] != node:
            self.parent[node] = self.parent[self.parent[node]]
            node = self.parent[node]
        return node

    def union(self, a: int, b: int) -> None:
        root_a, root_b = self.find(a), self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a


def load_jsonl(path: Path) -> dict[str, dict]:
    rows = {}
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows[row["question_id"]] = row
    return rows


def main() -> int:
    uq.enable_utf8_stdout()
    uq.ensure_results_dir()

    semantic = load_jsonl(uq.RESULTS_DIR / "semantic_entropy.jsonl")
    print(f"reading pairwise NLI matrices for {len(semantic)} questions")

    rows = []
    for question_id, row in semantic.items():
        n = row["n_samples"]
        adjacency = np.zeros((n, n))
        for pair in row.get("pairwise", []):
            if pair.get("equivalent"):
                adjacency[pair["i"], pair["j"]] = 1.0
                adjacency[pair["j"], pair["i"]] = 1.0

        union_find = UnionFind(n)
        for i in range(n):
            for j in range(i + 1, n):
                if adjacency[i, j]:
                    union_find.union(i, j)
        num_sets = len({union_find.find(node) for node in range(n)})

        degrees = adjacency.sum(axis=1)
        laplacian = np.diag(degrees) - adjacency
        degree_matrix = float(laplacian.trace())
        eigv = float(np.linalg.eigvalsh(laplacian).sum())

        # Floyd-Warshall for eccentricity
        infinity = float("inf")
        distance = [[0.0 if i == j else infinity for j in range(n)] for i in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                if adjacency[i, j]:
                    distance[i][j] = distance[j][i] = 1.0
        for k in range(n):
            for i in range(n):
                for j in range(n):
                    if distance[i][k] + distance[k][j] < distance[i][j]:
                        distance[i][j] = distance[i][k] + distance[k][j]
        eccentricities = []
        for i in range(n):
            finite = [distance[i][j] for j in range(n) if distance[i][j] != infinity]
            eccentricities.append(max(finite) if finite else 0.0)
        eccentricity = max(eccentricities) if eccentricities else 0.0

        rows.append(
            {
                "question_id": question_id,
                "category": row["category"],
                "n_samples": n,
                "num_sets": num_sets,
                "degree_matrix": round(degree_matrix, 6),
                "eigv": round(eigv, 6),
                "eccentricity": round(eccentricity, 6),
                "n_edges": int(adjacency.sum() / 2),
            }
        )

    uq.write_jsonl(uq.RESULTS_DIR / "graph_methods.jsonl", rows)
    print(f"scored {len(rows)} questions -> {uq.RESULTS_DIR / 'graph_methods.jsonl'}")
    for category in ("factual", "math", "reasoning"):
        group = [r for r in rows if r["category"] == category]
        if group:
            n = len(group)
            print(
                f"{category:<10} n={n:>3} mean num_sets={sum(r['num_sets'] for r in group) / n:.2f} "
                f"degree={sum(r['degree_matrix'] for r in group) / n:.2f} "
                f"eccentricity={sum(r['eccentricity'] for r in group) / n:.2f}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
