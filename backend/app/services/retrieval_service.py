import math
import re
from collections import Counter

STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}


class RetrievalError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z][a-zA-Z0-9'-]*\b", text.lower())
    return [token for token in tokens if token not in STOP_WORDS and len(token) > 1]


def _excerpt(text: str, query_terms: set[str], max_characters: int = 520) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_characters:
        return normalized

    lower_text = normalized.lower()
    first_hit = min(
        (lower_text.find(term) for term in query_terms if lower_text.find(term) >= 0),
        default=0,
    )
    start = max(first_hit - 120, 0)
    end = min(start + max_characters, len(normalized))
    excerpt = normalized[start:end].strip()

    if start > 0:
        excerpt = f"...{excerpt}"
    if end < len(normalized):
        excerpt = f"{excerpt}..."

    return excerpt


def retrieve_relevant_chunks(document: dict, question: str, limit: int = 5) -> list[dict]:
    chunks = document.get("chunks") or []
    if not chunks:
        raise RetrievalError("This document has no searchable text chunks.", 422)

    query_tokens = tokenize(question)
    if not query_tokens:
        raise RetrievalError("Please ask a more specific question.", 400)

    query_counts = Counter(query_tokens)
    query_terms = set(query_tokens)
    document_frequency = Counter()

    chunk_tokens = []
    for chunk in chunks:
        tokens = tokenize(chunk["text"])
        chunk_tokens.append(tokens)
        document_frequency.update(set(tokens))

    scored_chunks = []
    chunk_count = len(chunks)

    for chunk, tokens in zip(chunks, chunk_tokens):
        token_counts = Counter(tokens)
        if not token_counts:
            continue

        score = 0.0
        matched_terms = set()

        for term, query_count in query_counts.items():
            term_count = token_counts.get(term, 0)
            if not term_count:
                continue

            idf = math.log((chunk_count + 1) / (document_frequency[term] + 1)) + 1
            score += term_count * query_count * idf
            matched_terms.add(term)

        if score <= 0:
            continue

        scored_chunks.append(
            {
                "chunk_id": chunk["chunk_id"],
                "page": chunk["page"],
                "text": chunk["text"],
                "excerpt": _excerpt(chunk["text"], query_terms),
                "score": round(score, 4),
                "matched_terms": sorted(matched_terms),
            }
        )

    scored_chunks.sort(key=lambda item: (-item["score"], item["page"], item["chunk_id"]))
    return scored_chunks[:limit]
