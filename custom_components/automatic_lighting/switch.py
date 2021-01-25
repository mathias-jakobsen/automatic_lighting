#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from config.custom_components.automatic_lighting.sensor import AL_Entity
from config.custom_components.automatic_lighting.const import CONF_PROFILES
from datetime import datetime, timedelta
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_NAME, EVENT_HOMEASSISTANT_START, STATE_ON
from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.template import Template, is_template_string
from logging import Logger, getLogger
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    supervisor = AL_Supervisor(config_entry)

    async_add_entities([supervisor.entities], update_before_add=True)
    return True



#-----------------------------------------------------------#
#       AL_Supervisor
#-----------------------------------------------------------#

class AL_Supervisor:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._config_entry = config_entry
        self._data = { **config_entry.data } if config_entry.source == SOURCE_IMPORT else { **config_entry.options }
        self._entities = self._create_entities(self._data.get(CONF_PROFILES, []))

    @property
    def entities(self) -> List[AL_Entity]:
        return self._entities

    def _create_entities(self, profiles: List[Dict[str, Any]]) -> List[AL_Entity]:
        entities = []
        for profile in profiles:
            entity = AL_Entity(profile)
        return entities



#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(SwitchEntity, RestoreEntity):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config: Dict[str, Any]):
        self._attributes = {}
        self._config = config
        self._is_on = None
        self._logger = None
        self._model = None
        self._name = f"Automatic Lighting - {config.get(CONF_NAME)}"


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        return self._attributes.copy()

    @property
    def is_on(self) -> bool:
        """ Gets a boolean indicating whether the entity is turned on. """
        return self._is_on

    @property
    def model(self) -> AL_Model:
        """ Gets the model of entity. """
        return self._model

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
        last_state = await self.async_get_last_state()
        self._logger = getLogger(f"{__name__}.{self.entity_id.split('.')[1]}")
        self._model = AL_Model(self.hass, self._logger, self._config, self.async_update_entity)

        if not last_state or last_state.state == STATE_ON:
            if self.hass.is_running:
                return await self.async_turn_on()
            else:
                return self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self.async_turn_on)

        await self.async_turn_off()

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._model.async_turn_off()


    #--------------------------------------------#
    #       Public Methods
    #--------------------------------------------#

    async def async_turn_off(self) -> None:
        """ Turns off the entity. """
        if self._is_on is not None and not self._is_on:
            return

        self._is_on = False
        await self._model.async_turn_off()

    async def async_turn_on(self, _ = None) -> None:
        """ Turns on the entity. """
        if self._is_on:
            return

        self._is_on = True
        await self._model.async_turn_on()

    async def async_update_entity(self, **attributes: Any) -> None:
        """ Updates the state of the entity. """
        self._attributes = { key: str(value) for key, value in attributes.items() if value is not None }
        self.async_schedule_update_ha_state(True)


#-----------------------------------------------------------#
#       AL_Model
#-----------------------------------------------------------#

class AL_Model:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, logger: Logger, config: Dict[str, Any], async_update_func: Callable[[Any], None]):
        logger.debug(config)


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#




    #--------------------------------------------#
    #       Public Methods
    #--------------------------------------------#

    async def async_turn_off(self):
        """ Turns off the model. """
        if not self.is_on:
            return

        #while self._listeners:
        #    self._listeners.pop()()

        #self._reset_block_timer()
        #self._reset_current_active_profile()

    async def async_turn_on(self):
        """ Turns on the model. """
        if self.is_on:
            return

        #self._listeners.append(async_track_state_change(self._hass, self._illuminance_entity, self._on_illuminance_update))
        #self._listeners.append(async_track_state_change(self._hass, self._light_entities, self._on_light_state_change))
        #self._listeners.append(async_track_state_change(self._hass, self._trigger_entities, self._on_trigger_state_change))

        #for time in self._idle_times:
        #    self._listeners.append(async_track_time_change(self._hass, self._on_idle_time_update, hour=time.hour, minute=time.minute, second=time.second))

        #self._current_illuminance = self._get_illuminance()
        #await self._update_status()