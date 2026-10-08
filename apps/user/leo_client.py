"""Thin client for leo's apps.integrations internal API. leo is the source of truth for
the product catalog, stores/regions, bonus codes/redemption and cart/orders — this
module is the only place usta-source talks to it, mirroring the style of
apps/user/utils.py: send_telegram_message."""

import requests
from django.conf import settings


class LeoAPIError(Exception):
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"leo API error {status_code}: {payload}")


def _headers():
    return {"X-Internal-Token": settings.LEO_INTERNAL_TOKEN}


def _request(method, path, **kwargs):
    try:
        res = requests.request(
            method, f"{settings.LEO_BASE_URL}{path}", headers=_headers(), timeout=10, **kwargs
        )
    except requests.exceptions.RequestException as e:
        # Unreachable leo looks like any other API error to callers, just with no
        # localized message to surface — they fall back to their own default wording.
        raise LeoAPIError(503, {"error": {"message_language": {}}}) from e

    if res.status_code >= 400:
        try:
            payload = res.json()
        except Exception:
            payload = {"error": {"message_language": {}}}
        raise LeoAPIError(res.status_code, payload)
    try:
        return res.json()
    except Exception as e:
        raise LeoAPIError(500, {"error": {"message_language": {}}}) from e


def _post(path, data=None, files=None):
    return _request("POST", path, data=data, files=files)


def _get(path, params=None):
    return _request("GET", path, params=params)


def _patch(path, data=None):
    return _request("PATCH", path, data=data)


def _delete(path, data=None):
    return _request("DELETE", path, data=data)


# -- user -------------------------------------------------------------------

def provision_user(chat_id, phone="", first_name="", telegram_username=""):
    return _post(
        "/api/v1/internal/user/provision/",
        {
            "telegram_chat_id": chat_id,
            "phone": phone,
            "first_name": first_name,
            "telegram_username": telegram_username,
        },
    )


# -- bonus ---------------------------------------------------------------

def check_bonus_code(code):
    return _get("/api/v1/internal/bonus/check/", {"code": code})


def redeem_bonus_code(chat_id, code):
    return _post(
        "/api/v1/internal/bonus/redeem/", {"telegram_chat_id": chat_id, "code": code}
    )


# -- catalog (public on leo's side, no token needed, kept here for one call site) ----

def get_categories():
    return _get("/api/v1/product/get_categories/")


def get_subcategories():
    # leo returns the full flat list (no category filter) — filter by `category` on
    # the caller's side if a specific category's children are needed.
    return _get("/api/v1/product/subcategories/")


def get_products(subcategory_id=None, page=None):
    params = {}
    if subcategory_id:
        params["subcategory"] = subcategory_id
    if page:
        params["page"] = page
    return _get("/api/v1/product/products/", params)


def get_product_detail(pk):
    return _get(f"/api/v1/product/products/{pk}/")


def get_regions():
    return _get("/api/v1/shared/regions/")


def get_stores(region_id=None):
    params = {"region": region_id} if region_id else None
    return _get("/api/v1/shared/stores/", params)


# -- cart / orders ---------------------------------------------------------

def get_cart(chat_id):
    return _post("/api/v1/internal/cart/", {"telegram_chat_id": chat_id})


def add_cart_item(chat_id, product_id, quantity=1):
    return _post(
        "/api/v1/internal/cart/items/",
        {"telegram_chat_id": chat_id, "product_id": product_id, "quantity": quantity},
    )


def update_cart_item(chat_id, item_id, quantity):
    return _patch(
        f"/api/v1/internal/cart/items/{item_id}/",
        {"telegram_chat_id": chat_id, "quantity": quantity},
    )


def remove_cart_item(chat_id, item_id):
    return _delete(
        f"/api/v1/internal/cart/items/{item_id}/", {"telegram_chat_id": chat_id}
    )


def create_order(chat_id, cart_item_ids, store_id):
    return _post(
        "/api/v1/internal/order/create/",
        {
            "telegram_chat_id": chat_id,
            "cart_item_ids": cart_item_ids,
            "store_id": store_id,
        },
    )


def confirm_order(chat_id, order_id, is_good, problem_note=""):
    return _post(
        "/api/v1/internal/order/confirm/",
        {
            "telegram_chat_id": chat_id,
            "order_id": order_id,
            "is_good": is_good,
            "problem_note": problem_note,
        },
    )


def list_orders(chat_id):
    return _post("/api/v1/internal/order/list/", {"telegram_chat_id": chat_id})
