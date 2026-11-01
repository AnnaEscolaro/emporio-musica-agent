from __future__ import annotations

import json
from typing import Any

from emporio_agent.data_loader import (
    get_connection,
    get_order_status,
    get_product_details,
    list_customer_orders,
    search_products,
)
from emporio_agent.policies_rag import search_policies

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Busca produtos no catálogo. A resposta traz products, matched_count e truncated. "
                "Se truncated for true, a lista está incompleta: diga isso, informe quantos ficaram de fora "
                "e ofereça o restante. Cada produto traz availability (disponivel ou indisponivel), "
                "nunca a quantidade em estoque."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo no nome ou descrição"},
                    "category_name": {"type": "string", "description": "Ex.: Violões, Guitarras"},
                    "max_price_brl": {"type": "number", "description": "Preço máximo (considera promo ativa)"},
                    "in_stock_only": {"type": "boolean", "default": False},
                    "limit": {
                        "type": "integer",
                        "default": 25,
                        "description": "Máximo de itens nesta página. Aumente se truncated for true.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": (
                "Detalhes de um produto por ID ou nome aproximado. "
                "Retorna availability (disponivel ou indisponivel), nunca a quantidade em estoque."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "name_query": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": (
                "Status, itens e rastreio de um pedido. Exige o e-mail do titular. "
                "Sem o e-mail correspondente, não devolve status, rastreio, itens nem nome."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "integer"},
                    "customer_email": {
                        "type": "string",
                        "description": "E-mail do titular. Obrigatório para liberar os dados do pedido.",
                    },
                },
                "required": ["order_id", "customer_email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_customer_orders",
            "description": (
                "Histórico de pedidos de um cliente, só pelo e-mail do titular. "
                "Use quando o cliente informar o e-mail e quiser ver os pedidos, mesmo sem o número. "
                "A resposta traz found, order_count e orders (número, data, status, total, pagamento, "
                "rastreio, previsão e itens). Se found for false, diga que não há pedido para esse e-mail. "
                "Nunca afirme que não há pedido sem chamar esta ferramenta."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "E-mail do titular cadastrado na compra.",
                    }
                },
                "required": ["email"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_store_policies",
            "description": "Busca trechos do manual de políticas (horários, endereço, trocas, pagamento, frete).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 4},
                },
                "required": ["query"],
            },
        },
    },
]


def _without_stock_quantity(product: dict[str, Any]) -> dict[str, Any]:
    """O modelo só vê disponibilidade, nunca o número de unidades."""
    public = dict(product)
    quantity = public.pop("stock_quantity", None)
    if quantity is not None:
        public["availability"] = "disponivel" if int(quantity) > 0 else "indisponivel"
    return public


def _hide_stock_counts(result: Any) -> Any:
    if isinstance(result, dict) and isinstance(result.get("products"), list):
        public = dict(result)
        public["products"] = [
            _without_stock_quantity(item) if isinstance(item, dict) else item
            for item in result["products"]
        ]
        return public
    if isinstance(result, list):
        return [_without_stock_quantity(item) if isinstance(item, dict) else item for item in result]
    if isinstance(result, dict) and "stock_quantity" in result:
        return _without_stock_quantity(result)
    return result


def dispatch_tool(name: str, arguments: dict[str, Any]) -> str:
    conn = get_connection()
    try:
        if name == "search_products":
            result = search_products(
                conn,
                query=arguments.get("query"),
                category_name=arguments.get("category_name"),
                max_price_brl=arguments.get("max_price_brl"),
                in_stock_only=bool(arguments.get("in_stock_only", False)),
                limit=int(arguments.get("limit", 25)),
            )
        elif name == "get_product_details":
            result = get_product_details(
                conn,
                product_id=arguments.get("product_id"),
                name_query=arguments.get("name_query"),
            )
            if result is None:
                result = {"error": "not_found", "message": "Produto não encontrado."}
        elif name == "get_order_status":
            result = get_order_status(
                conn,
                order_id=int(arguments["order_id"]),
                customer_email=arguments.get("customer_email"),
            )
            if result is None:
                result = {"error": "not_found", "message": "Pedido não encontrado."}
        elif name == "list_customer_orders":
            email = arguments.get("email") or arguments.get("customer_email") or ""
            result = list_customer_orders(conn, email=str(email))
        elif name == "search_store_policies":
            result = search_policies(
                query=str(arguments["query"]),
                top_k=int(arguments.get("top_k", 4)),
            )
        else:
            result = {"error": "unknown_tool", "message": f"Ferramenta desconhecida: {name}"}
        if name in {"search_products", "get_product_details"}:
            result = _hide_stock_counts(result)
    finally:
        conn.close()

    return json.dumps(result, ensure_ascii=False)
