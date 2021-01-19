#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from logging import getLogger
from typing import Any, Dict


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

DOMAIN = "motion_lighting"
LOGGER = getLogger(__name__)
PLATFORMS = ["switch"]
UNDO_UPDATE_LISTENER = "undo_update_listener"


#-----------------------------------------------------------#
#       Component Setup
#-----------------------------------------------------------#

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    data = hass.data.setdefault(DOMAIN, {})
    data[config_entry.entry_id] = { UNDO_UPDATE_LISTENER: config_entry.add_update_listener(async_update_options) }

    for platform in PLATFORMS:
        hass.async_create_task(hass.config_entries.async_forward_entry_setup(config_entry, platform))

    return True

async def async_update_options(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    unload_ok = all([await hass.config_entries.async_forward_entry_unload(config_entry, platform) for platform in PLATFORMS])

    data = hass.data[DOMAIN]
    data[config_entry.entry_id][UNDO_UPDATE_LISTENER]()

    if unload_ok:
        data.pop(config_entry.entry_id)

    if not data:
        hass.data.pop(DOMAIN)

    return unload_ok