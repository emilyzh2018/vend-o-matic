# Unit tests for Vend-O-Matic.

# Uses Flask's built-in test client so no external test dependencies needed.
# Covers all endpoints, status codes, and possible edge cases.
# Also tests ambiguous cases where the spec did not explicitly specify outcomes.

import unittest
from app import app, machine
from machine import VendingMachine, PurchaseResult


class CoinTests(unittest.TestCase):
    #Tests for inserting and refunding coins

    def setUp(self):
        self.client = app.test_client()
        machine.__init__()

    def test_insert_single_coin(self):
        resp = self.client.put("/", json={"coin": 1})
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers["X-Coins"], "1")

    def test_insert_multiple_coins(self):
        self.client.put("/", json={"coin": 1})
        resp = self.client.put("/", json={"coin": 1})
        self.assertEqual(resp.headers["X-Coins"], "2")

    def test_refund_returns_all_coins(self):
        self.client.put("/", json={"coin": 1})
        self.client.put("/", json={"coin": 1})
        resp = self.client.delete("/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers["X-Coins"], "2")

    def test_refund_with_no_coins(self):
        resp = self.client.delete("/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(resp.headers["X-Coins"], "0")

    def test_coins_reset_after_refund(self):
        """After refund, inserting a coin should show count of 1."""
        self.client.put("/", json={"coin": 1})
        self.client.delete("/")
        resp = self.client.put("/", json={"coin": 1})
        self.assertEqual(resp.headers["X-Coins"], "1")


class InventoryTests(unittest.TestCase):
    #Tests for inventory lookup endpoints. 

    def setUp(self):
        self.client = app.test_client()
        machine.__init__()

    def test_get_full_inventory(self):
        resp = self.client.get("/inventory")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), [5, 5, 5])

    def test_get_each_item(self):
        for item_id in [1, 2, 3]:
            resp = self.client.get(f"/inventory/{item_id}")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json(), 5)

    def test_get_invalid_item_returns_404(self):
        #what if we try to get a non existant item, 404 should be right status code. 
        resp = self.client.get("/inventory/99")
        self.assertEqual(resp.status_code, 404)


class PurchaseTests(unittest.TestCase):
    # Tests for the general purchase flow. 

    def setUp(self):
        self.client = app.test_client()
        machine.__init__()

    def _insert_coins(self, n):
        for _ in range(n):
            self.client.put("/", json={"coin": 1})

    def test_successful_purchase(self):
        self._insert_coins(2)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"quantity": 1})
        self.assertEqual(resp.headers["X-Coins"], "0")
        self.assertEqual(resp.headers["X-Inventory-Remaining"], "4")

    def test_purchase_returns_change(self):
        # Insert 3 coins, purchase costs 2 , expect 1 coin back. 
        self._insert_coins(3)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers["X-Coins"], "1")
    
    def test_overpay_still_dispenses_one(self):
       #Spec constraint 4: only one beverage per transaction. 
        self._insert_coins(10)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.get_json(), {"quantity": 1})
        self.assertEqual(resp.headers["X-Coins"], "8")
        self.assertEqual(resp.headers["X-Inventory-Remaining"], "4")

    def test_purchase_with_exact_coins(self):
        self._insert_coins(2)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.headers["X-Coins"], "0")

    def test_insufficient_funds_one_coin(self):
        self._insert_coins(1)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers["X-Coins"], "1")

    def test_insufficient_funds_zero_coins(self):
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.headers["X-Coins"], "0")

    def test_insufficient_funds_keeps_coins(self):
        # After a 403, coins should still be in the machine. 
        self._insert_coins(1)
        self.client.put("/inventory/1")  # 403
        self._insert_coins(1)  # now at 2 total
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 200)

    def test_out_of_stock_refunds_coins(self):
        #Buy all 5 of item 1, then try again , coins should be refunded.
        for _ in range(5):
            self._insert_coins(2)
            self.client.put("/inventory/1")

        self._insert_coins(2)
        resp = self.client.put("/inventory/1")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers["X-Coins"], "2")

    def test_inventory_decrements(self):
        self._insert_coins(2)
        self.client.put("/inventory/2")
        resp = self.client.get("/inventory/2")
        self.assertEqual(resp.get_json(), 4)

    def test_full_inventory_reflects_purchases(self):
        # GET /inventory should show updated counts after purchases. 
        self._insert_coins(2)
        self.client.put("/inventory/1")
        resp = self.client.get("/inventory")
        self.assertEqual(resp.get_json(), [4, 5, 5])

    def test_purchase_invalid_item(self):
        self._insert_coins(2)
        resp = self.client.put("/inventory/99")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.headers["X-Coins"], "2")
        # Verify coins were actually refunded, not just reported
        resp = self.client.put("/", json={"coin": 1})
        self.assertEqual(resp.headers["X-Coins"], "1")

    def test_coins_reset_after_successful_purchase(self):
        self._insert_coins(2)
        self.client.put("/inventory/1")
        resp = self.client.put("/", json={"coin": 1})
        self.assertEqual(resp.headers["X-Coins"], "1")

    def test_buy_all_items_across_beverages(self):
        for item_id in [1, 2, 3]:
            for _ in range(5):
                self._insert_coins(2)
                resp = self.client.put(f"/inventory/{item_id}")
                self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/inventory")
        self.assertEqual(resp.get_json(), [0, 0, 0])


class VendingMachineUnitTests(unittest.TestCase):
    def setUp(self):
        self.vm = VendingMachine()

    def test_initial_state(self):
        self.assertEqual(self.vm.coins, 0)
        self.assertEqual(self.vm.inventory, [5, 5, 5])

    def test_insert_coin_increments(self):
        self.assertEqual(self.vm.insert_coin(), 1)
        self.assertEqual(self.vm.insert_coin(), 2)

    def test_refund_clears_coins(self):
        self.vm.insert_coin()
        self.vm.insert_coin()
        self.assertEqual(self.vm.refund(), 2)
        self.assertEqual(self.vm.coins, 0)

    def test_get_inventory_returns_copy(self):
        # Mutating the returned list should not affect the machine's state.
        inv = self.vm.get_inventory()
        inv[0] = 999
        self.assertEqual(self.vm.inventory[0], 5)

    def test_purchase_check_order(self):
        # Insufficient funds should be checked before out-of-stock
        for x in range(5):
            self.vm.coins = 2
            self.vm.purchase(1)
        # Now try with 0 coins for non existent item, should get OUT_OF_STOCK
        result, _ = self.vm.purchase(99)
        self.assertEqual(result, PurchaseResult.OUT_OF_STOCK)


if __name__ == "__main__":
    unittest.main()
