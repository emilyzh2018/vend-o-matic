"""
Vending machine business logic file.
This is separated from the HTTP layer so the machine can be tested, reused,
or swapped to a different transport without touching business logic.
"""

from enum import Enum

#Outcome of a purchase attempt
class PurchaseResult(Enum):
    SUCCESS = "success"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    OUT_OF_STOCK = "out_of_stock"


# Models a beverage vending machine.

# Constraints from spec:
#   - Accepts only US quarters, one at a time.
#   - Purchase price for any item: 2 quarters.
#   - Inventory: 3 beverages, 5 of each initially.
#   - Dispenses 1 beverage per transaction.
#   - Returns unused quarters to user on transaction completion.
class VendingMachine:

    PRICE = 2          # quarters required per purchase
    NUM_ITEMS = 3      # number of distinct beverages
    INITIAL_STOCK = 5  # starting quantity per beverage

    def __init__(self):
        self.coins = 0
        self.inventory = [self.INITIAL_STOCK] * self.NUM_ITEMS

    def valid_item(self, item_id):
        # Check if an item ID (1-indexed) is within range.
        return 1 <= item_id <= len(self.inventory)

    def index(self, item_id):
        # Convert 1-indexed item ID to 0-indexed list position.
        return item_id - 1

    def insert_coin(self):
        # Take one quarter & returns updated coin count.
        self.coins += 1
        return self.coins

    def refund(self):
        # Return all inserted coins and resets the coint count. 
        refund = self.coins
        self.coins = 0
        return refund

    def get_inventory(self):
        # Return list of remaining quantities for all items. 
        return list(self.inventory)

    def get_item_quantity(self, item_id):
        # Return remaining quantity for a single item.
        # Returns None if item_id is out of range (or non existent).
        if not self.valid_item(item_id):
            return None
        return self.inventory[self.index(item_id)]

    def purchase(self, item_id):
        """
        Attempt to purchase an item.

        Order of checks matters:
            1. Invalid item  -> OUT_OF_STOCK  (resource doesn't exist)
            2. Insufficient funds -> INSUFFICIENT_FUNDS (keep coins, customer still inserting)
            3. Out of stock  -> OUT_OF_STOCK  (refund coins, transaction over)
            4. Success       -> SUCCESS       (dispense item, return change)

        Returns (PurchaseResult, dict) where dict contains:
            - coins: coins to return/show to customer
            - quantity: number of items vended (0 or 1 since at most can vend 1 @ a time)
            - inventory_remaining: stock left for an item
        """
        # 1. Invalid item ID
        if not self.valid_item(item_id):
            change = self.coins
            self.coins = 0
            return PurchaseResult.OUT_OF_STOCK, {
                "coins": change,
                "quantity": 0,
                "inventory_remaining": 0,
            }
        index = self.index(item_id)

        # 2. Not enough coins — 403, coins stay in machine
        if self.coins < self.PRICE:
            return PurchaseResult.INSUFFICIENT_FUNDS, {
                "coins": self.coins,
                "quantity": 0,
                "inventory_remaining": self.inventory[index],
            }

        # 3. Item out of stock — 404, refund all coins
        if self.inventory[index] <= 0:
            change = self.coins
            self.coins = 0
            return PurchaseResult.OUT_OF_STOCK, {
                "coins": change,
                "quantity": 0,
                "inventory_remaining": 0,
            }

        # 4. Successful purchase
        self.inventory[index] -= 1
        change = self.coins - self.PRICE
        #Upon transaction completion, any unused quarters must be dispensed back to the customer
        self.coins = 0 #Future transaction must start fresh 

        return PurchaseResult.SUCCESS, {
            "coins": change,
            "quantity": 1,
            "inventory_remaining": self.inventory[index],
        }
        