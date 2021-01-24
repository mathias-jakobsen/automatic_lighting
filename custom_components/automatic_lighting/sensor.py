#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER
from .const import CONF_BLOCK_LIGHTS, CONF_BLOCK_TIMEOUT, SERVICE_SCHEMA_TURN_OFF, SERVICE_SCHEMA_TURN_ON, STATE_AMBIANCE
from .utils import ContextGenerator, ManualControlTracker
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_LIGHTS, CONF_NAME, CONF_TYPE, EVENT_HOMEASSISTANT_START, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import Entity
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    async_add_entities([AL_Entity(config_entry)], update_before_add=True)
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(SERVICE_TURN_OFF, SERVICE_SCHEMA_TURN_OFF, async_service_turn_off)
    platform.async_register_entity_service(SERVICE_TURN_ON, SERVICE_SCHEMA_TURN_ON, async_service_turn_on)
    return True


#-----------------------------------------------------------#
#       Services
#-----------------------------------------------------------#

async def async_service_turn_off(entity: AL_Entity, service_call: ServiceCall) -> None:
    return await entity.model.async_turn_off({ **service_call.data })

async def async_service_turn_on(entity: AL_Entity, service_call: ServiceCall) -> None:
    return await entity.model.async_turn_on({ **service_call.data })


#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(Entity):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        self._attributes = []
        self._config = config_entry.options
        self._model = None
        self._name = f"Automatic Lighting - {config_entry.data[CONF_NAME]}"
        self._state = STATE_AMBIANCE


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        return self._attributes.copy()

    @property
    def model(self) -> AL_Model:
        """ Gets the logic model of the entity. """
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
    def state(self) -> bool:
        """ Gets the state of the entity. """
        return self._state

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Public Methods
    #--------------------------------------------#

    async def async_update_entity(self, **attributes: Any) -> None:
        """ Updates the state of the entity. """
        self._attributes = { key: str(value) for key, value in attributes.items() if value is not None }
        self.async_schedule_update_ha_state(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        self._model = AL_Model(self.hass, self._config, self)

        if self.hass.is_running:
            await self._model.initialize()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._model.initialize)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._model.destroy()


#-----------------------------------------------------------#
#       AL_Model
#-----------------------------------------------------------#

class AL_Model():
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, config: Dict[str, Any], entity: AL_Entity):
        self._block_lights = config.get(CONF_BLOCK_LIGHTS, [])
        self._block_timeout = config.get(CONF_BLOCK_TIMEOUT, 60)
        self._context = ContextGenerator()
        self._current_profile = None
        self._entity = entity
        self._hass = hass
        self._manual_control_tracker = ManualControlTracker(hass, self._context, self._block_lights)
        self._remove_listeners = []


    #--------------------------------------------#
    #       Methods - Init/Destroy
    #--------------------------------------------#

    async def destroy(self) -> None:
        while self._remove_listeners:
            self._remove_listeners.pop()()

        self._manual_control_tracker.destroy()

    async def initialize(self, _ = None) -> None:
        self._remove_listeners.append(self._manual_control_tracker.listen(self._async_on_manual_control))


    #--------------------------------------------#
    #       Methods - Services
    #--------------------------------------------#

    async def async_turn_off(self, service_data: Dict[str, Any]) -> None:
        pass

    async def async_turn_on(self, service_data: Dict[str, Any]) -> None:
        type = service_data.pop(CONF_TYPE)
        lights = self._async_resolve_entity_dict(service_data.pop(CONF_LIGHTS, {}))
        attributes = service_data





    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        pass


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    async def _async_resolve_entity_dict(self, entity_dict: Dict[str, Any]) -> List[str]:
        result = []

        entity_registry = await self._hass.helpers.entity_registry.async_get_registry()
        entity_entries = entity_registry.entities.values()

        target_areas = cv.ensure_list(entity_dict["area_id"])
        target_devices = cv.ensure_list(entity_dict["device_id"])
        target_entities = cv.ensure_list(entity_dict["entity_id"])

        for entity in entity_entries:
            if entity.disabled:
                continue

            if entity.entity_id in target_entities:
                result.append(entity.entity_id)
                continue

            if entity.device_id is not None and entity.device_id in target_devices:
                result.append(entity.entity_id)
                continue

            if entity.area_id is not None and entity.area_id in target_areas:
                result.append(entity.entity_id)
                continue

        return result

