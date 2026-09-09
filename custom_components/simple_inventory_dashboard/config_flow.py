"""Config flow for Simple Inventory Dashboard."""

from homeassistant import config_entries

from .const import DOMAIN


class SimpleInventoryDashboardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create the single dashboard entry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create the dashboard without requiring options."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Simple Inventory Dashboard", data={})
        return self.async_show_form(step_id="user")

