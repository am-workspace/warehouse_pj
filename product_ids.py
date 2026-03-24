from __future__ import annotations


def normalize_product_id(product_id: str) -> str:
    if not isinstance(product_id, str) or not product_id.strip():
        raise ValueError("product_id must be a non-empty string.")
    return product_id.strip().upper()


def normalize_product_query(query: str | None) -> str | None:
    if query is None:
        return None

    normalized = query.strip().upper()
    if not normalized:
        return None
    return normalized
