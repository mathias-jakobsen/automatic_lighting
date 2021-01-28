#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from .const import ATTR_BLOCKED_UNTIL, CONF_BLOCK_LIGHTS, CONF_BLOCK_TIMEOUT, CONF_NEW_STATE, CONF_OLD_STATE, EVENT_AUTOMATIC_LIGHTING, EVENT_TYPE_REFRESH, SERVICE_SCHEMA_TURN_OFF, SERVICE_SCHEMA_TURN_ON, STATE_AMBIANCE, STATE_BLOCKED, STATE_TRIGGERED
from .utils import EntityModel, Timer, async_resolve_target, async_track_manual_control
from datetime import datetime, timedelta
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN, EVENT_AUTOMATION_RELOADED
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_LIGHTS, CONF_NAME, CONF_TYPE, EVENT_HOMEASSISTANT_START, EVENT_STATE_CHANGED, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import Context, Event, HomeAssistant, ServiceCall
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later
from logging import Logger, getLogger
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

REFRESH_DEBOUNCE_TIME = 0.2
START_DELAY = 0.5


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
    data = { **service_call.data }
    data.pop(CONF_ENTITY_ID)
    return await entity.model.async_service_turn_off(data)

async def async_service_turn_on(entity: AL_Entity, service_call: ServiceCall) -> None:
    data = { **service_call.data }
    data.pop(CONF_ENTITY_ID)
    return await entity.model.async_service_turn_on(data)


#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(Entity):
    """ The entity that is created by the integration. """
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

    def update_entity(self, state: Any, **attributes: Any) -> None:
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
        self._model = AL_Model(self.hass, self._logger, self, self._config)

        if self.hass.is_running:
            await self._model.async_turn_on()
        else:
            self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._model.async_turn_on)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._model.async_turn_off()


#-----------------------------------------------------------#
#       AL_Model
#-----------------------------------------------------------#

