# Automatic Lighting
A Home Assistant custom component that provides a set of events and services to facilitate more advanced lighting setups with Home Assistant's default automation and blueprint engine.

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

## Tasks
- [ ] Refactor code.
- [ ] Automatic discovery of which entities to track regarding the blocking feature.
- [ ] Blocking of individual lights.
- [ ] Create blueprints to provide Adaptive Lighting functionality.


