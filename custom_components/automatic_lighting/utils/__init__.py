#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from config.custom_components.automatic_lighting.const import CONF_NEW_STATE, CONF_OLD_STATE
from .entity_base import EntityBase
from .timer import Timer
from homeassistant.components.automation import DOMAIN as AUTOMATION_DOMAIN, EVENT_AUTOMATION_RELOADED
from homeassistant.const import ATTR_DOMAIN, ATTR_SERVICE, ATTR_SERVICE_DATA, CONF_ENTITY_ID, EVENT_CALL_SERVICE, EVENT_STATE_CHANGED, SERVICE_RELOAD
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Entity
#-----------------------------------------------------------#

async def async_resolve_target(hass: HomeAssistant, target: Union[str, List[str], Dict[str, Any]]) -> List[str]:
    """ Resolves the target argument of a service call and returns a list of entity ids. """
    if isinstance(target, str):
        return cv.ensure_list_csv(target)

    if isinstance(target, list):
        return target

    result = []

    entity_registry = await hass.helpers.entity_registry.async_get_registry()
    entity_entries = entity_registry.entities.values()

    target_areas = target.get("area_id", [])
    target_devices = target.get("device_id", [])
    target_entities = target.get("entity_id", [])

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

    return result


#-----------------------------------------------------------#
#       Trackers
#-----------------------------------------------------------#

def async_track_automations_changed(hass: HomeAssistant, action: Callable[[str, str], None]) -> Callable[[], None]:
    """ Tracks automation changes (call_service, reloaded event). """
    reloading = False
    remove_listeners = []

    def clear_listeners() -> None:
        while remove_listeners:
            remove_listeners.pop()()

    async def on_automation_reloaded(event: Event) -> None:
        nonlocal reloading
        reloading = False
        await action(EVENT_AUTOMATION_RELOADED, [])

    async def on_service_call(event: Event) -> None:
        nonlocal reloading

        domain = event.data.get(ATTR_DOMAIN, None)
        service = event.data.get(ATTR_SERVICE, None)

        if domain != AUTOMATION_DOMAIN:
            return

        if service == SERVICE_RELOAD:
            reloading = True

    async def on_state_changed(event: Event) -> None:
        nonlocal reloading

        if reloading:
            return

        entity_id = event.data.get(CONF_ENTITY_ID, "")
        domain = entity_id.split(".")[0]

        if domain != AUTOMATION_DOMAIN:
            return

        old_state = event.data.get(CONF_OLD_STATE, None)
        new_state = event.data.get(CONF_NEW_STATE, None)

        if old_state is None or new_state is None:
            return

        if old_state.state == new_state.state:
            return

        await action(EVENT_STATE_CHANGED, entity_id)

    remove_listeners.append(hass.bus.async_listen(EVENT_AUTOMATION_RELOADED, on_automation_reloaded))
    remove_listeners.append(hass.bus.async_listen(EVENT_CALL_SERVICE, on_service_call))
    remove_listeners.append(hass.bus.async_listen(EVENT_STATE_CHANGED, on_state_changed))

    return clear_listeners

def async_track_manual_control(hass: HomeAssistant, entity_id: Union[str, List[str]], action: Callable[[List[str], Context], None], context_validator: Callable[[Context], bool]) -> Callable[[], None]:
    """ Tracks manual control of specific entities. """
    async def on_service_call(event: Event) -> None:
        entity_ids = cv.ensure_list_csv(entity_id)
        domains = [id.split(".")[0] for id in entity_ids]

        if not event.data.get(ATTR_DOMAIN, "") in domains:
            return

        service_data = event.data.get(ATTR_SERVICE_DATA, {})
        resolved_target = await async_resolve_target(hass, service_data)
        matched_entity_ids = [id for id in resolved_target if id in entity_ids]

        if len(matched_entity_ids) == 0:
            return

        if context_validator(event.context):
            return

        await action(matched_entity_ids, event.context)

    return hass.bus.async_listen(EVENT_CALL_SERVICE, on_service_call)

