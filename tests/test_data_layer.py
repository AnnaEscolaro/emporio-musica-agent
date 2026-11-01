import json

from emporio_agent.data_loader import get_connection, get_order_status, ingest_csvs, search_products
from emporio_agent.promotions import compute_effective_price
from emporio_agent.tools import dispatch_tool


def test_promotion_picks_highest_discount():
    price = compute_effective_price(1000.0, [(10, "A"), (25, "B")])
    assert price.effective_price_brl == 750.0
    assert price.discount_percent == 25


def test_search_violoes_under_1000_in_stock():
    ingest_csvs()
    conn = get_connection()
    try:
        items = search_products(
            conn,
            category_name="Violões",
            max_price_brl=1000,
            in_stock_only=True,
            limit=20,
        )
        assert items
        assert all(i["effective_price_brl"] <= 1000 for i in items)
        assert all(i["stock_quantity"] > 0 for i in items)
    finally:
        conn.close()


def test_tools_hide_exact_stock_quantity():
    ingest_csvs()
    listed = json.loads(
        dispatch_tool(
            "search_products",
            {"category_name": "Violões", "max_price_brl": 1000, "in_stock_only": True},
        )
    )
    assert listed
    assert all("stock_quantity" not in item for item in listed)
    assert all(item["availability"] == "disponivel" for item in listed)

    details = json.loads(dispatch_tool("get_product_details", {"product_id": listed[0]["product_id"]}))
    assert "stock_quantity" not in details
    assert details["availability"] in {"disponivel", "indisponivel"}


def test_order_not_found():
    ingest_csvs()
    conn = get_connection()
    try:
        assert get_order_status(conn, 9999) is None
    finally:
        conn.close()
