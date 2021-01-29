# Automatic Lighting
A Home Assistant custom component that provides a set of events and services to facilitate more advanced lighting setups with Home Assistant's default automation and blueprint engine.

## Blueprints
Ambient Lighting:\
https://raw.githubusercontent.com/mathias-jakobsen/automatic_lighting/dev/blueprints/automation/al_ambient_lighting.yaml

Triggered Lighting:\
https://raw.githubusercontent.com/mathias-jakobsen/automatic_lighting/dev/blueprints/automation/al_triggered_lighting.yaml

Triggered Lighting (RGB):\
https://raw.githubusercontent.com/mathias-jakobsen/automatic_lighting/v1.5/blueprints/automation/al_triggered_lighting_rgb.yaml

## Features
- Provides events and services to set ambient and triggered lighting through Home Assistant automations and blueprints.
- Detects manual control of lights, blocking itself for a set time period to prevent unwanted interference.

## Install
1. Add https://github.com/mathias-jakobsen/automatic_lighting.git to HACS as an integration.
2. Install the component through HACS.
3. Restart Home Assistant.

## Configuration
This integration can only be configured through the frontend by going to Configuration -> Integrations -> ( + Add Integration ) -> Automatic Lighting. To access the options, click the 'Options' button under your newly added integration.

### Options
| Name | Description | Default | Type |
| ---- | ----------- | ------- | ---- |
| block_lights | The lights to track for manual control. | [] | list |
| block_timeout | The time (in seconds) the integration is blocked. | 300 | int

## Events
The integration will fire an event called **automatic_lighting_event** with different event types depending on the situtation.

The available event types:
- _refresh_: This event is fired when the integration is evaluating which automation should be run (ambient or triggered) next. During the evaluation, automations should fire the **automatic_lighting.turn_on** service to mark itself as a candidate for selection. After the evaluation, the appropriate automation is selected and run. The event is fired under following circumstances:

    - When lights are being unblocked.
    - When the **automatic_lighting.turn_off** service is called.
    - When the **automatic_lighting_event (type: restart)** has been fired.
    
  Example: 
  ```
  trigger: 
    - platform: event
      event_type: automatic_lighting_event
      event_data:
        type: refresh
  action:
    - service: automatic_lighting.turn_on
      data:
        group_id: Hallway
        automation_id: 1251662215
        lights: light.office
        brightness: 50
        kelvin: 3000
  ```
  
- _restart_: This event is fired when the the integration is restarting itself. This happens under following circumstances:

    - When the configuration options are changed.
    - When any automation's state is changed (on/off)
    - On an automation_reloaded event.

## Tasks
- [x] Refactor code.
- [ ] Automatic discovery of which entities to track regarding the blocking feature.
- [ ] Blocking of individual lights.
- [ ] Create blueprints to provide Adaptive Lighting functionality.


