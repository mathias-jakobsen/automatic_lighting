#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from homeassistant.helpers.template import Template, is_template_string
from homeassistant.helpers.event import async_call_later
from .const import ATTR_BLOCKED_UNTIL, CONF_BLOCK_LIGHTS, CONF_BLOCK_TIMEOUT, CONF_DURATION, CONF_NEW_STATE, CONF_OLD_STATE, DOMAIN, EVENT_AUTOMATIC_LIGHTING, EVENT_TYPE_BLOCK_END, EVENT_TYPE_OVERRIDE, EVENT_TYPE_REFRESH, SERVICE_SCHEMA_TURN_OFF, SERVICE_SCHEMA_TURN_ON, STATE_AMBIANCE, STATE_BLOCKED, STATE_TRIGGERED
from .utils import ContextGenerator, ManualControlTracker, Timer
from datetime import datetime, timedelta
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN, EVENT_AUTOMATION_RELOADED
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_LIGHTS, CONF_NAME, CONF_TYPE, EVENT_HOMEASSISTANT_START, EVENT_STATE_CHANGED, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import Context, Event, HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity import Entity
from logging import Logger, getLogger
from typing import Any, Callable, Dict, List, Union
import time


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

REFRESH_THROTTLE_TIME = 200
START_DELAY = 500


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
        self._attributes = {}
        self._config = config_entry.options
        self._logger = None
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

    async def async_update_entity(self, state: Any, **attributes: Any) -> None:
        """ Updates the state of the entity. """
        if self._state != state:
            self._logger.debug(f"Entity state changed from {self._state} to {state}.")
        self._attributes = { key: str(value) for key, value in attributes.items() if value is not None }
        self._state = state
        self.async_schedule_update_ha_state(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        self._logger = getLogger(f"{__name__}.{self.entity_id.split('.')[1]}")
        self._model = AL_Model(self.hass, self._logger, self._config, self)

        if self.hass.is_running:
            await self._model.async_initialize()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._model.async_initialize)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._model.async_destroy()


#-----------------------------------------------------------#
#       AL_Model
#-----------------------------------------------------------#

