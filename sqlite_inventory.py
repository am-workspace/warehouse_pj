from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from inventory import (
    InsufficientStockError,
    InvalidQuantityError,
    InventoryItem,
    ProductNotFoundError,
)
from product_ids import normalize_product_id, normalize_product_query


class SQLiteInventory:
    """SQLite-backed inventory with the same small API as the in-memory version."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._initialize_schema()

    def add(self, product_id: str, quantity: int) -> InventoryItem:
        normalized_product_id = normalize_product_id(product_id)
        self._validate_quantity(quantity)

        with closing(sqlite3.connect(self._db_path)) as connection:
            current_quantity = self._fetch_quantity(connection, normalized_product_id)
            new_quantity = current_quantity + quantity

            connection.execute(
                """
                INSERT INTO inventory_items (product_id, quantity)
                VALUES (?, ?)
                ON CONFLICT(product_id)
                DO UPDATE SET quantity = excluded.quantity
                """,
                (normalized_product_id, new_quantity),
            )
            connection.commit()

        return InventoryItem(product_id=normalized_product_id, quantity=new_quantity)

    def remove(self, product_id: str, quantity: int) -> InventoryItem:
        normalized_product_id = normalize_product_id(product_id)
        self._validate_quantity(quantity)

        with closing(sqlite3.connect(self._db_path)) as connection:
            current_quantity = self._fetch_quantity(connection, normalized_product_id)
            if current_quantity == 0:
                raise ProductNotFoundError(f"Product '{normalized_product_id}' not found.")

            if quantity > current_quantity:
                raise InsufficientStockError(
                    f"Cannot remove {quantity} units from '{normalized_product_id}'; only {current_quantity} available."
                )

            new_quantity = current_quantity - quantity
            if new_quantity == 0:
                connection.execute(
                    "DELETE FROM inventory_items WHERE product_id = ?",
                    (normalized_product_id,),
                )
            else:
                connection.execute(
                    "UPDATE inventory_items SET quantity = ? WHERE product_id = ?",
                    (new_quantity, normalized_product_id),
                )
            connection.commit()

        return InventoryItem(product_id=normalized_product_id, quantity=new_quantity)

    def list_items(self, query: str | None = None) -> list[InventoryItem]:
        normalized_query = normalize_product_query(query)

        with closing(sqlite3.connect(self._db_path)) as connection:
            if normalized_query is None:
                rows = connection.execute(
                    "SELECT product_id, quantity FROM inventory_items ORDER BY product_id"
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT product_id, quantity
                    FROM inventory_items
                    WHERE product_id LIKE ?
                    ORDER BY product_id
                    """,
                    (f"%{normalized_query}%",),
                ).fetchall()

        return [InventoryItem(product_id=row[0], quantity=row[1]) for row in rows]

    def get(self, product_id: str) -> InventoryItem | None:
        normalized_product_id = normalize_product_id(product_id)

        with closing(sqlite3.connect(self._db_path)) as connection:
            quantity = self._fetch_quantity(connection, normalized_product_id)

        if quantity == 0:
            return None
        return InventoryItem(product_id=normalized_product_id, quantity=quantity)

    def _initialize_schema(self) -> None:
        with closing(sqlite3.connect(self._db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS inventory_items (
                    product_id TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL CHECK (quantity >= 0)
                )
                """
            )
            connection.commit()

    @staticmethod
    def _fetch_quantity(connection: sqlite3.Connection, product_id: str) -> int:
        row = connection.execute(
            "SELECT quantity FROM inventory_items WHERE product_id = ?",
            (product_id,),
        ).fetchone()
        if row is None:
            return 0
        return int(row[0])

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if not isinstance(quantity, int) or quantity <= 0:
            raise InvalidQuantityError("quantity must be a positive integer.")
