#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from __future__ import annotations
from . import LOGGER_BASE_NAME
from .const import CONF_GROUP, CONF_NEW_STATE, CONF_OLD_STATE, DOMAIN, EVENT_AUTOMATIC_LIGHTING, EVENT_TYPE_REFRESH, EVENT_TYPE_RESTART, NAME, SERVICE_REGISTER, SERVICE_SCHEMA_REGISTER, SERVICE_SCHEMA_TURN_OFF, SERVICE_SCHEMA_TURN_ON, STATE_AMBIANCE, STATE_BLOCKED, STATE_TRIGGERED
from .utils import Timer, async_resolve_target, async_track_manual_control, EntityBase, EntityHelpers
from datetime import datetime, timedelta
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN, EVENT_AUTOMATION_RELOADED
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_DOMAIN, ATTR_SERVICE, ATTR_SERVICE_DATA, CONF_ENTITY_ID, CONF_ID, CONF_LIGHTS, CONF_NAME, CONF_TYPE, EVENT_CALL_SERVICE, EVENT_HOMEASSISTANT_START, EVENT_SERVICE_REGISTERED, EVENT_STATE_CHANGED, SERVICE_RELOAD, SERVICE_TOGGLE, SERVICE_TURN_OFF, SERVICE_TURN_ON
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
RESTART_DEBOUNCE_TIME = 0.2
START_DELAY = 0.5


#-----------------------------------------------------------#
#       Entry Setup
#-----------------------------------------------------------#

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: Callable) -> bool:
    #circadian_lighting_sensor = CircadianLightingSensor()
    supervisor = AL_Supervisor(config_entry)


    async_add_entities([supervisor], update_before_add=True)


    platform = entity_platform.current_platform.get()
    platform.async_register_entity_service(SERVICE_REGISTER, SERVICE_SCHEMA_REGISTER, async_service_register)
    #platform.async_register_entity_service(SERVICE_TURN_OFF, SERVICE_SCHEMA_TURN_OFF, async_service_turn_off)
    #platform.async_register_entity_service(SERVICE_TURN_ON, SERVICE_SCHEMA_TURN_ON, async_service_turn_on)
    return True


#-----------------------------------------------------------#
#       Services
#-----------------------------------------------------------#

async def async_service_register(entity: AL_Supervisor, service_call: ServiceCall) -> None:
    await entity.async_service_register(service_call)


#-----------------------------------------------------------#
#       AL_Supervisor
#-----------------------------------------------------------#

