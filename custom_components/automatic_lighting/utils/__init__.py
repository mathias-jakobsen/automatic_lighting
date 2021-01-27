#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from .entity_model import EntityModel
from .timer import Timer
from homeassistant.const import ATTR_DOMAIN, ATTR_SERVICE_DATA, EVENT_CALL_SERVICE
from homeassistant.core import Context, Event, HomeAssistant
from homeassistant.helpers import config_validation as cv
from typing import Any, Callable, Dict, List, Union


#-----------------------------------------------------------#
#       Services
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

def async_track_manual_control(hass: HomeAssistant, entity_id: Union[str, List[str]], action: Callable[[List[str]], Context], context_validator: Callable[[Context], bool]) -> Callable[[], None]:
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

        action(matched_entity_ids, event.context)

    return hass.bus.async_listen(EVENT_CALL_SERVICE, on_service_call)

