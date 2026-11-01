import json

from emporio_agent.data_loader import get_connection, get_order_status, ingest_csvs, search_products
from emporio_agent.promotions import compute_effective_price
from emporio_agent.tools import dispatch_tool

ORDER_8_EMAIL = "anacarol.ferreira@coldmail.com"


def test_promotion_picks_highest_discount():
    price = compute_effective_price(1000.0, [(10, "A"), (25, "B")])
    assert price.effective_price_brl == 750.0
    assert price.discount_percent == 25


def test_search_violoes_under_1000_in_stock():
    ingest_csvs()
    conn = get_connection()
    try:
        page = search_products(
            conn,
            category_name="Violões",
            max_price_brl=1000,
            in_stock_only=True,
        )
        names = [item["name"] for item in page["products"]]
        assert page["matched_count"] == 12
        assert page["truncated"] is False
        assert page["returned_count"] == 12
        assert names[0].startswith("Tagima Memphis AC-39")
        assert all(item["effective_price_brl"] <= 1000 for item in page["products"])
        assert all(item["stock_quantity"] > 0 for item in page["products"])
    finally:
        conn.close()


def test_search_reports_truncation():
    ingest_csvs()
    conn = get_connection()
    try:
        page = search_products(
            conn,
            category_name="Violões",
            max_price_brl=1000,
            in_stock_only=True,
            limit=5,
        )
        assert page["truncated"] is True
        assert page["matched_count"] == 12
        assert page["returned_count"] == 5
        assert len(page["products"]) == 5
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
    products = listed["products"]
    assert listed["truncated"] is False
    assert listed["matched_count"] == 12
    assert all("stock_quantity" not in item for item in products)
    assert all(item["availability"] == "disponivel" for item in products)

    details = json.loads(dispatch_tool("get_product_details", {"product_id": products[0]["product_id"]}))
    assert "stock_quantity" not in details
    assert details["availability"] in {"disponivel", "indisponivel"}


def test_order_requires_matching_email():
    ingest_csvs()
    conn = get_connection()
    try:
        blocked = get_order_status(conn, 8)
        assert blocked["error"] == "email_required"
        assert "tracking_code" not in blocked
        assert "items" not in blocked
        assert "customer_name" not in blocked

        mismatch = get_order_status(conn, 8, "outra.pessoa@jmail.com")
        assert mismatch["error"] == "email_mismatch"
        assert "tracking_code" not in mismatch
        assert "items" not in mismatch

        ok = get_order_status(conn, 8, ORDER_8_EMAIL)
        assert ok["status"] == "shipped"
        assert ok["tracking_code"] == "BRJL5544332BR"
        assert ok["customer_name"] == "Ana Carolina Ferreira"

        assert get_order_status(conn, 9999, ORDER_8_EMAIL) is None
    finally:
        conn.close()


def test_tool_hides_order_until_email_matches():
    ingest_csvs()
    blocked = json.loads(dispatch_tool("get_order_status", {"order_id": 8}))
    assert blocked["error"] == "email_required"
    assert "tracking_code" not in blocked

    revealed = json.loads(
        dispatch_tool(
            "get_order_status",
            {"order_id": 8, "customer_email": ORDER_8_EMAIL},
        )
    )
    assert revealed["status"] == "shipped"
    assert revealed["tracking_code"] == "BRJL5544332BR"
