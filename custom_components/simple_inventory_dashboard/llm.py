"""Native Home Assistant LLM tools for Simple Inventory Dashboard."""

from __future__ import annotations

from typing import override

import voluptuous as vol

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.llm import LLM_API_ASSIST, LLMContext, Tool, ToolInput
from homeassistant.util.json import JsonObjectType

from .const import (
    DOMAIN,
    SERVICE_LIST_INVENTORIES,
    SERVICE_LIST_LOCATION,
    SERVICE_SEARCH_ITEMS,
    SERVICE_STORE_ITEM,
    SERVICE_TAKE_ITEM,
)


class InventoryTool(Tool):
    """Call one of the integration's response-enabled services."""

    def __init__(
        self,
        name: str,
        service: str,
        description: str,
        parameters: vol.Schema,
    ) -> None:
        self.name = f"{DOMAIN}__{name}"
        self.service = service
        self.description = description
        self.parameters = parameters

    @override
    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: ToolInput,
        llm_context: LLMContext,
    ) -> JsonObjectType:
        """Forward a tool call to the shared service implementation."""
        response = await hass.services.async_call(
            DOMAIN,
            self.service,
            dict(tool_input.tool_args),
            blocking=True,
            context=llm_context.context,
            return_response=True,
        )
        if not isinstance(response, dict):
            return {"success": False, "reason": "empty_response"}
        return response


OPTIONAL_INVENTORY = vol.Optional(
    "inventory",
    description="Exact inventory/furniture name or ID. Omit to search everywhere.",
)

TOOLS: list[Tool] = [
    InventoryTool(
        "list_inventories",
        SERVICE_LIST_INVENTORIES,
        "List all configured inventories or storage furniture. Use whenever the "
        "user asks which inventories, cupboards, cabinets or storage collections "
        "exist. Report their names and useful totals.",
        vol.Schema({}),
    ),
    InventoryTool(
        "search_items",
        SERVICE_SEARCH_ITEMS,
        "Search stored items by full or partial name. Use whenever the user asks "
        "where an object is, whether it is in stock, or how many remain. Report "
        "the inventory, location and quantity from the result.",
        vol.Schema(
            {
                vol.Required("query", description="Object name to search for."): cv.string,
                OPTIONAL_INVENTORY: cv.string,
            }
        ),
    ),
    InventoryTool(
        "list_location",
        SERVICE_LIST_LOCATION,
        "List everything stored in an exact location such as a bin. Use whenever "
        "the user asks what a bin, box, shelf or other storage location contains.",
        vol.Schema(
            {
                vol.Required(
                    "location", description="Exact location, for example Bac A1."
                ): cv.string,
                OPTIONAL_INVENTORY: cv.string,
            }
        ),
    ),
    InventoryTool(
        "store_item",
        SERVICE_STORE_ITEM,
        "Store a newly bought or put-away object. Creates it or increases the "
        "quantity when its exact name already exists. Inventory and location are "
        "required; ask the user when either is missing.",
        vol.Schema(
            {
                vol.Required("name", description="Singular object name."): cv.string,
                vol.Required(
                    "inventory", description="Exact destination inventory/furniture."
                ): cv.string,
                vol.Required(
                    "location", description="Exact destination, for example Bac A1."
                ): cv.string,
                vol.Optional("quantity", default=1, description="Quantity to add."): vol.All(
                    vol.Coerce(float), vol.Range(min=0.001, max=999)
                ),
                vol.Optional("category", description="Optional free-form category."): cv.string,
            }
        ),
    ),
    InventoryTool(
        "take_item",
        SERVICE_TAKE_ITEM,
        "Decrease stock when the user took, used or consumed an object. The tool "
        "resolves its inventory automatically. If it returns ambiguous matches, "
        "ask the user which one and call the tool again with the inventory.",
        vol.Schema(
            {
                vol.Required("name", description="Full or partial object name."): cv.string,
                OPTIONAL_INVENTORY: cv.string,
                vol.Optional(
                    "quantity", default=1, description="Quantity used or removed."
                ): vol.All(vol.Coerce(float), vol.Range(min=0.001, max=999)),
            }
        ),
    ),
]


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Expose inventory tools directly through Home Assistant's Assist API."""
    if api_id != LLM_API_ASSIST:
        return None
    return LLMTools(
        tools=TOOLS,
        prompt=(
            "Use the Simple Inventory tools for all questions or actions concerning "
            "stored household objects. Never invent an inventory result."
        ),
    )
