#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER
from .config_flow import get_options_schema
from .const import CONF_BLOCK_ATTRIBUTES, CONF_BLOCK_ENABLED, CONF_BLOCK_STATE, CONF_BLOCK_TIMEOUT, CONF_BLOCK_VARIANCE, STATE_AMBIANCE
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, EVENT_STATE_CHANGED
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from logging import Logger
from typing import Any, Callable, Dict


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    entity = AL_Entity(LOGGER, config_entry)
    async_add_entities([entity], update_before_add=True)
    return True


#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(Entity):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, logger: Logger, config_entry: ConfigEntry):
        self._attributes = []
        self._config = get_options_schema(config_entry.options)({ **config_entry.options })
        self._logger = logger
        self._model = None
        self._name = f"Automatic Lighting - {config_entry.data[CONF_NAME]}"
        self._state = STATE_AMBIANCE

        self._block_attributes = self._config[CONF_BLOCK_ATTRIBUTES]
        self._block_enabled = self._config[CONF_BLOCK_ENABLED]
        self._block_state = self._config[CONF_BLOCK_STATE]
        self._block_timeout = self._config[CONF_BLOCK_TIMEOUT]
        self._block_variance = self._config[CONF_BLOCK_VARIANCE]


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        return self._attributes.copy()

    @property
    def state(self) -> bool:
        """ Gets the state of the entity. """
        return self._state

    @property
    def name(self) -> str:
        """ Gets the name of entity. """
        return self._name

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether HomeAssistant should automatically poll the entity. """
        return True

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.test)
        # self._model = AL_Model(self.hass, self._logger, self._config, self.async_update_entity)

    async def test(self, e):
        id = e.data.get("entity_id", "")
        if id != "light.kitchen_spotlights":
            return
        LOGGER.debug(e.data.get("new_state"))

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._model.async_turn_off()


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_update_entity(self, **attributes: Any) -> None:
        """ Updates the state of the entity. """
        self._attributes = { key: str(value) for key, value in attributes.items() if value is not None }
        self.async_schedule_update_ha_state(True)
