from __future__ import annotations

from dataclasses import dataclass

from product_ids import normalize_product_id, normalize_product_query


@dataclass(frozen=True)
class InventoryItem:
    product_id: str
    quantity: int


class InventoryError(Exception):
    """Base exception for inventory-related failures."""


class InvalidQuantityError(InventoryError):
    """Raised when the requested quantity is not a positive integer."""


class ProductNotFoundError(InventoryError):
    """Raised when a product does not exist in inventory."""


class InsufficientStockError(InventoryError):
    """Raised when stock is not enough for a removal request."""


class Inventory:
    """In-memory inventory store with a small API that is easy to swap later."""

    def __init__(self) -> None:
        self._stock: dict[str, int] = {}

    def add(self, product_id: str, quantity: int) -> InventoryItem:
        normalized_product_id = normalize_product_id(product_id)
        self._validate_quantity(quantity)

        new_quantity = self._stock.get(normalized_product_id, 0) + quantity
        self._stock[normalized_product_id] = new_quantity
        return InventoryItem(product_id=normalized_product_id, quantity=new_quantity)

    def remove(self, product_id: str, quantity: int) -> InventoryItem:
        normalized_product_id = normalize_product_id(product_id)
        self._validate_quantity(quantity)

        if normalized_product_id not in self._stock:
            raise ProductNotFoundError(f"Product '{normalized_product_id}' not found.")

        current_quantity = self._stock[normalized_product_id]
        if quantity > current_quantity:
            raise InsufficientStockError(
                f"Cannot remove {quantity} units from '{normalized_product_id}'; only {current_quantity} available."
            )

        new_quantity = current_quantity - quantity
        if new_quantity == 0:
            del self._stock[normalized_product_id]
        else:
            self._stock[normalized_product_id] = new_quantity

        return InventoryItem(product_id=normalized_product_id, quantity=new_quantity)

    def list_items(self, query: str | None = None) -> list[InventoryItem]:
        normalized_query = normalize_product_query(query)
        return [
            InventoryItem(product_id=product_id, quantity=quantity)
            for product_id, quantity in sorted(self._stock.items())
            if normalized_query is None or normalized_query in product_id
        ]

    def get(self, product_id: str) -> InventoryItem | None:
        normalized_product_id = normalize_product_id(product_id)

        quantity = self._stock.get(normalized_product_id)
        if quantity is None:
            return None
        return InventoryItem(product_id=normalized_product_id, quantity=quantity)

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if not isinstance(quantity, int) or quantity <= 0:
            raise InvalidQuantityError("quantity must be a positive integer.")
