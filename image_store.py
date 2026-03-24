from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from product_ids import normalize_product_id


ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


@dataclass(frozen=True)
class StoredImage:
    product_id: str
    filename: str
    relative_path: str
    content_type: str | None
    size_bytes: int


class ImageStore:
    def __init__(self, base_dir: str | Path) -> None:
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        product_id: str,
        upload_filename: str | None,
        file_stream,
        content_type: str | None = None,
    ) -> StoredImage:
        normalized_product_id = normalize_product_id(product_id)
        suffix = self._normalize_suffix(upload_filename)

        product_dir = self._base_dir / normalized_product_id
        product_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex}{suffix}"
        target_path = product_dir / filename

        with target_path.open("wb") as output_file:
            shutil.copyfileobj(file_stream, output_file)

        size_bytes = target_path.stat().st_size
        relative_path = target_path.relative_to(self._base_dir).as_posix()
        return StoredImage(
            product_id=normalized_product_id,
            filename=filename,
            relative_path=relative_path,
            content_type=content_type,
            size_bytes=size_bytes,
        )

    def list_images(self, product_id: str) -> list[StoredImage]:
        normalized_product_id = normalize_product_id(product_id)

        product_dir = self._base_dir / normalized_product_id
        if not product_dir.exists():
            return []

        images: list[StoredImage] = []
        for path in sorted(product_dir.iterdir()):
            if path.is_file():
                images.append(
                    StoredImage(
                        product_id=normalized_product_id,
                        filename=path.name,
                        relative_path=path.relative_to(self._base_dir).as_posix(),
                        content_type=None,
                        size_bytes=path.stat().st_size,
                    )
                )
        return images

    def delete(self, relative_path: str) -> None:
        target_path = self._base_dir / Path(relative_path)
        if not target_path.exists():
            raise ValueError("image file not found.")

        target_path.unlink()

        product_dir = target_path.parent
        if product_dir.exists() and not any(product_dir.iterdir()):
            product_dir.rmdir()

    @staticmethod
    def _normalize_suffix(upload_filename: str | None) -> str:
        if not upload_filename:
            raise ValueError("image filename is required.")

        suffix = Path(upload_filename).suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError("unsupported image type.")
        return suffix
