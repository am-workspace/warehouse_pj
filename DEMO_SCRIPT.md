# Demo Script

## Short Version

"This is a small warehouse management prototype I built with a layered approach. I started from deterministic inventory rules, then added SQLite persistence, then a FastAPI backend, and only after that built the frontend. The result is a small but testable system that already supports stock changes, scan JSON input, image management, and a simple batch workflow."

## Two-Minute Walkthrough

1. Open the homepage at [http://127.0.0.1:8001/](http://127.0.0.1:8001/)

Say:

"The UI is intentionally simple. It is mainly here to exercise the backend I already stabilized."

2. Load or type a product ID

Say:

"The product detail panel is powered by a single aggregate endpoint, so the frontend does not have to stitch inventory and image data manually."

3. Add stock

Say:

"Adding the same product ID accumulates quantity. This behavior was implemented first in a pure in-memory version and then preserved in the SQLite-backed version."

4. Upload product images

Say:

"Files are stored on disk, but image metadata is stored in SQLite. That separation makes future image workflows easier."

5. Set a primary image

Say:

"Primary image selection is explicit, and deleting the primary image automatically promotes the next available one."

6. Run batch scan JSON

Say:

"The scan layer is input-oriented. It still calls the same backend rules for add and remove, so scanning does not bypass inventory validation."

7. Copy batch results

Say:

"This makes it easier to share a quick operation summary after a batch run."

8. Mention tests

Say:

"At this point the project has 33 passing tests covering the inventory logic, SQLite behavior, API flows, and image management."

## If You Need A 30-Second Summary

"This project is a warehouse management prototype focused on stable backend behavior first. It already supports stock changes, scan JSON submission, image management, batch operations, and a small frontend, all built on top of tested business logic." 
