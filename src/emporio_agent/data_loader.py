from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from emporio_agent.config import CSV_FILES, DATA_DIR, DB_PATH
from emporio_agent.promotions import PriceInfo, compute_effective_price


def _parse_specs(raw: str | None) -> dict[str, Any] | None:
    if not raw or not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def _read_csv(table_key: str) -> list[dict[str, str]]:
    filename = CSV_FILES[table_key]
    path = DATA_DIR / filename
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ingest_csvs(db_path: Path | None = None) -> Path:
    """Carrega CSVs em SQLite. Retorna caminho do banco."""
    db_path = db_path or DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(
            """
            CREATE TABLE categories (
                category_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT
            );
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                city TEXT
            );
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                price_brl REAL NOT NULL,
                name TEXT NOT NULL,
                category_id INTEGER,
                description TEXT,
                stock_quantity INTEGER,
                status TEXT,
                specs_json TEXT,
                created_at TEXT,
                FOREIGN KEY (category_id) REFERENCES categories(category_id)
            );
            CREATE TABLE promotions (
                promotion_id INTEGER PRIMARY KEY,
                product_id INTEGER,
                discount_percent REAL,
                description TEXT,
                is_active INTEGER,
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                order_date TEXT,
                status TEXT,
                total_brl REAL,
                payment_method TEXT,
                tracking_code TEXT,
                estimated_delivery TEXT,
                notes TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );
            CREATE TABLE order_items (
                order_id INTEGER,
                quantity INTEGER,
                product_id INTEGER,
                PRIMARY KEY (order_id, product_id),
                FOREIGN KEY (order_id) REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
            """
        )

        for row in _read_csv("categories"):
            conn.execute(
                "INSERT INTO categories VALUES (?,?,?)",
                (int(row["category_id"]), row["name"], row.get("description")),
            )

        for row in _read_csv("customers"):
            conn.execute(
                "INSERT INTO customers VALUES (?,?,?,?,?)",
                (
                    int(row["customer_id"]),
                    row["name"],
                    row.get("phone"),
                    row.get("email"),
                    row.get("city"),
                ),
            )

        for row in _read_csv("products"):
            specs = row.get("specs", "")
            conn.execute(
                """INSERT INTO products VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    int(row["product_id"]),
                    float(row["price_brl"]),
                    row["name"],
                    int(row["category_id"]),
                    row.get("description"),
                    int(row["stock_quantity"]),
                    row.get("status"),
                    specs,
                    row.get("created_at"),
                ),
            )

        for row in _read_csv("promotions"):
            conn.execute(
                "INSERT INTO promotions VALUES (?,?,?,?,?)",
                (
                    int(row["promotion_id"]),
                    int(row["product_id"]),
                    float(row["discount_percent"]),
                    row.get("description"),
                    int(row["is_active"]),
                ),
            )

        for row in _read_csv("orders"):
            conn.execute(
                """INSERT INTO orders VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    int(row["order_id"]),
                    int(row["customer_id"]),
                    row.get("order_date"),
                    row.get("status"),
                    float(row["total_brl"]) if row.get("total_brl") else None,
                    row.get("payment_method"),
                    row.get("tracking_code") or None,
                    row.get("estimated_delivery") or None,
                    row.get("notes") or None,
                ),
            )

        for row in _read_csv("order_items"):
            conn.execute(
                "INSERT INTO order_items VALUES (?,?,?)",
                (int(row["order_id"]), int(row["quantity"]), int(row["product_id"])),
            )

        conn.commit()
    finally:
        conn.close()

    return db_path


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    db_path = db_path or DB_PATH
    if not db_path.exists():
        ingest_csvs(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _active_promos_for_product(conn: sqlite3.Connection, product_id: int) -> list[tuple[float, str]]:
    rows = conn.execute(
        """
        SELECT discount_percent, description FROM promotions
        WHERE product_id = ? AND is_active = 1
        """,
        (product_id,),
    ).fetchall()
    return [(float(r["discount_percent"]), r["description"] or "") for r in rows]


def price_info_for_product(conn: sqlite3.Connection, product_id: int, list_price: float) -> PriceInfo:
    promos = _active_promos_for_product(conn, product_id)
    return compute_effective_price(list_price, promos)


def search_products(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    category_name: str | None = None,
    max_price_brl: float | None = None,
    in_stock_only: bool = False,
    limit: int = 25,
) -> dict[str, Any]:
    """Return every match, then page it. `truncated` is true when the page is incomplete."""
    sql = """
        SELECT p.product_id, p.name, p.price_brl, p.stock_quantity, p.status,
               c.name AS category_name
        FROM products p
        LEFT JOIN categories c ON c.category_id = p.category_id
        WHERE p.status = 'active'
    """
    params: list[Any] = []

    if category_name:
        sql += " AND LOWER(c.name) LIKE LOWER(?)"
        params.append(f"%{category_name.strip()}%")

    if query:
        sql += " AND (LOWER(p.name) LIKE LOWER(?) OR LOWER(p.description) LIKE LOWER(?))"
        q = f"%{query.strip()}%"
        params.extend([q, q])

    if in_stock_only:
        sql += " AND p.stock_quantity > 0"

    sql += " ORDER BY p.name"
    rows = conn.execute(sql, params).fetchall()
    matched: list[dict[str, Any]] = []
    for row in rows:
        price = price_info_for_product(conn, row["product_id"], float(row["price_brl"]))
        if max_price_brl is not None and price.effective_price_brl > max_price_brl:
            continue
        matched.append(
            {
                "product_id": row["product_id"],
                "name": row["name"],
                "category": row["category_name"],
                "stock_quantity": row["stock_quantity"],
                "list_price_brl": price.list_price_brl,
                "effective_price_brl": price.effective_price_brl,
                "promotion": price.promotion_description if price.has_active_promotion else None,
            }
        )

    matched.sort(key=lambda item: (item["effective_price_brl"], item["name"]))
    page_size = max(1, int(limit))
    page = matched[:page_size]
    return {
        "products": page,
        "matched_count": len(matched),
        "returned_count": len(page),
        "truncated": len(matched) > len(page),
    }


def get_product_details(
    conn: sqlite3.Connection,
    *,
    product_id: int | None = None,
    name_query: str | None = None,
) -> dict[str, Any] | None:
    if product_id is not None:
        row = conn.execute(
            """
            SELECT p.*, c.name AS category_name FROM products p
            LEFT JOIN categories c ON c.category_id = p.category_id
            WHERE p.product_id = ?
            """,
            (product_id,),
        ).fetchone()
    elif name_query:
        row = conn.execute(
            """
            SELECT p.*, c.name AS category_name FROM products p
            LEFT JOIN categories c ON c.category_id = p.category_id
            WHERE LOWER(p.name) LIKE LOWER(?)
            ORDER BY p.stock_quantity DESC
            LIMIT 1
            """,
            (f"%{name_query.strip()}%",),
        ).fetchone()
    else:
        return None

    if not row:
        return None

    price = price_info_for_product(conn, row["product_id"], float(row["price_brl"]))
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "category": row["category_name"],
        "description": row["description"],
        "stock_quantity": row["stock_quantity"],
        "status": row["status"],
        "specs": _parse_specs(row["specs_json"]),
        "list_price_brl": price.list_price_brl,
        "effective_price_brl": price.effective_price_brl,
        "discount_percent": price.discount_percent,
        "promotion": price.promotion_description,
    }


