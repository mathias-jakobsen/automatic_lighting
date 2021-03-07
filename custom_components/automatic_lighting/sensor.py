#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from datetime import datetime, timedelta
from homeassistant.helpers import entity_platform
from homeassistant.components.automation import EVENT_AUTOMATION_RELOADED
from homeassistant.helpers.event import async_call_later
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.const import ATTR_ID, CONF_ENTITY_ID, CONF_ID, CONF_NAME, CONF_STATE, EVENT_HOMEASSISTANT_START, SERVICE_TURN_OFF, SERVICE_TURN_ON
from . import LOGGER_BASE_NAME
from .const import ATTR_BLOCKED_UNTIL, CONF_BLOCK_DURATION, CONF_LIGHTS, CONF_LIGHT_GROUPS, DEFAULT_BLOCK_DURATION, DOMAIN, EVENT_DATA_TYPE_REQUEST, EVENT_DATA_TYPE_RESET, EVENT_TYPE_AUTOMATIC_LIGHTING, SERVICE_SCHEMA_TRACK_LIGHTS, SERVICE_SCHEMA_TURN_ON, SERVICE_TRACK_LIGHTS, STATE_ACTIVE, STATE_BLOCKED, STATE_IDLE
from .utils import EntityBase, async_resolve_target, async_track_automations_changed, async_track_manual_control
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Context, HomeAssistant, ServiceCall
from logging import Logger, getLogger
from typing import Any, Callable, Dict, List


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

BLOCK_THROTTLE_TIME = 0.2
REQUEST_DEBOUNCE_TIME = 0.2
RESET_DEBOUNCE_TIME = 0.2
START_DELAY = 0.5


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    async_add_entities([AL_Entity(config_entry)], update_before_add=True)
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(SERVICE_TRACK_LIGHTS, SERVICE_SCHEMA_TRACK_LIGHTS, "_async_service_track_lights")
    platform.async_register_entity_service(SERVICE_TURN_OFF, {}, "_async_service_turn_off")
    platform.async_register_entity_service(SERVICE_TURN_ON, SERVICE_SCHEMA_TURN_ON, "_async_service_turn_on")
    return True


