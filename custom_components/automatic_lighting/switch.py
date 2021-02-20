#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER_BASE_NAME
from .const import ATTR_ACTIVE_UNTIL, ATTR_BLOCKED_UNTIL, ATTR_LAST_TRIGGERED_AT, ATTR_LAST_TRIGGERED_BY, ATTR_STATUS, CONF_BLOCK_DURATION, CONF_CONSTRAIN, CONF_DURATION, CONF_TRIGGERS, DOMAIN, EVENT_AUTOMATIC_LIGHTING, EVENT_TYPE_REFRESH, SERVICE_CONSTRAIN, SERVICE_REGISTER, SERVICE_SCHEMA_CONSTRAIN, SERVICE_SCHEMA_REGISTER, STATUS_ACTIVE, STATUS_BLOCKED, STATUS_IDLE
from .utils import async_resolve_target, async_track_automations_changed, async_track_manual_control, EntityBase, Timer
from datetime import datetime, timedelta
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN, EVENT_AUTOMATION_RELOADED
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import CONF_ENTITY_ID, CONF_ID, CONF_LIGHTS, EVENT_HOMEASSISTANT_START, SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import Context, HomeAssistant, ServiceCall, State
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import entity_platform
from homeassistant.helpers.event import async_call_later, async_track_state_change
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import get_random_string
from logging import getLogger
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

REFRESH_DEBOUNCE_TIME = 0.4
START_DELAY = 0.4


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    #supervisor = AL_Supervisor(config_entry)
    async_add_entities([AL_Entity(config_entry)], update_before_add=True)
    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(SERVICE_CONSTRAIN, SERVICE_SCHEMA_CONSTRAIN, async_service_constrain)
    platform.async_register_entity_service(SERVICE_REGISTER, SERVICE_SCHEMA_REGISTER, async_service_register)
    #hass.services.async_register(DOMAIN, SERVICE_BLOCK, supervisor.async_service_block, SERVICE_SCHEMA_BLOCK)
    #hass.services.async_register(DOMAIN, SERVICE_REGISTER, supervisor.async_service_register, SERVICE_SCHEMA_REGISTER)
    return True


#-----------------------------------------------------------#
#       Services
#-----------------------------------------------------------#

async def async_service_constrain(entity: AL_Entity, service_call: ServiceCall):
    """ Handles a call to the automatic_lighting.constrain service. """
    entity.is_on and await entity._async_service_constrain(service_call)

async def async_service_register(entity: AL_Entity, service_call: ServiceCall):
    """ Handles a call to the automatic_lighting.register service. """
    entity.is_on and await entity._async_service_register(service_call)


#-----------------------------------------------------------#
#       AL_Entity
#-----------------------------------------------------------#