class AL_Model(EntityModel[AL_Entity]):
    """ An entity model that handles the logic of the integration. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, logger: Logger, entity: AL_Entity, config: Dict[str, Any]):
        super().__init__(hass, logger, entity)

        # ------ Attributes ---------------
        self._block_until = None

        # ------ Block ---------------
        self._block_lights = config.get(CONF_BLOCK_LIGHTS, [])
        self._block_config_timeout = config.get(CONF_BLOCK_TIMEOUT, 60)
        self._block_timeout = self._block_config_timeout

        # ------ Profiles ---------------
        self._current_profile = None
        self._refresh_profile = None

        # ------ Listeners & Timers ---------------
        self._block_timer = None
        self._refresh_timer = None
        self._remove_listeners = []


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_blocked(self) -> bool:
        """ Gets a boolean indicating whether the entity model is blocked. """
        return self.entity.state == STATE_BLOCKED

    @property
    def is_on(self) -> bool:
        """ Gets a boolean indicating whether the entity model is turned on. """
        return len(self._remove_listeners) > 0

    @property
    def is_refreshing(self) -> bool:
        """ Gets a boolean indicating whether the entity model is currently refreshing. """
        return self._refresh_timer is not None and self._refresh_timer.is_running


    #--------------------------------------------#
    #       Init Methods
    #--------------------------------------------#

    async def async_turn_off(self, *args: Any) -> None:
        """ Turns off the model. """
        while self._remove_listeners:
            self._remove_listeners.pop()()

        self._block_timer and self._block_timer.cancel()
        self._refresh_timer and self._refresh_timer.cancel()

    async def async_turn_on(self, *args: Any) -> None:
        """ Turns on the model. """
        if self.is_on:
            return

        self._remove_listeners.append(async_track_manual_control(self.hass, self._block_lights, self._on_manual_control, self.is_context_internal))
        self._remove_listeners.append(self._hass.bus.async_listen(EVENT_AUTOMATION_RELOADED, self._on_automations_reloaded))
        self._remove_listeners.append(self._hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_automation_state_change))
        self._remove_listeners.append(async_call_later(self._hass, START_DELAY, self._refresh))


    #--------------------------------------------#
    #       Service Methods (Turn On/Off)
    #--------------------------------------------#

    async def async_service_turn_off(self, service_data: Dict[str, Any]) -> None:
        """ Handles a service call to automatic_lighting.turn_off. """
        if self.is_blocked:
            return

        if not self._current_profile:
            return

        if service_data.get(CONF_ID, "") != self._current_profile.id:
            return

        self._refresh()

    async def async_service_turn_on(self, service_data: Dict[str, Any]) -> None:
        """ Handles a service call to automatic_lighting.turn_on. """
        id = service_data.pop(CONF_ID)
        entity_ids = await async_resolve_target(self._hass, service_data.pop(CONF_LIGHTS, {}))
        type = service_data.pop(CONF_TYPE)
        attributes = service_data

        if self.is_refreshing:
            if self._refresh_profile and type == STATE_AMBIANCE and self._refresh_profile.type == STATE_TRIGGERED:
                return

            self._refresh_profile = AL_Lighting_Profile(id, type, entity_ids, attributes)
            return

        if self.entity.state == STATE_TRIGGERED and type == STATE_AMBIANCE:
            return

        if self.is_blocked:
            return self.block(self._block_timeout)

        if self._current_profile:
            self._turn_off_unused_entities(self._current_profile.entity_ids, entity_ids)

        self._current_profile = AL_Lighting_Profile(id, type, entity_ids, attributes)
        self.entity.update_entity(type, lights=entity_ids, **attributes)
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=entity_ids, **attributes)


    #--------------------------------------------#
    #       Blocking Methods
    #--------------------------------------------#

    def block(self, timeout: int) -> None:
        """ Blocks the model for a time period. """
        self.logger.debug(f"Blocking for {self._block_timeout} seconds.")

        if self.is_blocked:
            self._block_timer.cancel()

        self._block_timeout = timeout
        self._blocked_until = datetime.now() + timedelta(seconds=self._block_timeout)
        self._block_timer = Timer(self.hass, self._block_timeout, self.unblock)
        self.entity.update_entity(state=STATE_BLOCKED, **{ ATTR_BLOCKED_UNTIL: self._blocked_until.strftime("%d/%m/%Y %H:%M:%S") })

    def unblock(self, _ = None) -> None:
        """ Unblocks the model """
        if not self.is_blocked:
            return

        self.logger.debug(f"Unblocking after {self._block_timeout} seconds of inactivity.")
        self._block_timer.cancel()
        self._refresh(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    def _on_automations_reloaded(self, event: Event) -> None:
        """ Triggered when an automation_reloaded event has fired. """
        self.logger.debug(f"Detected an automations reloaded event.")
        self._refresh()

    def _on_automation_state_change(self, event: Event) -> None:
        """ Triggered when an automation has changed state. """
        domain = event.data.get(CONF_ENTITY_ID, "").split(".")[0]

        if domain != AUTOMATION_DOMAIN:
            return

        old_state = event.data.get(CONF_OLD_STATE, None)
        new_state = event.data.get(CONF_NEW_STATE, None)

        if old_state is None or new_state is None:
            return

        if old_state.state == new_state.state:
            return

        self.logger.debug(f"Detected a state change for an automation.")
        self._refresh()

    def _on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        """ Triggered when manual control is detected. """
        self.logger.debug(f"Detected manual control of following entities: {entity_ids}")
        self.block(self._block_timeout if self.is_blocked else self._block_config_timeout)


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _refresh(self, bypass_block: bool = False) -> None:
        """ Refreshes the model. """
        if self.is_refreshing:
            self._refresh_timer.cancel()
        else:
            self._refresh_profile = None
            self.fire_event(EVENT_AUTOMATIC_LIGHTING, entity_id=self._entity.entity_id, type=EVENT_TYPE_REFRESH)

        def refresh():
            if self.is_blocked and not bypass_block:
                return

            if self._refresh_profile:
                if self._current_profile and (not self.is_blocked or (self.is_blocked and bypass_block)):
                    self._turn_off_unused_entities(self._current_profile.entity_ids, self._refresh_profile.entity_ids)

                self._current_profile = self._refresh_profile
                self.entity.update_entity(self._refresh_profile.type, lights=self._current_profile.entity_ids, **self._current_profile.attributes)
                return self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self._current_profile.entity_ids, **self._current_profile.attributes)

            if self._current_profile:
                self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=self._current_profile.entity_ids)

            self.entity.update_entity(STATE_AMBIANCE)

        self._refresh_timer = Timer(self.hass, REFRESH_DEBOUNCE_TIME, refresh)

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        unused_entities = [entity_id for entity_id in old_entity_ids if entity_id not in new_entity_ids]
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)


#-----------------------------------------------------------#
#       AL_Lighting_Profile
#-----------------------------------------------------------#

class AL_Lighting_Profile:
    """ A class that contains lighting properties. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, id: str, type: str, entity_ids: List[str], attributes: Dict[str, Any]):
        self._id = id
        self._type = type
        self._entity_ids = entity_ids
        self._attributes = attributes


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def attributes(self) -> Dict[str, Any]:
        """ Returns the attributes. """
        return self._attributes

    @property
    def entity_ids(self) -> List[str]:
        """ Returns the entity ids. """
        return self._entity_ids

    @property
    def id(self) -> str:
        """ Returns the id. """
        return self._id

    @property
    def type(self) -> str:
        """ Returns the id. """
        return self._type