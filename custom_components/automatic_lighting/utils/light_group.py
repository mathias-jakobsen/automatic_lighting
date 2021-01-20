from homeassistant.core import HomeAssistant
from typing import List

class LightGroup():

    def __init__(self, hass: HomeAssistant, entities: List[str], block_individually: bool = False):
        self._blocked_entities = []
        self._block_individually = block_individually
        self._entities = entities
        self._hass = hass


    @property
    def is_blocked(self) -> bool:
        return len(self._blocked_entities) == len(self._entities) if self._block_individually else len(self._blocked_entities) > 0

    def block(self, entity_id: str) -> None:
        if entity_id in self._entities and not entity_id in self._blocked_entities:
            self._blocked_entities.append(entity_id)

    def unblock(self, entity_id: str) -> None:
        if entity_id in self._entities and entity_id in self._blocked_entities:
            self._blocked_entities.remove(entity_id)