class AL_Entity(SwitchEntity, RestoreEntity, EntityBase):
    #-----------------------------------------------------------------------------#
    #
    #       Constructor
    #
    #-----------------------------------------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        EntityBase.__init__(self, getLogger(f"{LOGGER_BASE_NAME}.{config_entry.unique_id}"))

        # --- Entity Variables ---------------
        # -------------------------------------------
        self._is_on = None
        self._name = f"{DOMAIN} - {config_entry.unique_id}"

        # --- Logic Variables ---------------
        # -------------------------------------------
        self._listeners = []
        self._refresh_timer = None

        # --- Attributes ----------
        self._active_until = None
        self._blocked_until = None
        self._last_triggered_at = None
        self._last_triggered_by = None
        self._status = None

        # --- Block ----------
        self._block_config_duration = config_entry.options.get(CONF_BLOCK_DURATION)
        self._block_duration = self._block_config_duration
        self._block_enabled = True
        self._block_timer = None

        # --- Profiles ----------
        self._active_profiles = []
        self._idle_profiles = []
        self._current_active_profile = None
        self._current_idle_profile = None


    #-----------------------------------------------------------------------------#
    #
    #       Entity Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dict containing the entity attributes. """
        if not self.is_on:
            return {}

        attributes = { ATTR_STATUS: self._status }
        self._status == STATUS_ACTIVE and self._current_active_profile and attributes.update({ ATTR_ACTIVE_UNTIL: self._active_until, CONF_ENTITY_ID: self._current_active_profile.light_entities, **self._current_active_profile.attributes })
        self._status == STATUS_BLOCKED and attributes.update({ ATTR_BLOCKED_UNTIL: self._blocked_until })
        self._status == STATUS_IDLE and self._current_idle_profile and attributes.update({ CONF_ENTITY_ID: self._current_idle_profile.light_entities, **self._current_idle_profile.attributes })
        attributes.update({ ATTR_LAST_TRIGGERED_AT: self._last_triggered_at, ATTR_LAST_TRIGGERED_BY: self._last_triggered_by })

        return attributes

    @property
    def is_on(self) -> bool:
        """ Gets a boolean indicating whether the entity is turned on. """
        return self._is_on

    @property
    def name(self) -> str:
        """ Gets the name of entity. """
        return self._name

    @property
    def should_poll(self) -> bool:
        """ Gets a boolean indicating whether Home Assistant should automatically poll the entity. """
        return True

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_added_to_hass(self) -> None:
        """ Triggered when the entity has been added to HomeAssistant. """
        last_state = await self.async_get_last_state()

        if not last_state or last_state.state == STATE_ON:
            if self.hass.is_running:
                return await self.async_turn_on()
            else:
                return self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self.async_turn_on)

        await self.async_turn_off()

    async def async_will_remove_from_hass(self) -> None:
        """ Triggered when the entity is being removed from Home Assistant. """
        await self._async_turn_off()


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    async def async_turn_off(self, *args: Any) -> None:
        """ Turns off the entity. """
        if self._is_on is not None and not self._is_on:
            return

        self._is_on = False
        await self._async_turn_off()

    async def async_turn_on(self, *args: Any) -> None:
        """ Turns on the entity. """
        if self._is_on:
            return

        self._is_on = True
        await self._async_turn_on()


    #-----------------------------------------------------------------------------#
    #
    #       Logic Section
    #
    #-----------------------------------------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def is_active(self) -> bool:
        """ Gets a boolean indicating whether a trigger has activated a profile. """
        return self._current_active_profile is not None

    @property
    def is_blocked(self) -> bool:
        """ Gets a boolean indicating whether the entity is blocked. """
        return self._block_timer is not None

    @property
    def is_refreshing(self) -> bool:
        """ Gets a boolean indicating whether the entity is refreshing. """
        return self._refresh_timer is not None and self._refresh_timer.is_running

    @property
    def is_triggered(self) -> bool:
        """ Gets a boolean indicating whether any of the triggers have been triggered. """
        return any((state := self.hass.states.get(entity)) is not None and state.state == STATE_ON for entity in self.trigger_entities)

    @property
    def light_entities(self) -> List[str]:
        """ Gets a list of the registered light entities. """
        return list(set(sum([profile.light_entities for profile in self._active_profiles + self._idle_profiles], [])))

    @property
    def trigger_entities(self) -> List[str]:
        """ Gets a list of the registered trigger entities. """
        return list(set(sum([profile.trigger_entities if profile.trigger_entities is not None else [] for profile in self._active_profiles], [])))


    #--------------------------------------------#
    #       State Methods
    #--------------------------------------------#

    async def _async_turn_off(self) -> None:
        """ Resets the internal entity logic. """
        self._remove_listeners()
        self.async_schedule_update_ha_state(True)

    async def _async_turn_on(self) -> None:
        """ Turns on the internal entity logic. """
        self._listeners.append(async_call_later(self.hass, START_DELAY, self._refresh_profiles))


    #--------------------------------------------#
    #       Listener Methods
    #--------------------------------------------#

    def _remove_listeners(self) -> None:
        """ Removes the event listeners & resets the timers. """
        while self._listeners:
            self._listeners.pop()()

        self._reset_block_timer()
        self._reset_current_active_profile()

    def _setup_listeners(self) -> None:
        """ Sets up the event listeners. """
        self._listeners.append(async_track_automations_changed(self.hass, self._async_on_automations_changed))
        self._listeners.append(async_track_manual_control(self.hass, self.light_entities, self._async_on_manual_control, self.is_context_internal))
        self._listeners.append(async_track_state_change(self.hass, self.trigger_entities, self._async_on_trigger_state_change))


    #--------------------------------------------#
    #       Block Methods
    #--------------------------------------------#

    async def _block(self, duration: Union[int, None] = None) -> None:
        """ Blocks the entity. """
        self.logger.debug(f"Blocking entity for {duration} seconds.")
        self._reset_block_timer()
        self._block_duration = duration
        self._blocked_until = datetime.now() + timedelta(seconds=self._block_duration) if self._block_duration is not None else None
        self._block_timer = Timer(self.hass, self._block_duration, self._unblock)
        self._update()

    async def _unblock(self, *args: Any) -> None:
        """ Unblocks the entity. """
        self.logger.debug(f"Unblocking entity for after {self._block_duration} seconds of inactivity.")
        self._reset_block_timer()
        self._update()


    #--------------------------------------------#
    #       Profile Methods
    #--------------------------------------------#

    def _refresh_profiles(self, *args: Any) -> None:
        """ Refreshes the profiles. """
        if self.is_refreshing:
            self._refresh_timer.cancel()
        else:
            self._active_profiles = []
            self._idle_profiles = []
            self.fire_event(EVENT_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_TYPE_REFRESH)
            self._remove_listeners()

        async def async_refresh():
            self._setup_listeners()
            self._update()

        self._refresh_timer = Timer(self.hass, REFRESH_DEBOUNCE_TIME, async_refresh)

    def _set_active_profile(self) -> Union[Dict[str, Any], None]:
        """ Attempts to match and activate an active profile. """
        new_profile = next(filter(lambda profile: profile.is_valid(), self._active_profiles), None)

        if new_profile is None:
            if not self.is_active:
                return

            new_profile = self._current_active_profile
            self._reset_current_active_profile()

        self._active_until = None
        self._current_active_profile = new_profile
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self._current_active_profile.light_entities, **new_profile.attributes)
        self._turn_off_unused_entities(self.light_entities, new_profile.light_entities)

        return self._current_active_profile

    def _set_idle_profile(self) -> Union[Dict[str, Any], None]:
        """ Attempts to match and activate an idle profile."""
        new_profile = next(filter(lambda profile: profile.is_valid(), self._idle_profiles), None)

        if new_profile is None:
            self._current_idle_profile = None
            return self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=self.light_entities)

        self._current_idle_profile = new_profile
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self._current_idle_profile.light_entities, **new_profile.attributes)
        self._turn_off_unused_entities(self.light_entities, new_profile.light_entities)

        return new_profile


    #--------------------------------------------#
    #       Service Methods
    #--------------------------------------------#

    async def _async_service_constrain(self, service_call: ServiceCall) -> None:
        """ Handles a call to the automatic_lighting.constrain service. """
        data = { **service_call.data }
        constrain = data.pop(CONF_CONSTRAIN)
        id = data.pop(CONF_ID, self._get_profile_id(service_call.context))

        if id is None:
            return

        profile = next(filter(lambda profile: profile.id == id, self._active_profiles + self._idle_profiles), None)
        if profile is not None:
            self.logger.debug(f"Setting constraint mode of profile '{profile.id}' to {constrain}.")
            profile.set_constrain(constrain)

    async def _async_service_register(self, service_call: ServiceCall) -> None:
        """ Handles a call to the automatic_lighting.register service. """
        data = { **service_call.data }
        id = data.pop(CONF_ID, self._get_profile_id(service_call.context))

        if id is None:
            id = get_random_string()

        data.pop(CONF_ENTITY_ID)
        duration = data.pop(CONF_DURATION, None)
        lights = await async_resolve_target(self.hass, data.pop(CONF_LIGHTS, []))
        triggers = await async_resolve_target(self.hass, data.pop(CONF_TRIGGERS, None))
        profile = AL_Profile(self.hass, id, lights, data, triggers, duration)

        if len(triggers) > 0:
            self._active_profiles.append(profile)
        else:
            self._idle_profiles.append(profile)


    #--------------------------------------------#
    #       Timer Methods
    #--------------------------------------------#

    def _reset_block_timer(self) -> None:
        """ Resets the block timer. """
        if self._block_timer:
            self._block_timer.cancel()
            self._block_timer = None

    def _reset_current_active_profile(self) -> None:
        """ Resets the profile timer. """
        if self._current_active_profile:
            self._current_active_profile.cancel_timer()
            self._current_active_profile = None


    #--------------------------------------------#
    #       Update Methods
    #--------------------------------------------#

    def _update(self) -> None:
        """ Updates the status of the entity. """
        if not self.is_on:
            return self.async_schedule_update_ha_state(True)

        if self.is_active and self.is_blocked:
            self._reset_current_active_profile()

        if self.is_blocked:
            self._status = STATUS_BLOCKED
            return self.async_schedule_update_ha_state(True)

        if self.is_active:
            return self.async_schedule_update_ha_state(True)

        if self.is_triggered:
            if self._set_active_profile():
                self._status = STATUS_ACTIVE
                return self.async_schedule_update_ha_state(True)

        self._status = STATUS_IDLE
        self._set_idle_profile()
        return self.async_schedule_update_ha_state(True)


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def _async_on_active_profile_finished(self) -> None:
        """ Triggered when the profile has finished. """
        self._reset_current_active_profile()
        self._update()

    async def _async_on_automations_changed(self, event_type: str, entity_id: str) -> None:
        """ Triggered when an automation_reloaded event or automation state change event is detected. """
        if event_type == EVENT_AUTOMATION_RELOADED:
            self.logger.debug(f"Detected an automation_reloaded event.")
        else:
            self.logger.debug(f"Detected a state change to {entity_id}.")
        self._refresh_profiles()

    async def _async_on_manual_control(self, entity_ids: List[str], context: Context) -> None:
        """ Triggered when manual control of the lights are detected. """
        self.logger.debug(f"Manual control was detected for following entities: {entity_ids}")
        await self._block(self._block_duration if self.is_blocked else self._block_config_duration)

    async def _async_on_trigger_state_change(self, entity_id: str, old: State, new: State) -> None:
        """ Triggered when the state of a trigger changes. """
        if old is not None and old.state == new.state:
            return

        if new.state == STATE_OFF:
            if self.is_active and not self._current_active_profile.is_triggered:
                self._active_until = datetime.now() + timedelta(seconds=self._current_active_profile.duration)
                self._current_active_profile.start_timer(self._async_on_active_profile_finished)
                self._update()
            return

        if self.is_blocked:
            return await self._block(duration=self._block_duration)

        if self._current_active_profile and self._current_active_profile.is_timer_running:
            if self._current_active_profile.is_triggered:
                self._active_until = None
                self._current_active_profile.cancel_timer()
            else:
                self._current_active_profile.start_timer(self._async_on_active_profile_finished)

        self._last_triggered_at = datetime.now()
        self._last_triggered_by = entity_id
        self._update()


    #--------------------------------------------#
    #       Helper Methods
    #--------------------------------------------#

    def _get_profile_id(self, context: Context) -> str | None:
        """ Gets the profile id based on a context. """
        entity_ids = self.hass.states.async_entity_ids(AUTOMATION_DOMAIN)

        for entity_id in entity_ids:
            state = self.hass.states.get(entity_id)

            if not state:
                continue

            if state.context.parent_id == context.parent_id:
                return entity_id

        return None

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        unused_entities = [entity_id for entity_id in old_entity_ids if entity_id not in new_entity_ids]
        self.logger.debug(f"Turning following unused entities off: {unused_entities}")
        self.call_service(LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)


