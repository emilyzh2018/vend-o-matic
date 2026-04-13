# Flask app : HTTP layer over VendingMachine.

# Business logic lives in machine.py; this file only handles
# request parsing, response formatting, and status code selection.

from flask import Flask, jsonify, make_response
from machine import VendingMachine, PurchaseResult

app = Flask(__name__)
machine = VendingMachine()


@app.route("/", methods=["PUT"])
def insert_coin():
    # PUT: / Insert a quarter. Returns 204 with X-Coins header and # of coins accepted. 
    count = machine.insert_coin()
    response = make_response("", 204)
    response.headers["X-Coins"] = str(count)
    return response


@app.route("/", methods=["DELETE"])
def refund():
    # DELETE: / Cancel transaction, return all inserted coins. 
    refund_count = machine.refund()
    response = make_response("", 204)
    response.headers["X-Coins"] = str(refund_count)
    return response


@app.route("/inventory", methods=["GET"])
def get_inventory():
    # GET: /inventory Returns array of all remaining item quantities (int array).
    return jsonify(machine.get_inventory())


@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    # GET /inventory/:id Returns remaining quantity for a single item. 
    quantity = machine.get_item_quantity(item_id)
    if quantity is None:
        return make_response("", 404)
    return jsonify(quantity)


@app.route("/inventory/<int:item_id>", methods=["PUT"])
def purchase_item(item_id):
    """
    PUT /inventory/:id — Attempt to purchase an item.

    Status codes per spec:
        200 — Successful purchase
        403 — Insufficient funds (coins stay in machine)
        404 — Item out of stock or invalid (coins refunded)
    """
    result, data = machine.purchase(item_id)

    if result == PurchaseResult.SUCCESS:
        response = make_response(jsonify({"quantity": data["quantity"]}), 200)
        response.headers["X-Coins"] = str(data["coins"])
        response.headers["X-Inventory-Remaining"] = str(data["inventory_remaining"])
        return response

    if result == PurchaseResult.OUT_OF_STOCK:
        response = make_response("", 404)
        response.headers["X-Coins"] = str(data["coins"])
        return response

    # In case of insufficient funds to buy item
    response = make_response("", 403)
    response.headers["X-Coins"] = str(data["coins"])
    return response


if __name__ == "__main__":
    app.run(port=8000, debug=True)
    