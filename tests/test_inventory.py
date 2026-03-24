import unittest

from inventory import (
    InsufficientStockError,
    Inventory,
    InventoryItem,
    InvalidQuantityError,
    ProductNotFoundError,
)


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = Inventory()

    def test_add_new_product(self) -> None:
        item = self.inventory.add("SKU-001", 10)

        self.assertEqual(item, InventoryItem(product_id="SKU-001", quantity=10))

    def test_add_existing_product_accumulates_quantity(self) -> None:
        self.inventory.add("SKU-001", 10)

        item = self.inventory.add("SKU-001", 5)

        self.assertEqual(item.quantity, 15)
        self.assertEqual(self.inventory.get("SKU-001"), item)

    def test_add_existing_product_is_case_insensitive(self) -> None:
        self.inventory.add("sku-001", 2)

        item = self.inventory.add("SKU-001", 3)

        self.assertEqual(item, InventoryItem(product_id="SKU-001", quantity=5))
        self.assertEqual(self.inventory.get("sKu-001"), item)

    def test_remove_reduces_quantity(self) -> None:
        self.inventory.add("SKU-001", 10)

        item = self.inventory.remove("SKU-001", 4)

        self.assertEqual(item, InventoryItem(product_id="SKU-001", quantity=6))

    def test_remove_deletes_item_when_quantity_reaches_zero(self) -> None:
        self.inventory.add("SKU-001", 3)

        item = self.inventory.remove("SKU-001", 3)

        self.assertEqual(item.quantity, 0)
        self.assertIsNone(self.inventory.get("SKU-001"))
        self.assertEqual(self.inventory.list_items(), [])

    def test_remove_missing_product_raises_error(self) -> None:
        with self.assertRaises(ProductNotFoundError):
            self.inventory.remove("SKU-404", 1)

    def test_remove_more_than_available_raises_error(self) -> None:
        self.inventory.add("SKU-001", 2)

        with self.assertRaises(InsufficientStockError):
            self.inventory.remove("SKU-001", 3)

    def test_invalid_quantity_raises_error(self) -> None:
        with self.assertRaises(InvalidQuantityError):
            self.inventory.add("SKU-001", 0)

        with self.assertRaises(InvalidQuantityError):
            self.inventory.remove("SKU-001", -1)

    def test_list_items_returns_sorted_snapshot(self) -> None:
        self.inventory.add("SKU-002", 1)
        self.inventory.add("SKU-001", 2)

        items = self.inventory.list_items()

        self.assertEqual(
            items,
            [
                InventoryItem(product_id="SKU-001", quantity=2),
                InventoryItem(product_id="SKU-002", quantity=1),
            ],
        )

    def test_list_items_can_filter_by_case_insensitive_query(self) -> None:
        self.inventory.add("sku-001", 2)
        self.inventory.add("BOX-002", 1)

        items = self.inventory.list_items(query="sku")

        self.assertEqual(items, [InventoryItem(product_id="SKU-001", quantity=2)])


if __name__ == "__main__":
    unittest.main()
