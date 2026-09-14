################################################################################
## Inventory/Stats Override for LLM Player
##
## Overrides _vnf_get_inventory_stats() from vnflight.rpy to expose this
## game's actual state: the evidence Elara has collected, her trust/relationship
## meters, and key story flags.
##
## This runs at init -989 so it executes AFTER vnflight.rpy's default
## definition at init -990, replacing it.
################################################################################

init -989 python:

    _VNF_EOT_LOCATION_LABELS = {
        "lab": "Lab",
        "telescope": "Observation Dome",
        "comms": "Comms Array",
        "generator": "Power Systems",
        "habitat": "Habitat Module",
        "storage": "Storage",
        "exterior": "Exterior Antenna Array",
    }

    # eot_marcus_location() values -> agent-actionable descriptions. Every
    # value now names the map tile that reaches him: "go to where Marcus is"
    # is always directly actionable.
    _VNF_EOT_MARCUS_LOC_LABELS = {
        "generator": "Power Systems (map: GENERATOR)",
        "lab": "Lab (map: LAB)",
        "habitat": "Habitat Module (map: HABITAT)",
        "storage": "Storage (map: STORAGE)",
        "comms": "Comms Array (map: COMMS)",
    }

    def _vnf_get_inventory_stats():
        """
        Expose Echoes of Tomorrow game state to the LLM bridge.

        Only exposes player-visible information (what the HUD shows).
        Hidden variables (trust, relationship, flags) are tracked
        by the progress graph for supervisor/debug use only.
        """
        try:
            # Evidence log — player collects these throughout the game.
            inventory = []
            for item in getattr(renpy.store, "evidence_log", []):
                inventory.append({
                    "name": str(item),
                    "type": "evidence",
                })

            # Only HUD-visible stats — what the observatory_hud screen shows.
            stats = {}
            signal = getattr(renpy.store, "signal_strength", 0)
            aria = getattr(renpy.store, "aria_integrity", 0)
            storm = getattr(renpy.store, "storm_intensity", 0)
            time_left = getattr(renpy.store, "time_remaining", 6)
            priority = getattr(renpy.store, "power_priority", "balanced")
            power = getattr(renpy.store, "power_cells", 0)
            drives = getattr(renpy.store, "data_drives", 0)
            antenna = getattr(renpy.store, "antenna_parts", 0)
            long_night = bool(getattr(
                renpy.store, "long_night_active", False))
            operational_stats = bool(getattr(
                renpy.store, "operational_stats_active", True))
            location = getattr(renpy.store, "current_location", "lab")
            # Preserve the caller's route location during EVA while exposing
            # the exterior scene that is actually on screen.
            if getattr(renpy.store, "eot_audio_location", "") == "exterior":
                location = "exterior"
            if location not in _VNF_EOT_LOCATION_LABELS:
                location = "lab"
            location_label = _VNF_EOT_LOCATION_LABELS.get(location, location)

            def _time_label(minutes):
                minutes = max(0, int(minutes))
                hours = minutes // 60
                mins = minutes % 60
                if hours:
                    return "{}h {:02d}m".format(hours, mins)
                return "{}m".format(mins)

            if operational_stats:
                stats["signal_strength"] = signal
                stats["aria_integrity"] = aria
                stats["power_priority"] = priority
            stats["evidence_count"] = len(inventory)
            stats["evidence_archived"] = getattr(renpy.store, "evidence_archived", 0)
            # Marcus's live position is a map marker, not an ambient HUD fact.
            # Do not supply schedule updates while the player is in a terminal.
            try:
                _marcus_map_visible = (
                    renpy.get_screen("observatory_map") is not None
                    and renpy.get_screen("echo_terminal_live") is None
                    and renpy.get_screen("echo_terminal_choice") is None)
            except Exception:
                _marcus_map_visible = False
            _marcus_loc_fn = getattr(renpy.store, "eot_marcus_location", None)
            if long_night and _marcus_map_visible and _marcus_loc_fn is not None:
                try:
                    _mloc = _marcus_loc_fn()
                    stats["marcus_location"] = _VNF_EOT_MARCUS_LOC_LABELS.get(
                        _mloc, _mloc)
                except Exception:
                    stats["marcus_location"] = "unknown"

            # Only show storm/time when relevant (act 2+).
            if long_night:
                # Location is an actionable hub fact only during the Long
                # Night. Before and after it, current_location retains its
                # default while the story can be in the canteen or an ending,
                # so publishing it invents a contradictory room.
                stats["location"] = location_label
                stats["storm_intensity"] = storm
                stats["time_remaining"] = time_left

            # Resources (visible in equipment screen). KIT items (2026-08-14)
            # included — playing agents must see collected coolant/preamps
            # and the remaining auxiliary warmth in their normal state feed.
            coolant = getattr(renpy.store, "coolant_cartridges", 0)
            amps = getattr(renpy.store, "signal_amps", 0)
            aux = getattr(renpy.store, "aux_power_remaining", 0)
            if long_night or power or drives or antenna or coolant or amps:
                stats["power_cells"] = power
                stats["data_drives"] = drives
                # Presentation-only rename: the store variable stays
                # `antenna_parts`, but the compact header calls these
                # "couplings" and a live run read the two names as two
                # different resources. One name, both places.
                stats["spare_couplings"] = antenna
                stats["coolant_cartridges"] = coolant
                stats["signal_amps"] = amps
            if aux > 0:
                stats["aux_power_minutes"] = aux

            # Compact summary for brief mode.
            parts = []
            if long_night:
                parts.append("Location: {}".format(location_label))
            if operational_stats:
                parts.append("Evidence: {}".format(len(inventory)))
                parts.append("Signal: {}%".format(signal))
                parts.append("ARIA: {}%".format(aria))
                parts.append("Power: {}".format(priority))
            if long_night:
                parts.append("Storm: {}/3".format(storm))
                parts.append("Time left: {}".format(_time_label(time_left)))
                # KIT items surface in the header ONLY during the Long Night
                # (user design + Sol review: normal wait output prefers the
                # summary, so items invisible here were items invisible,
                # period — but outside the hub act they are just noise).
                kit = []
                if power:
                    kit.append("{} cell{}".format(power, "" if power == 1 else "s"))
                if drives:
                    kit.append("{} drive{}".format(drives, "" if drives == 1 else "s"))
                if antenna:
                    kit.append("{} coupling{}".format(antenna, "" if antenna == 1 else "s"))
                if coolant:
                    kit.append("{} coolant".format(coolant))
                if amps:
                    kit.append("{} preamp{}".format(amps, "" if amps == 1 else "s"))
                if kit:
                    parts.append("Kit: {}".format(", ".join(kit)))
                if aux > 0:
                    parts.append("Aux: {}m warm".format(aux))
            if parts:
                stats["_summary"] = " | ".join(parts)
            if not long_night and not operational_stats:
                # Preserve detailed inspection without an ending footer dump.
                stats["_suppress_brief"] = True

            return inventory, stats

        except Exception:
            return [], {}

    def _vnf_apply_inventory_changes(changes):
        """
        Apply inventory (evidence) modifications from an external client.

        Supported actions:
            - add:    Append a new evidence string to evidence_log.
            - remove: Remove evidence entries matching the item name
                      (exact match or substring).
            - clear:  Remove all evidence entries.

        Example command JSON:
            {
                "name": "inventory_modify",
                "args": {
                    "changes": [
                        {"action": "add", "item": "New lead discovered — anomalous power readings in Habitat B"},
                        {"action": "remove", "item": "Signal blocked"}
                    ]
                }
            }
        """
        try:
            log = getattr(renpy.store, "evidence_log", None)
            if log is None:
                return {"success": False, "message": "evidence_log not found"}

            added = 0
            removed = 0
            for change in changes:
                if not _vnf_is_mapping(change):
                    continue
                action = change.get("action", "")
                item = change.get("item", "")

                if action == "add":
                    text = item if isinstance(item, basestring) else item.get("name", str(item)) if _vnf_is_mapping(item) else str(item)
                    if text:
                        log.append(text)
                        added += 1

                elif action == "remove":
                    name = item if isinstance(item, basestring) else item.get("name", str(item)) if _vnf_is_mapping(item) else str(item)
                    before = len(log)
                    # Remove entries that match exactly or contain the search string
                    log[:] = [e for e in log if name not in e]
                    removed += before - len(log)

                elif action == "clear":
                    removed += len(log)
                    log[:] = []

            parts = []
            if added:
                parts.append("added {}".format(added))
            if removed:
                parts.append("removed {}".format(removed))
            msg = "Evidence log: {}".format(", ".join(parts)) if parts else "No changes applied"
            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # -- Auto-skip pause for sidebar/overlay screens --
    # When modal screens with clickable buttons are visible alongside a
    # single-choice NVL hub menu, pause auto-skip so those buttons can be
    # clicked before the menu auto-resolves.
    _VNF_EOT_PAUSE_SCREENS = {
        "terminal_topics",      # NVL hub research terminal sidebar
        "station_audit_console", # two-step station audit console
        "instrument_panel",     # unlabelled imagebutton calibration
        "observatory_map",      # hub location selection map
        # observatory_hud is NOT here (2026-08-17, presentation stage 4). It
        # used to be shown only around the map call, so pausing auto-skip
        # while it was up was the same rule as the rest of this set. It is now
        # the LONG NIGHT's persistent HUD — shown at the first hub stop and up
        # through every room until the climax — and a permanently visible
        # pause screen is a permanently paused auto-skip: live-caught, the
        # first room entered after the change stalled on its arrival narration
        # for good. Its buttons open equipment_screen / evidence_screen, both
        # still in this set, so the affordance is intact exactly when it is
        # needed.
        "echo_terminal_choice", # custom terminal choice modal
        "star_map_screen",      # star map with region buttons
        "equipment_screen",     # equipment selection
        "evidence_screen",      # evidence log review
        "power_allocation_screen",  # power priority selection
    }

    # -- Echoes button categorization --
    _VNF_EOT_TOPIC_SCREENS = {"terminal_topics", "station_audit_console"}
    _VNF_EOT_NAV_SCREENS = {"observatory_map", "star_map_screen"}
    _VNF_EOT_DEVELOPER_BUTTONS = {"Storm Tests", "Act 3 Music"}
    _VNF_EOT_MUSIC_DEBUG_FUNCTIONS = {
        "eot_hub_debug_cycle_intensity",
        "eot_hub_debug_cycle_aria_tier",
        "eot_hub_debug_reset_music",
    }

    def _vnf_eot_is_music_debug_button(action):
        """Recognize debug controls by their exact callback provenance."""
        raw = action.get("_action_obj")
        candidates = raw if _vnf_is_sequence(raw) else [raw]
        for candidate in candidates:
            callback = getattr(candidate, "callable", None)
            if callback is None:
                callback = getattr(candidate, "func", None)
            if getattr(callback, "__name__", "") in (
                    _VNF_EOT_MUSIC_DEBUG_FUNCTIONS):
                return True
        return action.get("screen") == "eot_hub_music_debug_panel"

    def _vnf_eot_hide_operator_controls(per_screen):
        """Keep user debug/restore controls out of the agent action surface."""
        visible = []
        for scr in per_screen:
            tag = scr.get("_tag", "")
            if tag == "eot_hub_music_debug_panel":
                continue
            if tag == "menu":
                scr["buttons"] = [
                    button for button in scr.get("buttons", [])
                    if button.get("label") not in _VNF_EOT_DEVELOPER_BUTTONS
                ]
            visible.append(scr)
        return visible

    _vnf_add_screen_transform(_vnf_eot_hide_operator_controls, priority=-10)

    def _vnf_eot_hide_operator_actions(actions, context):
        """Hide operator controls rebuilt by the focus-list fallback."""
        for action in actions:
            if (
                action.get("source") == "button"
                and (
                    action.get("label") == "Q.Load"
                    or (
                        action.get("screen") == "_focus_list"
                        and action.get("label")
                        in _VNF_EOT_DEVELOPER_BUTTONS
                    )
                    or _vnf_eot_is_music_debug_button(action)
                )
            ):
                action["hidden"] = True
        return actions

    _vnf_add_action_transform(_vnf_eot_hide_operator_actions, priority=-10)

    def _vnf_eot_categorize_buttons(per_screen):
        """Tag buttons with _category for display grouping."""
        for scr in per_screen:
            tag = scr.get("_tag", "")
            for btn in scr.get("buttons", []):
                actions = btn.get("action_strs", [])
                if tag in _VNF_EOT_TOPIC_SCREENS:
                    btn["_category"] = "topics"
                elif tag in _VNF_EOT_NAV_SCREENS:
                    btn["_category"] = "navigation"
                elif tag in ("power_allocation_screen", "equipment_screen"):
                    btn["_category"] = "items"
                elif tag == "quick_menu":
                    btn["_category"] = "navigation"
                elif tag == "nvl" and "ChoiceReturn" in actions:
                    btn["_category"] = "choices"
                elif tag == "echo_terminal_choice" and "Return" in actions:
                    btn["_category"] = "choices"
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_categorize_buttons, priority=0)

    ## The terminal draws its own scrollback and never speaks through say/NVL,
    ## so without this a user reads ARIA and ECHO-7 while an agent reads
    ## nothing — it was choosing replies to lines it had never seen. Registering
    ## the live terminal as a passive overlay surfaces those rows as screen_text
    ## without treating the always-visible log as input-blocking (Roadwarden's
    ## journal/map use the default blocking behavior).
    ##
    ## Registered on the LIVE screen, not the choice modal: the live terminal is
    ## the passive scrollback holder and is up for the whole scene, so this is
    ## not tied to any one act or menu.
    _vnf_register_overlay_screen(
        "echo_terminal_live", blocking=False, retain_generation=True)

    ## The three content modals (KIT / MAP / LOG) hold real game content —
    ## evidence entries, kit tiles with counts, star-map bearings — that a
    ## user reads off the panel and a text-only client never saw: their text
    ## only ever landed in the stateful screen_content channel, so act("LOG")
    ## came back with the nav bar restated and nothing else. Registering them
    ## routes their text to overlay_texts and sets overlay_active, which is the
    ## flag the format layer keys on to emit the panel body as screen_text.
    ##
    ## Blocking (the default, as Roadwarden's inventory/journal/charactersheet):
    ## all three declare `modal True`, so while one is up the hub menu beneath
    ## cannot be clicked and its pending choices are stale. Blocking makes the
    ## shim refuse advance() and the format layer suppress those choices in
    ## favour of the panel's own buttons, including Close/Return.
    ##
    ## They are also MODAL PRESENTATION (modal=True), not merely blocking: each
    ## paints a full-screen scrim (`add Solid("#020712..")`) over a centred
    ## frame, so the user sees the panel INSTEAD of the observatory map and
    ## HUD. Layering the panel's rows over the scene as a delta therefore
    ## described a screen nobody was looking at. Declaring them modal makes the
    ## panel the primary surface: its rows are the story text, its own buttons
    ## are the numbered list, and the covered hub menu is reported as hidden
    ## instead of silently vanishing. Roadwarden's journal/inventory stay
    ## layered — they sit beside their dialogue rather than replacing it.
    ##
    ## NOT modal: `echo_terminal_live` (passive scrollback, registered above),
    ## `terminal_topics` (a 540px side panel beside the live terminal, and not
    ## a registered overlay), `observatory_map`/`observatory_hud` (the scene
    ## itself), and `power_allocation_screen` (a `call screen` console that
    ## owns its own interaction — there is no story menu underneath for a
    ## hidden-menu note to describe).
    _VNF_EOT_CONTENT_OVERLAYS = {
        "equipment_screen",     # KIT — item tiles, counts, aux bus line
        "star_map_screen",      # MAP — bearing + region names
        "evidence_screen",      # LOG — evidence entries / empty state
    }
    ## The names the station's own nav bar uses, so the hidden-menu note reads
    ## "hidden behind LOG" rather than "behind evidence_screen".
    _VNF_EOT_CONTENT_OVERLAY_NAMES = {
        "equipment_screen": "KIT",
        "star_map_screen": "MAP",
        "evidence_screen": "LOG",
    }

    for _eot_ovr in sorted(_VNF_EOT_CONTENT_OVERLAYS):
        _vnf_register_overlay_screen(_eot_ovr, modal=True)
        _vnf_set_screen_display_name(
            _eot_ovr, _VNF_EOT_CONTENT_OVERLAY_NAMES[_eot_ovr])

    def _vnf_eot_hud_chrome_text(per_screen):
        """Omit duplicate meters, not incident/progress rows or story text."""
        import re
        headers = (
            "AETHON OBSERVATORY  //  PERSONAL LOG",
            "AETHON OBSERVATORY  //  STATION ADVISORY",
        )
        for scr in per_screen:
            if scr.get("_tag") not in ("observatory_hud", "nvl", "say"):
                continue
            texts = scr.get("texts") or []
            # NVL chrome ends at its dated header, before the story body.
            # Never pattern-filter narration below that boundary.
            boundary = next((i for i, text in enumerate(texts)
                             if text in headers), None)
            if scr.get("_tag") != "observatory_hud" and boundary is None:
                continue
            keep = []
            for i, text in enumerate(texts):
                chrome = scr.get("_tag") == "observatory_hud" or i < boundary
                duplicate = chrome and (
                    text in ("STATION STATUS", "PASSIVE RUNS", "NO KNOWN RUNS")
                    or re.match(r"^(SIGNAL|ARIA COHERENCE)\s+\d+%$", text)
                    or re.match(r"^STORM(?: PEAK IN\s+| \d/3\s+PEAK\s+).+$", text)
                    or re.match(r"^POWER\s+(BALANCED|ARIA|HEATING|SIGNAL)$", text)
                )
                header = boundary is not None and (
                    i == boundary or (
                        i == boundary + 1
                        and text == "E. VOSS \u00b7 05 MAR 2047"))
                if not duplicate and not header:
                    keep.append(i)
            if len(keep) != len(texts):
                scr["texts"] = [texts[i] for i in keep]
                for key in ("_text_sections", "_text_paths"):
                    metadata = scr.get(key) or []
                    scr[key] = ([metadata[i] for i in keep]
                                if len(metadata) == len(texts) else [])
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_hud_chrome_text, priority=11)

    def _vnf_eot_equipment_tile_text(per_screen):
        """Merge each KIT tile's name and count into a single line.

        The panel renders the tile label and its "x[count]" as two sibling
        texts, so the raw scrape reads "POWER CELL", "x2", "DATA DRIVE", "x2"
        — an ambiguous list where the counts float free of their tiles and
        two tiles holding the same quantity look like a duplicate. Merging
        them here keeps the count attached to its item and makes the tile
        list dedup-safe.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "equipment_screen":
                continue
            texts = scr.get("texts") or []
            merged = []
            for t in texts:
                bare = t.strip()
                if (merged and len(bare) > 1 and bare[0] == "x"
                        and bare[1:].isdigit()):
                    merged[-1] = "{} {}".format(merged[-1].strip(), bare)
                else:
                    merged.append(t)
            if merged != texts:
                scr["texts"] = merged
                # Positional metadata no longer lines up 1:1 with texts.
                scr["_text_sections"] = []
                scr["_text_paths"] = []
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_equipment_tile_text, priority=12)

    def _vnf_eot_power_preview_rows(per_screen):
        """Keep each power meter's value and projection on one scraped row.

        The screen draws a meter as three sibling Text displayables. A preview
        change may leave the percentage unchanged while changing only the
        projection; modal delta capture would then emit fragments such as
        ``ARRAY SIGNAL / 79% / +3/h`` where 79 belongs to ARIA. Atomic rows
        make both snapshot and delta rendering preserve that association.
        """
        meter_labels = ("ARRAY SIGNAL", "ARIA CORE")
        preview_marker = "ROUTING EFFECT // OTHER LOADS EXCLUDED"
        for scr in per_screen:
            if scr.get("_tag", "") != "power_allocation_screen":
                continue
            original_texts = list(scr.get("texts") or [])
            texts = list(original_texts)
            try:
                preview_start = texts.index(preview_marker) + 1
            except ValueError:
                continue
            # The target sits between LIVE BUS PREVIEW and the effect marker.
            # ARIA CORE is also a route label and a meter label, so preserve
            # this occurrence's role before the exact-text dedup pass.
            try:
                target_start = texts.index("LIVE BUS PREVIEW") + 1
                target_end = texts.index(preview_marker, target_start)
            except ValueError:
                target_start = target_end = -1
            route_targets = (
                "BALANCED", "TELESCOPE", "COMMS ARRAY", "THERMAL LOOP",
                "ARIA CORE")
            target_index = None
            for candidate_index in range(target_start, target_end):
                if texts[candidate_index].strip() in route_targets:
                    target_index = candidate_index
            if target_index is not None:
                target = texts[target_index].strip()
                prefix = (
                    "CURRENT TARGET" if "CURRENT ROUTE" in texts
                    else "PENDING TARGET")
                texts[target_index] = "{}  {}".format(prefix, target)
            merged = []
            i = 0
            while i < len(texts):
                text = texts[i]
                if (
                    i >= preview_start
                    and text.strip() in meter_labels
                    and i + 2 < len(texts)
                    and texts[i + 1].strip().endswith("%")
                    and (
                        texts[i + 2].strip().lower() == "steady"
                        or "/h" in texts[i + 2].strip().lower()
                    )
                ):
                    merged.append("{} {} {}".format(
                        text.strip(), texts[i + 1].strip(),
                        texts[i + 2].strip()))
                    i += 3
                    continue
                merged.append(text)
                i += 1
            if merged != original_texts:
                scr["texts"] = merged
                scr["_text_sections"] = []
                scr["_text_paths"] = []
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_power_preview_rows, priority=13)

    def _vnf_eot_evidence_process_order(per_screen):
        """Keep LOG process rows beneath their heading across viewports.

        Ren'Py's display-tree walk can visit the evidence viewport before a
        sibling process row even though the process frame is visually above
        it. The display paths are not stable across that viewport boundary,
        so use the game's canonical process rows as ownership instead. Move
        one occurrence per live row and preserve any equal evidence entry.
        """
        try:
            process_rows = [
                (label, renpy.store.eot_process_line(label, status))
                for label, status, _state
                in renpy.store.eot_station_processes()
            ]
        except Exception:
            return per_screen

        known_process_labels = [
            "ORIGIN SWEEP — BEARING 287.4",
            "ARIA PARTITION SCAN",
            "ARIA CORE SOURCE AUDIT",
            "ARCHIVE HASH — EVIDENCE LOG",
            "AUX RESERVE",
        ]

        def _looks_like_late_process_row(text, label):
            prefix = label + "  "
            if not text.startswith(prefix):
                return False
            tail = text[len(prefix):]
            leader, separator, status = tail.partition("  ")
            if not separator or len(leader) < 2 or set(leader) != set("."):
                return False
            status = status.strip()
            if label == "AUX RESERVE":
                return (
                    status.endswith("m WARM REMAINING")
                    and status[:-16].isdigit()
                )
            if status.startswith("COMPLETE —") or status.startswith("QUEUED —"):
                return True
            percent, marker, state = status.partition("% // ")
            return bool(marker and percent.isdigit() and state.strip())

        def _owns_process_row(text, label, current_line):
            if text == current_line or text == label:
                return True
            # Process progress/status is live store data, while the display
            # tree is the last rendered frame. Match the stable label prefix
            # so a percentage/ETA update between those two reads cannot leave
            # the visually upper process row below EVIDENCE ENTRIES.
            return _looks_like_late_process_row(text, label)

        for scr in per_screen:
            if scr.get("_tag", "") != "evidence_screen":
                continue
            texts = list(scr.get("texts") or [])
            try:
                active_index = texts.index("ACTIVE PROCESSES")
                evidence_index = texts.index("EVIDENCE ENTRIES")
            except ValueError:
                continue
            owned_indices = []
            owned_rows = []
            for canonical_index, (label, process_line) in enumerate(process_rows):
                section_matches = [
                    index for index in range(
                        active_index + 1, evidence_index)
                    if index not in owned_indices
                    and _owns_process_row(texts[index], label, process_line)
                ]
                late_matches = [
                    index for index in range(evidence_index + 1, len(texts))
                    if index not in owned_indices
                    and _owns_process_row(texts[index], label, process_line)
                ]
                if section_matches:
                    owned_indices.append(section_matches[0])
                    owned_rows.append((
                        label, texts[section_matches[0]], canonical_index))
                elif late_matches:
                    # The viewport-owned evidence entries are walked first;
                    # the sibling process frame normally supplies the last
                    # equal occurrence. Choosing from the tail preserves an
                    # evidence entry whose text happens to equal a live row.
                    owned_indices.append(late_matches[-1])
                    owned_rows.append((
                        label, texts[late_matches[-1]], canonical_index))
            # Store state can advance between the rendered frame and this
            # transform. Recover one visually rendered row for a process that
            # has just disappeared from eot_station_processes(), using the
            # game's finite label set and exact dotted-leader grammar.
            canonical_labels = set(label for label, _line in process_rows)
            for label in known_process_labels:
                if label in canonical_labels:
                    continue
                matches = [
                    index for index in range(evidence_index + 1, len(texts))
                    if index not in owned_indices
                    and _looks_like_late_process_row(texts[index], label)
                ]
                if matches:
                    owned_indices.append(matches[-1])
                    owned_rows.append((
                        label, texts[matches[-1]], len(process_rows)))
            if not owned_rows:
                continue
            if any(
                label in known_process_labels
                for label, _row, _canonical_index in owned_rows
            ):
                # A stale rendered process plus the store's new idle sentinel
                # is one transition frame, not two simultaneous processes.
                owned_rows = [
                    item for item in owned_rows
                    if item[0] != "NO BACKGROUND PROCESSES"
                ]
            known_rank = dict(
                (label, index)
                for index, label in enumerate(known_process_labels)
            )
            owned_rows.sort(key=lambda item: (
                known_rank.get(
                    item[0], len(known_process_labels) + item[2]),
                item[2],
            ))
            rows = [row for _label, row, _canonical_index in owned_rows]
            owned = set(owned_indices)
            remaining = [
                text for index, text in enumerate(texts) if index not in owned
            ]
            process_heading = remaining.index("ACTIVE PROCESSES")
            remaining[process_heading + 1:process_heading + 1] = rows
            if remaining != texts:
                scr["texts"] = remaining
                scr["_text_sections"] = []
                scr["_text_paths"] = []
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_evidence_process_order, priority=14)

    def _vnf_eot_terminal_complete_last_row(texts):
        """Finish the terminal row the scrape caught mid-typewriter.

        echo_terminal_rows_content renders the newest row as
        row_text[:echo_terminal_reveal], and the shim walks the screen's LAST
        BUILT displayable tree rather than re-rendering it. Both effects point
        the same way: the newest line leaves the shim as "T", "TH", "THE DOM"
        — text the terminal never said — or one frame behind what it has
        already committed to. Those partials are indistinguishable from real
        rows downstream, and once delivered they cannot be taken back.

        A store check alone is not enough: echo_terminal_finish_reveal() can
        have run (reveal == len) while the cached tree the walker reads still
        holds the truncated string. So compare against the row the store says
        is newest and patch the scrape up to it — completing the line rather
        than dropping it, which also lands it on THIS interaction instead of
        the next scrape's.
        """
        if not texts:
            return texts
        try:
            latest = renpy.store.echo_terminal_latest_text()
        except Exception:
            return texts
        ## F2 fleet (2026-08-19): the store rows keep RAW text by design —
        ## interpolation happens at draw time — so the row this helper
        ## injects carried "[_audit_elapsed]" etc. verbatim, the source of
        ## every placeholder leak the fleet reported. Worse, comparing the
        ## walker's SUBSTITUTED partial against the RAW latest made the
        ## prefix check fail exactly for interpolated rows, so those
        ## typewriter partials ("Run cost: 14 p") were delivered as-is,
        ## dozens per row. Substitute BEFORE injecting and comparing:
        ## like-with-like, and only resolved text ever leaves the shim.
        try:
            latest = _vnf_substitute(latest)
        except Exception:
            pass
        last = texts[-1]
        ## Only ever extend a genuine prefix of the newest row. When the last
        ## scraped text is something else entirely — chrome, a older row, the
        ## row before the newest one has rendered at all — leave it alone.
        if not latest or last == latest or not latest.startswith(last):
            return texts
        return texts[:-1] + [latest]

    def _vnf_eot_terminal_stable_rows(rows):
        """Chrome-filter + last-row completion for terminal scrollback rows.

        F3 wave (2026-08-19): the panel's CHROME rows are volatile
        — echo_terminal_title flips between modes ("// LIVE FEED",
        "// ENCRYPTED PERSONAL LOG", "// ENCRYPTED LINK") and the
        NIGHT/ARIA-LINK status lines tick every scrape. They sit at
        the TOP of the panel, so every mutation diverges the
        overlay ledger's prefix and re-delivers the whole
        scrollback below ("I AM YOU, ELARA landed for the third
        time" — f3-collapse; screenshot-confirmed bridge-side by
        f3-ariafirst). Filter them out of the text channel: the
        stats footer already carries time/ARIA/link state on every
        output, so agents lose nothing and the ledger sees only
        stable prose rows it can dedup.
        """
        _stable = []
        for _r in rows:
            _rs = _r.strip()
            if _rs.startswith("AETHON TERMINAL //"):
                continue
            if _rs.startswith("NIGHT ") and "//" in _rs:
                continue
            if _rs.startswith("ARIA LINK:"):
                continue
            _stable.append(_r)
        _fixed = _vnf_eot_terminal_complete_last_row(_stable)
        return _fixed if _fixed is not _stable else _stable

    def _vnf_eot_terminal_row_text(row):
        """Serialize one canonical terminal row with visible attribution."""
        text = row.get("display_text", row.get("text", ""))
        who = row.get("who", "")
        try:
            text = _vnf_substitute(text)
            who = _vnf_substitute(who)
        except Exception:
            pass
        if who and text:
            return u"[{}] {}".format(who, text)
        return text

    def _vnf_eot_terminal_store_rows():
        """Return the terminal's canonical rows, independent of its viewport.

        The rendered tree contains only the visible portion of the scrollback.
        Scrolling or opening a choice therefore used to look like a destructive
        rewrite to the overlay ledger. The game store is the source of truth;
        serialize it directly and perform the same draw-time interpolation the
        screen applies before any row leaves the shim.
        """
        try:
            source = renpy.store.echo_terminal_rows
        except Exception:
            return None
        rows = []
        for row in source or []:
            if not _vnf_is_mapping(row):
                continue
            text = _vnf_eot_terminal_row_text(row)
            if text:
                rows.append(text)
        return _vnf_eot_terminal_stable_rows(rows)

    def _vnf_eot_terminal_choice_scrape(per_screen):
        """Translate custom terminal choices into clean screen buttons.

        The terminal screens intentionally render accumulated text. The generic
        scraper can see that text as disabled pseudo-buttons, so suppress the
        passive live terminal and keep only real Return-backed option buttons
        on the choice modal.
        """
        _live_scr = None
        _canonical_rows = _vnf_eot_terminal_store_rows()
        for scr in per_screen:
            if scr.get("_tag", "") == "echo_terminal_live":
                ## Drop the pseudo-buttons (the walker sees scrollback rows as
                ## dead buttons) but KEEP the text — echo_terminal_live is
                ## registered as an overlay above, which is what routes these
                ## rows to the agent as screen_text.
                scr["buttons"] = []
                if _canonical_rows is None:
                    scr["texts"] = _vnf_eot_terminal_stable_rows(scr.get("texts") or [])
                else:
                    scr["texts"] = list(_canonical_rows)
                ## Keep the text-client ledger across the live/choice layer
                ## handoff. A real terminal clear/reset increments this value.
                scr["_overlay_generation"] = getattr(
                    renpy.store, "echo_terminal_generation", 0)
                _live_scr = scr
                continue

            if scr.get("_tag", "") != "echo_terminal_choice":
                continue
            options = []
            for btn in scr.get("buttons", []):
                actions = btn.get("actions", [])
                action_strs = btn.get("action_strs", [])
                has_return = (
                    "Return" in actions
                    or any("Return" in s for s in action_strs)
                )
                if not has_return or btn.get("is_disabled"):
                    continue
                btn["_category"] = "choices"
                ## Answering the terminal returns into script: the reply text
                ## arrives after the choice screen closes, so this is a story
                ## entry, not just a UI rebuild.
                btn["_wait_after_action"] = True
                btn["_story_entry"] = True
                options.append(btn)
            scr["buttons"] = options
            ## The passive live screen owns the scrollback and supplies
            ## overlay_texts. The choice screen draws the same rows again under
            ## its buttons; retaining both produces duplicate agent narration.
            scr["texts"] = []

        ## Layering handoff (screens.rpy 469b561, 2026-08-20): while the
        ## choice modal is up, echo_terminal_live deliberately renders NO row
        ## content — the modal owns the row layer, so wheel-scrolling cannot
        ## expose a displaced second copy. For the TEXT channel that handoff
        ## must be invisible: the live screen is the registered overlay whose
        ## tag carries the scrollback to the agent, and a rowless scrape here
        ## reads bridge-side as a CONFIRMED panel close — ending the ledger
        ## generation and re-delivering the entire scrollback after every
        ## terminal question (the exact class the chrome filter above fixed).
        ## Adopt the modal's rows (same rows, per the screen comment) into the
        ## live entry so the overlay contributor and its content stay
        ## continuous across the choice.
        if (_live_scr is not None and not _live_scr.get("texts")
                and _canonical_rows):
            _live_scr["texts"] = list(_canonical_rows)
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_terminal_choice_scrape, priority=2)

    def _vnf_eot_terminal_before_say(event, interact, **kwargs):
        """Capture committed terminal rows before the reaction's say event.

        Turbo can finish the terminal pauses between periodic scrapes. The
        store already contains the full rows, even if the last rendered tree
        still contains their typewriter prefixes. Use the normal scraper and
        canonical-row transform; do not manufacture another delivery lane or
        bypass the scraper's current-frame/focus guard.
        """
        if event != "begin" or not vnf_player.enabled:
            return
        if not vnf_player.scrape_screens:
            return
        try:
            if (renpy.get_screen("echo_terminal_live") is not None
                    or renpy.get_screen("echo_terminal_choice") is not None):
                _vnf_scrape_visible_screens(force=True)
        except Exception:
            # Observation must never prevent the game's say from running.
            pass

    # Run before the shim's say publisher on both callback APIs. Replace our
    # callback on Shift+R instead of stacking another scrape on every say.
    for _eot_callback_attr in ("all_character_callbacks", "all_nvl_callbacks"):
        _eot_callbacks = getattr(renpy.config, _eot_callback_attr, None)
        if _eot_callbacks is not None:
            _eot_callbacks[:] = [
                cb for cb in _eot_callbacks
                if getattr(cb, "__name__", "") != "_vnf_eot_terminal_before_say"
            ]
            _eot_callbacks.insert(0, _vnf_eot_terminal_before_say)

    def _vnf_eot_install_terminal_hide_capture():
        """Drain visible terminal rows before the script removes their screen."""
        prior = renpy.hide_screen
        prior = getattr(prior, "_vnf_eot_prior_hide_screen", prior)

        def hide_screen(tag, *args, **kwargs):
            name = tag[0] if isinstance(tag, tuple) and tag else tag
            if name in ("echo_terminal_live", "echo_terminal_choice"):
                _vnf_eot_terminal_before_say("begin", False)
            return prior(tag, *args, **kwargs)

        hide_screen._vnf_eot_prior_hide_screen = prior
        renpy.hide_screen = hide_screen

    _vnf_eot_install_terminal_hide_capture()

    _vnf_eot_prior_auto_skip_predicate = vnf_player.auto_skip_predicate
    if getattr(
        _vnf_eot_prior_auto_skip_predicate,
        "_vnf_eot_deadline_wrapper",
        False,
    ):
        _vnf_eot_prior_auto_skip_predicate = getattr(
            _vnf_eot_prior_auto_skip_predicate,
            "_vnf_eot_prior_predicate",
            None,
        )

    def _vnf_eot_auto_skip_predicate(
        label, _prior=_vnf_eot_prior_auto_skip_predicate
    ):
        """Keep deadline-blocked work out of single-choice auto-skip."""
        if _prior is not None and not _prior(label):
            return False
        allows_caption = getattr(
            renpy.store, "eot_deadline_allows_caption", None)
        if not callable(allows_caption):
            return True
        return bool(allows_caption(label))

    _vnf_eot_auto_skip_predicate._vnf_eot_deadline_wrapper = True
    _vnf_eot_auto_skip_predicate._vnf_eot_prior_predicate = (
        _vnf_eot_prior_auto_skip_predicate)
    vnf_player.auto_skip_predicate = _vnf_eot_auto_skip_predicate

    def _vnf_eot_deadline_choice_actions(actions, context):
        """Mirror Echoes' user deadline gate on the agent choice surface.

        The auto-skip predicate above handles the earlier single-choice path.
        This transform handles the normal agent decision surface, where
        ChoiceReturn itself remains sensitive despite the custom screen.
        """
        allows_caption = getattr(
            renpy.store, "eot_deadline_allows_caption", None)
        if not callable(allows_caption):
            return actions
        for action in actions:
            if (
                action.get("source") != "choice"
                or action.get("disabled")
                or action.get("caption")
            ):
                continue
            try:
                allowed = allows_caption(action.get("label", ""))
            except Exception:
                continue
            if not allowed:
                action["disabled"] = True
                action["is_disabled"] = True
                # The deadline transform is the authoritative owner of this
                # unavailable row. The following screen scrape can fail to
                # match a cost-styled ChoiceReturn label; that must not make
                # the row disappear from the agent surface.
                action["_keep_stale"] = True
                action["annotation"] = (
                    "Not enough time remains before storm peak.")
        return actions

    _vnf_add_action_transform(
        _vnf_eot_deadline_choice_actions, priority=29)

    def _vnf_eot_terminal_choice_actions(actions, context):
        """Give custom terminal choices normal choice-like ids."""
        idx = 1
        for action in actions:
            if (
                action.get("source") == "button"
                and action.get("screen") == "_focus_list"
                and set(action.get("actions", [])) == {"none"}
            ):
                ## Real Echoes choices come from named game screens. A
                ## no-op focus row is rendered prose that became focusable
                ## during reveal, never a command for the player.
                action["hidden"] = True
                continue

            if (
                action.get("source") == "button"
                and action.get("screen") == "echo_terminal_choice"
                and "Return" in action.get("actions", [])
            ):
                action["id"] = str(idx)
                action["_category"] = "choices"
                ## Same as the screen-level pass above: the answer returns
                ## into script, so mark the story entry as well.
                action["_wait_after_action"] = True
                action["_story_entry"] = True
                idx += 1
        return actions

    _vnf_add_action_transform(_vnf_eot_terminal_choice_actions, priority=30)

    def _vnf_eot_hud_actions_at_decisions(actions, context):
        """Expose persistent KIT/LOG controls only beside a real menu.

        The HUD stays visible throughout the Long Night. During a say pause,
        however, its buttons are the only scraped actions; treating that as a
        decision boundary lets an agent open a panel before the current label
        applies the state changes that follow its narration.
        """
        on_map = any(action.get("screen") == "observatory_map" for action in actions)
        # The preliminary screen-only pass has no choice-source actions.
        # Its output feeds the combined pass, so removing HUD buttons there
        # would make a live menu advertise controls that act cannot resolve.
        # This context is cleared by the menu wrapper's finally block.
        menu_active = bool(_vnf_current_menu_context[0])
        if context.get("has_choices") or menu_active or on_map:
            return actions
        return [
            action for action in actions
            if action.get("screen") != "observatory_hud"
        ]

    _vnf_add_action_transform(_vnf_eot_hud_actions_at_decisions, priority=30)

    def _vnf_eot_content_overlay_actions(actions, context):
        """Wait for KIT/LOG/MAP opens and closes to finish rebuilding UI.

        ToggleScreen changes the active modal after the click that produced the
        action. Without a post-action scrape the result can contain only the
        clicked label ("KIT"/"LOG") while the panel body arrives one frame
        later, which is indistinguishable from an empty overlay to an agent.
        """
        overlay_names = (
            "equipment_screen",
            "evidence_screen",
            "star_map_screen",
        )
        for action in actions:
            action_text = " ".join(action.get("action_strs", []) or [])
            if any(name in action_text for name in overlay_names):
                action["_wait_after_action"] = True
        return actions

    _vnf_add_action_transform(_vnf_eot_content_overlay_actions, priority=31)

    def _vnf_eot_preview_actions(actions, context):
        """Keep two-step console previews on the screen-state act path."""
        preview_screens = {"power_allocation_screen", "star_map_screen"}
        for action in actions:
            if action.get("screen") not in preview_screens:
                continue
            names = set(action.get("actions", []) or [])
            if "Return" in names:
                continue
            if names.intersection({"SetVariable", "SetScreenVariable"}):
                action["_interaction_type"] = "info"
                action["_wait_after_action"] = False
        return actions

    _vnf_add_action_transform(_vnf_eot_preview_actions, priority=32)

    def _vnf_eot_drop_choice_buttons(per_screen):
        """Drop actable NVL ChoiceReturn duplicates when a menu is active.

        Disabled widgets are the only rendered evidence that a canonical
        choice is visibly unavailable. Keep those so the generic choice
        merge can retain the row and its game-specific annotation.
        """
        if not _vnf_current_menu_context[0]:
            return per_screen
        for scr in per_screen:
            if scr.get("_tag") != "nvl":
                continue
            scr["buttons"] = [
                b for b in scr.get("buttons", [])
                if ("ChoiceReturn" not in b.get("actions", [])
                    or b.get("is_disabled"))
            ]
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_drop_choice_buttons, priority=0)

    def _vnf_eot_overlay_guard(per_screen):
        for scr in per_screen:
            if scr.get("_tag", "") in _VNF_EOT_PAUSE_SCREENS:
                # NOTE: the auto-skip state was consolidated into the
                # _vnf_autoskip instance; the old module global
                # _vnf_auto_skip_pause_reasons no longer exists. Appending to
                # the dead name raised NameError (silently swallowed by
                # _vnf_apply_screen_transforms), so the pause reason was never
                # registered and auto-advance would dismiss the call screen
                # (observatory_map etc.) with end_interaction(True) -> _return
                # True -> the "stay" fallback. Use the canonical instance list.
                _vnf_autoskip.pause_reasons.append("eot_overlay")
                return per_screen
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_overlay_guard, priority=1)

    # -- NVL / cumulative text deduplication --
    # Ren'Py NVL mode renders ALL accumulated dialogue entries each frame.
    # The tree walker re-scrapes everything, producing two kinds of noise:
    #   1. Exact duplicates: [A, A, B, A, B, C] — same string repeated.
    #   2. Cumulative containment: each successive entry includes all prior
    #      text (e.g. "line1", "line1\nline2", "line1\nline2\nline3").
    # Applied to all screens (not just nvl-tagged) because the say screen
    # also renders NVL viewport content.
    def _vnf_eot_text_dedup(per_screen):
        for scr in per_screen:
            texts = scr.get("texts")
            if not texts or len(texts) < 2:
                continue
            if scr.get("_tag", "") == "evidence_screen":
                # Evidence text is user-authored content, not a cumulative
                # dialogue page. An entry may legitimately equal a live
                # process row, so exact text cannot establish duplication.
                continue
            # Step 1: exact dedup (preserve order).
            seen = set()
            unique = []
            for t in texts:
                if t not in seen:
                    seen.add(t)
                    unique.append(t)
            # The content modals are not cumulative renderers: their panels
            # draw a fixed body once. Containment dedup there is destructive
            # (an evidence entry that is a prefix of a longer one, or a tile
            # label echoed inside its own description, would vanish), so they
            # get exact dedup only.
            if scr.get("_tag", "") in (
                    _VNF_EOT_CONTENT_OVERLAYS
                    | set(("power_allocation_screen",))):
                scr["texts"] = unique
                continue
            # Step 2: remove entries that are contained in a later entry.
            # This catches both prefix chains and substring containment.
            result = []
            for i, t in enumerate(unique):
                contained = False
                for j in range(i + 1, len(unique)):
                    if t in unique[j]:
                        contained = True
                        break
                if not contained:
                    result.append(t)
            scr["texts"] = result
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_text_dedup, priority=15)

    def _vnf_apply_stats_changes(changes):
        """
        Apply stat modifications from an external client.

        Only whitelisted game variables can be modified, and numeric
        values are clamped to their valid ranges.

        Example command JSON:
            {
                "name": "stats_modify",
                "args": {
                    "changes": {
                        "trust_signal": 2,
                        "marcus_relationship": -1,
                        "marcus_trust": 1,
                        "blocked_signal": false
                    }
                }
            }
        """
        try:
            # Whitelist of modifiable variables with (type, min, max) constraints.
            # None means no clamping (for bools / uncapped values).
            #
            # LOCKSTEP with game_variables.rpy: every clamp here is an
            # ENVELOPE around the scale the game itself uses, never a
            # narrower one. A clamp that sits below a story boundary does
            # not reject the write, it silently rewrites it into the wrong
            # branch -- which is exactly what happened when
            # marcus_relationship still clamped to [-2, 2] after the
            # 2026-08-15 weighting pass moved WARM to
            # eot_marcus_warm() -> marcus_relationship >= 3: an external
            # scenario asking for 3 got 2 and ran the cold fork.
            #
            #   trust_signal        -3..+3 (game_variables comment; the
            #                       highest gate in play is >= 2)
            #   marcus_relationship vulnerability +2 / companionship +1;
            #                       personal closeness, with WARM at >= 3
            #   marcus_trust        disclosures +2 / transparent work +1;
            #                       operational confidence, TRUSTED at >= 2
            #   both axes use the reachable band "roughly -4 to +8",
            #                       clamped a little wider at [-4, 8] so
            #                       route arithmetic never bumps the ceiling
            #
            # THE RULE: this clamp's upper bound must NEVER again sit below
            # eot_marcus_warm()'s boundary. If that boundary moves, this
            # ceiling moves with it (or stays above it) in the same commit.
            allowed = {
                "trust_signal":          (int, -3, 3),
                "marcus_relationship":   (int, -4, 8),
                "marcus_trust":          (int, -4, 8),
                "investigated_privately": (bool, None, None),
                "blocked_signal":        (bool, None, None),
                "read_all_logs":         (bool, None, None),
                "aria_warned":           (bool, None, None),
                "chose_leap_of_faith":   (bool, None, None),
            }

            applied = []
            rejected = []
            for name, value in changes.items():
                if name not in allowed:
                    rejected.append(name)
                    continue

                expected_type, lo, hi = allowed[name]
                if expected_type is bool:
                    value = bool(value)
                elif expected_type is int:
                    value = int(value)
                    if lo is not None:
                        value = max(lo, value)
                    if hi is not None:
                        value = min(hi, value)

                setattr(renpy.store, name, value)
                applied.append("{}={}".format(name, value))

            parts = []
            if applied:
                parts.append("set {}".format(", ".join(applied)))
            if rejected:
                parts.append("rejected {}".format(", ".join(rejected)))
            msg = "Stats: {}".format("; ".join(parts)) if parts else "No changes applied"
            return {"success": bool(applied), "message": msg}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # Echoes uses screen-based UI elements — enable screen_content events.
    vnf_player.scrape_screens = True

    # -- Screen display names for modals --
    _vnf_set_screen_display_name("instrument_panel", "Instrument Panel")
    _vnf_set_screen_display_name("station_audit_console", "Station Audit")
    _vnf_set_screen_display_name("observatory_map", "Observatory Map")
    _vnf_set_screen_display_name("star_map_screen", "Star Map")
    _vnf_set_screen_display_name("equipment_screen", "Equipment")
    _vnf_set_screen_display_name("power_allocation_screen", "Power Distribution")
    _vnf_set_screen_display_name("evidence_screen", "Evidence Log")

    # -- Label unlabelled imagebuttons on game screens --
    # Many Echoes screens use imagebuttons with SetVariable/Return actions but
    # no visible text label. This is a small reference pattern for game-specific
    # mods: keep rendered textbuttons as-is, and derive fallback labels from the
    # game's own action values when a button is image-only.

    _VNF_EOT_BAND_LABELS = {
        "hydrogen": "Hydrogen band",
        "microwave": "Microwave band",
        "optical": "Optical band",
    }

    _VNF_EOT_REGION_LABELS = {
        "known_sources": "Known Sources region",
        "signal_origin": "Signal Origin region",
        "anomaly_cluster": "Anomaly Cluster region",
    }

    _VNF_EOT_ITEM_LABELS = {
        "power_cell": "Power Cell",
        "data_drive": "Data Drive",
        ## Coupling language everywhere a player or agent reads the item —
        ## the tile ("COUPLING"), the header ("2 couplings"), the detailed
        ## stats (spare_couplings) and this button label must never diverge.
        "antenna_part": "Spare Coupling",
        # Conditional tiles: only rendered once the item is held, and
        # image-only like the rest, so they need labels to be actable.
        "coolant_cartridge": "Coolant Cartridge",
        "signal_amp": "RF Preamp",
    }

    _VNF_EOT_MAP_BUTTON_LABELS = {
        "telescope": "TELESCOPE",
        "lab": "LAB",
        "comms": "COMMS",
        "generator": "GENERATOR",
        "habitat": "HABITAT",
        "storage": "STORAGE",
    }

    def _vnf_eot_map_subtitle(value):
        storm = getattr(renpy.store, "storm_intensity", 0)
        antenna_damaged = getattr(renpy.store, "antenna_damaged", False)
        generator_repaired = getattr(renpy.store, "generator_repaired", False)
        antenna_reroute_active = getattr(renpy.store, "antenna_reroute_active", False)
        if value == "telescope":
            return "Storm telemetry" if storm >= 2 else "Observation dome"
        if value == "lab":
            return "ARIA station"
        if value == "comms":
            if antenna_damaged and not generator_repaired:
                return "ARRAY DAMAGED"
            if antenna_reroute_active:
                return "Temporary reroute under strain"
            return "Antenna repaired" if antenna_damaged else "Antenna array"
        if value == "generator":
            if antenna_damaged and not generator_repaired:
                parts = getattr(renpy.store, "antenna_parts", 0)
                return "Reroute ready" if parts > 0 else "Coupling required"
            return "Power systems"
        if value == "habitat":
            return "Warmest room left" if storm >= 3 else "Canteen & quarters"
        if value == "storage":
            if (getattr(renpy.store, "marcus_eva_waiting_for_parts", False)
                    and not getattr(renpy.store, "storage_supplies_found", False)):
                return "Emergency rack — array couplings"
            return "Requisitions"
        return None

    def _vnf_eot_map_label(value):
        ## "stay" mapping removed with the corridor-wait button (round 3);
        ## the script-side guard swallows any synthesized "stay" at no cost.
        location = _VNF_EOT_MAP_BUTTON_LABELS.get(value)
        if location:
            current = getattr(renpy.store, "current_location", None)
            if value == current:
                return "{} (current)".format(location)
            return location
        return None

    # Mapping: screen tag -> {action_value: label}. Values come from the game
    # actions (SetVariable/Return), while labels are the player-facing fallback.
    _EOT_BUTTON_LABELS = {
        "instrument_panel": {
            "hydrogen": _VNF_EOT_BAND_LABELS["hydrogen"],
            "microwave": _VNF_EOT_BAND_LABELS["microwave"],
            "optical": _VNF_EOT_BAND_LABELS["optical"],
        },
        "station_audit_console": {
            "trust": "Trust Protocol dataset",
            "temporal": "Temporal Model dataset",
            "chen": "Chen Profile dataset",
            "aria_code": "ARIA Core Audit dataset",
        },
        "star_map_screen": {
            "known_sources": _VNF_EOT_REGION_LABELS["known_sources"],
            "signal_origin": _VNF_EOT_REGION_LABELS["signal_origin"],
            "anomaly_cluster": _VNF_EOT_REGION_LABELS["anomaly_cluster"],
        },
        "equipment_screen": {
            "power_cell": _VNF_EOT_ITEM_LABELS["power_cell"],
            "data_drive": _VNF_EOT_ITEM_LABELS["data_drive"],
            "antenna_part": _VNF_EOT_ITEM_LABELS["antenna_part"],
            "coolant_cartridge": _VNF_EOT_ITEM_LABELS["coolant_cartridge"],
            "signal_amp": _VNF_EOT_ITEM_LABELS["signal_amp"],
        },
    }

    def _vnf_eot_unquote(value):
        return str(value).strip().strip("'\"")

    def _vnf_eot_action_value(action_str):
        """Extract the game value from simple SetVariable/Return actions."""
        if "value=" in action_str:
            raw = action_str.split("value=", 1)[1].split(")", 1)[0]
            return _vnf_eot_unquote(raw)

        if "Return" in action_str and "(" in action_str:
            raw = action_str.split("(", 1)[1].rsplit(")", 1)[0]
            return _vnf_eot_unquote(raw)

        # Some Ren'Py versions render SetVariable as positional arguments.
        if ("SetVariable" in action_str or "SetScreenVariable" in action_str) and "(" in action_str:
            raw = action_str.split("(", 1)[1].rsplit(")", 1)[0]
            parts = raw.split(",")
            if len(parts) >= 2:
                return _vnf_eot_unquote(parts[-1])

        return None

    def _vnf_eot_label_buttons(per_screen):
        """Label unlabelled imagebuttons on Echoes screens.

        Reads SetVariable/Return actions to determine the button's
        purpose and generates a human-readable label.
        """
        for scr in per_screen:
            tag = scr.get("_tag", "")
            labels_map = _EOT_BUTTON_LABELS.get(tag)
            if not labels_map and tag != "observatory_map":
                continue
            for btn in scr.get("buttons", []):
                # Observatory map labels include icon glyphs such as the
                # current-location marker. Rebuild them from Return values so
                # agents see deterministic labels instead of glyph fallbacks.
                force_label = tag == "observatory_map"
                # Skip other buttons that already have a label.
                if (
                    not force_label
                    and btn.get("label")
                    and not btn["label"].startswith("[")
                ):
                    continue
                # Try to extract value from action strings.
                for action_str in btn.get("action_strs", []):
                    val = _vnf_eot_action_value(action_str)
                    if tag == "observatory_map":
                        label = _vnf_eot_map_label(val)
                    else:
                        label = labels_map.get(val)
                    if label:
                        btn["original_label"] = btn.get("label", "")
                        btn["label"] = label
                        if tag == "observatory_map":
                            subtitle = _vnf_eot_map_subtitle(val)
                            if subtitle:
                                btn["annotation"] = subtitle
                        break
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_label_buttons, priority=10)

    # -- Two-step console: reflect the armed state (freeplay live-run item) --
    # REFERENCE PATTERN for two-step select-then-run screens: the audit
    # console's dataset buttons only ARM a selection (SetVariable); a
    # separate action button runs it. The transform surfaces that state as
    # ONE terse status line read from the screen's own selection variable —
    # Roadwarden idiom: reflect the state ("armed or not"), never explain
    # the mechanic. The screen's own "Select a dataset to expose available
    # actions." text already covers the unarmed case.
    _VNF_EOT_AUDIT_DATASET_LABELS = {
        "trust": "Trust Protocol",
        "temporal": "Temporal Model",
        "chen": "Chen Profile",
        "aria_code": "ARIA Core Audit",
        "liaison": "Liaison Thread '45",
    }

    def _vnf_eot_audit_armed_status(per_screen):
        for scr in per_screen:
            if scr.get("_tag", "") != "station_audit_console":
                continue
            label = _VNF_EOT_AUDIT_DATASET_LABELS.get(
                getattr(renpy.store, "audit_focus", None))
            if label:
                scr["texts"] = ["DATASET ARMED: {}".format(label)] + (
                    scr.get("texts") or [])
        return per_screen

    _vnf_add_screen_transform(_vnf_eot_audit_armed_status, priority=12)