#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(EntityBase):
    #-----------------------------------------------------------------------------#
    #
    #       Constructor
    #
    #-----------------------------------------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        EntityBase.__init__(self, getLogger(f"{LOGGER_BASE_NAME}.{config_entry.unique_id}"))

        # --- Attributes ----------
        self._blocked_at = None
        self._blocked_until = None

        # --- Block ----------
        self._block_config_duration = config_entry.options.get(CONF_BLOCK_DURATION, DEFAULT_BLOCK_DURATION)
        self._block_duration = self._block_config_duration
        self._block_enabled = True

        # --- Entity ----------
        self._name = f"{DOMAIN} - {config_entry.data.get(CONF_NAME)}"
        self._state = STATE_IDLE

        # --- Lights ----------
        self._light_groups = config_entry.options.get(CONF_LIGHT_GROUPS, {})
        self._tracked_lights = list(set(sum(self._light_groups.values(), [])))

        # --- Listeners ----------
        self._listeners = []

        # --- Profile ----------
        self._current_profile = None

        # --- Timers ----------
        self._block_timer = None
        self._request_timer = None
        self._reset_timer = None


    #-----------------------------------------------------------------------------#
    #
    #       Entity Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        attributes = {}

        if self.is_blocked:
            attributes.update({ ATTR_BLOCKED_UNTIL: self._blocked_until })

        if not self.is_blocked and self._current_profile:
            attributes.update({ ATTR_ID: self._current_profile.id, **self._current_profile.attributes })

        return attributes

    @property
    def name(self) -> str:
        """ Gets the name of entity. """
        return self._name

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether Home Assistant should automatically poll the entity. """
        return True

    @property
    def state(self) -> bool:
        """ Gets the state of the entity. """
        return STATE_BLOCKED if self.is_blocked else self._state

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to Home Assistant. """
        if self.hass.is_running:
            return self._initialize()

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._initialize)

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        self._remove_listeners()


    #-----------------------------------------------------------------------------#
    #
    #       Logic Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_blocked(self) -> bool:
        """ Gets a boolean indicating whether the entity is blocked. """
        return self._block_timer is not None


    #--------------------------------------------#
    #       Initialization
    #--------------------------------------------#

    def _initialize(self, *args: Any) -> None:
        """ Initializes the entity's internal logic. """
        self._listeners.append(async_call_later(self.hass, START_DELAY, self._reset))


    #--------------------------------------------#
    #       Request Methods
    #--------------------------------------------#

    def _request(self) -> None:
        """ Fires the request event, requesting the next lighting settings. """
        if self._request_timer:
            self._reset_request_timer()
        else:
            self.logger.debug(f"Firing request event.")
            self._current_profile = None
            self.fire_event(EVENT_TYPE_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_DATA_TYPE_REQUEST)

        def _on_request_finished(*args: Any) -> None:
            """ Triggered when the request event has finished. """
            self._reset_request_timer()

            if self.is_blocked:
                return

            if self._current_profile:
                self.logger.debug(f"A lighting profile was provided: {self._current_profile.id}")
                self._state = self._current_profile.state
                self._turn_off_unused_entities(self._tracked_lights, self._current_profile.lights)
                self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self._current_profile.lights, **self._current_profile.attributes)
            else:
                self.logger.debug(f"No lighting profile was provided. Turning off all tracked lights.")
                self._state = STATE_IDLE
                self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=self._tracked_lights)

            self.async_schedule_update_ha_state(True)

        self._request_timer = async_call_later(self.hass, REQUEST_DEBOUNCE_TIME, _on_request_finished)

    def _reset(self, *args: Any) -> None:
        """ Fires the reset event. """
        if self._reset_timer:
            self._reset_reset_timer()
        else:
            self.logger.debug(f"Firing reset event.")
            self._tracked_lights = list(set(sum(self._light_groups.values(), [])))
            self._remove_listeners()
            self.fire_event(EVENT_TYPE_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_DATA_TYPE_RESET)

        def _on_reset_finished(*args: Any) -> None:
            """ Triggered when the reset event has finished. """
            self.logger.debug(f"Tracking {len(self._tracked_lights)} lights for manual control.")
            self._reset_reset_timer()
            self._setup_listeners()
            self._request()

        self._reset_timer = async_call_later(self.hass, RESET_DEBOUNCE_TIME, _on_reset_finished)


    #--------------------------------------------#
    #       Listeners Methods
    #--------------------------------------------#

    def _remove_listeners(self, *args: Any) -> None:
        """ Removes the event listeners. """
        while self._listeners:
            self._listeners.pop()()

        self._reset_block_timer()
        self._reset_request_timer()
        self._reset_reset_timer()

    def _setup_listeners(self, *args: Any) -> None:
        """ Sets up the event listeners. """
        self._listeners.append(async_track_automations_changed(self.hass, self._async_on_automations_changed))
        self._listeners.append(async_track_manual_control(self.hass, self._tracked_lights, self._async_on_manual_control, self.is_context_internal))


    #--------------------------------------------#
    #       Timer Methods
    #--------------------------------------------#

    def _reset_block_timer(self) -> None:
        """ Resets the block timer. """
        if self._block_timer:
            self._block_timer()
            self._block_timer = None

    def _reset_request_timer(self) -> None:
        """ Resets the request timer. """
        if self._request_timer:
            self._request_timer()
            self._request_timer = None

    def _reset_reset_timer(self) -> None:
        """ Resets the request timer. """
        if self._reset_timer:
            self._reset_timer()
            self._reset_timer = None


    #--------------------------------------------#
    #       Block Methods
    #--------------------------------------------#

    def _block(self, duration: int) -> None:
        """ Blocks the entity. """
        if self.is_blocked and (datetime.now() - self._blocked_at).total_seconds() < BLOCK_THROTTLE_TIME and duration == self._block_duration:
            return

        self.logger.debug(f"Blocking entity for {duration} seconds.")
        self._reset_block_timer()
        self._block_duration = duration
        self._blocked_at = datetime.now()
        self._blocked_until = self._blocked_at + timedelta(seconds=self._block_duration) if self._block_duration is not None else None
        self._block_timer = async_call_later(self.hass, self._block_duration, self._unblock)
        self.async_schedule_update_ha_state(True)

    def _unblock(self, *args: Any) -> None:
        """ Unblocks the entity. """
        self.logger.debug(f"Unblocking entity for after {self._block_duration} seconds of inactivity.")
        self._reset_block_timer()
        self._request()


    #--------------------------------------------#
    #       Entity Methods
    #--------------------------------------------#

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        blacklist = []
        unused_entities = []

        for i in old_entity_ids:
            if i in self._light_groups:
                blacklist = blacklist + self._light_groups[i]
                unused_entities.append(i)
                continue

        for i in old_entity_ids:
            if i in self._light_groups:
                continue

            if not i in blacklist:
                unused_entities.append(i)

        for i in new_entity_ids:
            for x in unused_entities:
                if x in self._light_groups and i in self._light_groups[x]:
                    unused_entities.remove(x)
                    unused_entities = unused_entities + [t for t in self._light_groups[x] if t not in new_entity_ids]

                if x == i:
                    unused_entities.remove(x)

        if len(unused_entities) > 0:
            self.logger.debug(f"Turning off unused entities: {unused_entities}")
            self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)


    #--------------------------------------------#
    #       Service Methods
    #--------------------------------------------#

    async def _async_service_track_lights(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.track_lights' service. """
        lights = await async_resolve_target(self.hass, service_data.get(CONF_LIGHTS))
        for light in lights:
            if not light in self._tracked_lights:
                self._tracked_lights.append(light)

    async def _async_service_turn_off(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.turn_off' service. """
        if self.is_blocked:
            return

        if not self._current_profile:
            return

        self._request()

    async def _async_service_turn_on(self, **service_data: Any) -> None:
        """ Handles a call to the 'automatic_lighting.turn_on' service. """
        id = service_data.pop(CONF_ID)
        state = service_data.pop(CONF_STATE)
        lights = await async_resolve_target(self.hass, service_data.pop(CONF_LIGHTS))
        attributes = service_data

        if self._request_timer:
            if self._current_profile and self._current_profile.state == STATE_ACTIVE and state == STATE_IDLE:
                return

            self._current_profile = AL_Lighting_Profile(id, state, lights, attributes)
            return

        if self.is_blocked:
            return self._block(self._block_duration)

        if self._current_profile and self._current_profile.id != id:
            self._turn_off_unused_entities(self._current_profile.lights, lights)

        self.logger.debug(f"Turning on profile {id} with following values: {attributes}")
        self._current_profile = AL_Lighting_Profile(id, state, lights, attributes)
        self._state = state
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=lights, **attributes)
        self.async_schedule_update_ha_state(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_automations_changed(self, event_type: str, entity_id: str) -> None:
        """ Triggered when an automation_reloaded event or automation state change event is detected. """
        if event_type == EVENT_AUTOMATION_RELOADED:
            self.logger.debug(f"Detected an automation_reloaded event.")
        else:
            self.logger.debug(f"Detected a state change to {entity_id}.")

        self._reset()

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        """ Triggered when manual control of the lights are detected. """
        self.logger.debug(f"Manual control was detected for the following entities: {entity_ids}")
        self._block(self._block_duration if self.is_blocked else self._block_config_duration)


#-----------------------------------------------------------#
#       AL_Lighting_Profile
#-----------------------------------------------------------#

class AL_Lighting_Profile:
    """ A class that contains lighting properties. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, id: str, state: str, lights: List[str], attributes: Dict[str, Any]):
        self._id = id
        self._state = state
        self._lights = lights
        self._attributes = attributes


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def attributes(self) -> Dict[str, Any]:
        """ Returns the attributes. """
        return self._attributes

    @property
    def id(self) -> str:
        """ Returns the id. """
        return self._id

    @property
    def lights(self) -> List[str]:
        """ Returns the list of lights """
        return self._lights

    @property
    def state(self) -> str:
        """ Returns the state. """
        return self._state