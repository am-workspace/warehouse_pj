from __future__ import annotations

import sqlite3
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from product_ids import normalize_product_id


@dataclass(frozen=True)
class ImageRecord:
    id: int
    product_id: str
    filename: str
    relative_path: str
    content_type: str | None
    size_bytes: int
    uploaded_at: str
    is_primary: bool


class SQLiteImageStore:
    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._initialize_schema()

    def add_image(
        self,
        product_id: str,
        filename: str,
        relative_path: str,
        content_type: str | None,
        size_bytes: int,
    ) -> ImageRecord:
        normalized_product_id = normalize_product_id(product_id)

        with closing(sqlite3.connect(self._db_path)) as connection:
            has_primary = connection.execute(
                "SELECT 1 FROM product_images WHERE product_id = ? AND is_primary = 1 LIMIT 1",
                (normalized_product_id,),
            ).fetchone()
            is_primary = has_primary is None

            cursor = connection.execute(
                """
                INSERT INTO product_images (
                    product_id,
                    filename,
                    relative_path,
                    content_type,
                    size_bytes,
                    uploaded_at,
                    is_primary
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                """,
                (
                    normalized_product_id,
                    filename,
                    relative_path,
                    content_type,
                    size_bytes,
                    1 if is_primary else 0,
                ),
            )
            connection.commit()
            image_id = int(cursor.lastrowid)

        return self.get_image(image_id)

    def list_images(self, product_id: str) -> list[ImageRecord]:
        normalized_product_id = normalize_product_id(product_id)

        with closing(sqlite3.connect(self._db_path)) as connection:
            rows = connection.execute(
                """
                SELECT id, product_id, filename, relative_path, content_type, size_bytes, uploaded_at, is_primary
                FROM product_images
                WHERE product_id = ?
                ORDER BY is_primary DESC, uploaded_at ASC, id ASC
                """,
                (normalized_product_id,),
            ).fetchall()

        return [self._row_to_record(row) for row in rows]

    def get_image(self, image_id: int) -> ImageRecord:
        with closing(sqlite3.connect(self._db_path)) as connection:
            row = connection.execute(
                """
                SELECT id, product_id, filename, relative_path, content_type, size_bytes, uploaded_at, is_primary
                FROM product_images
                WHERE id = ?
                """,
                (image_id,),
            ).fetchone()
        if row is None:
            raise ValueError("image not found.")
        return self._row_to_record(row)

    def set_primary(self, product_id: str, image_id: int) -> ImageRecord:
        normalized_product_id = normalize_product_id(product_id)

        with closing(sqlite3.connect(self._db_path)) as connection:
            row = connection.execute(
                "SELECT id FROM product_images WHERE id = ? AND product_id = ?",
                (image_id, normalized_product_id),
            ).fetchone()
            if row is None:
                raise ValueError("image not found.")

            connection.execute(
                "UPDATE product_images SET is_primary = 0 WHERE product_id = ?",
                (normalized_product_id,),
            )
            connection.execute(
                "UPDATE product_images SET is_primary = 1 WHERE id = ?",
                (image_id,),
            )
            connection.commit()

        return self.get_image(image_id)

    def delete_image(self, product_id: str, image_id: int) -> ImageRecord:
        normalized_product_id = normalize_product_id(product_id)

        with closing(sqlite3.connect(self._db_path)) as connection:
            row = connection.execute(
                """
                SELECT id, product_id, filename, relative_path, content_type, size_bytes, uploaded_at, is_primary
                FROM product_images
                WHERE id = ? AND product_id = ?
                """,
                (image_id, normalized_product_id),
            ).fetchone()
            if row is None:
                raise ValueError("image not found.")

            deleted_record = self._row_to_record(row)

            connection.execute(
                "DELETE FROM product_images WHERE id = ? AND product_id = ?",
                (image_id, normalized_product_id),
            )

            if deleted_record.is_primary:
                replacement = connection.execute(
                    """
                    SELECT id
                    FROM product_images
                    WHERE product_id = ?
                    ORDER BY uploaded_at ASC, id ASC
                    LIMIT 1
                    """,
                    (normalized_product_id,),
                ).fetchone()
                if replacement is not None:
                    connection.execute(
                        "UPDATE product_images SET is_primary = 1 WHERE id = ?",
                        (int(replacement[0]),),
                    )

            connection.commit()

        return deleted_record

    def _initialize_schema(self) -> None:
        with closing(sqlite3.connect(self._db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS product_images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    content_type TEXT,
                    size_bytes INTEGER NOT NULL CHECK (size_bytes >= 0),
                    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_primary INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1))
                )
                """
            )
            connection.commit()

    @staticmethod
    def _row_to_record(row: tuple) -> ImageRecord:
        return ImageRecord(
            id=int(row[0]),
            product_id=str(row[1]),
            filename=str(row[2]),
            relative_path=str(row[3]),
            content_type=row[4],
            size_bytes=int(row[5]),
            uploaded_at=str(row[6]),
            is_primary=bool(row[7]),
        )
