#-----------------------------------------------------------#
#       Imports
#-----------------------------------------------------------#

from homeassistant.core import Context
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.template import is_template_string, Template
from homeassistant.util import get_random_string
from logging import Logger
from typing import Any, Dict


#-----------------------------------------------------------#
#       Constants
#-----------------------------------------------------------#

CONTEXT_MAX_LENGTH = 36


#-----------------------------------------------------------#
#       Class - EntityBase
#-----------------------------------------------------------#

class EntityBase(Entity):
    """ Provides a set of base functions for an entity. """
    #--------------------------------------------#
    #       Constructor
    #--------------------------------------------#

    def __init__(self, logger: Logger):
        self._context_unique_id = get_random_string(6)
        self._logger = logger


    #--------------------------------------------#
    #       Properties
    #--------------------------------------------#

    @property
    def logger(self) -> Logger:
        """ Gets the logger. """
        return self._logger


    #--------------------------------------------#
    #       Context Methods
    #--------------------------------------------#

    def create_context(self) -> Context:
        """ Creates a new context. """
        return Context(id=f"{self._context_unique_id}{get_random_string(CONTEXT_MAX_LENGTH)}"[:CONTEXT_MAX_LENGTH])

    def is_context_internal(self, context: Context) -> bool:
        """ Determines whether the context is of internal origin (created by the class instance). """
        return context.id.startswith(self._context_unique_id)


    #--------------------------------------------#
    #       Action Methods
    #--------------------------------------------#

    def call_service(self, domain: str, service: str, **service_data: Any) -> None:
        """ Calls a service. """
        context = self.create_context()
        self.async_set_context(context)
        parsed_service_data = self._parse_service_data(service_data)
        self.hass.async_create_task(self.hass.services.async_call(domain, service, { **parsed_service_data }, context=context, blocking=True))


    def fire_event(self, event_type: str, **event_data: Any) -> None:
        """ Fires an event using the Home Assistant bus. """
        context = self.create_context()
        self.async_set_context(context)
        self.hass.bus.async_fire(event_type, event_data, context=context)


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