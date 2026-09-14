# Roadwarden

Unofficial adapters for Roadwarden (GOG build, Ren'Py 7.5.2, Python 2). See the notice for commercial-game adapters in the top-level README.

- `roadwarden.rpy` (installed as `vnf_inventory_stats.rpy`): renames the game's menu buttons to what they open (inventory, character sheet, journal), filters bookkeeping labels out of the scraped text, exposes inventory and character stats, registers the overlay and shop screens, and adds the game-specific commands (travel, map).
- `roadwarden_progress.rpy` (installed as `vnf_roadwarden_progress.rpy`): day and quest progress for the `progress` verb.