#-----------------------------------------------------------#
#       AL_Profile
#-----------------------------------------------------------#

class AL_Profile:
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, id: str, lights: List[str], attributes: Dict[str, Any], triggers: List[str] | None = None, duration: int | None = None):
        self._attributes = attributes
        self._duration = duration
        self._hass = hass
        self._id = id
        self._is_constrained = False
        self._light_entities = lights
        self._timer = None
        self._trigger_entities = triggers


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def attributes(self) -> Dict[str, Any]:
        """ Gets a dict containing the attributes used in light service calls. """
        return self._attributes

    @property
    def duration(self) -> int | None:
        """ Gets the duration of the profile (returns None if it not an active profile). """
        return self._duration

    @property
    def id(self) -> str:
        """ Gets the profile id. """
        return self._id

    @property
    def is_constrained(self) -> bool:
        """ Gets a boolean indicating whether the profile is constrained. """
        return self._is_constrained

    @property
    def is_timer_running(self) -> bool:
        """ Gets a boolean indicating wether the timer is running. """
        return self._timer is not None and self._timer.is_running

    @property
    def is_triggered(self) -> bool:
        """ Gets a boolean indicating whether the profile's triggers have been triggered. """
        return any((state := self._hass.states.get(entity)) is not None and state.state == STATE_ON for entity in (self._trigger_entities if self._trigger_entities is not None else []))

    @property
    def light_entities(self) -> List[str]:
        """ Gets a list of the light entities in the profile. """
        return self._light_entities

    @property
    def trigger_entities(self) -> List[str] | None:
        """ Gets a list of the trigger entities in the profile (returns an empty list if it is not an active profile). """
        return self._trigger_entities


    #--------------------------------------------#
    #       Constrain Methods
    #--------------------------------------------#

    def set_constrain(self, constrain: bool) -> None:
        """ Set whether the profile is constrained. """
        self._is_constrained = constrain


    #--------------------------------------------#
    #       Timer Methods
    #--------------------------------------------#

    def cancel_timer(self) -> None:
        """ Cancels the timer if it has been started. """
        if self._timer is None:
            return

        self._timer.cancel()
        self._timer = None

    def start_timer(self, action: Callable[[], None]) -> None:
        """ Starts the timer with the duration of the profile (only works for active profiles). """
        if self._duration is None:
            return

        self.cancel_timer()
        self._timer = Timer(self._hass, self._duration, action)


    #--------------------------------------------#
    #       Validation Methods
    #--------------------------------------------#

    def is_valid(self) -> bool:
        """ Determines whether the profile is valid for use. """
        if self._is_constrained:
            return False

        if self._trigger_entities is not None and not self.is_triggered:
            return False

        return True