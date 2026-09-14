# Echoes of Tomorrow

Adapters for the sample game [Echoes of Tomorrow](https://github.com/vnflight/echoes_of_tomorrow), played through on Ren'Py 8.5.2 and 7.5.2 (the manifest ids `echoes_of_tomorrow` and `echoes_of_tomorrow_r7` point at the same two files).

- `echoes_of_tomorrow.rpy` (installed as `vnf_inventory_stats.rpy`): names the HUD panels (KIT, LOG, MAP) and their controls, filters repeated HUD chrome out of the scraped text, captures the terminal screen's rows before the game hides or replaces them, exposes the station stats and the equipment inventory, and limits Marcus's location to the map.
- `echoes_progress.rpy` (installed as `vnf_echoes_progress.rpy`): story-beat and ending tracking for the `progress` verb.
