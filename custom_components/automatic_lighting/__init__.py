#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from .const import CONFIG_SCHEMA, DOMAIN, PLATFORMS, UNDO_UPDATE_LISTENER
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_SOURCE
from homeassistant.core import HomeAssistant
from typing import Any, Dict


#-----------------------------------------------------------#
#       Component Setup
#-----------------------------------------------------------#

async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    if DOMAIN in config:
        for entry in config[DOMAIN]:
            hass.async_create_task(hass.config_entries.flow.async_init(DOMAIN, context={ CONF_SOURCE: SOURCE_IMPORT }, data=entry))
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