# Vend-O-Matic

A REST API service for the Marigold take home assessment. The service supports
a beverage vending machine that is tested via HTTP.

## Setup

Requires **Python 3.8+** (tested on 3.12.6).
```bash
cd vend-o-matic

# Create the virtual environment to install flask
python3 -m venv venv
source venv/bin/activate

# Install flask dependency
pip install flask
```

## Running the Server
```bash
python app.py
```

The server should start on `http://localhost:8000`.

## Running Unit Tests
In a seperate terminal window, activate the virtual environment first:
```bash
source venv/bin/activate
```
Then run:
```bash
python3 -m unittest tests.py -v
```

There are no additional test dependencies. I used Flask's test client and Python's
`unittest` standard library module.

## Example Curl Testing Usage

With the server running, you can test via curl:
```bash
# Insert two quarters
curl -X PUT http://localhost:8000/ -H "Content-Type: application/json" -d '{"coin": 1}' -i
curl -X PUT http://localhost:8000/ -H "Content-Type: application/json" -d '{"coin": 1}' -i

# Purchase item 1
curl -X PUT http://localhost:8000/inventory/1 -i

# Check remaining inventory
curl http://localhost:8000/inventory
```

## API Reference

| Verb   | URI              | Status | Description                          |
|--------|------------------|--------|--------------------------------------|
| PUT    | /                | 204    | Insert a quarter                     |
| DELETE | /                | 204    | Cancel transaction, return the # of coins back to user    |
| GET    | /inventory       | 200    | List all remaining item quantities             |
| GET    | /inventory/:id   | 200    | Get single remaining item quantity             |
| PUT    | /inventory/:id   | 200    | Purchase an item (2 quarters required)  |
| PUT    | /inventory/:id   | 403    |an attempt to purchase is made, but the number of coins are insuﬃcient.                |
| PUT    | /inventory/:id   | 404    | Item out of stock                    |

All endpoints use `application/json`. Items are **1-indexed** (1, 2, 3).

Custom response headers:
- `X-Coins` : number of coins accepted or to be returned
- `X-Inventory-Remaining` : stock left after a successful purchase

## Design Decisions

**Flask with no other dependencies** : The spec recommends minimal
dependencies. Flask is a single install with no other dependencies (unlike fast API which needs pydantic, Starlette etc.), needs no async runtime, and is
good for a synchronous request/response API.

**Separation of concerns** : `machine.py` contains all business logic. `app.py` is a fast & lightweight translation layer mapping
HTTP verbs and status codes to machine operations.

**In-memory state** : There is no database. The state lives in a Python object in memory. We are testing it sequentially via HTTP before deploying it in a production 
environment. The spec says single content type of “application/json” will be tested. If persistence were needed, the `VendingMachine` class could be backed by SQLite without changing the API layer.

**Standard library tests** : `unittest` and Flask's test client are
sufficient. No reason to add pytest as a dependency (spec says minimal dependencies).

**1-indexed item IDs** : Vending machines in the real world use 1-indexed
buttons. The API exposes items as 1, 2, 3 and internally they map to a
0-indexed list.

## Spec Ambiguities and Assumptions

- **Invalid item IDs** (such as `/inventory/99`): Returns 404. The spec only
  defines 404 for out-of-stock, but "resource not found" is the correct
  HTTP usually for a nonexistent item.
- **Coins on out-of-stock**: Refunded. A failed purchase is a completed
  transaction per the spec's refund rule.
- **Coins on insufficient funds**: Retained. The customer is still in the
  process of inserting money.
- **Request body on PUT /**: Accepted but not validated / parsed. The machine only
  accepts quarters, so the only known action is incrementing by one.
