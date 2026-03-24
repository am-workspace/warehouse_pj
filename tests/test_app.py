import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import app as app_module
from image_store import ImageStore
from sqlite_image_store import SQLiteImageStore
from sqlite_inventory import SQLiteInventory


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "api-test.db"
        self.image_dir = Path(self.temp_dir.name) / "images"
        app_module.inventory = SQLiteInventory(self.db_path)
        app_module.image_store = ImageStore(self.image_dir)
        app_module.image_metadata_store = SQLiteImageStore(self.db_path)
        self.client = TestClient(app_module.app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_health_check(self) -> None:
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_frontend_index(self) -> None:
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("仓库管理系统", response.text)
        self.assertIn("搜索产品", response.text)
        self.assertIn("确认提交", response.text)
        self.assertIn("上传图片", response.text)

    def test_add_and_get_item(self) -> None:
        add_response = self.client.post(
            "/items/add",
            json={"product_id": "SKU-001", "quantity": 5},
        )
        get_response = self.client.get("/items/SKU-001")

        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(add_response.json(), {"product_id": "SKU-001", "quantity": 5})
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json(), {"product_id": "SKU-001", "quantity": 5})

    def test_add_and_get_item_is_case_insensitive(self) -> None:
        add_response = self.client.post(
            "/items/add",
            json={"product_id": "sku-001", "quantity": 2},
        )
        second_add_response = self.client.post(
            "/items/add",
            json={"product_id": "SKU-001", "quantity": 3},
        )
        get_response = self.client.get("/items/SkU-001")

        self.assertEqual(add_response.status_code, 200)
        self.assertEqual(second_add_response.status_code, 200)
        self.assertEqual(second_add_response.json(), {"product_id": "SKU-001", "quantity": 5})
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json(), {"product_id": "SKU-001", "quantity": 5})

    def test_remove_item(self) -> None:
        self.client.post("/items/add", json={"product_id": "SKU-001", "quantity": 5})

        response = self.client.post(
            "/items/remove",
            json={"product_id": "SKU-001", "quantity": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"product_id": "SKU-001", "quantity": 3})

    def test_remove_missing_item_returns_404(self) -> None:
        response = self.client.post(
            "/items/remove",
            json={"product_id": "SKU-404", "quantity": 1},
        )

        self.assertEqual(response.status_code, 404)

    def test_remove_too_much_returns_409(self) -> None:
        self.client.post("/items/add", json={"product_id": "SKU-001", "quantity": 1})

        response = self.client.post(
            "/items/remove",
            json={"product_id": "SKU-001", "quantity": 2},
        )

        self.assertEqual(response.status_code, 409)

    def test_get_product_detail(self) -> None:
        self.client.post("/items/add", json={"product_id": "SKU-DETAIL-001", "quantity": 5})
        first = self.client.post(
            "/images",
            data={"product_id": "SKU-DETAIL-001"},
            files={"image": ("first.png", b"one", "image/png")},
        ).json()
        second = self.client.post(
            "/images",
            data={"product_id": "SKU-DETAIL-001"},
            files={"image": ("second.png", b"two", "image/png")},
        ).json()
        self.client.post(
            "/images/SKU-DETAIL-001/primary",
            json={"image_id": second["id"]},
        )

        response = self.client.get("/products/SKU-DETAIL-001")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["product_id"], "SKU-DETAIL-001")
        self.assertEqual(payload["quantity"], 5)
        self.assertEqual(payload["primary_image"]["id"], second["id"])
        self.assertEqual(len(payload["images"]), 2)
        self.assertEqual({image["id"] for image in payload["images"]}, {first["id"], second["id"]})

    def test_get_product_detail_returns_404_for_missing_item(self) -> None:
        response = self.client.get("/products/SKU-MISSING")

        self.assertEqual(response.status_code, 404)

    def test_list_items(self) -> None:
        self.client.post("/items/add", json={"product_id": "SKU-002", "quantity": 1})
        self.client.post("/items/add", json={"product_id": "SKU-001", "quantity": 2})

        response = self.client.get("/items")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"product_id": "SKU-001", "quantity": 2},
                {"product_id": "SKU-002", "quantity": 1},
            ],
        )

    def test_list_items_supports_case_insensitive_query(self) -> None:
        self.client.post("/items/add", json={"product_id": "sku-002", "quantity": 1})
        self.client.post("/items/add", json={"product_id": "SKU-001", "quantity": 2})

        response = self.client.get("/items", params={"query": "sku-00"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {"product_id": "SKU-001", "quantity": 2},
                {"product_id": "SKU-002", "quantity": 1},
            ],
        )

    def test_scan_add_item(self) -> None:
        response = self.client.post(
            "/scan",
            json={
                "action": "add",
                "product_id": "SKU-SCAN-001",
                "quantity": 3,
                "source": "barcode",
                "raw_code": '{"product_id":"SKU-SCAN-001","quantity":3}',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "action": "add",
                "source": "barcode",
                "raw_code": '{"product_id":"SKU-SCAN-001","quantity":3}',
                "item": {"product_id": "SKU-SCAN-001", "quantity": 3},
            },
        )

    def test_scan_remove_item(self) -> None:
        self.client.post("/items/add", json={"product_id": "SKU-SCAN-001", "quantity": 5})

        response = self.client.post(
            "/scan",
            json={
                "action": "remove",
                "product_id": "SKU-SCAN-001",
                "quantity": 2,
                "source": "barcode",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "action": "remove",
                "source": "barcode",
                "raw_code": None,
                "item": {"product_id": "SKU-SCAN-001", "quantity": 3},
            },
        )

    def test_upload_image(self) -> None:
        response = self.client.post(
            "/images",
            data={"product_id": "sku-img-001"},
            files={"image": ("sample.png", b"fake-image-bytes", "image/png")},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(payload["id"], 0)
        self.assertEqual(payload["product_id"], "SKU-IMG-001")
        self.assertEqual(payload["content_type"], "image/png")
        self.assertEqual(payload["size_bytes"], len(b"fake-image-bytes"))
        self.assertIsInstance(payload["uploaded_at"], str)
        self.assertTrue(payload["is_primary"])
        self.assertTrue(payload["filename"].endswith(".png"))

    def test_list_images(self) -> None:
        self.client.post(
            "/images",
            data={"product_id": "sku-img-001"},
            files={"image": ("first.jpg", b"one", "image/jpeg")},
        )
        self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-001"},
            files={"image": ("second.png", b"two", "image/png")},
        )

        response = self.client.get("/images/sKu-ImG-001")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        self.assertEqual({item["product_id"] for item in payload}, {"SKU-IMG-001"})
        self.assertEqual(sum(1 for item in payload if item["is_primary"]), 1)

    def test_set_primary_image(self) -> None:
        first = self.client.post(
            "/images",
            data={"product_id": "sku-img-001"},
            files={"image": ("first.jpg", b"one", "image/jpeg")},
        ).json()
        second = self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-001"},
            files={"image": ("second.png", b"two", "image/png")},
        ).json()

        response = self.client.post(
            "/images/sKu-ImG-001/primary",
            json={"image_id": second["id"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], second["id"])
        self.assertTrue(response.json()["is_primary"])

        list_response = self.client.get("/images/SKU-IMG-001")
        images = list_response.json()
        self.assertEqual(images[0]["id"], second["id"])
        self.assertTrue(images[0]["is_primary"])
        self.assertFalse(any(item["id"] == first["id"] and item["is_primary"] for item in images))

    def test_delete_image(self) -> None:
        uploaded = self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-DEL"},
            files={"image": ("sample.png", b"delete-me", "image/png")},
        ).json()

        response = self.client.delete(f"/images/SKU-IMG-DEL/{uploaded['id']}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], uploaded["id"])

        list_response = self.client.get("/images/SKU-IMG-DEL")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json(), [])

    def test_delete_primary_image_promotes_next_image(self) -> None:
        first = self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-DEL"},
            files={"image": ("first.png", b"one", "image/png")},
        ).json()
        second = self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-DEL"},
            files={"image": ("second.png", b"two", "image/png")},
        ).json()

        response = self.client.delete(f"/images/SKU-IMG-DEL/{first['id']}")

        self.assertEqual(response.status_code, 200)
        list_response = self.client.get("/images/SKU-IMG-DEL")
        images = list_response.json()
        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]["id"], second["id"])
        self.assertTrue(images[0]["is_primary"])

    def test_upload_image_rejects_unsupported_file_type(self) -> None:
        response = self.client.post(
            "/images",
            data={"product_id": "SKU-IMG-001"},
            files={"image": ("notes.txt", b"text", "text/plain")},
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
