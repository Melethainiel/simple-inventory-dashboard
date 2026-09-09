"""Sidebar dashboard for Simple Inventory."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PANEL_ELEMENT, PANEL_ICON, PANEL_JS_URL, PANEL_TITLE, PANEL_URL


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Register the dashboard asset and sidebar panel."""
    if hass.data.get(DOMAIN):
        return True

    source = Path(__file__).parent / "www" / "dashboard.js"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_JS_URL, str(source), cache_headers=False)]
    )
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        frontend_url_path=PANEL_URL,
        config={
            "_panel_custom": {
                "name": PANEL_ELEMENT,
                "module_url": f"{PANEL_JS_URL}?v=0.1.1",
                "embed_iframe": False,
                "trust_external": False,
            }
        },
        require_admin=False,
    )
    hass.data[DOMAIN] = True
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the sidebar panel."""
    if hass.data.pop(DOMAIN, None):
        frontend.async_remove_panel(hass, PANEL_URL)
    return True
