# Warehouse Tool

A small warehouse management practice project built with a low-uncertainty, layered approach.

The current goal is not to build everything at once. The goal is to keep each layer independently testable and easy to extend:

- core inventory rules first
- SQLite persistence next
- FastAPI API layer after that
- frontend and AI-related features only on top of stable backend behavior

## Current Milestone

This project is now at a presentable prototype milestone.

Presentation helpers:

- [SHOWCASE.md](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/SHOWCASE.md)
- [DEMO_SCRIPT.md](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/DEMO_SCRIPT.md)

Working today:

- add stock
- remove stock
- list stock
- scan JSON submission
- upload product images
- set a primary image
- delete product images
- aggregate product detail view
- lightweight web UI
- batch scan runner in the UI

## Architecture

The code is intentionally split into small layers.

- [inventory.py](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/inventory.py): in-memory inventory core
- [sqlite_inventory.py](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/sqlite_inventory.py): SQLite-backed inventory implementation
- [image_store.py](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/image_store.py): filesystem image storage
- [sqlite_image_store.py](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/sqlite_image_store.py): SQLite image metadata storage
- [app.py](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/app.py): FastAPI routes and aggregate endpoints
- [static/index.html](/C:/Users/amwor/Documents/codex_pj/warehouse_pj/static/index.html): frontend console

Design principles used here:

- AI handles perception later, not business decisions
- each step should be testable on its own
- avoid cross-module mega-tasks
- keep API routes thin and push behavior into reusable logic

## Project Features

### Inventory

- `POST /items/add`
- `POST /items/remove`
- `GET /items`
- `GET /items/{product_id}`

Behavior:

- adding the same `product_id` accumulates quantity
- removing stock validates product existence
- removing stock validates sufficient quantity

### Product Detail

- `GET /products/{product_id}`

Returns:

- inventory quantity
- primary image
- image list

### Scan Input

- `POST /scan`

Accepts explicit action-based scan payloads such as:

```json
{
  "action": "add",
  "product_id": "SKU-001",
  "quantity": 3,
  "source": "scanner",
  "raw_code": "{\"product_id\":\"SKU-001\",\"quantity\":3}"
}
```

### Image Management

- `POST /images`
- `GET /images/{product_id}`
- `POST /images/{product_id}/primary`
- `DELETE /images/{product_id}/{image_id}`

Behavior:

- image files are stored on disk
- image metadata is stored in SQLite
- first image becomes primary automatically
- deleting the primary image promotes the next image if available

### Frontend Console

Available at:

- `GET /`

Current UI supports:

- product lookup
- standard add/remove stock
- scan JSON parsing and submission
- image upload
- primary image switching
- image deletion
- inventory filtering
- quick product selection from inventory list
- recent activity view
- batch scan runner
- batch result copy

## How To Run

### 1. Install dependencies

```powershell
& "C:\Users\amwor\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r "C:\Users\amwor\Documents\codex_pj\warehouse_pj\requirements.txt"
```

### 2. Run tests

```powershell
& "C:\Users\amwor\AppData\Local\Programs\Python\Python312\python.exe" -m unittest discover -s "C:\Users\amwor\Documents\codex_pj\warehouse_pj\tests" -v
```

### 3. Start the server

```powershell
& "C:\Users\amwor\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn app:app --host 127.0.0.1 --port 8001
```

Then open:

- [http://127.0.0.1:8001/](http://127.0.0.1:8001/)
- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

## Test Status

Current automated coverage includes:

- in-memory inventory logic
- SQLite inventory logic
- FastAPI API flows
- image management flows
- aggregate product detail endpoint
- frontend entrypoint smoke check

Current suite:

- `33` tests passing

## Suggested Demo Flow

If you want to show this project to someone, this flow works well:

1. Open the web UI
2. Add stock for a new SKU
3. Upload one or two images
4. Set one image as primary
5. Run a batch scan with mixed add/remove lines
6. Open the product detail view
7. Copy batch results

That sequence shows inventory, images, aggregate APIs, and the frontend in one short demo.

## Why This Project Structure Works

This project is intentionally not starting with AI features.

That makes the system easier to reason about:

- inventory decisions stay deterministic
- persistence can be verified independently
- API behavior is easy to test
- UI work can move faster on top of stable endpoints
- future AI recognition can plug into an already-defined input path

## Next Ideas

Good next steps from here:

- polish the README demo screenshots
- add frontend automated tests
- add config management for database path and image directory
- add product deletion or archiving rules
- add image preview thumbnails in the UI
- add import/export for inventory snapshots
- add AI-assisted product recognition as an input helper, not a decision maker
