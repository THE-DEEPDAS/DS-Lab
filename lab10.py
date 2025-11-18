"""Implementations for common streaming and data mining algorithms.

Included algorithms:
1. Flajolet–Martin approximate distinct counter for data streams.
2. Apriori and FP-Growth frequent itemset mining.
3. Bloom filter for probabilistic membership testing.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import chain, combinations
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

############################
# Flajolet–Martin Algorithm
############################


def _hash_to_int(value: str, seed: int) -> int:
    """Return a deterministic 64-bit hash for the given value and seed."""
    digest = hashlib.blake2b(f"{seed}:{value}".encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, byteorder="big", signed=False)


def _trailing_zeroes(value: int) -> int:
    """Count trailing zero bits; return width when value is zero."""
    if value == 0:
        return 64
    tz = 0
    while (value & 1) == 0:
        tz += 1
        value >>= 1
    return tz


def flajolet_martin(stream: Iterable[str], num_hashes: int = 64) -> Tuple[float, List[int]]:
    """Estimate number of distinct elements using Flajolet–Martin.

    Returns the estimate and the list of max trailing-zero counts per hash function.
    """
    max_zeroes = [0] * num_hashes
    for item in stream:
        item_str = str(item)
        for seed in range(num_hashes):
            hashed = _hash_to_int(item_str, seed)
            tz = _trailing_zeroes(hashed)
            max_zeroes[seed] = max(max_zeroes[seed], tz)

    mean_zeroes = sum(max_zeroes) / num_hashes
    estimate = 2 ** mean_zeroes / 0.77351  # bias correction constant
    return estimate, max_zeroes


############################
# Frequent Itemset Mining
############################

Transaction = FrozenSet[str]


def powerset(iterable: Iterable[str]) -> Iterable[Transaction]:
    """Generate the powerset of an iterable (excluding the empty set)."""
    items = list(iterable)
    for r in range(1, len(items) + 1):
        for combo in combinations(items, r):
            yield frozenset(combo)


def apriori(transactions: Sequence[Transaction], min_support: int) -> Dict[int, Dict[Transaction, int]]:
    """Compute frequent itemsets using the Apriori algorithm."""
    item_counts = Counter(chain.from_iterable(transactions))
    frequent_sets: Dict[int, Dict[Transaction, int]] = {}

    level = 1
    current = {frozenset([item]): count for item, count in item_counts.items() if count >= min_support}
    while current:
        frequent_sets[level] = current
        level += 1
        candidate_items = set(chain.from_iterable(current.keys()))
        # Generate candidate (level)-itemsets by joining frequent sets of previous level.
        candidates = set()
        current_keys = list(current.keys())
        for i in range(len(current_keys)):
            for j in range(i + 1, len(current_keys)):
                union_set = current_keys[i] | current_keys[j]
                if len(union_set) == level:
                    subsets_valid = all(frozenset(subset) in current for subset in combinations(union_set, level - 1))
                    if subsets_valid:
                        candidates.add(union_set)

        candidate_counts: Dict[Transaction, int] = {candidate: 0 for candidate in candidates}
        for transaction in transactions:
            for candidate in candidates:
                if candidate.issubset(transaction):
                    candidate_counts[candidate] += 1

        current = {itemset: count for itemset, count in candidate_counts.items() if count >= min_support}

    return frequent_sets


class FPTreeNode:
    """Node used by the FP-Growth tree structure."""

    def __init__(self, item: Optional[str], count: int, parent: Optional["FPTreeNode"]) -> None:
        self.item = item
        self.count = count
        self.parent = parent
        self.children: Dict[str, FPTreeNode] = {}
        self.node_link: Optional[FPTreeNode] = None

    def increment(self, count: int) -> None:
        self.count += count


class FPTree:
    """FP-Tree data structure for mining frequent patterns."""

    def __init__(self) -> None:
        self.root = FPTreeNode(item=None, count=0, parent=None)
        self.headers: Dict[str, Tuple[int, Optional[FPTreeNode]]] = {}

    def add_transaction(self, transaction: List[str], count: int = 1) -> None:
        current_node = self.root
        for item in transaction:
            if item not in current_node.children:
                new_node = FPTreeNode(item=item, count=0, parent=current_node)
                current_node.children[item] = new_node
                # Link into header table
                if item in self.headers:
                    _, first_node = self.headers[item]
                    assert first_node is not None
                    while first_node.node_link:
                        first_node = first_node.node_link
                    first_node.node_link = new_node
                else:
                    self.headers[item] = (0, new_node)
            current_node = current_node.children[item]
            current_node.increment(count)

    def build(self, transactions: Sequence[Tuple[List[str], int]]) -> None:
        for items, count in transactions:
            self.add_transaction(items, count)
        # Fill header counts
        for item, (_, node) in list(self.headers.items()):
            total = 0
            current = node
            while current:
                total += current.count
                current = current.node_link
            self.headers[item] = (total, self.headers[item][1])

    def conditional_pattern_base(self, item: str) -> List[Tuple[List[str], int]]:
        patterns: List[Tuple[List[str], int]] = []
        _, node = self.headers[item]
        current = node
        while current:
            path = []
            parent = current.parent
            while parent and parent.item is not None:
                path.append(parent.item)
                parent = parent.parent
            if path:
                patterns.append((list(reversed(path)), current.count))
            current = current.node_link
        return patterns


def fp_growth(transactions: Sequence[Transaction], min_support: int) -> Dict[Transaction, int]:
    """Compute frequent itemsets using the FP-Growth algorithm."""
    # First, count supports of items to filter infrequent ones.
    item_counts = Counter(chain.from_iterable(transactions))
    frequent_items = {item for item, count in item_counts.items() if count >= min_support}
    if not frequent_items:
        return {}

    # Sort items in each transaction by decreasing frequency for tree insertion.
    ordered_transactions: List[Tuple[List[str], int]] = []
    for transaction in transactions:
        filtered = [item for item in transaction if item in frequent_items]
        filtered.sort(key=lambda item: (-item_counts[item], item))
        if filtered:
            ordered_transactions.append((filtered, 1))

    tree = FPTree()
    tree.build(ordered_transactions)

    frequent_itemsets: Dict[Transaction, int] = {}

    def mine(tree: FPTree, prefix: Transaction) -> None:
        items = sorted(tree.headers.items(), key=lambda kv: (kv[1][0], kv[0]))
        for item, (support, _) in items:
            new_prefix = prefix | {item}
            frequent_itemsets[new_prefix] = support
            conditional_patterns = tree.conditional_pattern_base(item)
            conditional_tree = FPTree()
            conditional_tree.build(conditional_patterns)
            if conditional_tree.headers:
                mine(conditional_tree, new_prefix)

    mine(tree, frozenset())
    return frequent_itemsets


############################
# Bloom Filter
############################


def _random_hash_function(seed: int, size: int):
    def _hash(value: str) -> int:
        digest = hashlib.blake2b(f"{seed}:{value}".encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, byteorder="big", signed=False) % size

    return _hash


@dataclass
class BloomFilter:
    """Simple Bloom filter for streaming membership testing."""

    size: int
    num_hashes: int
    seeds: Optional[List[int]] = None

    def __post_init__(self) -> None:
        if self.size <= 0:
            raise ValueError("size must be positive")
        if self.num_hashes <= 0:
            raise ValueError("num_hashes must be positive")
        rng = random.Random(42)
        self.seeds = self.seeds or [rng.randrange(1, 1_000_000) for _ in range(self.num_hashes)]
        self.bit_array = [0] * self.size
        self.hash_functions = [_random_hash_function(seed, self.size) for seed in self.seeds]

    def add(self, value: str) -> None:
        for hash_fn in self.hash_functions:
            idx = hash_fn(value)
            self.bit_array[idx] = 1

    def __contains__(self, value: str) -> bool:
        return all(self.bit_array[hash_fn(value)] for hash_fn in self.hash_functions)

    def false_positive_rate(self, inserted_items: int) -> float:
        """Return the theoretical false positive rate after inserting given items."""
        return (1 - math.exp(-self.num_hashes * inserted_items / self.size)) ** self.num_hashes


############################
# Demonstration Harness
############################


def demo_flajolet_martin() -> None:
    print("Flajolet–Martin Demo:")
    stream = [f"user_{i}" for i in range(1000)] + ["user_42"] * 1000
    estimate, zeroes = flajolet_martin(stream, num_hashes=64)
    print(f"  Exact distinct count: 1000")
    print(f"  Estimated distinct count: {estimate:.2f}")
    print(f"  Max trailing zeroes sample (first 5 hashes): {zeroes[:5]}")


def demo_apriori_fp_growth() -> None:
    print("\nApriori and FP-Growth Demo:")
    transactions = [
        frozenset({"milk", "bread", "butter"}),
        frozenset({"beer", "bread"}),
        frozenset({"milk", "bread", "beer", "butter"}),
        frozenset({"bread", "butter"}),
        frozenset({"milk", "bread", "butter"}),
    ]
    min_support = 2

    apriori_result = apriori(transactions, min_support)
    print("  Apriori frequent itemsets:")
    for level, itemsets in apriori_result.items():
        for itemset, count in itemsets.items():
            print(f"    {set(itemset)} -> support {count}")

    fp_result = fp_growth(transactions, min_support)
    print("  FP-Growth frequent itemsets:")
    for itemset, count in fp_result.items():
        print(f"    {set(itemset)} -> support {count}")


def demo_bloom_filter() -> None:
    print("\nBloom Filter Demo:")
    bloom = BloomFilter(size=1000, num_hashes=5)
    words = ["apple", "banana", "cherry", "date", "elderberry"]
    for word in words:
        bloom.add(word)
    queries = words + ["fig", "grape"]
    for q in queries:
        print(f"  {q:10s} -> {'maybe' if q in bloom else 'definitely not'}")
    print(f"  Estimated false positive rate after {len(words)} inserts: {bloom.false_positive_rate(len(words)):.6f}")


if __name__ == "__main__":
    demo_flajolet_martin()
    demo_apriori_fp_growth()
    demo_bloom_filter()