def get_order_status(
    conn: sqlite3.Connection,
    order_id: int,
    customer_email: str | None = None,
) -> dict[str, Any] | None:
    if not customer_email or not str(customer_email).strip():
        return {
            "error": "email_required",
            "message": "Informe o e-mail do titular para consultar este pedido.",
        }

    row = conn.execute(
        """
        SELECT o.*, cu.email, cu.name AS customer_name
        FROM orders o
        JOIN customers cu ON cu.customer_id = o.customer_id
        WHERE o.order_id = ?
        """,
        (order_id,),
    ).fetchone()
    if not row:
        return None

    stored_email = (row["email"] or "").lower()
    if stored_email != customer_email.strip().lower():
        return {"error": "email_mismatch", "message": "E-mail não confere com o pedido informado."}

    items = conn.execute(
        """
        SELECT oi.quantity, oi.product_id, p.name
        FROM order_items oi
        JOIN products p ON p.product_id = oi.product_id
        WHERE oi.order_id = ?
        """,
        (order_id,),
    ).fetchall()

    return {
        "order_id": row["order_id"],
        "status": row["status"],
        "order_date": row["order_date"],
        "total_brl": row["total_brl"],
        "payment_method": row["payment_method"],
        "tracking_code": row["tracking_code"],
        "estimated_delivery": row["estimated_delivery"],
        "notes": row["notes"],
        "customer_name": row["customer_name"],
        "items": [
            {"product_id": i["product_id"], "name": i["name"], "quantity": i["quantity"]}
            for i in items
        ],
    }


def list_customer_orders(conn: sqlite3.Connection, email: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT o.order_id, o.order_date, o.status, o.total_brl
        FROM orders o
        JOIN customers cu ON cu.customer_id = o.customer_id
        WHERE LOWER(cu.email) = LOWER(?)
        ORDER BY o.order_date DESC
        """,
        (email.strip(),),
    ).fetchall()
    return [
        {
            "order_id": r["order_id"],
            "order_date": r["order_date"],
            "status": r["status"],
            "total_brl": r["total_brl"],
        }
        for r in rows
    ]
