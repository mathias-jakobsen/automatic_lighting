#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.template import is_template_string, Template
from homeassistant.util import get_random_string
from logging import Logger
from typing import Any, Dict, Generic, TypeVar


#-----------------------------------------------------------#
#       Type Variables
#-----------------------------------------------------------#

T = TypeVar("T", bound=Entity)


#-----------------------------------------------------------#
#       Class - EntityModel
#-----------------------------------------------------------#

class EntityModel(Generic[T]):
    """ Provides a set of base functions for an entity model. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, hass: HomeAssistant, logger: Logger, entity: T):
        self._context_unique_id = get_random_string(10)
        self._entity = entity
        self._hass = hass
        self._logger = logger


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def entity(self) -> T:
        """ Gets the entity. """
        return self._entity

    @property
    def hass(self) -> HomeAssistant:
        """ Gets the Home Assistant instance. """
        return self._hass

    @property
    def logger(self) -> Logger:
        """ Gets the logger. """
        return self._logger


    #--------------------------------------------#
    #       Init Methods
    #--------------------------------------------#

    async def async_turn_off(self, *args: Any) -> None:
        """ Turns off the model. """
        pass

    async def async_turn_on(self, *args: Any) -> None:
        """ Turns on the model. """
        pass


    #--------------------------------------------#
    #       Context Methods
    #--------------------------------------------#

    def create_context(self) -> Context:
        """ Creates a new context. """
        return Context(id=f"{self._context_unique_id}{get_random_string(30)}")

    def is_context_internal(self, context: Context) -> bool:
        """ Determines whether the context is of internal origin (created by the model). """
        return context.id.startswith(self._context_unique_id)


    #--------------------------------------------#
    #       Action Methods
    #--------------------------------------------#

    def call_service(self, domain: str, service: str, **service_data: Any):
        """ Calls a service. """
        context = self.create_context()
        parsed_service_data = self._parse_service_data(service_data)
        self._entity.async_set_context(context)
        self._hass.async_create_task(self._hass.services.async_call(domain, service, { **parsed_service_data }, context=context))

    def fire_event(self, event_type: str, **event_data: Any):
        """ Fires an event using the Home Assistant bus. """
        context = self.create_context()
        self._entity.async_set_context(context)
        self._hass.bus.async_fire(event_type, event_data, context=context)


    #--------------------------------------------#
    #       Private Methods
    #--------------------------------------------#

    def _parse_service_data(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """ Parses the service data by rendering possible templates. """
        result = {}

        for key, value in service_data.items():
            if isinstance(value, str) and is_template_string(value):
                try:
                    template = Template(value, self._hass)
                    result[key] = template.async_render()
                except Exception as e:
                    self._logger.warn(f"Error parsing {key} in service_data {service_data}: Invalid template was given -> {value}.")
                    self._logger.warn(e)
            else:
                result[key] = value

        return result