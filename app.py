from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

from inventory import (
    InsufficientStockError,
    InvalidQuantityError,
    InventoryItem,
    ProductNotFoundError,
)
from image_store import ImageStore, StoredImage
from product_ids import normalize_product_id
from sqlite_image_store import ImageRecord, SQLiteImageStore
from sqlite_inventory import SQLiteInventory


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BASE_DIR / "warehouse.db"
DEFAULT_IMAGE_DIR = BASE_DIR / "images"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="Warehouse Inventory API")
inventory = SQLiteInventory(DEFAULT_DB_PATH)
image_store = ImageStore(DEFAULT_IMAGE_DIR)
image_metadata_store = SQLiteImageStore(DEFAULT_DB_PATH)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class StockChangeRequest(BaseModel):
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)


class InventoryItemResponse(BaseModel):
    product_id: str
    quantity: int


class ScanPayload(BaseModel):
    action: Literal["add", "remove"]
    product_id: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    source: str = Field(default="scanner", min_length=1)
    raw_code: str | None = None


class ScanResultResponse(BaseModel):
    action: str
    source: str
    raw_code: str | None
    item: InventoryItemResponse


class ImageResponse(BaseModel):
    id: int
    product_id: str
    filename: str
    relative_path: str
    content_type: str | None
    size_bytes: int
    uploaded_at: str
    is_primary: bool


class SetPrimaryImageRequest(BaseModel):
    image_id: int = Field(..., gt=0)


class ProductDetailResponse(BaseModel):
    product_id: str
    quantity: int
    primary_image: ImageResponse | None
    images: list[ImageResponse]


def _to_response(item: InventoryItem) -> InventoryItemResponse:
    return InventoryItemResponse(product_id=item.product_id, quantity=item.quantity)


def _to_image_response(image: ImageRecord) -> ImageResponse:
    return ImageResponse(
        id=image.id,
        product_id=image.product_id,
        filename=image.filename,
        relative_path=image.relative_path,
        content_type=image.content_type,
        size_bytes=image.size_bytes,
        uploaded_at=image.uploaded_at,
        is_primary=image.is_primary,
    )


def _apply_stock_change(action: str, product_id: str, quantity: int) -> InventoryItem:
    try:
        if action == "add":
            return inventory.add(product_id, quantity)
        if action == "remove":
            return inventory.remove(product_id, quantity)
        raise HTTPException(status_code=400, detail="Unsupported action.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except InvalidQuantityError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ProductNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InsufficientStockError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def frontend_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/items", response_model=list[InventoryItemResponse])
def list_items(query: str | None = Query(default=None)) -> list[InventoryItemResponse]:
    try:
        return [_to_response(item) for item in inventory.list_items(query=query)]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/items/{product_id}", response_model=InventoryItemResponse)
def get_item(product_id: str) -> InventoryItemResponse:
    item = inventory.get(product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found.")
    return _to_response(item)


@app.get("/products/{product_id}", response_model=ProductDetailResponse)
def get_product_detail(product_id: str) -> ProductDetailResponse:
    item = inventory.get(product_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Product not found.")

    images = image_metadata_store.list_images(product_id)
    image_responses = [_to_image_response(image) for image in images]
    primary_image = next((image for image in image_responses if image.is_primary), None)

    return ProductDetailResponse(
        product_id=item.product_id,
        quantity=item.quantity,
        primary_image=primary_image,
        images=image_responses,
    )


@app.post("/items/add", response_model=InventoryItemResponse)
def add_item(payload: StockChangeRequest) -> InventoryItemResponse:
    item = _apply_stock_change("add", payload.product_id, payload.quantity)
    return _to_response(item)


@app.post("/items/remove", response_model=InventoryItemResponse)
def remove_item(payload: StockChangeRequest) -> InventoryItemResponse:
    item = _apply_stock_change("remove", payload.product_id, payload.quantity)
    return _to_response(item)


@app.post("/scan", response_model=ScanResultResponse)
def scan_item(payload: ScanPayload) -> ScanResultResponse:
    item = _apply_stock_change(payload.action, payload.product_id, payload.quantity)
    return ScanResultResponse(
        action=payload.action,
        source=payload.source,
        raw_code=payload.raw_code,
        item=_to_response(item),
    )


# 最大允许上传文件大小：10MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024


@app.post("/images", response_model=ImageResponse)
async def upload_image(
    product_id: str = Form(...),
    image: UploadFile = File(...),
) -> ImageResponse:
    file_content = None
    try:
        # 先读取文件内容到内存，避免在数据库操作前占用文件流
        file_content = await image.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"读取文件失败: {exc}") from exc
    finally:
        await image.close()

    if not file_content:
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 检查文件大小限制
    if len(file_content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"文件大小超过限制，最大允许 {MAX_IMAGE_SIZE // 1024 // 1024}MB"
        )

    # 先生成文件名和路径信息（不实际保存文件）
    from io import BytesIO
    from datetime import UTC, datetime
    from uuid import uuid4
    from pathlib import Path
    from product_ids import normalize_product_id

    normalized_product_id = normalize_product_id(product_id)
    suffix = Path(image.filename or "").suffix.lower() if image.filename else ""
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    filename = f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid4().hex}{suffix}"
    relative_path = f"{normalized_product_id}/{filename}"

    try:
        # 先保存元数据到数据库
        image_record = image_metadata_store.add_image(
            product_id=normalized_product_id,
            filename=filename,
            relative_path=relative_path,
            content_type=image.content_type,
            size_bytes=len(file_content),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        # 再保存文件到磁盘
        image_store.save_bytes(
            relative_path=relative_path,
            content=file_content,
        )
    except Exception as exc:
        # 文件保存失败，尝试删除已创建的元数据记录
        try:
            image_metadata_store.delete_image(normalized_product_id, image_record.id)
        except Exception:
            pass  # 忽略清理失败的错误
        raise HTTPException(status_code=500, detail=f"保存文件失败: {exc}") from exc

    return _to_image_response(image_record)


@app.get("/images/{product_id}", response_model=list[ImageResponse])
def list_product_images(product_id: str) -> list[ImageResponse]:
    try:
        images = image_metadata_store.list_images(product_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return [_to_image_response(image) for image in images]


@app.post("/images/{product_id}/primary", response_model=ImageResponse)
def set_primary_image(product_id: str, payload: SetPrimaryImageRequest) -> ImageResponse:
    try:
        image = image_metadata_store.set_primary(product_id, payload.image_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_image_response(image)


@app.delete("/images/{product_id}/{image_id}", response_model=ImageResponse)
def delete_image(product_id: str, image_id: int) -> ImageResponse:
    try:
        deleted_image = image_metadata_store.delete_image(product_id, image_id)
        image_store.delete(deleted_image.relative_path)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return _to_image_response(deleted_image)
