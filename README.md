# Automatic Lighting
A Home Assistant custom component that provides a set of events and services to facilitate more advanced lighting setups with Home Assistant's default automation and blueprint engine.

## Features
- Provides events and services to set ambient and triggered lighting through Home Assistant automations and blueprints.
- Detects manual control of lights, blocking itself for a set time period to prevent unwanted interference.

## Install
1. Add https://github.com/mathias-jakobsen/automatic_lighting.git to HACS as an integration.
2. Install the component as an integration through HACS.
3. Restart Home Assistant.
4. Go to Configuration -> Integrations to setup an instance of the component.

## Tasks
- [ ] Refactor code.
- [ ] Automatic discovery of which entities to track regarding the blocking feature.
- [ ] Blocking of individual lights.
- [ ] Create blueprints to provide Adaptive Lighting functionality.