class AL_Supervisor(EntityBase):
    """ The entity that acts as a supervisor for the automatic lighting system. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, config_entry: ConfigEntry):
        super().__init__(getLogger(f"{LOGGER_BASE_NAME}.supervisor"))
        self._automations_reloading = False
        self._config = config_entry.options
        self._groups = {}
        self._name = f"{NAME} Supervisor"
        self._remove_listeners = []
        self._restart_timer = None


    #--------------------------------------------#
    #       Properties (HA)
    #--------------------------------------------#

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        """ Gets a dictionary containing the entity attributes. """
        return { key: group.state for [key, group] in sorted(self._groups.items(), key=lambda kv: kv[0]) }

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
        return f"{len(self._groups)}"

    @property
    def unique_id(self) -> str:
        """ Gets the unique ID of entity. """
        return self._name


    #--------------------------------------------#
    #       Properties (HA)
    #--------------------------------------------#

    @property
    def is_restarting(self) -> bool:
        """ Gets a boolean indicating whether the entity is restarting. """
        return self._restart_timer is not None and self._restart_timer.is_running

    @property
    def tracked_lights(self) -> List[str]:
        return set(sum([group.tracked_lights for group in self._groups.values()], []))


    #--------------------------------------------#
    #       Init Methods
    #--------------------------------------------#

    def remove_listeners(self, *args: Any) -> None:
        self.logger.debug(f"Removes event listeners and cleans up timers.")

        while self._remove_listeners:
            self._remove_listeners.pop()()

        for group in self._groups:
            group.reset()

        self._restart_timer and self._restart_timer.cancel()

    def setup_listeners(self, *args: Any) -> None:
        """ Sets up event listeners. """
        self.logger.debug(f"Setting up event listeners.")
        self._remove_listeners.append(self.hass.bus.async_listen(EVENT_CALL_SERVICE, self.async_on_automation_reload))
        self._remove_listeners.append(self.hass.bus.async_listen(EVENT_AUTOMATION_RELOADED, self.async_on_automation_reloaded))
        self._remove_listeners.append(self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.async_on_automation_state_change))
        self._remove_listeners.append(self.hass.bus.async_listen(EVENT_CALL_SERVICE, self.async_on_light_service_call))
        self._remove_listeners.append(async_call_later(self.hass, START_DELAY, self.restart))


    #--------------------------------------------#
    #       Event Handlers
    #--------------------------------------------#

    async def async_on_automation_reload(self, event: Event) -> None:
        """ Triggered when the automations are about to reload """
        domain = event.data.get(ATTR_DOMAIN, None)
        service = event.data.get(ATTR_SERVICE, None)

        if domain != AUTOMATION_DOMAIN:
            return

        if service != SERVICE_RELOAD:
            return

        self.logger.debug(f"Detected an upcoming automation reload event.")
        self._automations_reloading = True

    async def async_on_automation_reloaded(self, event: Event) -> None:
        """ Triggered when the an automation reloaded event has been fired. """
        self.logger.debug(f"Detected an automation reloaded event.")
        self._automations_reloading = False
        self.restart()

    async def async_on_automation_state_change(self, event: Event) -> None:
        """ Triggered when an automation has changed state. """
        if self._automations_reloading:
            return

        domain = event.data.get(CONF_ENTITY_ID, "").split(".")[0]

        if domain != AUTOMATION_DOMAIN:
            return

        old_state = event.data.get(CONF_OLD_STATE, None)
        new_state = event.data.get(CONF_NEW_STATE, None)

        if old_state is None or new_state is None:
            return

        if old_state.state == new_state.state:
            return

        self.logger.debug(f"Detected an automation state change event.")
        self.restart()

    async def async_on_light_service_call(self, event: Event) -> None:
        """ Triggered when a service call within the light domain is detected. """
        domain = event.data.get(ATTR_DOMAIN, None)

        if domain != LIGHT_DOMAIN:
            return

        service_data = event.data.get(ATTR_SERVICE_DATA, {})
        resolved_target = await async_resolve_target(self.hass, service_data)

        for group in self._groups.values():
            if group.is_context_internal(event.context):
                continue

            if len([id for id in resolved_target if id in group.tracked_lights]) > 0:
                group.block()


    #--------------------------------------------#
    #       Refresh/Restart Methods
    #--------------------------------------------#

    def refresh(self, group_id: str, bypass_block: bool = False) -> None:
        """ Refreshes the specified group. """
        if not group_id in self._groups:
            return

        group = self._groups.get(group_id)
        refresh_timer = group.refresh_timer

        if refresh_timer and refresh_timer.is_running:
            refresh_timer.cancel()
        else:
            self.logger.debug(f"Firing refresh event for group {group_id}.")
            group.refresh_profile = None
            self.fire_event(EVENT_AUTOMATIC_LIGHTING, group=group_id, type=EVENT_TYPE_REFRESH)

        def refresh():
            group.refresh()

            if all([group.refresh_timer is None or not group.refresh_timer.is_running for group in self._groups.values()]):
                self.logger.debug("All groups have finished refreshing.")
                self.async_schedule_update_ha_state(True)

        group.refresh_timer = Timer(self.hass, REFRESH_DEBOUNCE_TIME, refresh)

    def restart(self, *args: Any) -> None:
        """ Restarts the supervisor. """
        if self.is_restarting:
            self._restart_timer.cancel()
        else:
            self.logger.debug(f"Restarting automatic lighting. Firing event {EVENT_AUTOMATIC_LIGHTING} (type: {EVENT_TYPE_RESTART}).")
            self.logger.debug(f"{len(self._groups)} groups are being removed.")
            self.logger.debug(f"{len(self.tracked_lights)} lights are being untracked.")

            for key in [key for key in self._groups]:
                self._groups[key].refresh_timer and self._groups[key].refresh_timer.cancel()
                del self._groups[key]

            self.fire_event(EVENT_AUTOMATIC_LIGHTING, entity_id=self.entity_id, type=EVENT_TYPE_RESTART)

        def restart():
            self.logger.debug(f"{len(self._groups)} groups have been created.")
            self.logger.debug(f"{len(self.tracked_lights)} lights are being tracked for manual control.")

            if len(self._groups) == 0:
                self.logger.debug("No groups were registered.")
                return self.async_schedule_update_ha_state(True)

            for group_id in self._groups:
                self.refresh(group_id)

        self._restart_timer = Timer(self.hass, RESTART_DEBOUNCE_TIME, restart)


    #--------------------------------------------#
    #       Service Methods
    #--------------------------------------------#

    async def async_service_register(self, service_call: ServiceCall) -> None:
        if not self.is_restarting:
            return

        group = service_call.data.get(CONF_GROUP, None)
        lights = service_call.data.get(CONF_LIGHTS, None)

        if group and not group in self._groups:
            self._groups[group] = AL_Group(self.hass, group)

        if lights:
            self._groups[group].track_lights(await async_resolve_target(self.hass, lights))


#-----------------------------------------------------------#
#       AL_Group
#-----------------------------------------------------------#

class AL_Group(EntityHelpers):
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, id: str):
        super().__init__(getLogger(f"{LOGGER_BASE_NAME}.group.{id}"))
        self._hass = hass
        self._id = id
        self._tracked_lights = []
        self.current_profile = None
        self.is_blocked = False
        self.refresh_profile = None
        self.refresh_timer = None
        self.state = STATE_AMBIANCE


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def id(self) -> str:
        """ Gets the id of the group. """
        return self._id

    @property
    def tracked_lights(self) -> List[str]:
        """ Gets the list of tracked lights. """
        return self._tracked_lights


    #--------------------------------------------#
    #       Methods
    #--------------------------------------------#

    def refresh(self, bypass_block: bool = False) -> None:
        """ Refreshes the group. """
        if not self.is_blocked or (self.is_blocked and bypass_block):
            if self.refresh_profile:
                if self.current_profile:
                    self._turn_off_unused_entities(self.current_profile.entity_ids, self.refresh_profile.entity_ids)

                self.current_profile = self.refresh_profile
                self.state = self.current_profile.type

                return self.call_service(self._hass, LIGHT_DOMAIN, SERVICE_TURN_ON, entity_id=self.current_profile.entity_ids, **self.current_profile.attributes)

            if self.current_profile:
                self.call_service(self._hass, LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=self.current_profile.entity_ids)

            self.state = STATE_AMBIANCE

    def track_lights(self, lights: List[str]) -> None:
        """ Add lights to the list of tracked lights. """
        for light in lights:
            if not light in self._tracked_lights:
                self._tracked_lights.append(light)


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _turn_off_unused_entities(self, old_entity_ids: List[str], new_entity_ids: List[str]) -> None:
        """ Turns off entities if they are not used in the current profile. """
        unused_entities = [entity_id for entity_id in old_entity_ids if entity_id not in new_entity_ids]
        self.call_service(self._hass, LIGHT_DOMAIN, SERVICE_TURN_OFF, entity_id=unused_entities)


#-----------------------------------------------------------#
#       AL_Group
#-----------------------------------------------------------#