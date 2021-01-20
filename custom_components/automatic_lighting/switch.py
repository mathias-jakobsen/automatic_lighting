#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import DOMAIN, LOGGER
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from typing import Callable


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    LOGGER.debug(f"Setting up config entry (id: {config_entry.entry_id}).")
    #entity = AL_Entity(LOGGER, config_entry)
    #async_add_entities([entity], update_before_add=True)
    LOGGER.debug(config_entry.data)
    LOGGER.debug(config_entry.options)
    return True