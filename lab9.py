from __future__ import annotations
import re
import random
from itertools import combinations
from typing import Dict, Iterable, List, Set, Tuple

_PRIME = 4_294_967_311  # Large prime for hashing; fits within 64-bit integers.


def normalize_text(text: str) -> List[str]:
    """Lower-case and tokenize text into alphanumeric words."""
    return re.findall(r"\w+", text.lower())


def build_shingles(text: str, k: int) -> Set[str]:
    """Create k-word shingles from text; fallback to single tokens if too short."""
    tokens = normalize_text(text)
    if len(tokens) < k:
        return set(tokens)
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard_similarity(a: Set[str], b: Set[str]) -> float:
    """Compute Jaccard similarity between two shingle sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


class ShinglingMinHash:
    """Maintain shingle sets and MinHash signatures for multiple documents."""

    def __init__(self, k: int = 3, num_hashes: int = 128, seed: int = 42) -> None:
        if k <= 0:
            raise ValueError("k must be positive")
        if num_hashes <= 0:
            raise ValueError("num_hashes must be positive")
        self.k = k
        self.num_hashes = num_hashes
        self._rng = random.Random(seed)
        self._hash_coeffs = self._generate_hash_coefficients()
        self._shingle_index: Dict[str, int] = {}
        self._documents: Dict[str, Set[str]] = {}
        self._signatures: Dict[str, List[int]] = {}

    def _generate_hash_coefficients(self) -> List[Tuple[int, int]]:
        coeffs = set()
        while len(coeffs) < self.num_hashes:
            a = self._rng.randrange(1, _PRIME)
            b = self._rng.randrange(0, _PRIME)
            coeffs.add((a, b))
        return list(coeffs)

    def add_document(self, doc_id: str, text: str) -> None:
        shingles = build_shingles(text, self.k)
        self._documents[doc_id] = shingles
        for shingle in shingles:
            if shingle not in self._shingle_index:
                self._shingle_index[shingle] = len(self._shingle_index)
        self._signatures.pop(doc_id, None)

    def _shingle_ids(self, doc_id: str) -> Set[int]:
        shingles = self._documents.get(doc_id)
        if shingles is None:
            raise KeyError(f"Document '{doc_id}' is not registered")
        return {self._shingle_index[s] for s in shingles}

    def _compute_signature(self, doc_id: str) -> List[int]:
        shingle_ids = self._shingle_ids(doc_id)
        if not shingle_ids:
            return [(_PRIME - 1)] * self.num_hashes
        signature = []
        for a, b in self._hash_coeffs:
            min_hash = min((a * sid + b) % _PRIME for sid in shingle_ids)
            signature.append(min_hash)
        return signature

    def _ensure_signature(self, doc_id: str) -> List[int]:
        if doc_id not in self._signatures:
            self._signatures[doc_id] = self._compute_signature(doc_id)
        return self._signatures[doc_id]

    def shingles(self, doc_id: str) -> Set[str]:
        if doc_id not in self._documents:
            raise KeyError(f"Document '{doc_id}' is not registered")
        return self._documents[doc_id]

    def signature(self, doc_id: str) -> List[int]:
        return list(self._ensure_signature(doc_id))

    def jaccard(self, doc_id_a: str, doc_id_b: str) -> float:
        return jaccard_similarity(self.shingles(doc_id_a), self.shingles(doc_id_b))

    def minhash_similarity(self, doc_id_a: str, doc_id_b: str) -> float:
        sig_a = self._ensure_signature(doc_id_a)
        sig_b = self._ensure_signature(doc_id_b)
        matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
        return matches / len(sig_a)

    def pairwise_similarities(self, approximate: bool = False) -> Dict[Tuple[str, str], float]:
        scores: Dict[Tuple[str, str], float] = {}
        for doc_a, doc_b in combinations(self._documents.keys(), 2):
            if approximate:
                scores[(doc_a, doc_b)] = self.minhash_similarity(doc_a, doc_b)
            else:
                scores[(doc_a, doc_b)] = self.jaccard(doc_a, doc_b)
        return scores

    def similarity_report(self) -> List[Tuple[str, str, float, float]]:
        report: List[Tuple[str, str, float, float]] = []
        for doc_a, doc_b in combinations(self._documents.keys(), 2):
            exact = self.jaccard(doc_a, doc_b)
            approx = self.minhash_similarity(doc_a, doc_b)
            report.append((doc_a, doc_b, exact, approx))
        return report


def compare_documents(documents: Dict[str, str], k: int = 3, num_hashes: int = 128) -> List[Tuple[str, str, float, float]]:
    """Helper to build a model and return similarity scores."""
    model = ShinglingMinHash(k=k, num_hashes=num_hashes)
    for doc_id, text in documents.items():
        model.add_document(doc_id, text)
    return model.similarity_report()


if __name__ == "__main__":
    sample_docs = {
        "doc1": "Natural language processing enables computers to understand text.",
        "doc2": "Natural language processing helps machines interpret human text data.",
        "doc3": "Reinforcement learning trains agents through rewards and penalties.",
    }

    report = compare_documents(sample_docs, k=3, num_hashes=128)
    print("doc_a\tdoc_b\tJaccard\tMinHash")
    for doc_a, doc_b, exact, approx in report:
        print(f"{doc_a}\t{doc_b}\t{exact:.4f}\t{approx:.4f}")
