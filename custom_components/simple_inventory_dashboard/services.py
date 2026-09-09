"""Assist-friendly wrappers around Simple Inventory services."""

from __future__ import annotations

import unicodedata
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    SERVICE_EDIT_ITEM,
    SERVICE_LIST_INVENTORIES,
    SERVICE_LIST_LOCATION,
    SERVICE_SEARCH_ITEMS,
    SERVICE_STORE_ITEM,
    SERVICE_TAKE_ITEM,
)

UPSTREAM_DOMAIN = "simple_inventory"


def _normalise(value: Any) -> str:
    """Build a case- and accent-insensitive comparison value."""
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    return "".join(char for char in text if not unicodedata.combining(char)).casefold()


def _annotated_items(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten current and legacy upstream response shapes."""
    result: list[dict[str, Any]] = []
    inventories = response.get("inventories")
    if isinstance(inventories, list):
        for inventory in inventories:
            if not isinstance(inventory, dict):
                continue
            for raw_item in inventory.get("items", []):
                if isinstance(raw_item, dict):
                    item = dict(raw_item)
                    item.setdefault("inventory_id", inventory.get("inventory_id"))
                    item.setdefault("inventory_name", inventory.get("inventory_name"))
                    result.append(item)
        return result
    return [dict(item) for item in response.get("items", []) if isinstance(item, dict)]


async def _upstream_response(
    hass: HomeAssistant, service: str, data: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not hass.services.has_service(UPSTREAM_DOMAIN, service):
        raise HomeAssistantError(f"Le service {UPSTREAM_DOMAIN}.{service} n'est pas disponible")
    response = await hass.services.async_call(
        UPSTREAM_DOMAIN, service, data or {}, blocking=True, return_response=True
    )
    return response if isinstance(response, dict) else {}


async def _all_items(hass: HomeAssistant) -> list[dict[str, Any]]:
    return _annotated_items(
        await _upstream_response(hass, "get_items_from_all_inventories")
    )


async def _all_response(hass: HomeAssistant) -> dict[str, Any]:
    return await _upstream_response(hass, "get_items_from_all_inventories")


def _matches_inventory(item: dict[str, Any], inventory: str | None) -> bool:
    if not inventory:
        return True
    wanted = _normalise(inventory)
    return wanted in (
        _normalise(item.get("inventory_id")),
        _normalise(item.get("inventory_name")),
    )


def _find(items: list[dict[str, Any]], query: str, inventory: str | None) -> list[dict[str, Any]]:
    needle = _normalise(query)
    return [
        item
        for item in items
        if _matches_inventory(item, inventory) and needle in _normalise(item.get("name"))
    ]


def _locations(item: dict[str, Any]) -> list[str]:
    value = item.get("locations", item.get("location", []))
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


async def _search(call: ServiceCall) -> dict[str, Any]:
    items = _find(await _all_items(call.hass), call.data["query"], call.data.get("inventory"))
    return {"count": len(items), "items": items}


async def _list_inventories(call: ServiceCall) -> dict[str, Any]:
    """Return a compact inventory catalogue without duplicating every item."""
    response = await _all_response(call.hass)
    inventories = []
    for entry in response.get("inventories", []):
        if not isinstance(entry, dict):
            continue
        items = [item for item in entry.get("items", []) if isinstance(item, dict)]
        inventories.append(
            {
                "inventory_id": entry.get("inventory_id"),
                "inventory_name": entry.get("inventory_name"),
                "description": entry.get("description", ""),
                "item_count": len(items),
                "total_quantity": sum(
                    float(item.get("quantity", 0) or 0) for item in items
                ),
            }
        )
    return {"count": len(inventories), "inventories": inventories}


async def _list_location(call: ServiceCall) -> dict[str, Any]:
    wanted = _normalise(call.data["location"])
    items = [
        item
        for item in await _all_items(call.hass)
        if _matches_inventory(item, call.data.get("inventory"))
        and any(wanted == _normalise(location) for location in _locations(item))
    ]
    return {"count": len(items), "location": call.data["location"], "items": items}


def _inventory_match(response: dict[str, Any], inventory: str) -> dict[str, Any]:
    wanted = _normalise(inventory)
    matches = {
        str(entry["inventory_id"]): entry
        for entry in response.get("inventories", [])
        if isinstance(entry, dict) and entry.get("inventory_id")
        and wanted in (_normalise(entry.get("inventory_id")), _normalise(entry.get("inventory_name")))
    }
    if len(matches) != 1:
        raise ServiceValidationError(
            f"Inventaire introuvable ou ambigu : {inventory}. Utilisez son nom exact ou son ID."
        )
    return next(iter(matches.values()))


async def _store(call: ServiceCall) -> dict[str, Any]:
    response = await _all_response(call.hass)
    items = _annotated_items(response)
    inventory = _inventory_match(response, call.data["inventory"])
    inventory_id = str(inventory["inventory_id"])
    name, quantity = call.data["name"].strip(), call.data["quantity"]
    exact = [
        item for item in items
        if str(item.get("inventory_id")) == inventory_id
        and _normalise(item.get("name")) == _normalise(name)
    ]
    if exact:
        name = exact[0]["name"]
        await call.hass.services.async_call(
            UPSTREAM_DOMAIN, "increment_item",
            {"inventory_id": inventory_id, "name": name, "amount": quantity}, blocking=True
        )
        action = "incremented"
    else:
        data = {"inventory_id": inventory_id, "name": name, "quantity": quantity,
                "location": call.data["location"]}
        if call.data.get("category"):
            data["category"] = call.data["category"]
        await call.hass.services.async_call(UPSTREAM_DOMAIN, "add_item", data, blocking=True)
        action = "created"
    return {"success": True, "action": action, "name": name, "quantity": quantity,
            "inventory_id": inventory_id, "inventory_name": inventory.get("inventory_name"),
            "location": call.data["location"]}


async def _take(call: ServiceCall) -> dict[str, Any]:
    candidates = _find(await _all_items(call.hass), call.data["name"], call.data.get("inventory"))
    exact = [item for item in candidates if _normalise(item.get("name")) == _normalise(call.data["name"])]
    if exact:
        candidates = exact
    if not candidates:
        return {"success": False, "reason": "not_found", "matches": []}
    if len(candidates) > 1:
        return {"success": False, "reason": "ambiguous", "matches": candidates}
    item, quantity = candidates[0], call.data["quantity"]
    await call.hass.services.async_call(
        UPSTREAM_DOMAIN, "decrement_item",
        {"inventory_id": item["inventory_id"], "name": item["name"], "amount": quantity},
        blocking=True,
    )
    return {"success": True, "name": item["name"], "quantity": quantity,
            "inventory_id": item.get("inventory_id"), "inventory_name": item.get("inventory_name"),
            "location": item.get("locations", item.get("location"))}


EDITABLE_FIELDS = (
    "quantity",
    "unit",
    "location",
    "category",
    "description",
    "barcode",
    "price",
    "expiry_date",
    "expiry_alert_days",
    "auto_add_enabled",
    "auto_add_to_list_quantity",
    "desired_quantity",
    "todo_list",
    "todo_quantity_placement",
)


async def _edit(call: ServiceCall) -> dict[str, Any]:
    """Resolve one item and update every explicitly supplied field."""
    candidates = _find(
        await _all_items(call.hass), call.data["name"], call.data.get("inventory")
    )
    exact = [
        item for item in candidates
        if _normalise(item.get("name")) == _normalise(call.data["name"])
    ]
    if exact:
        candidates = exact
    if not candidates:
        return {"success": False, "reason": "not_found", "matches": []}
    if len(candidates) > 1:
        return {"success": False, "reason": "ambiguous", "matches": candidates}

    changes = {field: call.data[field] for field in EDITABLE_FIELDS if field in call.data}
    if "new_name" in call.data:
        changes["name"] = call.data["new_name"].strip()
    if not changes:
        raise ServiceValidationError("Indiquez au moins un champ à modifier.")

    item = candidates[0]
    data = {
        "inventory_id": item["inventory_id"],
        "old_name": item["name"],
        "name": changes.get("name", item["name"]),
        **{key: value for key, value in changes.items() if key != "name"},
    }
    await call.hass.services.async_call(
        UPSTREAM_DOMAIN, "update_item", data, blocking=True
    )
    return {
        "success": True,
        "old_name": item["name"],
        "name": data["name"],
        "inventory_id": item.get("inventory_id"),
        "inventory_name": item.get("inventory_name"),
        "changes": changes,
    }


TEXT = vol.All(cv.string, vol.Length(min=1))
QUANTITY = vol.All(vol.Coerce(float), vol.Range(min=0.001, max=999))


def async_register_services(hass: HomeAssistant) -> None:
    """Register high-level response services."""
    definitions = (
        (SERVICE_LIST_INVENTORIES, _list_inventories, {}),
        (SERVICE_SEARCH_ITEMS, _search, {vol.Required("query"): TEXT, vol.Optional("inventory"): cv.string}),
        (SERVICE_LIST_LOCATION, _list_location, {vol.Required("location"): TEXT, vol.Optional("inventory"): cv.string}),
        (SERVICE_STORE_ITEM, _store, {vol.Required("name"): TEXT, vol.Required("inventory"): TEXT,
         vol.Required("location"): TEXT, vol.Optional("quantity", default=1): QUANTITY,
         vol.Optional("category"): cv.string}),
        (SERVICE_TAKE_ITEM, _take, {vol.Required("name"): TEXT, vol.Optional("inventory"): cv.string,
         vol.Optional("quantity", default=1): QUANTITY}),
        (SERVICE_EDIT_ITEM, _edit, {
            vol.Required("name"): TEXT,
            vol.Optional("inventory"): cv.string,
            vol.Optional("new_name"): TEXT,
            vol.Optional("quantity"): vol.All(vol.Coerce(float), vol.Range(min=0, max=999)),
            vol.Optional("unit"): cv.string,
            vol.Optional("location"): cv.string,
            vol.Optional("category"): cv.string,
            vol.Optional("description"): cv.string,
            vol.Optional("barcode"): cv.string,
            vol.Optional("price"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("expiry_date"): cv.string,
            vol.Optional("expiry_alert_days"): vol.All(vol.Coerce(int), vol.Range(min=0)),
            vol.Optional("auto_add_enabled"): cv.boolean,
            vol.Optional("auto_add_to_list_quantity"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("desired_quantity"): vol.All(vol.Coerce(float), vol.Range(min=0)),
            vol.Optional("todo_list"): cv.string,
            vol.Optional("todo_quantity_placement"): vol.In(("name", "description")),
        }),
    )
    for name, handler, schema in definitions:
        hass.services.async_register(
            DOMAIN, name, handler, schema=vol.Schema(schema),
            supports_response=SupportsResponse.ONLY,
        )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Unregister high-level services."""
    for service in (
        SERVICE_LIST_INVENTORIES,
        SERVICE_SEARCH_ITEMS,
        SERVICE_LIST_LOCATION,
        SERVICE_STORE_ITEM,
        SERVICE_TAKE_ITEM,
        SERVICE_EDIT_ITEM,
    ):
        hass.services.async_remove(DOMAIN, service)