class AL_Model():
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, logger: Logger, config: Dict[str, Any], entity: AL_Entity):
        self._block_lights = config.get(CONF_BLOCK_LIGHTS, [])
        self._block_config_timeout = config.get(CONF_BLOCK_TIMEOUT, 60)
        self._block_timeout = self._block_config_timeout
        self._block_timer = None
        self._block_until = None
        self._context = ContextGenerator()
        self._current_profile = None
        self._current_refresh_profile = None
        self._entity = entity
        self._hass = hass
        self._logger = logger
        self._manual_control_tracker = ManualControlTracker(hass, self._context, self._block_lights)
        self._ambiance_timer = None
        self._refresh_throttle_timer = None
        self._remove_listeners = []


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_blocked(self) -> bool:
        return self._block_timer is not None and self._block_timer.is_running

    @property
    def is_refreshing(self) -> bool:
        return self._refresh_throttle_timer is not None and self._refresh_throttle_timer.is_running


    #--------------------------------------------#
    #       Methods - Init/Destroy
    #--------------------------------------------#

    async def async_destroy(self) -> None:
        while self._remove_listeners:
            self._remove_listeners.pop()()

        self._block_timer and self._block_timer.cancel()
        self._manual_control_tracker.destroy()
        self._refresh_throttle_timer and self._refresh_throttle_timer.cancel()

    async def async_initialize(self, _ = None) -> None:
        self._remove_listeners.append(self._manual_control_tracker.listen(self._async_on_manual_control))
        self._remove_listeners.append(self._hass.bus.async_listen(EVENT_AUTOMATION_RELOADED, self._async_on_automations_reloaded))
        self._remove_listeners.append(self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._async_on_automation_state_change))

        self._logger.debug(f"Entity has initialized.")
        self._remove_listeners.append(async_call_later(self._hass, START_DELAY / 1000, self._async_refresh))


    #--------------------------------------------#
    #       Methods - Services
    #--------------------------------------------#

    async def async_block(self, timeout: int) -> None:
        self._logger.debug(f"Blocking for {self._block_timeout} seconds.")

        if self._block_timer:
            self._block_timer.cancel()

        self._block_timeout = timeout
        self._blocked_until = datetime.now() + timedelta(seconds=self._block_timeout)
        self._block_timer = Timer(self._hass, timeout, self.async_unblock)
        await self._entity.async_update_entity(state=STATE_BLOCKED, **{ ATTR_BLOCKED_UNTIL: self._blocked_until })

    async def async_unblock(self, _ = None) -> None:
        self._logger.debug(f"Unblocking after {self._block_timeout} seconds of inactivity.")

        if self._block_timer:
            self._block_timer.cancel()
            self._block_timer = None

        await self._async_fire_event(EVENT_AUTOMATIC_LIGHTING, { CONF_ENTITY_ID: self._entity.entity_id, CONF_TYPE: EVENT_TYPE_BLOCK_END })
        await self._async_refresh(True)

    async def async_turn_off(self, service_data: Dict[str, Any]) -> None:
        self._logger.debug(f"Registered a call to the {DOMAIN}.{SERVICE_TURN_OFF} service with the following data: {service_data}")

        if self.is_blocked:
            return

        if not self._current_profile:
            return

        if service_data.get(CONF_ID, "") != self._current_profile.id:
            return

        await self._async_refresh()

    async def async_turn_on(self, service_data: Dict[str, Any]) -> None:
        entity_id = service_data.pop(CONF_ENTITY_ID)
        id = service_data.pop(CONF_ID)
        type = service_data.pop(CONF_TYPE)
        lights = await self._async_resolve_entity_dict(service_data.pop(CONF_LIGHTS, {}))
        attributes = service_data

        if self.is_refreshing:
            self._logger.debug(f"Registered a turn on call while refreshing. {[id, type, lights, attributes]}")

            if self._current_refresh_profile and type == STATE_AMBIANCE and self._current_refresh_profile.type == STATE_TRIGGERED:
                return

            self._current_refresh_profile = Profile(id, type, lights, attributes)
            return

        if self.is_blocked:
            return await self.async_block(self._block_config_timeout)

        if self._current_profile:
            old_lights = [light for light in self._current_profile.entity_ids if light not in lights]
            await self._async_call_service(SERVICE_TURN_OFF, old_lights)

        self._logger.debug(f"Registered a call to the {DOMAIN}.{SERVICE_TURN_ON} service with the following data: {[id, type, lights, attributes]}")
        self._current_profile = Profile(id, type, lights, attributes)

        await self._entity.async_update_entity(type)
        await self._async_call_service(SERVICE_TURN_ON, self._current_profile.entity_ids, self._current_profile.attributes)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_automations_reloaded(self, event: Event) -> None:
        self._logger.debug(f"Detected an automations reloaded event.")
        await self._async_refresh()

    async def _async_on_automation_state_change(self, event: Event) -> None:
        domain = event.data.get(CONF_ENTITY_ID, "").split(".")[0]

        if domain != AUTOMATION_DOMAIN:
            return

        old_state = event.data.get(CONF_OLD_STATE, None)
        new_state = event.data.get(CONF_NEW_STATE, None)

        if old_state and new_state and old_state.state == new_state.state:
            return

        self._logger.debug(f"Detected a state change for an automation.")
        await self._async_refresh()

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        self._logger.debug(f"Detected manual control of following entities: {entity_ids}")
        await self.async_block(self._block_timeout)


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    async def _async_fire_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        context = self._context.generate()
        self._entity.async_set_context(context)
        self._hass.bus.async_fire(event_type, event_data, context=context)

    async def _async_call_service(self, service: str, entity_ids: List[str], service_data: Dict[str, Any] = {}) -> None:
        self._logger.debug(f"Calling {LIGHT_DOMAIN}.{service} with following service data: {service_data}")
        parsed_service_data = self._parse_service_data(service_data)
        self._hass.async_create_task(
            self._hass.services.async_call(LIGHT_DOMAIN, service, { CONF_ENTITY_ID: entity_ids, **parsed_service_data }, context=self._context.generate())
        )

    async def _async_refresh(self, bypass_block: bool = False):
        if self._refresh_throttle_timer and self._refresh_throttle_timer.is_running:
            self._refresh_throttle_timer.cancel()
        else:
            self._logger.debug(f"Firing refresh event.")
            self._current_refresh_profile = None
            await self._async_fire_event(EVENT_AUTOMATIC_LIGHTING, { CONF_ENTITY_ID: self._entity.entity_id, CONF_TYPE: EVENT_TYPE_REFRESH })

        async def async_refresh():
            self._logger.debug(f"Refresh ended.")
            if self.is_blocked and not bypass_block:
                return
            if self._current_refresh_profile:
                if not self._entity.state == self._current_refresh_profile.type:
                    await self._entity.async_update_entity(self._current_refresh_profile.type)

                if self._current_profile and (not self.is_blocked or self.is_blocked and bypass_block):
                    old_lights = [light for light in self._current_profile.entity_ids if light not in self._current_refresh_profile.entity_ids]
                    await self._async_call_service(SERVICE_TURN_OFF, old_lights)

                self._current_profile = self._current_refresh_profile
                return await self._async_call_service(SERVICE_TURN_ON, self._current_refresh_profile.entity_ids, self._current_refresh_profile.attributes)
            elif self._current_profile:
                await self._async_call_service(SERVICE_TURN_OFF, self._current_profile.entity_ids)
            await self._entity.async_update_entity(STATE_AMBIANCE)

        self._refresh_throttle_timer = Timer(self._hass, REFRESH_THROTTLE_TIME / 1000, async_refresh)

    async def _async_resolve_entity_dict(self, entity_dict: Dict[str, Any]) -> List[str]:
        result = []

        entity_registry = await self._hass.helpers.entity_registry.async_get_registry()
        entity_entries = entity_registry.entities.values()

        target_areas = entity_dict.get("area_id", [])
        target_devices = entity_dict.get("device_id", [])
        target_entities = entity_dict.get("entity_id", [])

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

    def _parse_service_data(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Parses and the returns the provided service data. """
        result = {}

        for key, value in service_data.items():
            if isinstance(value, str) and is_template_string(value):
                try:
                    template = Template(value, self._hass)
                    result[key] = template.async_render()
                except Exception as e:
                    self._logger.warn(f"[{self._name}] Ignoring attribute {key}. Invalid template was given -> {value}.")
                    self._logger.warn(e)
                    continue
            else:
                result[key] = value

        return result


class Profile:
    def __init__(self, id: str, type: str, entity_ids: List[str], attributes: Dict[str, Any]):
        self.id = id
        self.type = type
        self.entity_ids = entity_ids
        self.attributes = attributes