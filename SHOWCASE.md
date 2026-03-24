# Showcase Notes

## One-Line Pitch

Warehouse Tool is a small warehouse management prototype that prioritizes deterministic business rules, testable layers, and incremental delivery over feature sprawl.

## What Makes This Worth Showing

- It is not just a CRUD demo. The project has a clear development strategy.
- Core inventory logic was built before persistence, API, or frontend work.
- The API layer stays thin and reuses stable logic instead of duplicating rules.
- Image handling is already split into file storage plus SQLite metadata.
- The UI is small, but it already exercises real workflows end-to-end.

## What Works Today

- Add stock
- Remove stock
- List current inventory
- Submit scan JSON
- Upload product images
- Set a primary image
- Delete images
- View aggregate product detail
- Run batch scans from the UI
- Copy batch scan results

## Why The Architecture Matters

This project was built with a low-uncertainty flow:

1. core logic
2. SQLite persistence
3. FastAPI API
4. frontend on top of stable endpoints
5. AI features later

That matters because:

- rules are easier to verify
- each layer can be tested independently
- future changes have clearer boundaries
- AI can be added as an input helper instead of a source of business decisions

## Good Demo Sequence

1. Open the UI at [http://127.0.0.1:8001/](http://127.0.0.1:8001/)
2. Create stock for a fresh SKU
3. Upload two product images
4. Set one image as primary
5. Run a batch scan with mixed add and remove operations
6. Open the product detail view
7. Copy the batch results summary

## Key Talking Points

- "I intentionally did not start with AI features. I wanted a stable inventory core first."
- "The same inventory behavior works in memory and in SQLite."
- "The API mostly adapts requests to already-tested logic."
- "The frontend is small, but it demonstrates the backend rather than mocking around it."
- "Image files and image metadata are managed separately, which will make later features easier."

## Current Quality Bar

- `33` automated tests passing
- backend layers separated by responsibility
- UI wired to real API endpoints
- presentable end-to-end workflow

## Best Next Steps After The Demo

- add screenshots to the README
- add frontend automated tests
- add config management
- add image previews
- add import/export
- add AI-assisted recognition as a helper layer
