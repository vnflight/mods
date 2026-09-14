################################################################################
## Inventory/Stats Override for LLM Player - Roadwarden
##
## Overrides _vnf_get_inventory_stats() from vnflight.rpy to expose this
## game's player-visible state: inventory items, character stats (vitality,
## mana, food, armor, appearance, cleanliness), class, religion, goal,
## location, coins, and day/time.
##
## Hidden internal state (quest flags, NPC relationships, area unlocks,
## internal counters) is exposed separately via _rw_hidden_stats() in
## roadwarden_progress.rpy.
##
## This runs at init -989 so it executes AFTER vnflight.rpy's default
## definition at init -990, replacing it.
################################################################################

init -989 python:

    # -- Roadwarden screen transform: label attitude buttons --
    def _vnf_roadwarden_label_attitudes(per_screen):
        """Relabel attitude imagebuttons with ``[attitude: value]``.

        Roadwarden's attitude system uses imagebuttons that set
        ``field=at`` to one of: friendly, playful, distanced,
        intimidating, vulnerable.  The scraper auto-labels them
        ``[value]`` from the action; this transform prefixes with
        ``attitude:`` so they're distinguishable from class actions.
        """
        _att = {"friendly", "playful", "distanced",
                "intimidating", "vulnerable"}
        _att_upper = {a.upper() for a in _att}
        for scr in per_screen:
            for btn in scr.get("buttons", []):
                for s in btn.get("action_strs", []):
                    if "field=at " in s and "value=" in s:
                        val = s.split("value=", 1)[1].split()[0]
                        if val in _att:
                            btn["original_label"] = btn.get("label", "")
                            btn["label"] = "[attitude: {}]".format(val)
                        break
            # Clean up ability/attitude description texts that leak
            # from the UI (e.g. "PLAYFUL\nUse a joke or a witty comment."
            # or "KNOWLEDGE\nYour education could be of use here.").
            _class_upper = {"FORCE", "SPELL", "KNOWLEDGE"}
            if scr.get("texts"):
                _cleaned = []
                for t in scr["texts"]:
                    _first = t.split("\n", 1)[0].strip()
                    if _first in _att_upper:
                        # Attitude descriptions: drop entirely
                        # (redundant with [attitude: X] buttons).
                        continue
                    if _first in _class_upper:
                        # Class ability descriptions: reformat as
                        # tagged hint (e.g. "[knowledge] desc...").
                        _rest = t.split("\n", 1)[1].strip() if "\n" in t else ""
                        if _rest:
                            _cleaned.append("[{}] {}".format(
                                _first.lower(), _rest))
                        continue
                    _cleaned.append(t)
                scr["texts"] = _cleaned
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_label_attitudes, priority=8)

    # -- Roadwarden menu augmenter: tag choices by inline image type --
    _VNF_RW_CHOICE_IMAGE_TAGS = {
        "d6": "[chance]",          # dice = random chance
        "d62": "[chance]",         # dice variant
        "coin": "[cost]",          # coin = costs money
        "cointest": "[cost]",      # coin variant
        "coin3": "[cost]",
        "coinalt": "[cost]",
        "coingray": "[cost]",
        "100coins": "[cost]",
    }

    def _vnf_roadwarden_augment_dice(ctx):
        """Tag choices by their inline image type (extracted from raw label).

        The shim extracts {image=X} tags from raw choice labels before
        stripping and stores them as _image_tags on the choice dict.
        """
        _filtered = []
        for c in ctx["choices"]:
            label = c.get("label", "")
            _stripped = label.strip()
            # Drop the shim's disabled-placeholder sentinel — it's a
            # slot awaiting class/attitude selection with no useful
            # info for the agent.
            if _stripped in ("(disabled)", ""):
                if c.get("is_disabled") or c.get("disabled"):
                    continue
            _filtered.append(c)
            if any(label.startswith(p) for p in ("[chance]", "[cost]", "[special]")):
                continue
            tags = c.get("_image_tags", [])
            if tags:
                prefix = None
                for tag in tags:
                    base = tag.rsplit("/", 1)[-1].split(".")[0]
                    if base in _VNF_RW_CHOICE_IMAGE_TAGS:
                        prefix = _VNF_RW_CHOICE_IMAGE_TAGS[base]
                        break
                if prefix is None:
                    prefix = "[special]"
                c["label"] = "{} {}".format(prefix, _stripped)
            elif label != label.lstrip():
                # Fallback: leading space from stripped image tag.
                c["label"] = "[special] {}".format(_stripped)
        ctx["choices"] = _filtered
        return ctx

    _vnf_add_menu_augmenter(_vnf_roadwarden_augment_dice, priority=20)

    # -- Roadwarden menu augmenter: drop stale "(disabled)" hints --

    def _vnf_roadwarden_drop_stale_hints(ctx):
        """Drop "(disabled)"-suffix hints whose `if` condition has
        become False since Menu.execute.

        Roadwarden uses pattern like:
            'I'm too exhausted... (disabled)' if not pc_hp and scholar:
                pass

        When Menu.execute captured pc_hp=0, the hint is included and
        surfaced.  After the player drinks a potion, pc_hp>0 and the
        condition is False — but the frozen ctx still shows the hint.
        Re-evaluate live and drop items whose condition no longer
        holds.
        """
        raw = ctx.get("raw_ast_items") or []
        if not raw:
            return None
        # Collect labels whose `if` condition is currently False.
        _dead = set()
        for ri in raw:
            _cond = ri.get("condition")
            if not isinstance(_cond, str):
                _ik = ri.get("item_kwargs", {})
                if _vnf_is_mapping(_ik):
                    _cond = _ik.get("condition")
            if not isinstance(_cond, str):
                continue
            try:
                _live = bool(renpy.python.py_eval(_cond))
            except Exception:
                _live = True
            if not _live:
                _dead.add(ri.get("label", ""))
        if not _dead:
            return None
        _kept = []
        _changed = False
        for c in ctx["choices"]:
            lbl = c.get("label", "")
            if c.get("disabled") and lbl.endswith("(disabled)"):
                # The dice/icon augmenter (priority 20) may have
                # prepended [chance]/[cost]/[special] to the label.
                # Strip known prefixes before matching against raw
                # AST labels which lack them.
                _match_lbl = lbl
                for _pfx in ("[chance] ", "[cost] ", "[special] "):
                    if _match_lbl.startswith(_pfx):
                        _match_lbl = _match_lbl[len(_pfx):]
                        break
                for _dl in _dead:
                    if _dl and (_dl == _match_lbl
                                or _match_lbl.startswith(_dl[:40])):
                        _changed = True
                        break
                else:
                    _kept.append(c)
                    continue
                continue
            _kept.append(c)
        if _changed:
            ctx["choices"] = _kept
            return ctx
        return None

    _vnf_add_menu_augmenter(_vnf_roadwarden_drop_stale_hints, priority=22)

    # -- Roadwarden screen transform: tag choice buttons by icon --
    # Image tag -> label prefix mapping.
    _VNF_RW_IMAGE_TAGS = {
        "d6": "[chance]",          # dice = random chance
        "d62": "[chance]",         # dice variant
        "coin": "[cost]",          # coin = costs money
        "cointest": "[cost]",      # coin variant
        "coin3": "[cost]",
        "coinalt": "[cost]",
        "coingray": "[cost]",
        "100coins": "[cost]",
    }

    def _vnf_roadwarden_tag_dice(per_screen):
        """Tag ChoiceReturn buttons by their inline icon type.

        Uses _image_tags from the walker to distinguish dice (chance)
        from dragon bones (cost) and other icons.
        """
        for scr in per_screen:
            for btn in scr.get("buttons", []):
                if "ChoiceReturn" not in btn.get("actions", []):
                    continue
                label = btn.get("label", "")
                if label.startswith("[chance]") or label.startswith("[cost]"):
                    continue
                tags = btn.get("_image_tags", [])
                prefix = None
                for tag in tags:
                    # Match by basename (tags may include path).
                    base = tag.rsplit("/", 1)[-1].split(".")[0]
                    if base in _VNF_RW_IMAGE_TAGS:
                        prefix = _VNF_RW_IMAGE_TAGS[base]
                        break
                if prefix:
                    btn["label"] = "{} {}".format(prefix, label.strip())
                elif btn.get("has_image"):
                    # Unknown image — tag generically.
                    btn["label"] = "[special] {}".format(label.strip())
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_tag_dice, priority=7)

    # -- Roadwarden screen transform: label map destination buttons --
    # Map of internal destination names to user-friendly labels.
    # The local LLM can fill in missing entries by reading the game
    # source; any destination not listed here falls back to the raw
    # internal name (e.g. "[map: southerncrossroads]").
    _VNF_ROADWARDEN_MAP_NAMES = {
        "militarycamp": "Tulia's Camp",
        "southerncrossroads": "Southern Crossroads",
        "peltnorth": "Pelt of the North",
        "ruinedvillage": "Ruined Village",
        "beholder": "The Large Tree",
        "druidcave": "The Elders' Cave",
        "howlersdell": "Howler's Dell",
        "rockslide": "A Rockslide",
        "fishinghamlet": "The Fishing Hamlet",
        "westerncrossroads": "The Western Crossroads",
        "oldpagos": "Old Pagos",
        "monastery": "The Monastery",
        "westgate": "The Gate",
        "ford": "A Ford",
        "bogentrance": "The Old Forest Garden",
        "bogcrossroads": "Bog Crossroads",
        "bogroad": "Bog Road",
        "peatfield": "The Peat Fields",
        "vines": "The Creepers",
        "whitemarshes": "White Marshes",
        "ruinedshelter": "Ruined Shelter",
        "northernroad": "The Northern Road",
        "foggylake": "Foggy Lake",
        "howlerslair": "The Lair of Howlers",
        "oldtunnel": "The Old Tunnel",
        "galerocks": "Gale Rocks",
        "beach": "The Pier",
        "dolmen": "The Dolmen",
        "fallentree": "A Fallen Tree",
        "watchtower": "The Abandoned Watchtower",
        "eudociahouse": "The Secluded Residence",
        "stonebridge": "The Old Bridge",
        "stonesign": "A Woodland Edge",
        "ghoulcave": "A Small Cave",
        "giantstatue": "The Giant",
        "mountainroad": "A Nest",
        "greenmountaintribe": "The Tribe of the Green Mountain",
        "huntercabin": "The Cabin",
        "foragingground": "Foraging Ground",
        "wanderer": "The Wanderer",
        "creeks": "Creeks",
    }

    # Area ids the name table above does not carry, because they are not
    # map destinations: the sea legs, path segments between roads, and
    # numbered/suffixed variants of a named place.  Resolved by rule rather
    # than by listing every one, so a variant we have never stood in still
    # comes out readable instead of as a raw id.
    _VNF_ROADWARDEN_EXTRA_AREA_NAMES = {
        "banditshideout": "Bandits Hideout",
        "beforebeach": "Towards the beach",
        "cairn": "Cairn",
        "griffonsroad": "Griffons Road",
        "herbalmeadow": "Herbal Meadow",
    }

    # The seven shortcut segments run their words together in the id.
    # Spell them out; an unlisted one keeps its suffix verbatim.
    _VNF_ROADWARDEN_SHORTCUT_NAMES = {
        "westernentrance": "western entrance",
        "easternentrance": "eastern entrance",
        "deepforest": "deep forest",
        "darkforest": "dark forest",
        "woodenroad": "wooden road",
        "banditshideoutroad": "bandits hideout road",
        "cairn": "cairn",
        "herbalmeadow": "herbal meadow",
    }

    def _vnf_rw_area_display(area):
        """Return a readable name for a pc_area id.

        Order: the map table, then our extras, then the shapes the game
        uses for non-destination areas -- a "sea_north<n>" crossing, a
        "shortcut-<where>" segment, a "<place>_<variant>" blockade, a
        "<place><nn>" numbered stretch.  Anything still unrecognised is
        returned verbatim: a raw id is stable, journallable and usually
        self-describing, and it keeps the gap visible instead of silent.
        """
        if not area:
            return None
        # No shim helpers here: this runs inside slices of the mod that the
        # tests exec against a bare namespace, and area ids are plain
        # identifiers on both Python 2 and 3.
        _key = area if hasattr(area, "startswith") else "%s" % (area,)
        _named = _VNF_ROADWARDEN_MAP_NAMES.get(_key)
        if _named:
            return _named
        _named = _VNF_ROADWARDEN_EXTRA_AREA_NAMES.get(_key)
        if _named:
            return _named
        if _key.startswith("sea_south"):
            return "Voyage back from High Island"
        if _key.startswith("sea_"):
            return "Voyage to High Island"
        if _key.startswith("shortcut-"):
            _raw = _key[len("shortcut-"):]
            _where = _VNF_ROADWARDEN_SHORTCUT_NAMES.get(
                _raw, _raw.replace("-", " ").replace("_", " "))
            return "Shortcut ({})".format(_where) if _where else "Shortcut"
        # "<place>_<variant>" and "<place><nn>": fall back to the place.
        _base = _key.split("_")[0]
        _stripped = _base.rstrip("0123456789")
        for _candidate in (_base, _stripped):
            if _candidate and _candidate != _key:
                _named = (_VNF_ROADWARDEN_MAP_NAMES.get(_candidate)
                          or _VNF_ROADWARDEN_EXTRA_AREA_NAMES.get(_candidate))
                if _named:
                    return _named
        # "<place><suffix>" with no separator (eudociahouseinside): the
        # longest named place the id starts with.
        _prefix = ""
        for _table in (_VNF_ROADWARDEN_MAP_NAMES,
                       _VNF_ROADWARDEN_EXTRA_AREA_NAMES):
            for _place in _table:
                if (len(_place) > len(_prefix) and len(_place) >= 4
                        and _key.startswith(_place)):
                    _prefix = _place
        if _prefix:
            return (_VNF_ROADWARDEN_MAP_NAMES.get(_prefix)
                    or _VNF_ROADWARDEN_EXTRA_AREA_NAMES.get(_prefix))
        return _key

    # Map destination IDs whose _firsttime variable prefix differs
    # from the destination ID used in SetField actions.
    _VNF_ROADWARDEN_VARPREFIX = {
        "eudociahouse": "eudocia",
        "militarycamp": "prologuemilitarycamp",
    }

    # Locations that have no _firsttime variable — treat as visited
    # whenever their _unlocked flag is set.  The prologue camp is the
    # starting area and never gets a _firsttime counter.
    _VNF_ROADWARDEN_ALWAYS_VISITED = {"militarycamp"}

    # High Island expedition: departure-point IDs -> friendly names.
    # Mined from bridge/logs/playthrough_20260817_091448.jsonl: the only
    # non-destination gameplay button on map_display carries
    #   SetField field=world_popupnarration_name value=highislandprep
    #   SetField field=highisland_journey_startingpoint value=hamlet
    # and scrapes with the bare label "[hamlet]" (a raw Ren'Py-style
    # token, not a sentence), which made the finale departure screen
    # effectively undiscoverable.  Only "hamlet" has ever been observed;
    # unknown IDs fall through to the raw value.
    _VNF_ROADWARDEN_DEPARTURE_POINTS = {
        "hamlet": "The Fishing Hamlet",
    }

    def _vnf_rw_fmt_quarters(q):
        """Format a Roadwarden travel time (quarter-hours) as "3h15m"."""
        try:
            q = int(q)
        except Exception:
            return None
        _h = q // 4
        _m = (q % 4) * 15
        if _h and _m:
            return "{}h{:02d}m".format(_h, _m)
        if _h:
            return "{}h".format(_h)
        return "{}m".format(_m)

    def _vnf_rw_daylight_left():
        """Quarters of daylight remaining today, or None if unknown."""
        _wdl = getattr(renpy.store, "world_daylength", None)
        _q = getattr(renpy.store, "quarters", None)
        if _wdl is None or _q is None:
            return None
        try:
            return int(_wdl) - int(_q)
        except Exception:
            return None

    # Per-location facility data extracted from map.rpy.
    # Each entry: (condition_string_or_None, short_label).
    # None = always available when the location is explored.
    _VNF_ROADWARDEN_FACILITIES = {
        "militarycamp": [
            (None, "shelter"),
        ],
        "southerncrossroads": [
            ("day >= southerncrossroads_wildplants_start "
             "and southerncrossroads_wildplants_left", "food"),
        ],
        "peltnorth": [
            ("peltnorth_resting", "shelter"),
            ("peltnorth_resting", "rest"),
            ("iason_shop or iason_food_berries == 2", "food"),
            ("iason_shop or peltnorth_selling", "trader"),
            ("peltnorth_armorer_abouttrade", "tailor"),
            (None, "water"),
        ],
        "ruinedvillage": [
            ("ruinedvillage_part_river", "water"),
            ("ruinedvillage_part_river", "fishing"),
        ],
        "druidcave": [
            ("druidcave_cave_open", "shelter"),
        ],
        "howlersdell": [
            ("howlersdell_eryx_about_room", "shelter"),
            ("howlersdell_eryx_about_room", "rest"),
            ("howlersdell_eryx_about_shop", "food"),
            ("akakios_shop_firsttime", "trader"),
            ("howlersdell_bion_shop", "tailor"),
            ("howlersdell_mundanework_available "
             "and not howlersdell_mundanework_blocked", "work"),
        ],
        "fishinghamlet": [
            ("fishinghamlet_areas_seen_07", "water"),
        ],
        "monastery": [
            ("monastery_sleep_unlocked", "shelter"),
        ],
        "bogentrance": [
            ("day >= 5", "food"),
        ],
        "peatfield": [
            ("thyrsus_shop", "trader"),
        ],
        "whitemarshes": [
            ("whitemarshes_rest_unlocked "
             "and not whitemarshes_attacked", "shelter"),
            ("helvius_about_buying "
             "and not whitemarshes_attacked", "trader"),
        ],
        "galerocks": [
            ("galerocks_fulvia_sleep", "shelter"),
            ("galerocks_porcia_firsttime", "food"),
            ("galerocks_tatius_firsttime", "trader"),
            ("galerocks_rufina_firsttime", "tailor"),
            ("galerocks_aquila_firsttime", "water"),
        ],
        "beach": [
            ("galerocks_photios_about_mundanejob", "work"),
            (None, "water"),
        ],
        "fallentree": [
            (None, "water"),
            (None, "fishing"),
        ],
        "watchtower": [
            ("watchtower_open", "shelter"),
            ("day >= watchtower_wildplants_start "
             "and watchtower_wildplants_left", "food"),
        ],
        "eudociahouse": [
            ("eudocia_sleep_available", "shelter"),
            ("eudocia_about_selling", "trader"),
        ],
        "ghoulcave": [
            ("ghoulcave_wildplants_left", "food"),
            (None, "water"),
            (None, "fishing"),
        ],
        "greenmountaintribe": [
            ("greenmountaintribe_sleep", "shelter"),
            ("cephasgaiane_shop "
             "and not cephasgaiane_shop_dragonhorn", "trader"),
        ],
        "foragingground": [
            ("foragingground_foraging_amount < 4", "food"),
        ],
        "wanderer": [
            (None, "water"),
            (None, "fishing"),
        ],
        "foggylake": [
            ("foggy_about_shelter", "shelter"),
            ("foggy_about_shelter", "rest"),
            ("foggy_about_trade", "food"),
            ("foggy_about_trade", "trader"),
        ],
        "creeks": [
            ("creeks_sleep_available", "shelter"),
            ("oldhava_about_trade", "food"),
            ("creeks_mundanework", "work"),
            (None, "water"),
        ],
        "northernroad": [
            (None, "fishing"),
        ],
    }

    def _vnf_get_location_facilities(loc):
        """Return list of active facility short-labels for a location."""
        entries = _VNF_ROADWARDEN_FACILITIES.get(loc)
        if not entries:
            return []
        active = []
        for cond, label in entries:
            if cond is None:
                active.append(label)
                continue
            try:
                if renpy.python.py_eval(cond):
                    active.append(label)
            except Exception:
                pass
        # Deduplicate while preserving order.
        seen = set()
        result = []
        for f in active:
            if f not in seen:
                seen.add(f)
                result.append(f)
        return result

    def _vnf_roadwarden_label_map_buttons(per_screen):
        """Relabel map destination buttons with their destination name.

        Roadwarden's map screens (map_display, map_onlyview) use
        unlabelled imagebuttons whose actions include
        ``SetField field=destination value=<location>`` or
        ``SetField field=travel_destination value=<location>``.
        Without this transform they show as empty or ``[unlabelled]``.

        Also cleans up map-specific UI buttons:
        - Close/dismiss buttons get a ``[close map]`` label
        - Tutorial dismiss buttons (SetField tutorial_*) are prefixed
        """
        # If map_onlyview is showing (modal, read-only), suppress any
        # lingering map_display screen's output — the game layers both
        # when transitioning, and merged texts produce duplicate map
        # headers ("Interactive..." alongside "Read-only...") that
        # confuse agents.
        _has_onlyview = any(
            s.get("_tag", "") == "map_onlyview" for s in per_screen)
        for scr in per_screen:
            scr_tag = scr.get("_tag", "")
            if "map" not in scr_tag:
                continue
            if _has_onlyview and scr_tag == "map_display":
                # Hide stale map_display texts/buttons — map_onlyview
                # takes precedence.
                scr["texts"] = []
                scr["buttons"] = []
                continue
            # Drop static legend texts (Nighttime shelter, etc.)
            # — they're map key labels, not narrative content.
            # Replace with current location header.
            _cur_area = getattr(renpy.store, "pc_area", None)
            _cur_name = _vnf_rw_area_display(_cur_area) if _cur_area else None
            # map_onlyview is always read-only by definition.  Only
            # trust timescreen for map_display, where it actually
            # distinguishes "travel allowed" from "view only" modes.
            if scr_tag == "map_onlyview":
                _can_travel = False
            else:
                _can_travel = getattr(
                    renpy.store, "timescreen", None) == 1
            _header = "Current location: {}".format(
                _cur_name) if _cur_name else "Map"
            if _can_travel:
                _header = ("[Interactive travel map — pick a destination "
                           "to travel. Takes in-game time.]\n" + _header)
            else:
                _header = ("[Read-only map — cannot travel from here. "
                           "Close to continue.]\n" + _header)
            def _is_travel_notice_path(_path, _button_paths):
                """Return True for map notice text rendered after map buttons."""
                try:
                    _p = tuple(_path or ())
                except Exception:
                    return False
                if len(_p) < 3:
                    return False
                # The travel notice is rendered as a Window/Text sibling after
                # the map buttons. Use the text path relative to button paths
                # instead of preserving arbitrary non-static map text.
                _container = _p[:-2]
                _sibling = _p[-2]
                _max_button_sibling = None
                for _bp in _button_paths:
                    try:
                        _bt = tuple(_bp or ())
                    except Exception:
                        continue
                    if len(_bt) <= len(_container):
                        continue
                    if _bt[:len(_container)] != _container:
                        continue
                    _bi = _bt[len(_container)]
                    if not isinstance(_bi, int):
                        continue
                    if (_max_button_sibling is None
                            or _bi > _max_button_sibling):
                        _max_button_sibling = _bi
                return (
                    _max_button_sibling is not None
                    and isinstance(_sibling, int)
                    and _sibling > _max_button_sibling)

            _travel_notice_texts = []
            _travel_notice_paths = []
            if scr_tag == "map_display" and _can_travel:
                _button_paths = [
                    _btn.get("_path", ()) for _btn in scr.get("buttons", [])
                ]
                _text_paths = scr.get("_text_paths", [])
                for _ti, _raw_text in enumerate(scr.get("texts", [])):
                    _raw_text_s = str(_raw_text).strip()
                    if not _raw_text_s:
                        continue
                    _raw_path = (
                        _text_paths[_ti] if _ti < len(_text_paths) else ())
                    _raw_text_l = _raw_text_s.lower()
                    _is_notice = _is_travel_notice_path(
                        _raw_path, _button_paths)
                    # Fallback for older shim snapshots without text paths.
                    if not _is_notice and not _raw_path:
                        _is_notice = "muddy roads" in _raw_text_l
                    if _is_notice:
                        _travel_notice_texts.append(_raw_text_s)
                        _travel_notice_paths.append(_raw_path)
            scr["texts"] = [_header] + _travel_notice_texts
            scr["_text_paths"] = [()] + _travel_notice_paths
            scr["_text_sections"] = [0] * len(scr["texts"])

            # Build focus_list coordinate lookup for this screen.
            # Maps destination ID -> (x, y) from rendered button
            # positions, used for compass direction calculation.
            _dest_coords = {}
            _cur_loc_xy = None
            try:
                for _f in renpy.display.focus.focus_list:
                    if _f.x is None:
                        continue
                    _fscr = _vnf_get_focus_screen_name(_f)
                    if _fscr != scr_tag:
                        continue
                    _fa = getattr(_f.widget, "action", None)
                    if _fa is None:
                        continue
                    _fa_list = (_fa if _vnf_is_sequence(_fa)
                                else [_fa])
                    # Current location: Hide-only button whose
                    # tooltip mentions the current area name.
                    # Player marker uses Hide (closes map on click);
                    # locked locations use NullAction.
                    if (_cur_loc_xy is None
                            and len(_fa_list) == 1
                            and _fa_list[0].__class__.__name__ == "Hide"):
                        _hov = getattr(_f.widget, "hovered", None)
                        _hov_list = (_hov if _vnf_is_sequence(_hov) else
                            [_hov] if _hov else [])
                        for _ha in _hov_list:
                            _tt = str(getattr(_ha, "value", ""))
                            if _cur_name and _cur_name in _tt:
                                _cur_loc_xy = (
                                    _f.x + _f.w // 2,
                                    _f.y + _f.h // 2)
                                break
                    for _a in _fa_list:
                        if _a.__class__.__name__ == "SetField":
                            _fld = getattr(_a, "field", "")
                            if _fld in ("travel_destination",
                                         "destination"):
                                _val = getattr(_a, "value", "")
                                _dest_coords[_val] = (
                                    _f.x + _f.w // 2,
                                    _f.y + _f.h // 2)
            except Exception:
                pass

            # Fallback: if current location isn't on the map (intermediary
            # locations like bog_road), approximate from the nearest
            # destination by travel time.
            if _cur_loc_xy is None and _dest_coords:
                _best_dist = 9999
                _best_dest = None
                for _fd, _fxy in _dest_coords.items():
                    _fdist = getattr(renpy.store, "to" + _fd, None)
                    if _fdist is not None and int(_fdist) < _best_dist:
                        _best_dist = int(_fdist)
                        _best_dest = _fd
                if _best_dest is not None:
                    _cur_loc_xy = _dest_coords[_best_dest]

            for btn in scr.get("buttons", []):
                lbl = btn.get("label", "")
                acts_strs = btn.get("action_strs", [])
                acts = btn.get("actions", [])

                # High Island expedition: crew-gathering / departure
                # button.  It is NOT a travel destination (it opens
                # world_popupnarration_box with the crew roster), and
                # the game renders it as the bare token "[hamlet]" in
                # the map's nav strip, which reads as noise.  Relabel it
                # in the game's own diction: "Once I'm ready, I need to
                # go to my boat in the early morning hours.  From there,
                # I'll gather my crew and we'll leave in the evening."
                # The button only exists once the expedition is
                # unlocked (absent on days 1-13 of the logged run,
                # present from day 34), so annotating whenever it is
                # scraped is already gated on its own availability.
                if any("field=world_popupnarration_name "
                       "value=highislandprep" in s for s in acts_strs):
                    _dep_id = None
                    for s in acts_strs:
                        if ("field=highisland_journey_startingpoint "
                                "value=" in s):
                            _dep_id = s.split("value=", 1)[1].split()[0]
                            break
                    _dep_name = _VNF_ROADWARDEN_DEPARTURE_POINTS.get(
                        _dep_id, _dep_id or "your boat")
                    btn["original_label"] = lbl
                    btn["label"] = (
                        "[depart: {}] set sail for the High Island — "
                        "be at the boat in the early morning hours to "
                        "gather your crew (or go alone); "
                        "you leave in the evening".format(_dep_name))
                    btn["_category"] = "map"
                    # Sort ahead of every travel destination: this is
                    # the finale gate and was found by trial and error.
                    btn["_sort_dist"] = -1
                    continue

                # Destination buttons: unlabelled or raw internal name.
                _dest_fields = ("field=destination ", "field=travel_destination ")
                _found_dest = False
                for s in acts_strs:
                    if not any(df in s for df in _dest_fields):
                        continue
                    if "value=" not in s:
                        continue
                    raw = s.split("value=", 1)[1].split()[0]
                    friendly = _VNF_ROADWARDEN_MAP_NAMES.get(raw, raw)
                    # Check if destination has been visited.
                    # _firsttime >= 1 means physically visited (game
                    # uses 1 for first visit, 2+ for repeat visits).
                    _var_pfx = _VNF_ROADWARDEN_VARPREFIX.get(raw, raw)
                    _ft = getattr(
                        renpy.store, _var_pfx + "_firsttime", None)
                    _explored = (_ft is not None and _ft >= 1) or raw in _VNF_ROADWARDEN_ALWAYS_VISITED
                    # Travel time from to<dest> variable (in quarters).
                    _dist = getattr(renpy.store, "to" + raw, None)
                    _dist_q = int(_dist) if (_dist is not None
                        and isinstance(_dist, (int, float))) else None
                    if _dist_q is not None:
                        _hrs = _dist_q // 4
                        _mins = (_dist_q % 4) * 15
                        _time_str = "{}h{:02d}m".format(
                            _hrs, _mins) if _hrs else "{}m".format(_mins)
                    else:
                        _time_str = None
                    # Compass direction from focus_list coordinates.
                    _arrow = ""
                    _dxy = _dest_coords.get(raw)
                    if _cur_loc_xy and _dxy:
                        _dx = _dxy[0] - _cur_loc_xy[0]
                        _dy = _cur_loc_xy[1] - _dxy[1]  # Y inverted
                        if abs(_dx) > 20 or abs(_dy) > 20:
                            if abs(_dy) > abs(_dx) * 2:
                                _arrow = "\u2191" if _dy > 0 else "\u2193"
                            elif abs(_dx) > abs(_dy) * 2:
                                _arrow = "\u2190" if _dx < 0 else "\u2192"
                            elif _dy > 0:
                                _arrow = "\u2196" if _dx < 0 else "\u2197"
                            else:
                                _arrow = "\u2199" if _dx < 0 else "\u2198"
                    # Build label.
                    _prefix = "{} ".format(_arrow) if _arrow else ""
                    if _explored:
                        _facs = _vnf_get_location_facilities(raw)
                        _parts = []
                        if _time_str:
                            _parts.append(_time_str)
                        _parts.extend(_facs)
                        _suffix = (
                            " \u2014 " + ", ".join(_parts)
                            if _parts else "")
                        btn["label"] = "{}[map: {}{}]".format(
                            _prefix, friendly, _suffix)
                    else:
                        # Not yet visited: hide name and facilities
                        # (matches user experience — just an arrow).
                        if _time_str:
                            btn["label"] = "{}[map: unexplored \u2014 {}]".format(
                                _prefix, _time_str)
                        else:
                            btn["label"] = "{}[map: unexplored]".format(
                                _prefix)
                    btn["original_label"] = lbl
                    btn["_sort_dist"] = _dist_q if _dist_q is not None else 9999
                    btn["_category"] = "map"
                    # Selecting a destination closes the map immediately, but
                    # Roadwarden may spend several seconds applying travel
                    # before the destination narration is emitted.  Tell the
                    # generic act settle path this button enters story flow;
                    # otherwise it accepts the intermediate location state
                    # and a blind wait-only player misses the arrival prose.
                    # _story_entry is the flag that means that.  Keep
                    # _wait_after_action too: the map closes and the UI
                    # rebuilds, so a post-click re-scrape is expected as well.
                    btn["_wait_after_action"] = True
                    btn["_story_entry"] = True
                    _found_dest = True
                    break
                if _found_dest:
                    continue

                # Close/dismiss button: bare Hide with no destination.
                if lbl in ("", "[unlabelled]") and acts == ["Hide"]:
                    btn["original_label"] = lbl
                    btn["label"] = "[close map]"
                    continue

                # Tutorial dismiss buttons on the map.
                _is_tutorial = any("field=tutorial_" in s for s in acts_strs)
                if _is_tutorial:
                    # Tutorial tooltip controls are not gameplay/map
                    # actions, and in Roadwarden they also hide the map.
                    # Agents already have [close map], so suppress these
                    # subscreen controls from the actionable map output.
                    btn["_vnf_hide"] = True
                    continue

            scr["buttons"] = [
                b for b in scr.get("buttons", [])
                if not b.get("_vnf_hide")
            ]

            # Synthesize [locked] entries for known-but-not-routable
            # destinations on the interactive map.  Without this, agents
            # see only destinations the game currently allows, with no
            # way to tell whether a known-about location is "not unlocked
            # yet" vs "never reachable via map."  Surface the
            # ambiguity-resolver: if the location has *_unlocked set
            # (player has encountered it in dialogue / inventory /
            # read-only map) but isn't on the current travel screen,
            # emit a "[locked] NAME" non-clickable entry.  Only applied
            # to map_display (interactive); map_onlyview already lists
            # everything agents know about.
            if scr_tag == "map_display":
                _rem_q = _vnf_rw_daylight_left()
                _reachable_ids = set()
                for _btn in scr.get("buttons", []):
                    for _s in _btn.get("action_strs", []):
                        if ("field=destination value=" in _s
                                or "field=travel_destination value=" in _s):
                            _raw = _s.split("value=", 1)[1].split()[0]
                            _reachable_ids.add(_raw)
                            break
                for _mid, _mname in _VNF_ROADWARDEN_MAP_NAMES.items():
                    if _mid == _cur_area or _mid in _reachable_ids:
                        continue
                    _vpfx = _VNF_ROADWARDEN_VARPREFIX.get(_mid, _mid)
                    _unlocked = getattr(
                        renpy.store, _vpfx + "_unlocked", None)
                    if not _unlocked:
                        continue
                    # Known but not currently routable — emit locked
                    # entry with sort_dist beyond real destinations.
                    # Category "map" groups with reachable
                    # destinations without overloading generic nav.
                    #
                    # Split the observable causes. Mining the logged run
                    # (playthrough_20260817_091448.jsonl) showed the
                    # game's travel list is filtered by BOTH:
                    #   * daylight — at The Woodland Edge the list went
                    #     29 -> 15 entries as the day burned down, and
                    #     every dropped entry cost more than the time
                    #     left (max shown 4h15m vs 4h15m remaining);
                    #   * story gates — at Howler's Dell the mountain
                    #     locations stayed absent on day 34 with 13h15m
                    #     of daylight and only appeared on days 41/42.
                    # So: travel time > daylight left => certainly too
                    # late today; travel time <= daylight left but still
                    # not offered => another gate or timing margin blocks
                    # it. Values >= 100 are Roadwarden's no-route sentinel,
                    # not a literal 25-hour journey.
                    #
                    # ``to<dest>`` is live and area-relative for locked
                    # destinations too, not just offered ones — verified
                    # live on day 35: White Marshes read 2h15m from
                    # Foggy Lake and 5h30m from Pelt of the North.
                    #
                    # LIMIT (honest) 1: time wins when both apply.  A
                    # destination that is both too late AND gated reports
                    # only "too late today" — the game omits it for
                    # the time reason alone, so nothing in the scrape
                    # proves the gate.  Verified live: White Marshes
                    # read "blocked" at Pelt of the North with 7h45m of
                    # daylight and flipped to "too late today" at 3h.
                    # The map key says so.
                    #
                    # LIMIT (honest) 2: "blocked" is deliberately not
                    # called a story gate.  Live probe at Foggy Lake,
                    # day 35, 3h of daylight: The Pier (2h15m) was
                    # offered while The Peat Fields (2h15m) was not, and
                    # The Peat Fields came back at 3h15m — so the game
                    # applies at least one extra departure margin beyond
                    # "does the trip fit before dusk". We cannot tell that
                    # apart from a story flag in the scrape: the game
                    # exposes no per-destination gate reason in any
                    # scraped field (no tooltip, no disabled button, no
                    # action_strs at all — these entries are synthesized
                    # by us, the game simply omits them).
                    #
                    # LIMIT (honest) 3: when ``to<dest>`` is missing we
                    # cannot split at all and fall back to bare
                    # "[locked]", as before.
                    _ldist = getattr(renpy.store, "to" + _mid, None)
                    if not isinstance(_ldist, (int, float)):
                        _ldist = None
                    _lock_tag = "[locked]"
                    if _ldist is not None and int(_ldist) >= 100:
                        _lock_tag = "[route unavailable]"
                    elif _ldist is not None and _rem_q is not None:
                        _ldist_s = _vnf_rw_fmt_quarters(_ldist)
                        if int(_ldist) > _rem_q:
                            _lock_tag = (
                                "[too late today: "
                                "{} travel, {} of daylight left]".format(
                                    _ldist_s,
                                    _vnf_rw_fmt_quarters(_rem_q)))
                        else:
                            _lock_tag = (
                                "[blocked: {} travel fits, but another "
                                "gate or extra timing margin prevents "
                                "departure]".format(_ldist_s))
                    scr.setdefault("buttons", []).append({
                        "label": "{} {}".format(_lock_tag, _mname),
                        "screen": scr_tag,
                        "actions": [],
                        "action_strs": [],
                        "is_disabled": True,
                        "_category": "map",
                        "_sort_dist": 99999,
                    })

            # Sort destination buttons by distance (closest first).
            # Non-destination buttons (close, tutorial, Show Map Key)
            # stay at the end.  [locked] entries sort last among
            # destinations via their 99999 distance.
            _dest_btns = [b for b in scr.get("buttons", [])
                          if "_sort_dist" in b]
            _other_btns = [b for b in scr.get("buttons", [])
                           if "_sort_dist" not in b]
            _dest_btns.sort(key=lambda b: b["_sort_dist"])
            scr["buttons"] = _dest_btns + _other_btns

            _map_key_visible = any(
                str(b.get("label", "")).strip() == "Show Map Key"
                for b in scr.get("buttons", []))
            if _map_key_visible:
                scr["texts"].append(
                    "Map key:\n"
                    "  - Arrows show direction from your current location.\n"
                    "  - Travel times show how long a destination takes to reach.\n"
                    "  - Tags mark known facilities: water, fishing, food, "
                    "shelter, rest, trader, tailor, work.\n"
                    "  - [too late today] means the map's timing rules "
                    "do not permit setting out now; try earlier.\n"
                    "  - [route unavailable] means there is currently no "
                    "usable route; leaving earlier will not help.\n"
                    "  - [blocked] means the raw trip fits before dusk, "
                    "but another gate or extra timing margin prevents "
                    "departure. The game does not expose which.\n"
                    "  - [locked] alone means the travel time is "
                    "unknown, so the two cases cannot be told apart.\n"
                    "  - unexplored means the destination is not identified yet.")
                scr.setdefault("_text_paths", []).append(())
                scr.setdefault("_text_sections", []).append(0)

            # Signpost the expedition departure entry.  It is the only
            # map entry that is not a travel destination, and the run
            # debrief reported it as undiscoverable, so name it in the
            # map text as well as in the button label.
            if any(str(b.get("label", "")).startswith("[depart:")
                   for b in scr.get("buttons", [])):
                scr["texts"].append(
                    "Expedition: the [depart: ...] entry above is not a "
                    "travel destination — it opens the crew-gathering "
                    "and departure screen for the High Island journey.")
                scr.setdefault("_text_paths", []).append(())
                scr.setdefault("_text_sections", []).append(0)

            # View-only map: no destination buttons, so generate a
            # text summary of known locations with facilities and
            # compass directions.
            if scr_tag == "map_onlyview":
                # Build coordinate lookup from Hide buttons by
                # matching tooltip text to location names.
                _view_coords = {}
                try:
                    for _f in renpy.display.focus.focus_list:
                        if _f.x is None:
                            continue
                        _fscr = _vnf_get_focus_screen_name(_f)
                        if _fscr != scr_tag:
                            continue
                        _hov = getattr(_f.widget, "hovered", None)
                        _hov_list = (_hov if _vnf_is_sequence(_hov) else
                            [_hov] if _hov else [])
                        for _ha in _hov_list:
                            _tt = str(getattr(_ha, "value", ""))
                            for _mid, _mname in _VNF_ROADWARDEN_MAP_NAMES.items():
                                if _mname in _tt:
                                    _view_coords[_mid] = (
                                        _f.x + _f.w // 2,
                                        _f.y + _f.h // 2)
                                    break
                            break  # only check first hovered action
                except Exception:
                    pass
                _visited = []
                _undiscovered = 0
                for _mid, _mname in _VNF_ROADWARDEN_MAP_NAMES.items():
                    if _mid == _cur_area:
                        continue
                    _vpfx = _VNF_ROADWARDEN_VARPREFIX.get(_mid, _mid)
                    _vft = getattr(
                        renpy.store, _vpfx + "_firsttime", None)
                    _unlocked = getattr(
                        renpy.store, _vpfx + "_unlocked", None)
                    if not _unlocked:
                        continue
                    if (_vft is not None and _vft >= 1) or _mid in _VNF_ROADWARDEN_ALWAYS_VISITED:
                        _vfacs = _vnf_get_location_facilities(_mid)
                        # Compass direction
                        _varrow = ""
                        _vdxy = _view_coords.get(_mid)
                        if _cur_loc_xy and _vdxy:
                            _vdx = _vdxy[0] - _cur_loc_xy[0]
                            _vdy = _cur_loc_xy[1] - _vdxy[1]
                            if abs(_vdx) > 20 or abs(_vdy) > 20:
                                if abs(_vdy) > abs(_vdx) * 2:
                                    _varrow = "\u2191 " if _vdy > 0 else "\u2193 "
                                elif abs(_vdx) > abs(_vdy) * 2:
                                    _varrow = "\u2190 " if _vdx < 0 else "\u2192 "
                                elif _vdy > 0:
                                    _varrow = "\u2196 " if _vdx < 0 else "\u2197 "
                                else:
                                    _varrow = "\u2199 " if _vdx < 0 else "\u2198 "
                        _entry = "{}{}".format(_varrow, _mname)
                        if _vfacs:
                            _entry += " ({})".format(", ".join(_vfacs))
                        _visited.append(_entry)
                    else:
                        _undiscovered += 1
                if _visited or _undiscovered:
                    # Header already has the read-only marker; just
                    # list visited destinations.
                    _summary_parts = ["Visited locations:"]
                    _summary_parts.extend(
                        "  - {}".format(v) for v in _visited)
                    if _undiscovered:
                        _summary_parts.append(
                            "{} unexplored location{}".format(
                                _undiscovered,
                                "s" if _undiscovered != 1 else ""))
                    scr["texts"].append("\n".join(_summary_parts))
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_label_map_buttons, priority=9)

    # -- Roadwarden interaction aliases --
    # Travel and Map refer to the same HUD slot but appear in
    # different game contexts.  Register both as aliases so either
    # name works regardless of which is currently visible.
    def _vnf_roadwarden_aliases(interactions):
        for itr in interactions:
            label = itr.get("display_label", "")
            if label == "Travel":
                itr.setdefault("aliases", []).append("Map")
            elif label == "Map":
                itr.setdefault("aliases", []).append("Travel")
            elif label == "Sleep":
                itr.setdefault("aliases", []).append("Seek Shelter")
            elif label == "Seek Shelter":
                itr.setdefault("aliases", []).append("Sleep")
        return interactions

    _vnf_add_alias_provider(_vnf_roadwarden_aliases, priority=50)

    # -- Fallthrough diagnostics: game variables worth logging when
    # run_context returns unexpectedly (moved here from the shim) --
    _vnf_set_diag_state_vars([
        "pc_area", "day", "pc_class", "pc_goal", "pc_hp",
        "destination", "traveltype", "traveling", "pc_state",
        "returning", "griffonsroad_griffons",
    ])

    # -- Screen display names --
    _vnf_set_screen_display_name("restscreen", "Shelter")
    _vnf_set_screen_display_name("waitscreen", "Wait")
    _vnf_set_screen_display_name("map_display", "Map")
    _vnf_set_screen_display_name("map_onlyview", "Map (view only)")
    _vnf_set_screen_display_name("selling", "Shop")
    _vnf_set_screen_display_name("shopscreen", "Shop")
    _vnf_set_screen_display_name("mundanejob", "Work")
    _vnf_set_screen_display_name("charactersheet", "Character")
    _vnf_set_screen_display_name("inventory", "Inventory")
    _vnf_set_screen_display_name("journal", "Journal")
    _vnf_set_screen_display_name("history", "Archive")
    _vnf_set_screen_display_name("confirm", "Confirm")
    _vnf_set_screen_display_name("world_popupnarration_box", "Quest Info")

    # -- Roadwarden auto-skip pause on navigation availability --
    # When HUD buttons like Travel or Sleep are visible, pause
    # auto-skip so the agent can interact with navigation instead
    # of blazing through single-choice continues.
    _VNF_RW_NAV_BUTTONS = {"Travel", "Map", "Wait", "Sleep", "Seek Shelter"}

    # -- Roadwarden button categorization --
    # Tag buttons with _category so the formatter groups them properly.
    _VNF_RW_NAV_LABELS = {
        "Character", "Inventory", "Wait", "Travel", "Map",
        "Sleep", "Seek Shelter", "Rest",
        "Settings", "Q. Save", "Q. Load", "Archive", "Journal",
    }

    def _vnf_roadwarden_categorize_buttons(per_screen):
        """Tag buttons with _category for display grouping."""
        for scr in per_screen:
            tag = scr.get("_tag", "")
            _kept = []
            for btn in scr.get("buttons", []):
                label = btn.get("label", "")
                _action_names = btn.get("actions", [])

                if tag == "nvl":
                    if "Jump" in _action_names:
                        btn["_category"] = "topics"
                    elif "ChoiceReturn" in _action_names:
                        btn["_category"] = "choices"
                    elif not _action_names or all(a in ("none", "NullAction") for a in _action_names):
                        # Disabled-contract mechanism 4: Roadwarden renders
                        # some unavailable options as NullAction textbuttons
                        # (not insensitive ChoiceReturns), so they never hit
                        # the menu contract and used to hide as "info" —
                        # Sonnet's Day-40 "can't use isn't surfaced".
                        # Promote the ones whose label SAYS they are locked
                        # into listed-disabled choices; leave true captions
                        # as info.
                        if ("(disabled)" in label
                                or "(Required" in label
                                or "to unlock" in label):
                            btn["is_disabled"] = True
                            btn["_category"] = "choices"
                        else:
                            btn["_category"] = "info"
                elif tag == "quick_menu":
                    if label in _VNF_RW_NAV_LABELS:
                        # Hide unavailable nav buttons (NullAction).
                        _acts = btn.get("actions", [])
                        if _acts and all(
                                a in ("none", "NullAction")
                                for a in _acts):
                            btn["is_disabled"] = True
                        btn["_category"] = "navigation"
                elif tag in ("shopscreen", "selling"):
                    btn["_category"] = "shop"
                elif tag in ("map_display", "map_onlyview"):
                    btn["_category"] = "navigation"
                elif tag == "tutorialtooltips":
                    btn["_category"] = "info"
                _kept.append(btn)
            scr["buttons"] = _kept
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_categorize_buttons, priority=0)

    def _vnf_roadwarden_drop_choice_buttons(per_screen):
        """Drop NVL choice buttons when a menu is active.
        ChoiceReturn and NullAction/no-action buttons duplicate the
        pending choices (active and disabled) — no need to show both."""
        if not _vnf_current_menu_context[0]:
            return per_screen
        _null_actions = {"none", "NullAction"}
        for scr in per_screen:
            if scr.get("_tag") != "nvl":
                continue
            scr["buttons"] = [
                b for b in scr.get("buttons", [])
                if "ChoiceReturn" not in b.get("action_strs", [])
                and not all(a in _null_actions for a in b.get("actions", ["none"]))
            ]
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_drop_choice_buttons, priority=0)

    def _vnf_roadwarden_nav_guard(per_screen):
        for scr in per_screen:
            for btn in scr.get("buttons", []):
                if btn.get("label", "") in _VNF_RW_NAV_BUTTONS:
                    # Only pause if the button is actually actionable
                    # (not disabled / NullAction).
                    _astrs = btn.get("action_strs", [])
                    if _astrs and all(a == "NullAction" for a in _astrs):
                        continue
                    _vnf_autoskip.pause_reasons.append(
                        "nav_available")
                    return per_screen
        return per_screen

    _vnf_add_screen_transform(_vnf_roadwarden_nav_guard, priority=1)

    # -- Roadwarden HUD cleanup --
    # characterstatus is the always-on side HUD. Its tooltip/status text can
    # outlive focus changes and leak stale armor/item descriptions into state
    # and wait output; the stats footer already carries the useful values.
    def _vnf_roadwarden_drop_characterstatus_hud(per_screen):
        for scr in per_screen:
            if scr.get("_tag", "") == "characterstatus":
                scr["texts"] = []
                scr["buttons"] = []
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_drop_characterstatus_hud, priority=1)

    # -- Roadwarden auto-skip pause on overlay screens --
    # When modal overlays are visible, pause auto-skip so the agent
    # can interact with them before single-choice menus auto-resolve.
    _VNF_RW_OVERLAY_SCREENS = {
        "shopscreen", "selling", "restscreen", "inventory",
        "waitscreen", "mundanejob", "confirm",
        "world_popupnarration_box", "map_onlyview",
        "map_display", "charactersheet", "preferences", "history",
    }

    # Register overlays so the shim sets overlay_active on screen
    # events and pending requests — consumers can suppress stale
    # pending choices without heuristics.
    for _rw_ovr in _VNF_RW_OVERLAY_SCREENS:
        _vnf_register_overlay_screen(_rw_ovr)

    # Register game-specific button categories.
    _vnf_register_button_category("topics", "TOPICS")
    _vnf_register_button_category("shop", "SHOP")
    _vnf_register_button_category("map", "MAP", compact=True)
    _vnf_register_button_category("wait_for", "WAIT FOR...")
    _vnf_register_button_category("wait_until", "WAIT UNTIL...")
    _vnf_register_button_category("rest_free", "SLEEP (FREE)")
    _vnf_register_button_category("rest_paid", "RENT A BED")
    _vnf_register_button_category("rest_util", "OPTIONS")

    # Register section depths for tree-based grouping.
    # Tree at depth 5: two MultiBoxes (text columns, button columns).
    # Their children at depth 6 are the per-room groups.
    _vnf_set_screen_section_depth("restscreen", 5)

    def _vnf_roadwarden_overlay_guard(per_screen):
        for scr in per_screen:
            if scr.get("_tag", "") in _VNF_RW_OVERLAY_SCREENS:
                _vnf_autoskip.pause_reasons.append(
                    "overlay_screen")
                return per_screen
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_overlay_guard, priority=1)

    # -- Roadwarden screen transform: label custom input prompts --
    def _vnf_roadwarden_input_prompt_label(prompt, default="", screen="input"):
        if prompt == "[custom1]":
            return "Which place are you asking about?"
        return prompt

    vnf_player.input_prompt_transform = _vnf_roadwarden_input_prompt_label

    def _vnf_roadwarden_input_prompt_transform(per_screen):
        """Replace internal screen-input labels with player-facing prompts."""
        for scr in per_screen:
            if scr.get("_tag", "") != "input":
                continue
            texts = scr.get("texts", [])
            if "[custom1]" in texts:
                scr["texts"] = [
                    _vnf_roadwarden_input_prompt_label(t)
                    for t in texts
                ]
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_input_prompt_transform, priority=9)

    # -- Roadwarden post-input hook --
    # Roadwarden screen inputs expose a separate Confirm button after text is
    # typed. Keep this game-specific quirk in the mod; shared Python handlers
    # only call the generic after_input_text hook when a mod advertises it.
    def _vnf_roadwarden_after_input_text(cmd_name, cmd_args):
        global _vnf_native_action_queue, _vnf_pending_click
        try:
            for tag, scr in _vnf_get_showing_screens(
                    vnf_player.scrape_visible_list):
                if tag != "confirm":
                    continue
                if scr.child is None and hasattr(scr, "update"):
                    try:
                        scr.update()
                    except Exception:
                        pass
                buttons = []
                _vnf_collect_button_actions(scr, buttons, tag)
                for disp, action_obj, label, screen_name in buttons:
                    norm = _vnf_normalize_quotes(
                        str(label or "")).lower().strip()
                    if norm != "confirm":
                        continue
                    _vnf_native_action_queue = action_obj
                    _vnf_pending_click = {
                        "label": label,
                        "screen": screen_name,
                    }
                    return {
                        "success": True,
                        "handled": True,
                        "causal_boundary": True,
                        "auto_confirmed": True,
                        "resolved_as": "button",
                        "label": label,
                        "screen": screen_name,
                    }
            return {
                "success": True,
                "handled": False,
                "auto_confirm_skipped": "no_confirm_screen",
            }
        except _CONTROL_EXCEPTIONS:
            raise
        except Exception as e:
            return {"success": False, "error": str(e)}

    _vnf_add_command_handler(
        "after_input_text", _vnf_roadwarden_after_input_text)

    # -- Roadwarden screen transform: selling screen --
    # Selling screen buttons are image-only with TooltipAction + Jump.
    # The Jump label encodes the item name (e.g. 'foggylakesellingelkfur').
    # Relabel them so the click handler can find them.
    import re as _vnf_re_sell_scr
    _SELL_SCR_RE = _vnf_re_sell_scr.compile(r'selling(\w+)$')

    def _vnf_roadwarden_sell_transform(per_screen):
        for scr in per_screen:
            if scr.get("_tag", "") != "selling":
                continue
            for btn in scr.get("buttons", []):
                lbl = btn.get("label", "")
                if lbl and lbl not in ("", "[]", "[unlabelled]"):
                    continue
                for s in btn.get("action_strs", []):
                    if not s.startswith("Jump label="):
                        continue
                    target = s.split("label=", 1)[1].split()[0]
                    m = _SELL_SCR_RE.search(target)
                    if m:
                        raw = m.group(1)
                        friendly = _VNF_RW_ITEM_NAMES.get(raw, raw)
                        btn["original_label"] = lbl
                        btn["label"] = "[Sell: {}]".format(friendly)
                    break
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_sell_transform, priority=9)

    # -- Roadwarden screen transform: difficulty selection --

    # Maps SetField field names -> human-readable setting names.
    _VNF_ROADWARDEN_DIFFICULTY_FIELDS = {
        "difficultypick_advanced_world_deadline": "Time limit",
        "difficultypick_advanced_bonusdamage": "Nighttime damage",
        "difficultypick_advanced_questseasier": "Easier quests",
        "difficultypick_advanced_potion": "Healing potion",
        "difficultypick_advanced_coins": "Coins at start",
        "difficultypick_advanced_skip_prologue": "Skip prologue",
    }

    # Fields that are secondary side-effects of another button
    # (e.g. time limit buttons also set questseasier=0).
    # Buttons whose FIRST SetField is one of these get skipped
    # for labelling — the primary field is the one that matters.
    _VNF_ROADWARDEN_DIFFICULTY_SECONDARY = set()

    def _vnf_roadwarden_difficulty_transform(per_screen):
        """Relabel difficulty screen buttons with their setting names.

        Option 2 approach: strip flat setting-name texts, prefix every
        button label with its setting name so the button list is
        self-documenting.  Mark selected buttons.

        For the preset screen, restructure the flat description texts
        to explicitly label each difficulty level.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "difficultypick":
                continue
            btn_labels = [b.get("label", "") for b in scr.get("buttons", [])]
            is_preset = any(l == "Casual" for l in btn_labels)

            if is_preset:
                # Restructure flat texts into labelled blocks.
                # The texts come in order: header, Casual desc,
                # Standard desc, Restrictive desc.
                texts = scr.get("texts", [])
                presets = ["Casual", "Standard", "Restrictive"]
                # Find section headers ("For those...")
                sections = []
                current = []
                for t in texts:
                    if t.startswith("For those") or t.startswith("For the"):
                        if current:
                            sections.append(current)
                        current = [t]
                    elif t.startswith("*"):
                        current.append(t.lstrip("* ").rstrip("."))
                    # Skip the header lines
                if current:
                    sections.append(current)
                if len(sections) == len(presets):
                    new_texts = [
                        "Pick difficulty mode."
                        " This choice can't be altered later on."
                    ]
                    for name, parts in zip(presets, sections):
                        desc = parts[0]
                        if len(parts) > 1:
                            desc += " " + ", ".join(parts[1:]) + "."
                        new_texts.append("{}: {}".format(name, desc))
                    scr["texts"] = new_texts
            else:
                # Advanced mode: prefix labels with setting name,
                # strip texts to just the header.
                _skip = (
                    "Proceed",
                    "(switch to preset options)",
                    "(switch to advanced options)",
                )
                # Track which settings have active buttons so we
                # can show disabled placeholders for missing ones.
                _seen_settings = set()
                for btn in scr.get("buttons", []):
                    lbl = btn.get("label", "")
                    if lbl in _skip:
                        continue
                    # Relabel NullAction hint buttons for locked
                    # settings (e.g. "select no time limit to unlock"
                    # → "Easier quests: disabled (...)").
                    acts = btn.get("actions", [])
                    if acts == ["NullAction"] and "to unlock" in lbl:
                        btn["label"] = "-: Easier quests (disabled," \
                            " select no time limit to enable)"
                        continue
                    # Find the primary SetField for this button.
                    for s in btn.get("action_strs", []):
                        if not s.startswith("SetField"):
                            continue
                        if "field=" not in s:
                            continue
                        field = s.split("field=", 1)[1].split()[0]
                        if field in _VNF_ROADWARDEN_DIFFICULTY_SECONDARY:
                            continue
                        setting = _VNF_ROADWARDEN_DIFFICULTY_FIELDS.get(
                            field)
                        if setting:
                            _seen_settings.add(setting)
                            sel = ""
                            if btn.get("is_selected"):
                                sel = " (selected)"
                            btn["original_label"] = lbl
                            btn["label"] = "{}: {}{}".format(
                                setting, lbl, sel)
                        break
                # Strip flat setting-name texts — the prefixed
                # buttons are now self-documenting.
                scr["texts"] = [
                    "Pick difficulty mode."
                    " This choice can't be altered later on."
                ]
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_difficulty_transform, priority=9
    )

    # -- Roadwarden screen transform: shop screen --

    def _vnf_roadwarden_shop_transform(per_screen):
        """Restructure shop screen texts and filter icon buttons.

        The shopscreen shows bare numeric texts for the player's dragon
        bones and rations (no labels), plus item name/description.
        This transform labels the resources and drops NullAction
        imagebuttons (resource icons with no useful text).
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "shopscreen":
                continue
            # Separate numeric-only texts (resource indicators)
            # from descriptive texts (item name, description).
            nums = []
            descs = []
            for t in scr.get("texts", []):
                if t.strip().isdigit():
                    nums.append(t.strip())
                else:
                    descs.append(t)
            # Only keep resources line — item descriptions are already
            # encoded in enriched button labels (Buy X: price).
            _coins = getattr(renpy.store, "coins", 0)
            _rations = getattr(renpy.store, "item_rations", 0)
            scr["texts"] = [
                "Your resources: {} dragon bones, {} rations".format(
                    _coins, _rations)]
            # Descriptions alternate: name, description, name, …
            # Services come first, then purchasable items.
            _all_names = [descs[i] for i in range(0, len(descs), 2)]

            # Count item buttons (Buy: or disabled Buy or bare "Buy"
            # from the ingredient-shop layout) to separate service
            # names from item names.
            _n_buy = 0
            for b in scr.get("buttons", []):
                _bl = b.get("label", "")
                if (_bl.startswith("Buy:") or _bl.startswith("Buy ")
                        or _bl == "Buy"):
                    _n_buy += 1
                elif _bl.startswith("You already"):
                    _n_buy += 1

            # Detect column-major layout (ingredient shop): descs
            # starts with "An Ingredient" header, followed by N item
            # names, then "Useful for..." header, then N descriptions.
            # The regular shop uses row-major alternating name/desc
            # pairs which _all_names (every-other-from-0) handles.
            _is_col_major = (
                _n_buy > 0
                and len(descs) >= 2
                and descs[0] == "An Ingredient")
            if _is_col_major:
                # Skip leading "An Ingredient" header; next _n_buy
                # items are names.  Services (if any) would appear
                # after the descriptions block; treat none as
                # services for the ingredient shop.
                _item_names = descs[1:1 + _n_buy]
                _service_names = []
            else:
                _n_services = max(len(_all_names) - _n_buy, 0)
                _service_names = _all_names[:_n_services]
                _item_names = _all_names[_n_services:]

            # Clean up buttons: filter NullAction icons (but keep
            # disabled buy buttons), label close, enrich buy and
            # pay buttons with names from display texts.
            cleaned = []
            _buy_idx = 0
            _pay_idx = 0
            for b in scr.get("buttons", []):
                _is_null = b.get("actions", []) == ["NullAction"]
                lbl = b.get("label", "")
                # NullAction icon buttons with no label — pure noise.
                if (_is_null and not lbl.startswith("Buy")
                        and not lbl.startswith("Pay")):
                    continue
                if "Hide" in b.get("actions", []) and not (
                        lbl.startswith("Buy")
                        or lbl.startswith("Pay")
                        or lbl.startswith("You already")):
                    b["original_label"] = lbl
                    b["label"] = "[close shop]"
                elif lbl.startswith("Pay:"):
                    # Service payment — enrich with service name.
                    if _pay_idx < len(_service_names):
                        _price = lbl.split(":", 1)[1].strip()
                        b["original_label"] = lbl
                        b["label"] = "Pay for {}: {}".format(
                            _service_names[_pay_idx], _price)
                    _pay_idx += 1
                elif (lbl.startswith("Buy:")
                        or (_is_null and lbl.startswith("Buy"))
                        or lbl == "Buy"
                        or lbl.startswith("Buy ")):
                    # Bare "Buy" (no colon, no price) appears on the
                    # ingredient-shop layout where price is in a
                    # sibling text column.  Extract name + price from
                    # action_strs: SetField field=item_X value=N +
                    # SetField field=coins value=NEW_COINS.
                    _name = None
                    _bare_price = None
                    _item_key = ""
                    _new_coins = None
                    for s in b.get("action_strs", []):
                        if "field=item_" in s:
                            _item_key = s.split("field=item_", 1)[1].split()[0]
                        elif "field=coins value=" in s:
                            try:
                                _new_coins = int(
                                    s.split("field=coins value=", 1)[1].split()[0])
                            except (ValueError, IndexError):
                                pass
                    if _new_coins is not None and _coins is not None:
                        _bare_price = _coins - _new_coins
                    if _item_key:
                        _kl = _item_key.lower()
                        _best = None
                        _best_len = 9999
                        for t in descs:
                            _tl = t.lower()
                            if _kl in _tl and len(t) < _best_len:
                                _best = t
                                _best_len = len(t)
                            elif _best is None:
                                for i in range(len(_kl)):
                                    _suf = _kl[i:]
                                    if len(_suf) >= 4 and _suf in _tl and len(t) < _best_len:
                                        _best = t
                                        _best_len = len(t)
                                        break
                        if _best:
                            _name = _best
                    # Fallback: positional match against item names.
                    if not _name and _buy_idx < len(_item_names):
                        _name = _item_names[_buy_idx]
                    _buy_idx += 1
                    if _name:
                        # Price source: inline ("Buy: N") if present,
                        # otherwise computed coin-delta for bare "Buy".
                        if ":" in lbl:
                            _price = lbl.split(":", 1)[1].strip()
                        elif _bare_price is not None:
                            _price = str(_bare_price)
                        else:
                            _price = "?"
                        b["original_label"] = lbl
                        if _is_null:
                            b["label"] = "Buy {}: {} (too expensive)".format(
                                _name, _price)
                        else:
                            b["label"] = "Buy {}: {}".format(_name, _price)
                cleaned.append(b)
            scr["buttons"] = cleaned
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_shop_transform, priority=9
    )

    # -- Roadwarden screen transform: character sheet --

    # Known skill labels (as they appear in scraped texts).
    _SKILL_LABELS = [
        "Combat\nexperience", "Spared\nanimals", "Religion",
        "Faith", "Lies", "Sewing\nexperience", "Gambling\nexperience",
    ]
    # Stat bar button prefixes (in order of appearance).
    _STAT_BAR_PREFIXES = [
        "Vitality:", "Nourishment:", "Armor:", "Appearance:",
        "Cleanliness:",
    ]
    # Modifier texts map to stat bars by keyword.
    _MODIFIER_KEYWORDS = {
        "vitality": "Vitality:",
        "clothes need no": "Armor:",
        "stained with blood": "Appearance:",
        "regular outfit": "Cleanliness:",
    }

    def _vnf_roadwarden_character_transform(per_screen):
        """Restructure the character sheet into readable output.

        The menu screen dumps stat bars as NullAction buttons, skill
        labels as bare texts, and class info / backstory / modifiers
        all mixed together.  This transform pairs them into structured
        lines.  Detected by "Character Sheet" text in the menu screen.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "menu":
                continue
            if "Character Sheet" not in scr.get("texts", []):
                continue
            texts = scr.get("texts", [])
            buttons = scr.get("buttons", [])

            # -- Classify texts --
            # Order on screen: name, backstory, abilities, modifiers,
            # skill labels, "Character Sheet" title, random quote.
            # We only keep recognized patterns; the random quote of
            # the day (from an overlay) is dropped.
            name = ""
            backstory = []
            abilities = []
            modifiers = []  # "+0 - Regular vitality." etc.
            skill_labels = []
            _seen_ability = False
            for t in texts:
                if t in _SKILL_LABELS:
                    skill_labels.append(t.replace("\n", " "))
                elif t == "Character Sheet":
                    continue
                elif not name:
                    name = t
                elif t.lstrip("+-").startswith("0 - ") or t.lstrip("+-").startswith("1 - ") or t.lstrip("+-").startswith("2 - "):
                    modifiers.append(t)
                elif " - " in t and any(
                    w in t.lower() for w in (
                        "vitality", "training", "force",
                        "magic", "scholar", "advantage",
                        "spells", "overcome",
                    )
                ):
                    abilities.append(t)
                    _seen_ability = True
                elif not _seen_ability and t.strip():
                    # Backstory: only texts before the first ability.
                    backstory.append(t)
                # else: drop (random quote overlay, etc.)

            # -- Classify buttons --
            stat_bars = []  # NullAction stat bar buttons
            skill_values = []  # NullAction skill value buttons
            kept_buttons = []  # real menu buttons
            _in_skills = False
            for b in buttons:
                lbl = b.get("label", "")
                is_null = b.get("actions", []) == ["NullAction"]
                if is_null:
                    if any(lbl.startswith(p) or (
                        "+" in lbl and p.rstrip(":") in lbl
                    ) for p in _STAT_BAR_PREFIXES):
                        stat_bars.append(lbl)
                        continue
                    # After stat bars, remaining NullAction buttons
                    # are skill values.
                    skill_values.append(lbl)
                    continue
                kept_buttons.append(b)

            # -- Pair stat bars with modifiers --
            stat_lines = []
            used_mods = set()
            for bar in stat_bars:
                matched = []
                for mi, m in enumerate(modifiers):
                    if mi in used_mods:
                        continue
                    ml = m.lower()
                    for kw, prefix in _MODIFIER_KEYWORDS.items():
                        if kw in ml and bar.startswith(prefix):
                            matched.append(m)
                            used_mods.add(mi)
                            break
                    # Also match +N prefix for Cleanliness
                    if mi not in used_mods and "Cleanliness" in bar:
                        if m.startswith("+") or m.startswith("-"):
                            for kw2 in ("outfit", "regular outfit"):
                                if kw2 in ml:
                                    matched.append(m)
                                    used_mods.add(mi)
                                    break
                if matched:
                    stat_lines.append("{} ({})".format(
                        bar, ", ".join(matched)))
                else:
                    stat_lines.append(bar)
            # Append unused modifiers.
            for mi, m in enumerate(modifiers):
                if mi not in used_mods:
                    stat_lines.append(m)

            # -- Pair skill labels with values --
            skill_lines = []
            for si, sl in enumerate(skill_labels):
                if si < len(skill_values):
                    skill_lines.append("{}: {}".format(sl, skill_values[si]))
                else:
                    skill_lines.append(sl)

            # -- Build new texts --
            new_texts = []
            if name:
                new_texts.append(name)
            for b in backstory:
                new_texts.append(b)
            for a in abilities:
                new_texts.append(a)
            for s in stat_lines:
                new_texts.append(s)
            for sk in skill_lines:
                new_texts.append(sk)

            scr["texts"] = new_texts
            scr["buttons"] = kept_buttons
            # Rename tag so overlay detection surfaces texts.
            scr["_tag"] = "charactersheet"
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_character_transform, priority=9
    )

    # -- Roadwarden screen transform: inventory screen --

    # Item ID -> readable name lookup.  Keys match button action_strs
    # (value=rations, value=axe02, etc.).
    _VNF_RW_ITEM_NAMES = {
        "rations": "Food Rations",
        "chicken": "Chicken",
        "wildplants": "Wild Plants",
        "spiritrock": "Spirit Rock",
        "generichealingpotion": "Healing Potion",
        "magicfruit": "Magic Fruit",
        "potiondolmen": "Dolmen Potion",
        "smallhealingpotion": "Small Healing Potion",
        "sharpeningpotion": "Sharpening Potion",
        "asteriontablet": "Asterion's Wax Tablet",
        "asterionspear": "Asterion's Spear",
        "axe01": "Axe",
        "axe02": "Axe (2nd)",
        "axe03": "Axe (3rd)",
        "crossbow": "Crossbow",
        "crossbowquarrels": "Crossbow Quarrels",
        "mountainroadspear": "Mountain Road Spear",
        "trollurine": "Troll Urine",
        "blindingpowder": "Blinding Powder",
        "goblinspear": "Goblin Spear",
        "golemglove": "Golem Glove",
        "gambeson01": "Gambeson",
        "gambeson02": "Gambeson (2nd)",
        "shield": "Shield",
        "boxfromdolmen": "Box from Dolmen",
        "oceannecklace": "Ocean Necklace",
        "bronzerod": "Bronze Rod",
        "asterionkey": "Asterion's Key",
        "oldtunnelkey": "Old Tunnel Key",
        "trapdoorkeydolmen": "Trapdoor Key",
        "watchtowerkey": "Watchtower Key",
        "piershedkey": "Pier's Shed Key",
        "bonehook": "Bone Hook",
        "dragonhorn": "Dragon Horn",
        "lantern": "Lantern",
        "magicchisel": "Magic Chisel",
        "travelequipment": "Travel Equipment",
        "witheringdust": "Withering Dust",
        "machete": "Machete",
        "letterwhitemarshes": "Letter from White Marshes",
        "casket": "Casket",
        "arrow": "Arrow",
        "snakebait": "Snake Bait",
        "thaisletter": "Thais's Letter",
        "teethset": "Teeth Set",
        "thyrsusgift": "Thyrsus's Gift",
        "magicpens": "Magic Pens",
        "magicalsapling": "Magical Sapling",
        "cidercask": "Cider Cask",
        "furlesswolftrophy": "Furless Wolf Trophy",
        "griffonegg": "Griffon Egg",
        "asterionbow": "Asterion's Bow",
        "brokenknife": "Broken Knife",
        "boartusks": "Boar Tusks",
        "bonering": "Bone Ring",
        "spidersilk": "Spider Silk",
        "wingedhourglass": "Winged Hourglass",
        "ghoulblood": "Ghoulish Blood",
        "stingointment": "Sting Ointment",
        "beholderroot": "Beholder Root",
        "cavemushroom": "Cave Mushroom",
        "antlers": "Antlers",
        "asterionwine": "Asterion's Wine",
        "elkfur": "Elk Fur",
        "harepelt": "Hare Pelt",
        "sealskin": "Seal Skin",
        "ironscraps": "Iron Scraps",
        "ironingot": "Iron Ingot",
        "linen": "Linen",
        "spices": "Spices",
        "stoat": "Stoat",
        "peltnorthberryclaw": "Peltnorth Berry Claw",
        "peltnorthberrytools": "Peltnorth Berry Tools",
        "peltnorthberrytools02": "Peltnorth Berry Tools",
        "dragonlingpaw": "Dragonling Paw",
        "dragonlingclaws": "Dragonling Claws",
        "rope": "Rope",
        "horse01": "Horse",
        "coins": "Coins",
        "dragonbones": "Dragon Bones",
        "travelset": "Travel Set",
        "fishtrap": "Fish Trap",
        "lostmanblanket": "Blanket",
        "scholaringredients": "Scholar Ingredients",
        "writinginstruments": "Writing Instruments",
        "keysidle": "Keys",
        "empresscarp": "Empress Carp",
        "bugrepellent": "Bug Repellent",
        "goblinrepellent": "Goblin Repellent",
    }

    # Categories the game uses on the inventory screen.
    _VNF_RW_INV_CATEGORIES = {
        "Supplies", "Merchandise", "Equipment", "Weapons",
    }

    # Item ID -> category mapping for inventory grouping.
    _VNF_RW_ITEM_CATEGORY = {
        # Supplies (food, potions, spirit items)
        "rations": "Supplies", "chicken": "Supplies",
        "wildplants": "Supplies", "spiritrock": "Supplies",
        "generichealingpotion": "Supplies", "magicfruit": "Supplies",
        "potiondolmen": "Supplies", "smallhealingpotion": "Supplies",
        "sharpeningpotion": "Supplies",
        # Merchandise (trade goods, trophies, materials)
        "oceannecklace": "Merchandise", "cidercask": "Merchandise",
        "snakebait": "Merchandise", "furlesswolftrophy": "Merchandise",
        "griffonegg": "Merchandise", "asterionbow": "Merchandise",
        "boartusks": "Merchandise", "bonering": "Merchandise",
        "spidersilk": "Merchandise", "wingedhourglass": "Merchandise",
        "ghoulblood": "Merchandise", "magicpens": "Merchandise",
        "antlers": "Merchandise", "asterionwine": "Merchandise",
        "elkfur": "Merchandise", "harepelt": "Merchandise",
        "sealskin": "Merchandise", "ironscraps": "Merchandise",
        "ironingot": "Merchandise", "linen": "Merchandise",
        "spices": "Merchandise", "stoat": "Merchandise",
        "peltnorthberryclaw": "Merchandise",
        "goblinspear": "Merchandise",
        "dragonlingclaws": "Merchandise", "coins": "Merchandise",
        "empresscarp": "Merchandise",
        "bugrepellent": "Supplies",
        # Equipment (armor, tools, keys, travel gear)
        "gambeson01": "Equipment", "gambeson02": "Equipment",
        "shield": "Equipment", "golemglove": "Equipment",
        "asterionkey": "Equipment", "oldtunnelkey": "Equipment",
        "trapdoorkeydolmen": "Equipment", "watchtowerkey": "Equipment",
        "piershedkey": "Equipment", "bonehook": "Equipment",
        "dragonhorn": "Equipment", "lantern": "Equipment",
        "magicchisel": "Equipment", "travelequipment": "Equipment",
        "witheringdust": "Equipment", "rope": "Equipment",
        "horse01": "Equipment", "travelset": "Equipment",
        "fishtrap": "Equipment", "keysidle": "Equipment",
        "lostmanblanket": "Equipment",
        "scholaringredients": "Equipment",
        "writinginstruments": "Equipment",
        # Weapons
        "asterionspear": "Weapons", "axe01": "Weapons",
        "axe02": "Weapons", "axe03": "Weapons",
        "crossbow": "Weapons", "crossbowquarrels": "Weapons",
        "mountainroadspear": "Weapons", "blindingpowder": "Weapons",
        "machete": "Weapons",
        # Miscellaneous (quest items, letters, special)
        "asteriontablet": "Miscellaneous",
        "boxfromdolmen": "Miscellaneous", "bronzerod": "Miscellaneous",
        "casket": "Miscellaneous", "arrow": "Miscellaneous",
        "brokenknife": "Miscellaneous",
        "thaisletter": "Miscellaneous", "teethset": "Miscellaneous",
        "thyrsusgift": "Miscellaneous", "magicalsapling": "Miscellaneous",
        "peltnorthberrytools": "Miscellaneous",
        "peltnorthberrytools02": "Miscellaneous",
        "dragonlingpaw": "Miscellaneous", "trollurine": "Miscellaneous",
        "goblinrepellent": "Miscellaneous",
        "stingointment": "Miscellaneous", "beholderroot": "Miscellaneous",
        "cavemushroom": "Miscellaneous",
    }
    # Conditional: letterwhitemarshes is Miscellaneous when unread,
    # Merchandise when read.  Handled in the transform.

    def _vnf_roadwarden_inventory_transform(per_screen):
        """Restructure inventory screen into readable output.

        The inventory menu screen dumps category labels, numeric counts,
        and item tooltip text as flat texts, and shows item icons as
        buttons with [image_tag] labels.  This transform:
        - Replaces [image_tag] button labels with readable item names
        - Groups flat texts into a selected-item tooltip + category summary
        - Drops NullAction icon buttons (pure visuals)
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "menu":
                continue
            buttons = scr.get("buttons", [])
            # Detect inventory screen: at least one button with
            # item_detailedmenu in action_strs.
            _is_inv = False
            for b in buttons:
                for a in b.get("action_strs", []):
                    if "item_detailedmenu" in a:
                        _is_inv = True
                        break
                if _is_inv:
                    break
            if not _is_inv:
                continue
            # Rename tag so overlay detection kicks in (same pattern
            # as journal transform).  "inventory" is registered via
            # _vnf_register_overlay_screen.
            scr["_tag"] = "inventory"

            # During an active inventory scan, suppress noisy intermediate
            # screen states and show a progress indicator instead.
            if _vnf_inv_scan_active[0]:
                done = len(_vnf_inv_scan_results[0])
                scr["texts"] = [
                    "Inventory scan in progress ({}/{})...".format(
                        done, _vnf_inv_scan_total[0])]
                scr["buttons"] = []
                continue

            texts = scr.get("texts", [])

            # -- Classify texts --
            # Texts appear in this order: [selected item tooltip],
            # category labels interleaved with counts, "Inventory".
            # Digit-only texts before the first category are icon
            # quantity badges (not counts); skip them.
            tooltip_parts = []
            categories = []  # list of (name, count_str)
            _cur_cat = None
            _seen_cat = False
            for t in texts:
                _ts = t.strip()
                if _ts == "Inventory":
                    continue
                if _ts in _VNF_RW_INV_CATEGORIES:
                    # Flush previous category if it had no count.
                    if _cur_cat is not None:
                        categories.append((_cur_cat, ""))
                    _cur_cat = _ts
                    _seen_cat = True
                elif _cur_cat is not None and _ts.isdigit():
                    categories.append((_cur_cat, _ts))
                    _cur_cat = None
                elif _seen_cat:
                    pass  # stray text after categories
                elif _ts.isdigit():
                    pass  # quantity badge on icon — skip
                else:
                    tooltip_parts.append(_ts)
            # Flush trailing category.
            if _cur_cat is not None:
                categories.append((_cur_cat, ""))

            # -- Rebuild texts --
            new_texts = ["Inventory"]
            if categories:
                cat_parts = []
                for cname, ccount in categories:
                    if ccount:
                        cat_parts.append("{} ({})".format(cname, ccount))
                    else:
                        cat_parts.append(cname)
                new_texts.append("Categories: {}".format(
                    ", ".join(cat_parts)))
            if tooltip_parts:
                new_texts.append("Selected: {}".format(
                    " - ".join(tooltip_parts)))
            scr["texts"] = new_texts

            # -- Relabel item buttons --
            cleaned = []
            _seen_item_action_labels = set()
            for b in buttons:
                lbl = b.get("label", "")
                _action_strs = b.get("action_strs", [])
                _is_detail_action = False
                for a in _action_strs:
                    if ("inventoryinteraction" in a or
                            "inventoryscreenmode value=list" in a):
                        _is_detail_action = True
                        break
                if _is_detail_action:
                    _detail_key = lbl.strip().lower()
                    if _detail_key in _seen_item_action_labels:
                        continue
                    _seen_item_action_labels.add(_detail_key)
                    b["_category"] = "item_action"
                    cleaned.append(b)
                    continue
                _is_use_action = False
                for a in _action_strs:
                    if "SetField field=" not in a:
                        continue
                    if ("field=inventoryscreenmode " in a or
                            "field=item_detailedmenu " in a or
                            "field=tutorial_" in a):
                        continue
                    _is_use_action = True
                    break
                if _is_use_action:
                    _detail_key = lbl.strip().lower()
                    if _detail_key in _seen_item_action_labels:
                        continue
                    _seen_item_action_labels.add(_detail_key)
                    b["_category"] = "item_action"
                    cleaned.append(b)
                    continue
                # Tutorial tooltip is a dismissable button — show as text.
                _is_tutorial = False
                for a in _action_strs:
                    if "field=tutorial_" in a:
                        _is_tutorial = True
                        break
                if _is_tutorial:
                    new_texts.append(lbl)
                    continue
                # Extract item id from action_strs.
                _item_id = ""
                for a in _action_strs:
                    if "item_detailedmenu" in a:
                        # "SetField field=item_detailedmenu value=rations"
                        parts = a.split("value=", 1)
                        if len(parts) > 1:
                            _item_id = parts[1].strip()
                        break
                if _item_id:
                    _readable = _VNF_RW_ITEM_NAMES.get(
                        _item_id, _item_id)
                    b["original_label"] = lbl
                    b["label"] = _readable
                    # Assign category for grouping.
                    _cat = _VNF_RW_ITEM_CATEGORY.get(_item_id)
                    # Conditional: letter is Miscellaneous when
                    # unread (==1), Merchandise when read (==2).
                    if _item_id == "letterwhitemarshes":
                        _lv = getattr(renpy.store,
                            "item_letterwhitemarshes", 0)
                        _cat = ("Merchandise" if _lv >= 2
                                else "Miscellaneous")
                    if _cat:
                        b["_category"] = _cat
                    cleaned.append(b)
                elif lbl.startswith("[") and lbl.endswith("]"):
                    # Unlabelled image button — drop it.
                    continue
                else:
                    _raw_id = lbl.lower().strip()
                    if _raw_id in _VNF_RW_ITEM_NAMES:
                        b["original_label"] = lbl
                        b["label"] = _VNF_RW_ITEM_NAMES[_raw_id]
                        _cat = _VNF_RW_ITEM_CATEGORY.get(_raw_id)
                        if _cat:
                            b["_category"] = _cat
                        cleaned.append(b)
                        continue
                    # Sidebar nav buttons (Return, Save, Load, etc.)
                    # have NullAction — they duplicate quick_menu and
                    # cause ambiguity (e.g. sidebar Return vs inner
                    # panel Return).  Drop them.
                    _all_null = all(
                        a == "NullAction" for a in b.get("action_strs", []))
                    if _all_null and b.get("action_strs"):
                        continue
                    cleaned.append(b)
            scr["buttons"] = cleaned
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_inventory_transform, priority=9
    )

    # -- Roadwarden journal transform --
    #
    # The journal opens via ShowMenu, so the scraper sees it as the
    # "menu" screen wrapper.  Rename the tag to "journal" so the
    # overlay mechanism surfaces its texts to the agent.

    _VNF_RW_JOURNAL_TABS = {
        "Quests", "Users", "Groups & Places",
        "Bestiary", "Glossary", "Notes",
    }

    _vnf_register_overlay_screen("journal")

    def _vnf_roadwarden_journal_transform(per_screen):
        for scr in per_screen:
            if scr.get("_tag") != "menu":
                continue
            buttons = scr.get("buttons", [])
            # Detect journal: at least 4 of the 6 tab buttons present.
            _tab_count = 0
            for b in buttons:
                if b.get("label", "") in _VNF_RW_JOURNAL_TABS:
                    _tab_count += 1
            if _tab_count < 4:
                continue
            # Rename tag so overlay detection kicks in.
            scr["_tag"] = "journal"
            # Categorize tab buttons and sidebar buttons.
            cleaned = []
            for b in buttons:
                lbl = b.get("label", "")
                if lbl in _VNF_RW_JOURNAL_TABS:
                    b["_category"] = "journal_tab"
                    cleaned.append(b)
                elif lbl in ("Return", "Save", "Load", "Journal",
                             "Inventory", "Character sheet", "Archive",
                             "Settings", "Main Menu", "Quit"):
                    b["_category"] = "navigation"
                    cleaned.append(b)
                elif lbl == "new note":
                    b["_category"] = "journal_action"
                    cleaned.append(b)
                else:
                    # Entry buttons (quest names, NPC names, etc.)
                    b["_category"] = "journal_entry"
                    cleaned.append(b)
            scr["buttons"] = cleaned
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_journal_transform, priority=8
    )

    _vnf_register_button_category("journal_tab", "TABS")
    _vnf_register_button_category("journal_entry", "ENTRIES")
    _vnf_register_button_category("journal_action", "JOURNAL")

    # -- Roadwarden archive transform --
    #
    # The history/archive screen renders its scrollback through a viewport that
    # Ren'Py exposes as a large disabled button with no action. Keep the same
    # text via screen texts, but suppress that fake button so agents only see
    # the useful Return/sidebar controls.

    _VNF_RW_ARCHIVE_NAV_LABELS = {
        "Return", "Save", "Load", "Journal", "Inventory",
        "Character sheet", "Archive", "Settings", "Main Menu", "Quit",
    }

    def _vnf_roadwarden_is_archive_screen(scr):
        _tag = scr.get("_tag")
        if _tag == "history":
            return True
        if _tag not in ("menu", "_focus_list"):
            return False
        buttons = scr.get("buttons", [])
        labels = set(str(b.get("label", "")).strip() for b in buttons)
        if not _VNF_RW_ARCHIVE_NAV_LABELS.issubset(labels):
            return False
        # Do not reclassify the already-recognized journal wrapper: it
        # shares the same sidebar but also has journal tabs/entries.
        if labels.intersection(_VNF_RW_JOURNAL_TABS):
            return False
        has_archive_title = any(
            str(t).strip() == "Archive" for t in scr.get("texts", [])
        )
        if has_archive_title:
            return True
        # Fallback for focus-list-only scrapes: Roadwarden's archive
        # viewport can appear as one huge no-op button.
        if _tag != "_focus_list":
            return False
        has_history_viewport = any(
            len(str(b.get("label", "")).strip()) > 500
            and not b.get("action_strs", [])
            and b.get("actions", []) == ["none"]
            for b in buttons
        )
        return has_history_viewport

    def _vnf_roadwarden_archive_transform(per_screen):
        for scr in per_screen:
            if not _vnf_roadwarden_is_archive_screen(scr):
                continue
            scr["_tag"] = "history"
            cleaned = []
            for b in scr.get("buttons", []):
                lbl = str(b.get("label", "")).strip()
                if lbl in _VNF_RW_ARCHIVE_NAV_LABELS:
                    b["_category"] = "navigation"
                    cleaned.append(b)
                    continue
                _action_names = b.get("action_names", b.get("actions", []))
                _action_strs = b.get("action_strs", [])
                _no_action = not _action_strs and all(
                    a in ("none", "None", "NullAction")
                    for a in _action_names
                )
                if _no_action or b.get("is_disabled") or b.get("disabled"):
                    continue
                cleaned.append(b)
            scr["buttons"] = cleaned
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_archive_transform, priority=8
    )

    # -- Roadwarden inventory scan command --
    #
    # Multi-cycle command that clicks through every inventory item,
    # captures detail texts, and returns a consolidated result.

    _vnf_inv_scan_active = [False]
    _vnf_inv_scan_phase = ["idle"]
    _vnf_inv_scan_queue = [[]]
    _vnf_inv_scan_current = [""]
    _vnf_inv_scan_results = [[]]
    _vnf_inv_scan_deadline = [0.0]
    _vnf_inv_scan_settle = [0.0]
    _vnf_inv_scan_total = [0]
    _VNF_INV_SCAN_TIMEOUT = 5.0
    _VNF_INV_SCAN_SETTLE_DELAY = 0.2

    def _vnf_inv_scan_reset():
        _vnf_inv_scan_active[0] = False
        _vnf_inv_scan_phase[0] = "idle"
        _vnf_inv_scan_queue[0] = []
        _vnf_inv_scan_current[0] = ""
        _vnf_inv_scan_results[0] = []
        _vnf_inv_scan_deadline[0] = 0.0
        _vnf_inv_scan_settle[0] = 0.0
        _vnf_inv_scan_total[0] = 0

    def _vnf_inv_scan_abort(reason):
        partial = list(_vnf_inv_scan_results[0])
        try:
            renpy.store.inventoryscreenmode = "list"
            renpy.exports.restart_interaction()
        except Exception:
            pass
        _vnf_inv_scan_reset()
        _vnf_client.push_event(dict(
            type="command_result", command="inventory_scan",
            success=False, status="aborted", error=reason,
            partial_results=partial))

    def _vnf_inv_scan_finish():
        results = list(_vnf_inv_scan_results[0])
        # Restore list view while still "active" so the transform
        # suppresses any intermediate detail-view screen scrape.
        try:
            renpy.store.inventoryscreenmode = "list"
            renpy.exports.restart_interaction()
        except Exception:
            pass
        _vnf_inv_scan_reset()
        _vnf_client.push_event(dict(
            type="command_result", command="inventory_scan",
            success=True, status="complete",
            item_count=len(results), items=results))

    def _vnf_inv_scan_capture_texts():
        """Walk the menu screen and capture detail view texts."""
        texts = []
        try:
            for sname, scr in _vnf_get_showing_screens():
                if getattr(scr, "tag", None) != "menu":
                    continue
                data = {"_tag": "menu", "texts": [], "choices": [],
                        "value_map": {}, "buttons": []}
                _vnf_walk_screen(scr, data)
                for t in data.get("texts", []):
                    ts = t.strip()
                    if not ts:
                        continue
                    if ts == "Inventory":
                        continue
                    if ts in _VNF_RW_INV_CATEGORIES:
                        continue
                    if ts.isdigit() and len(ts) <= 3:
                        continue
                    texts.append(ts)
        except _CONTROL_EXCEPTIONS:
            raise
        except Exception:
            pass
        return texts

    def _vnf_periodic_inventory_scan():
        if not _vnf_inv_scan_active[0]:
            return
        now = _vnf_time_mod.time()
        phase = _vnf_inv_scan_phase[0]

        # Timeout guard.
        if now > _vnf_inv_scan_deadline[0]:
            _vnf_inv_scan_abort(
                "Timeout in phase: {}".format(phase))
            return

        if phase == "click_item":
            if not _vnf_inv_scan_queue[0]:
                _vnf_inv_scan_phase[0] = "done"
                return
            item_id = _vnf_inv_scan_queue[0].pop(0)
            _vnf_inv_scan_current[0] = item_id
            try:
                renpy.store.inventoryscreenmode = "details"
                renpy.store.item_detailedmenu = item_id
                renpy.exports.restart_interaction()
            except _CONTROL_EXCEPTIONS:
                raise
            except Exception as e:
                _vnf_inv_scan_abort(
                    "Failed to select item: {}".format(e))
                return
            _vnf_inv_scan_phase[0] = "wait_detail"
            _vnf_inv_scan_deadline[0] = now + _VNF_INV_SCAN_TIMEOUT
            _vnf_inv_scan_settle[0] = 0.0

        elif phase == "wait_detail":
            mode = getattr(renpy.store, "inventoryscreenmode", None)
            if mode == "details":
                if _vnf_inv_scan_settle[0] == 0.0:
                    _vnf_inv_scan_settle[0] = (
                        now + _VNF_INV_SCAN_SETTLE_DELAY)
                elif now >= _vnf_inv_scan_settle[0]:
                    _vnf_inv_scan_phase[0] = "capture"

        elif phase == "capture":
            texts = _vnf_inv_scan_capture_texts()
            item_id = _vnf_inv_scan_current[0]
            _vnf_inv_scan_results[0].append({
                "id": item_id,
                "name": _VNF_RW_ITEM_NAMES.get(item_id, item_id),
                "texts": texts,
            })
            # Return to list view before next item or finishing.
            _vnf_inv_scan_phase[0] = "return_to_list"
            _vnf_inv_scan_deadline[0] = (
                now + _VNF_INV_SCAN_TIMEOUT)
            _vnf_inv_scan_settle[0] = 0.0
            try:
                renpy.store.inventoryscreenmode = "list"
                renpy.exports.restart_interaction()
            except _CONTROL_EXCEPTIONS:
                raise
            except Exception:
                pass

        elif phase == "return_to_list":
            mode = getattr(renpy.store, "inventoryscreenmode", None)
            if mode != "details":
                if _vnf_inv_scan_settle[0] == 0.0:
                    _vnf_inv_scan_settle[0] = (
                        now + _VNF_INV_SCAN_SETTLE_DELAY)
                elif now >= _vnf_inv_scan_settle[0]:
                    if _vnf_inv_scan_queue[0]:
                        _vnf_inv_scan_phase[0] = "click_item"
                        _vnf_inv_scan_deadline[0] = (
                            now + _VNF_INV_SCAN_TIMEOUT)
                    else:
                        _vnf_inv_scan_finish()

    _register_periodic(_vnf_periodic_inventory_scan, 0.15)

    def _vnf_rw_cmd_inventory_scan(cmd_name, cmd_args):
        _action = cmd_args.get("action", "start") if cmd_args else "start"
        if _action == "cancel":
            if _vnf_inv_scan_active[0]:
                _vnf_inv_scan_abort("Cancelled by user")
            else:
                _vnf_client.push_event(dict(
                    type="command_result", command="inventory_scan",
                    success=True, status="no_scan_active"))
            return

        if _vnf_inv_scan_active[0]:
            _vnf_client.push_event(dict(
                type="command_result", command="inventory_scan",
                success=False,
                error="Scan already in progress"))
            return

        # Collect item IDs from visible inventory buttons.
        item_ids = []
        try:
            for sname, scr in _vnf_get_showing_screens():
                if getattr(scr, "tag", None) != "menu":
                    continue
                data = {"_tag": "menu", "texts": [], "choices": [],
                        "value_map": {}, "buttons": []}
                _vnf_walk_screen(scr, data)
                for btn in data.get("buttons", []):
                    for a_str in btn.get("action_strs", []):
                        if "item_detailedmenu" in a_str:
                            parts = a_str.split("value=", 1)
                            if len(parts) > 1:
                                _iid = parts[1].strip()
                                if _iid and _iid not in item_ids:
                                    item_ids.append(_iid)
        except _CONTROL_EXCEPTIONS:
            raise
        except Exception:
            pass

        if not item_ids:
            _vnf_client.push_event(dict(
                type="command_result", command="inventory_scan",
                success=False,
                error="No inventory items found. "
                      "Is the inventory screen open?"))
            return

        _vnf_inv_scan_queue[0] = list(item_ids)
        _vnf_inv_scan_results[0] = []
        _vnf_inv_scan_current[0] = ""
        _vnf_inv_scan_total[0] = len(item_ids)
        _vnf_inv_scan_phase[0] = "click_item"
        _vnf_inv_scan_active[0] = True
        _vnf_inv_scan_deadline[0] = (
            _vnf_time_mod.time() + _VNF_INV_SCAN_TIMEOUT)

        _vnf_client.push_event(dict(
            type="command_result", command="inventory_scan",
            success=True, status="started",
            item_count=len(item_ids),
            items=[_VNF_RW_ITEM_NAMES.get(i, i)
                   for i in item_ids]))

    _vnf_add_command_handler(
        "inventory_scan", _vnf_rw_cmd_inventory_scan,
        causal_boundary=True)

    # -- Roadwarden screen transform: rest screen --

    def _vnf_roadwarden_rest_transform(per_screen):
        """Restructure rest screen into room options with associated buttons.

        Uses tree-based _section grouping (section_depth=6) to split rooms
        instead of pattern-matching text content.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "restscreen":
                continue

            # Extract sleep effects from statuspoints/ image filenames.
            # BFS (pop from front) preserves visual left-to-right order
            # so the half-split below attributes icons to the correct room.
            _effects = []
            try:
                _rs = renpy.get_screen("restscreen")
                if _rs and _rs.child:
                    _seen = set()
                    _stack = [_rs.child]
                    while _stack:
                        _d = _stack.pop(0)
                        _cn = type(_d).__name__
                        if _cn in ("Image", "ImageReference"):
                            _fn = getattr(_d, "filename", None)
                            if _fn and "statuspoints/" in _fn and _fn not in _seen:
                                _seen.add(_fn)
                                _base = _fn.rsplit("/", 1)[-1].split(".")[0]
                                if _base.startswith("plus"):
                                    _sign = "+"
                                    _rest = _base[4:]
                                elif _base.startswith("minus"):
                                    _sign = "-"
                                    _rest = _base[5:]
                                else:
                                    continue
                                if _rest.startswith("questionmark"):
                                    _num = "?"
                                    _rest = _rest[len("questionmark"):]
                                else:
                                    _num = ""
                                    while _rest and _rest[0].isdigit():
                                        _num += _rest[0]
                                        _rest = _rest[1:]
                                if _num and _rest:
                                    _effects.append(
                                        "{}{} {}".format(_sign, _num, _rest))
                        for _c in getattr(_d, "children", []):
                            if _c is not None:
                                _stack.append(_c)
                        if hasattr(_d, "child") and _d.child is not None:
                            _stack.append(_d.child)
            except Exception:
                pass

            # Group texts and buttons by tree section.
            sections = _vnf_group_by_section(scr)

            # Identify room sections (those with descriptive text, not just
            # numeric indicators or side-panel leftovers).
            rooms = []  # list of (section_index, name, description)
            for sec_i in sorted(sections.keys()):
                sec = sections[sec_i]
                # Filter out numeric-only texts (resource indicators).
                descs = [t for t in sec["texts"]
                         if not t.strip().isdigit()]
                if len(descs) >= 2:
                    # First text = room header, second = description.
                    _name = descs[0].replace("\n", " ")
                    _desc = descs[1]
                    rooms.append((sec_i, _name, _desc))

            # Split effects between rooms (first half = room 1).
            _n_rooms = len(rooms)
            _mid = len(_effects) // 2 if _n_rooms >= 2 else len(_effects)
            _room_effects = [
                _effects[:_mid],
                _effects[_mid:],
            ] if _n_rooms >= 2 else [_effects]

            # Collect NullAction text labels (e.g. "You're hungry!").
            _warnings = []
            for btn in scr.get("buttons", []):
                if (btn.get("actions", []) == ["NullAction"]
                        and not btn.get("label", "").startswith("Rent:")):
                    _lbl = btn.get("label", "")
                    if _lbl and not _lbl.startswith("["):
                        _warnings.append(_lbl)

            # Build room-to-category mapping from section indices.
            _room_secs = set()
            for _ri, (sec_i, _, _) in enumerate(rooms):
                _room_secs.add(sec_i)

            # Clean up buttons and categorize.
            cleaned = []
            for btn in scr.get("buttons", []):
                _acts = btn.get("actions", [])
                if _acts == ["NullAction"]:
                    if btn.get("label", "").startswith("Rent:"):
                        btn["is_disabled"] = True
                        btn["_category"] = "rest_paid"
                        cleaned.append(btn)
                    continue  # Already extracted warnings above.
                if _acts == ["Hide"]:
                    btn["original_label"] = btn.get("label", "")
                    btn["label"] = "Close"
                    btn["_category"] = "rest_util"
                    cleaned.append(btn)
                    continue
                _a_strs = btn.get("action_strs", [])
                _is_eat = any("pc_food" in a for a in _a_strs)
                lbl = btn.get("label", "")
                if lbl == "Travel":
                    btn["_category"] = "rest_util"
                    cleaned.append(btn)
                    continue
                if _is_eat:
                    btn["original_label"] = btn.get("label", "")
                    btn["label"] = "Eat rations"
                    btn["_category"] = "rest_util"
                    cleaned.append(btn)
                    continue
                if lbl.startswith("Rent:"):
                    _price = lbl.split(":", 1)[1].strip()
                    if _price.isdigit():
                        btn["original_label"] = lbl
                        btn["label"] = "Rent: {} dragon bones".format(
                            _price)
                    btn["_category"] = "rest_paid"
                elif btn.get("_section", -1) in _room_secs:
                    btn["_category"] = "rest_free"
                else:
                    btn["_category"] = "rest_free"
                cleaned.append(btn)
            scr["buttons"] = cleaned

            # Build structured texts per room.
            new_texts = []
            for _ri, (sec_i, _name, _desc) in enumerate(rooms):
                _parts = [_desc]
                if _ri < len(_room_effects) and _room_effects[_ri]:
                    _parts.append(
                        "Effects: {}".format(
                            ", ".join(_room_effects[_ri])))
                new_texts.append("{}: {}".format(
                    _name, " ".join(_parts)))
            if _warnings:
                new_texts.extend(_warnings)
            _coins = getattr(renpy.store, "coins", 0)
            # Rations are stored as item_rations; the `food` store var
            # (if it exists) is the fullness stat, not the count.
            _rations = getattr(renpy.store, "item_rations", 0)
            new_texts.append(
                "Your resources: {} dragon bones, {} rations".format(
                    _coins, _rations))
            scr["texts"] = new_texts
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_rest_transform, priority=9
    )

    # -- Roadwarden screen transform: mundanejob (work) screen --

    def _vnf_roadwarden_mundanejob_transform(per_screen):
        """Append statuspoints icon effects to the work screen description.

        The mundanejob overlay shows one job with its description, a Work
        button, and a row of statuspoints icons previewing the outcome
        (e.g. +2 coins, -1 food, -1 appearance).  This transform reads
        those icons and appends them as "Effects: ..." so the agent can
        see the cost/reward before committing.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "mundanejob":
                continue
            # BFS walk to collect statuspoints icons. Try the expected
            # screen name first, then fall back to scanning ALL showing
            # screens on every layer (mundanejob's icons may be rendered
            # by a sibling screen).
            _effects = []
            _seen_files = set()
            _roots = []
            try:
                _ms = renpy.get_screen("mundanejob")
                if _ms and _ms.child:
                    _roots.append(_ms.child)
            except Exception:
                pass
            if not _roots:
                try:
                    for _layer in ("screens", "overlay", "master"):
                        try:
                            _showing = renpy.exports.showing(None)
                        except Exception:
                            _showing = []
                        for _tag in list(_showing or []):
                            try:
                                _s = renpy.get_screen(_tag)
                                if _s and _s.child:
                                    _roots.append(_s.child)
                            except Exception:
                                pass
                except Exception:
                    pass
            _seen = set()
            _stack = list(_roots)
            while _stack:
                _d = _stack.pop(0)
                _id = id(_d)
                if _id in _seen:
                    continue
                _seen.add(_id)
                _cn = type(_d).__name__
                if _cn in ("Image", "ImageReference"):
                    _fn = getattr(_d, "filename", None)
                    if _fn and "statuspoints/" in _fn and _fn not in _seen_files:
                        _seen_files.add(_fn)
                        _base = _fn.rsplit("/", 1)[-1].split(".")[0]
                        if _base.startswith("plus"):
                            _sign = "+"
                            _rest = _base[4:]
                        elif _base.startswith("minus"):
                            _sign = "-"
                            _rest = _base[5:]
                        else:
                            continue
                        # Magnitude: digits OR "questionmark" (uncertain outcome).
                        if _rest.startswith("questionmark"):
                            _num = "?"
                            _rest = _rest[len("questionmark"):]
                        else:
                            _num = ""
                            while _rest and _rest[0].isdigit():
                                _num += _rest[0]
                                _rest = _rest[1:]
                        if _num and _rest:
                            _effects.append(
                                "{}{} {}".format(_sign, _num, _rest))
                for _c in getattr(_d, "children", []):
                    if _c is not None:
                        _stack.append(_c)
                if hasattr(_d, "child") and _d.child is not None:
                    _stack.append(_d.child)

            # Drop numeric-only texts (icon counters like "0") and append
            # the effects line to the longest remaining text (the job desc).
            _texts = [t for t in scr.get("texts", [])
                      if not t.strip().isdigit()]
            if _effects and _texts:
                _texts[-1] = "{} Effects: {}".format(
                    _texts[-1], ", ".join(_effects))

            # Rename the unlabelled Hide button to Close.
            for btn in scr.get("buttons", []):
                if btn.get("label") in ("", "[unlabelled]") and \
                   "Hide" in btn.get("actions", []):
                    btn["original_label"] = btn.get("label", "")
                    btn["label"] = "Close"
            scr["texts"] = _texts
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_mundanejob_transform, priority=9
    )

    # -- Roadwarden screen transform: wait screen --

    def _vnf_roadwarden_wait_transform(per_screen):
        """Clean up waitscreen buttons into a readable time selector.

        The waitscreen overlay shows duration buttons (0:15, 0:30, etc.)
        and time-of-day buttons (Morning, Noon, etc.).  This transform
        removes the close button, splits into two categories, and marks
        unavailable times.
        """
        _duration_pattern = __import__("re").compile(r"^\d+:\d+$")
        for scr in per_screen:
            if scr.get("_tag", "") != "waitscreen":
                continue
            durations = []
            times = []
            for btn in scr.get("buttons", []):
                lbl = btn.get("label", "").strip()
                if not lbl or lbl == "[unlabelled]":
                    continue  # Skip close button.
                acts = btn.get("actions", [])
                if "NullAction" in acts:
                    btn["is_disabled"] = True
                if _duration_pattern.match(lbl):
                    btn["_category"] = "wait_for"
                    durations.append(btn)
                else:
                    btn["_category"] = "wait_until"
                    times.append(btn)
            scr["buttons"] = durations + times
            # Clear texts — the categorized buttons are self-explanatory.
            scr["texts"] = []
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_wait_transform, priority=9
    )

    # -- Roadwarden screen transform: tutorial tooltips --

    def _vnf_roadwarden_tutorial_transform(per_screen):
        """Prefix tutorialtooltips content with 'Tutorial:'.

        Roadwarden's tutorial tooltips appear alongside game screens.
        Without a prefix, their content merges indistinguishably with
        narrative content.  The tooltip may be a plain text or a
        clickable button (dismiss-on-click), so prefix both.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "tutorialtooltips":
                continue
            scr["texts"] = [
                "Tutorial: {}".format(t) for t in scr.get("texts", [])
            ]
            for btn in scr.get("buttons", []):
                lbl = btn.get("label", "")
                if lbl:
                    btn["original_label"] = lbl
                    btn["label"] = "Tutorial: {}".format(lbl)
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_tutorial_transform, priority=9
    )

    # -- Roadwarden screen transform: categorize end credits overlay --
    def _vnf_roadwarden_credits_transform(per_screen):
        """Categorize endcredits screen content as 'credits'.

        The endcredits screen overlays credit names/roles on top of
        the narrative during the ending sequence.  Tagging with
        _text_category keeps them out of the main narrative text
        but preserves them under a separate 'credits' section.
        """
        for scr in per_screen:
            if scr.get("_tag", "") != "endcredits":
                continue
            scr["_text_category"] = "credits"
            scr["buttons"] = []
        return per_screen

    _vnf_add_screen_transform(
        _vnf_roadwarden_credits_transform, priority=9
    )

    # -- Roadwarden action transform: clean up NVL tutorial + class buttons --
    def _vnf_roadwarden_nvl_button_cleanup(actions, context):
        """Re-categorize NVL tutorial dismiss buttons and class action buttons.

        Tutorial dismiss buttons (SetField field=tutorial_*) are rendered
        inside the NVL screen, not the tutorialtooltips screen, so the
        screen transform doesn't see them.  Re-tag them so the client
        categorizes them as info.

        Class action buttons (SetField field=at value=*) like [force] are
        the warrior's (or other classes') special ability modifiers.
        Promote them so they render prominently below the choices.
        """
        for a in actions:
            if a["source"] != "button" or a.get("screen") != "nvl":
                continue
            strs = a.get("action_strs", [])
            # Tutorial dismiss buttons -> info
            if any("field=tutorial_" in s for s in strs):
                a["screen"] = "tutorialtooltips"
                lbl = a.get("label", "")
                if lbl and not lbl.startswith("Tutorial:"):
                    a["label"] = "Tutorial: {}".format(lbl)
                continue
            # Class action buttons (SetField field=at) -> promoted,
            # but NOT attitude buttons (handled by promote_attitudes) or
            # reset buttons like value=0 after a reveal.
            # Read from shared pipeline state written by augmenter.
            _shared = context.get("shared", {})
            _att_vals = _shared.get("attitude_vals", set())
            _class_vals = _shared.get(
                "class_action_vals", _ROADWARDEN_CLASS_ACTIONS)
            for s in strs:
                if "field=at value=" in s:
                    _at_val = s.split("value=", 1)[1].split()[0]
                    if _at_val in _class_vals and _at_val not in _att_vals:
                        a["promoted"] = True
                        a["annotation"] = (
                            "class ability toggle — click to"
                            " reveal/hide class-specific"
                            " choices, then re-read")
                    elif _at_val in _ROADWARDEN_AT_RESET_VALUES:
                        a["hidden"] = True
                    break
        return actions

    _vnf_add_action_transform(
        _vnf_roadwarden_nvl_button_cleanup, priority=25
    )

    # -- Roadwarden vis-check filter: skip when class action toggle present --

    def _vnf_roadwarden_vis_check_filter(pending, rendered, hidden, btns):
        """Skip vis-check filtering when a class action toggle is on screen.

        When a class action toggle ([force], [focus], etc.) is present,
        clicking it changes which choices are visible.  Since the vis
        check is one-shot, it only sees the current toggle state.
        Rather than filtering based on partial information, skip
        filtering entirely so the LLM sees all available choices.
        """
        for _vd, _va, _vl, _vs in btns:
            _va_list = _va if _vnf_is_sequence(_va) else [_va]
            for _va_item in _va_list:
                if _va_item.__class__.__name__ != "SetField":
                    continue
                if getattr(_va_item, "field", None) == "at":
                    return False  # class toggle found, skip filtering
        return True  # no toggle, proceed normally

    vnf_player.vis_check_filter = _vnf_roadwarden_vis_check_filter

    # Re-enabled: tooltip lifecycle works with current screen setup.
    vnf_player.suppress_default_focus = True

    # Enable screen scraping (off by default in shim).
    vnf_player.scrape_screens = True
    vnf_player.scrape_visible_screens = True
    # Include selling/map screens in scrape even during call_screen.
    vnf_player.scrape_extra_screens = ["selling", "map_display"]

    # Roadwarden supports free-form save slot names.
    vnf_player.watchdog_save_slot_fmt = "diagnostic-{n}"

    # Agent UX policy for class ability buttons such as [knowledge].
    # True: merge class-gated choices into the current view with pre-resolve
    # steps. False: leave the visible toggle as the way to reveal choices.
    if not hasattr(vnf_player, "roadwarden_merge_class_toggles"):
        vnf_player.roadwarden_merge_class_toggles = True

    def _vnf_roadwarden_merge_class_toggles_enabled():
        return bool(getattr(
            vnf_player, "roadwarden_merge_class_toggles", True))

    # -- Roadwarden menu augmenter: filter + toggle discovery --

    import re as _vnf_re_mod

    # Known attitude values for Roadwarden.
    _ROADWARDEN_ATTITUDES = {"friendly", "playful", "distanced",
                             "intimidating", "vulnerable"}
    _ROADWARDEN_CLASS_ACTIONS = {"force", "spell", "knowledge"}
    _ROADWARDEN_AT_RESET_VALUES = {"0", "None", "none", "False", "false"}

    def _vnf_roadwarden_choice_filter(ctx):
        """Filter class-locked items and recover attitude/toggle choices.

        Parses ``at == 'value'`` from condition strings to discover all
        possible toggle values (attitudes + class actions).  Removes
        items unreachable for the current class, adds pre_sets for items
        needing a different toggle state.

        Writes to shared pipeline state:
          - ``attitude_vals``: set of attitude toggle values found
          - ``class_action_vals``: set of class action toggle values
        """
        raw_ast_items = ctx["raw_ast_items"]
        choices = ctx["choices"]
        value_map = ctx["value_map"]
        pre_sets = ctx["pre_sets"]
        shared = ctx.get("shared", {})

        # Build ast_index -> condition string map.
        kwargs_by_ast = {}
        for ri in raw_ast_items:
            _ik = ri.get("item_kwargs", {})
            if _ik and "condition" in _ik:
                kwargs_by_ast[ri["ast_index"]] = _ik["condition"]
        # Debug trace of raw items even when kwargs empty.
        _vnf_log("CA RAW n={} items={}".format(
            len(raw_ast_items),
            [(r.get("ast_index"), (r.get("label","") or "")[:40],
              r.get("item_kwargs")) for r in raw_ast_items]))
        if not kwargs_by_ast:
            return None

        # Discover available toggle values:
        # 1) Default (0).
        # 2) Class unlocks (force/spell/knowledge if unlocked).
        # 3) Values parsed from at == 'val' in conditions (attitudes).
        toggles = [0]
        class_action_vals = set()
        for val in _ROADWARDEN_CLASS_ACTIONS:
            try:
                if renpy.python.py_eval("at_unlock_" + val):
                    toggles.append(val)
                    class_action_vals.add(val)
            except Exception:
                pass

        # Parse all at == 'val' from conditions.
        discovered_vals = set()
        for cond_str in kwargs_by_ast.values():
            for m in _vnf_re_mod.finditer(r"at\s*==\s*['\"](\w+)['\"]",
                                          cond_str):
                discovered_vals.add(m.group(1))

        # Attitudes are always available; class actions only if unlocked.
        attitude_vals = discovered_vals & _ROADWARDEN_ATTITUDES
        for v in attitude_vals:
            if v not in toggles:
                toggles.append(v)

        # Write discoveries to shared pipeline state.
        shared["attitude_vals"] = attitude_vals
        shared["class_action_vals"] = class_action_vals

        # Evaluate each condition with each toggle value.
        old_at = getattr(store, "at", 0)
        merge_class_toggles = _vnf_roadwarden_merge_class_toggles_enabled()
        reachable = {}
        for ast_idx, cond_str in kwargs_by_ast.items():
            for toggle_val in toggles:
                try:
                    store.at = toggle_val
                    result = renpy.python.py_eval(cond_str)
                except Exception:
                    result = False
                finally:
                    store.at = old_at
                if result:
                    reachable[ast_idx] = toggle_val
                    break
        _vnf_log("CA DEBUG toggles={} class_action_vals={} kwargs={} reachable={}".format(
            toggles, class_action_vals,
            {k: v[:80] for k, v in kwargs_by_ast.items()},
            reachable))

        # Build label -> (skill, ast_index) map for disabled choices.
        # Disabled items aren't in value_map, so match by label against
        # raw_ast_items conditions to detect skill-gated unavailables.
        # Check ALL class abilities, not just unlocked ones, so we can
        # hide disabled choices for abilities the character can never use.
        # Track ast_index so we can cross-ref against `reachable` to
        # hide variants whose full condition is False (e.g. two
        # knowledge hints conditioned on different game flags).
        _all_class_actions = _ROADWARDEN_CLASS_ACTIONS
        _disabled_skill = {}
        for ri in raw_ast_items:
            _ri_kw = ri.get("item_kwargs", {})
            _ri_cond = _ri_kw.get("condition", "")
            if not _ri_cond:
                continue
            for _cv in _all_class_actions:
                if "at" in _ri_cond and _cv in _ri_cond:
                    _disabled_skill[ri.get("label", "")] = (
                        _cv, ri["ast_index"])
                    break

        # Filter: remove unreachable, add pre_sets, annotate attitudes.
        new_choices = []
        new_value_map = {}
        new_idx = 1
        changed = False
        for c in choices:
            if c.get("caption") or c.get("disabled"):
                # Hide disabled dice/chance choices — always noise.
                if c.get("disabled"):
                    _dlbl = c.get("label", "")
                    if _dlbl.startswith("[chance]") or _dlbl.lstrip().startswith("[chance]"):
                        changed = True
                        continue
                # Filter/tag disabled choices gated behind class abilities.
                if c.get("disabled") and _disabled_skill:
                    _ds_info = _disabled_skill.get(c.get("label", ""))
                    if _ds_info:
                        _ds, _ds_ast = _ds_info
                        if _ds not in class_action_vals:
                            # Wrong class entirely — hide the choice.
                            _vnf_log("Filter: removed disabled [%.50s] "
                                     "(requires %s, not unlocked)" % (
                                         c["label"], _ds))
                            changed = True
                            continue
                        # Right class, but check if condition is
                        # actually reachable.  Menus can have multiple
                        # variants of a disabled hint conditioned on
                        # different game flags — only keep the one
                        # whose full condition would be True.
                        if _ds_ast not in reachable:
                            _vnf_log("Filter: removed disabled [%.50s] "
                                     "(condition unreachable)" % (
                                         c["label"],))
                            changed = True
                            continue
                        _toggle_val = reachable[_ds_ast]
                        if _toggle_val != old_at:
                            if not merge_class_toggles:
                                c = dict(c)
                                c["label"] = "[{}] {}".format(_ds, c["label"])
                                changed = True
                                new_choices.append(c)
                                continue
                            # Promote this class-gated disabled item to
                            # enabled: it becomes actionable via a pre_set
                            # that flips `at` before end_interaction, same
                            # flow as the mage's pearl pendant and
                            # scholar's [cost] options.  Without this
                            # promotion, agents can only reach these
                            # options via the manual [force]/[spell]
                            # toggle-then-wait-then-act dance.
                            c = dict(c)
                            c["label"] = "[{}] {}".format(_ds, c["label"])
                            c["disabled"] = False
                            c["index"] = new_idx
                            c["_class_action"] = _toggle_val
                            pre_sets[new_idx] = [("at", _toggle_val)]
                            new_choices.append(c)
                            new_value_map[new_idx] = _ds_ast
                            new_idx += 1
                            changed = True
                            continue
                        # Same toggle as current — keep as visible hint
                        # (already reachable by live state, Ren'Py just
                        # hasn't flipped the ChoiceReturn yet).
                        c = dict(c)
                        c["label"] = "[{}] {}".format(_ds, c["label"])
                        # Preserve across scrape ticks even when Ren'Py
                        # stops rendering the underlying ChoiceReturn —
                        # the hint is still relevant to the agent.
                        c["_keep_stale"] = True
                        changed = True
                new_choices.append(c)
                continue
            old_idx = c["index"]
            ast_idx = value_map.get(old_idx)
            if ast_idx is not None and ast_idx in kwargs_by_ast:
                if ast_idx not in reachable:
                    _vnf_log("Filter: removed [%.50s] "
                             "(cond=%s, no toggle)" % (
                                 c["label"],
                                 kwargs_by_ast[ast_idx]))
                    changed = True
                    continue
                toggle_val = reachable[ast_idx]
                needs_toggle = toggle_val != old_at
                # Annotate attitude choices for downstream transforms.
                if toggle_val in attitude_vals:
                    if needs_toggle:
                        pre_sets[new_idx] = [("at", toggle_val)]
                    c = dict(c)
                    c["_attitude"] = toggle_val
                    changed = True
                # Class ability toggles: add pre_resolve_steps so the
                # viewer sees the toggle clicked before the choice.
                elif toggle_val in class_action_vals and needs_toggle:
                    if not merge_class_toggles:
                        changed = True
                        continue
                    pre_sets[new_idx] = [("at", toggle_val)]
                    c = dict(c)
                    _prefix = "[{}]".format(toggle_val)
                    if not c.get("label", "").strip().lower().startswith(
                            _prefix.lower()):
                        c["label"] = "{} {}".format(
                            _prefix, c.get("label", "").strip())
                    c["_class_action"] = toggle_val
                    changed = True
                elif needs_toggle:
                    pre_sets[new_idx] = [("at", toggle_val)]
            c_copy = dict(c)
            c_copy["index"] = new_idx
            new_choices.append(c_copy)
            new_value_map[new_idx] = (
                ast_idx if ast_idx is not None
                else value_map.get(old_idx))
            new_idx += 1

        if not changed and not pre_sets:
            return None

        _vnf_log("Filter: %d -> %d choices, %d pre_sets" % (
            len(value_map), len(new_value_map), len(pre_sets)))
        ctx["choices"] = new_choices
        ctx["value_map"] = new_value_map
        ctx["next_idx"] = new_idx
        return ctx

    _vnf_add_menu_augmenter(_vnf_roadwarden_choice_filter, priority=25)

    # -- Roadwarden action transform: merge attitude buttons into choices --

    def _vnf_extract_at_value(action):
        """Extract the ``at`` value from a button's action_strs, or None."""
        for s in action.get("action_strs", []):
            if "field=at value=" in s:
                return s.split("value=", 1)[1].split()[0]
        return None

    def _vnf_roadwarden_promote_attitudes(actions, context):
        """Merge attitude buttons with their corresponding dialogue choices.

        Reads ``attitude_vals`` from shared pipeline state (written by
        the augmenter) to identify attitude buttons.

        Supports two scenarios:
          A) Augmenter-recovered choices: each choice has ``_attitude``
             from the augmenter.  Match by value.
          B) Both attitudes and choices visible: positional 1:1 mapping.

        In both cases, annotate each choice with its attitude, add
        pre_resolve_steps (click attitude button first), and hide the
        separate attitude buttons.
        """
        if not context.get("has_choices"):
            return actions

        # Read attitude set from shared pipeline state.
        _shared = context.get("shared", {})
        _att_set = _shared.get("attitude_vals", _ROADWARDEN_ATTITUDES)

        # Collect attitude buttons by value from action_strs.
        att_buttons = {}
        for a in actions:
            if a["source"] != "button":
                continue
            _val = _vnf_extract_at_value(a)
            if _val and _val in _att_set:
                att_buttons[_val] = a
        if not att_buttons:
            return actions

        # --- Path A: augmenter-annotated choices (value-based match) ---
        augmented = [a for a in actions
                     if a["source"] == "choice" and "_attitude" in a]
        if augmented:
            for a in actions:
                if a["source"] != "choice" or "_attitude" not in a:
                    continue
                att_val = a["_attitude"]
                a["id"] = att_val
                a["annotation"] = att_val
                a["pre_resolve_steps"] = [
                    {"type": "click_button",
                     "match_action_field": "at",
                     "match_action_value": att_val},
                    {"type": "wait", "duration": 0.3},
                ]
        else:
            # --- Path B: positional 1:1 mapping (both visible on screen) ---
            attitudes = list(att_buttons.keys())
            choosable = []
            for a in actions:
                if a["source"] != "choice":
                    continue
                if a.get("disabled") or a.get("caption"):
                    continue
                _lbl = a["label"].strip()
                if not _lbl or _lbl == "(disabled)":
                    continue
                choosable.append(a)

            if len(attitudes) != len(choosable):
                return actions

            _att_map = {}
            for i, att_val in enumerate(attitudes):
                _att_map[choosable[i]["index"]] = att_val

            for a in actions:
                if a["source"] != "choice":
                    continue
                att_val = _att_map.get(a["index"])
                if att_val:
                    a["id"] = att_val
                    a["annotation"] = att_val
                    a["pre_set"] = [("at", att_val)]
                    a["pre_resolve_steps"] = [
                        {"type": "click_button",
                         "match_action_field": "at",
                         "match_action_value": att_val},
                        {"type": "wait", "duration": 0.3},
                    ]

        # Hide attitude buttons and tutorial tooltip in both paths.
        for a in actions:
            if a["source"] != "button":
                continue
            _val = _vnf_extract_at_value(a)
            if _val and _val in _att_set:
                a["hidden"] = True
            elif a.get("label", "").startswith("Whenever you meet new people"):
                a["hidden"] = True
        return actions

    _vnf_add_action_transform(_vnf_roadwarden_promote_attitudes, priority=30)

    # -- Roadwarden action transform: hide bookkeeping choices --
    # Single choices with labels like '(helvius1 set)' are internal
    # containers that keep NVL alive while topic buttons are active.
    # Hide them so the agent only sees and interacts with the buttons.

    _VNF_RW_NAV_CATEGORIES = frozenset(("navigation", "nav"))

    def _vnf_roadwarden_hide_bookkeeping(actions, context):
        # Find any interactable non-nav content on the same screen.
        # Previously this only looked for _category=="topics" buttons,
        # but bookkeeping containers can coexist with topic lists
        # whose category tag is briefly absent (transition ticks) or
        # with choice-category buttons.  Hide bookkeeping whenever
        # ANY other visible, actionable item exists — nav bar doesn't
        # count (always present and not a substitute for real choices).
        has_other = False
        _bookkeeping = []
        for a in actions:
            if a.get("hidden"):
                continue
            if a["source"] == "choice":
                if _vnf_roadwarden_bookkeeping_re.match(a.get("label", "")):
                    _bookkeeping.append(a)
                    continue
                if not a.get("caption") and not a.get("disabled"):
                    has_other = True
            elif a["source"] == "button":
                cat = a.get("_category", "")
                if cat in _VNF_RW_NAV_CATEGORIES:
                    continue
                if not a.get("disabled") and not a.get("is_disabled"):
                    has_other = True
        for a in _bookkeeping:
            if has_other:
                a["hidden"] = True
            else:
                # A lone bookkeeping choice is a transient NVL container:
                # keep it active for Ren'Py, but suppress it from agent-facing
                # pending text until the real topic/action buttons arrive.
                a["_suppress_pending_choice"] = True
                a["_container_choice"] = True
        return actions

    _vnf_add_action_transform(_vnf_roadwarden_hide_bookkeeping, priority=35)

    # -- Roadwarden action transform: class ability pre-resolve steps --

    def _vnf_roadwarden_class_action_steps(actions, context):
        """Add pre_resolve_steps for choices gated behind class ability toggles.

        Choices annotated with ``_class_action`` by the augmenter need the
        class toggle button ([knowledge], [force], [spell]) clicked first
        so the viewer sees the reveal before the choice is made.
        """
        if not _vnf_roadwarden_merge_class_toggles_enabled():
            return actions
        if not context.get("has_choices"):
            return actions

        _shared = context.get("shared", {})
        _ca_vals = _shared.get("class_action_vals", set())
        if not _ca_vals:
            return actions

        for a in actions:
            if a["source"] != "choice":
                continue
            ca_val = a.get("_class_action")
            if ca_val:
                # Use pre_set (setattr at=val before end_interaction)
                # instead of clicking the toggle button. The toggle
                # click causes a menu re-render that invalidates the
                # saved value_map, so end_interaction fires on the
                # wrong choice.  Setting the store var directly
                # matches how attitudes work and resolves cleanly.
                a["pre_set"] = [("at", ca_val)]
        return actions

    _vnf_add_action_transform(_vnf_roadwarden_class_action_steps, priority=31)

    # -- Roadwarden action transform: label merged class choices --

    def _vnf_roadwarden_label_merged_class_choices(actions, context):
        """Make merged class choices self-describing and hide duplicate toggles.

        When the menu augmenter recovers a class-gated choice, the agent should
        act on that semantic choice directly, not on the raw [force]/[spell]/
        [knowledge] toggle.  Keep toggles visible only when no merged choice for
        that class action exists in the current view.
        """
        if not _vnf_roadwarden_merge_class_toggles_enabled():
            return actions

        merged_vals = set()
        for a in actions:
            if a.get("source") != "choice":
                continue
            ca_val = a.get("_class_action")
            if ca_val not in _ROADWARDEN_CLASS_ACTIONS:
                continue
            merged_vals.add(ca_val)
            prefix = "[{}]".format(ca_val)
            label = a.get("label", "")
            if not label.strip().lower().startswith(prefix.lower()):
                a["label"] = "{} {}".format(prefix, label.strip())

        if not merged_vals:
            return actions

        for a in actions:
            if a.get("source") != "button":
                continue
            at_val = _vnf_extract_at_value(a)
            if at_val in merged_vals:
                a["hidden"] = True
        return actions

    _vnf_add_action_transform(
        _vnf_roadwarden_label_merged_class_choices, priority=32
    )

    # -- Roadwarden action transform: label selling screen items --
    import re as _vnf_re_sell
    _SELL_LABEL_RE = _vnf_re_sell.compile(r'selling(\w+)$')

    def _vnf_roadwarden_selling_labels(actions, context):
        """Extract item names from Jump labels on the selling screen.

        Selling screen buttons are image-only with TooltipAction + Jump
        actions.  The Jump label encodes the item name, e.g.
        'howlersdellsellingbronzerod' -> 'Bronze Rod'.
        """
        for a in actions:
            if a.get("screen") != "selling" or a["source"] != "button":
                continue
            if a.get("label") and a["label"] not in ("", "[]", "[unlabelled]"):
                continue  # already labelled
            strs = a.get("action_strs", [])
            for s in strs:
                if not s.startswith("Jump label="):
                    continue
                target = s.split("label=", 1)[1].split()[0]
                m = _SELL_LABEL_RE.search(target)
                if m:
                    raw = m.group(1)
                    friendly = _VNF_RW_ITEM_NAMES.get(raw, raw)
                    a["label"] = "[Sell: {}]".format(friendly)
                    break
        return actions

    _vnf_add_action_transform(_vnf_roadwarden_selling_labels, priority=25)

    # -- Roadwarden auto-skip filter: suppress bookkeeping labels --
    # Matches:
    #   (NAME set)      e.g. (tulia1 set), (helvius1 set), (druidcave1 set)
    #   (NAME preset)   e.g. (elpis1 preset)
    #   (preset NAME)   e.g. (preset foggy1) — different word order
    #   (NAME)          e.g. (custom1), (foggy1) — bare variable-name tokens
    #                   used as single-item bookkeeping menus.
    import re as _vnf_re
    _vnf_roadwarden_bookkeeping_re = _vnf_re.compile(
        r'^\((?:'
        r'preset\b[^)]*'              # (preset NAME)
        r'|[^)]*\b(?:pre)?set'        # (NAME set) / (NAME preset)
        r'|[a-z_][a-z0-9_]*'          # (name1) / (custom1)
        r')\)$')

    def _vnf_roadwarden_auto_skip_filter(label):
        """Return False for internal bookkeeping labels like '(tulia1 set)'.

        Roadwarden uses single-choice menus with labels matching
        (nameN set) as hub checkpoints.  These carry no narrative
        value and should be hidden from the LLM event stream.
        """
        return not _vnf_roadwarden_bookkeeping_re.match(label)

    vnf_player.auto_skip_event_filter = _vnf_roadwarden_auto_skip_filter

    # -- Roadwarden auto-skip predicate: block skip for hub containers --
    def _vnf_roadwarden_auto_skip_predicate(label):
        """Block auto-skip when questionpreset is set.

        Roadwarden uses single-choice menus like '(tulia1 set)' as
        containers that keep the NVL interaction alive while question
        buttons (from nvlchoices.rpy) are displayed.  The player is
        expected to click a button, not the menu choice.  Auto-skipping
        resolves the menu prematurely, causing NVL duplication.
        """
        qp = getattr(renpy.store, 'questionpreset', None)
        if qp:
            return False  # block auto-skip — hub buttons are active
        return True

    vnf_player.auto_skip_predicate = _vnf_roadwarden_auto_skip_predicate

    # -- Roadwarden NVL hub deduplication --
    # The game has no `nvl clear` between hub re-entries (e.g. the
    # Tulia question hub at prolcamp01questions01).  Each hub cycle
    # re-adds all question captions as NVL text, causing duplicates
    # in the NVL buffer.  Detect hub re-entry (current choices are
    # a strict subset of previous choices) and clear the NVL buffer.
    _vnf_roadwarden_prev_choices = [None]

    def _vnf_roadwarden_nvl_dedup(choice_labels, is_nvl):
        # Skip single-choice menus (bookkeeping labels like "(tulia1 set)")
        # so they don't poison the previous-choices tracker and break
        # hub re-entry detection.
        if len(choice_labels) <= 1:
            return
        prev = _vnf_roadwarden_prev_choices[0]
        _vnf_roadwarden_prev_choices[0] = list(choice_labels)
        # Hub re-entry: current choices are a strict subset of
        # the previous menu (same labels minus the picked one).
        if prev is not None and len(choice_labels) < len(prev):
            if all(c in prev for c in choice_labels):
                # Clear NVL buffer but preserve the last entry —
                # it's the menu-context say (the response to the
                # topic the player just picked).
                _nvl_last = renpy.store.nvl_list[-1:] if renpy.store.nvl_list else []
                renpy.store.nvl_list = list(_nvl_last)
                # Clear NVL-kind entries from _history_list to
                # prevent the custom NVL screen from re-rendering
                # accumulated question text.  Keep the most recent
                # one (matches the preserved nvl_list entry).
                _hl = getattr(renpy.store, '_history_list', [])
                _before = len(_hl)
                _nvl_entries = [h for h in _hl if getattr(h, 'kind', None) == 'nvl']
                _keep_last = _nvl_entries[-1] if _nvl_entries else None
                renpy.store._history_list = [
                    h for h in _hl
                    if getattr(h, 'kind', None) != 'nvl' or h is _keep_last
                ]
                _after = len(renpy.store._history_list)
                _vnf_client.push_event(dict(
                    type="debug",
                    msg="Hub re-entry! Cleared nvl_list (kept last) + %d nvl history entries (%d -> %d)" % (
                        _before - _after, _before, _after,
                    ),
                ))

    vnf_player.pre_menu_callback = _vnf_roadwarden_nvl_dedup

    # -- Roadwarden startup: auto-dismiss quote of the day --
    #
    # Roadwarden shows a random quote overlay with an "Enter" button
    # before the main menu.  A user player clicks it away instantly.
    # This periodic callback detects the Enter button, waits a short
    # delay (so the user viewer can read the quote), then dismisses
    # it automatically.

    _vnf_startup_quote_deadline = [0]   # monotonic deadline; 0 = not detected yet
    _vnf_startup_quote_done = [False]

    def _vnf_periodic_dismiss_startup_quote():
        if _vnf_startup_quote_done[0]:
            return
        try:
            showing = _vnf_get_showing_screens()
            found_enter = None
            for sname, scr in showing:
                btns = []
                _vnf_collect_button_actions(scr, btns, sname)
                for d, action, label, screen in btns:
                    if label == "Enter":
                        found_enter = (d, action, label, screen)
                        break
                if found_enter:
                    break

            if found_enter:
                now = _time_monotonic()
                if _vnf_startup_quote_deadline[0] == 0:
                    delay = max(vnf_player.post_action_delay, 2.0)
                    _vnf_startup_quote_deadline[0] = now + delay
                    _vnf_log("Startup quote detected, will dismiss in {:.1f}s".format(delay))
                    return
                if now < _vnf_startup_quote_deadline[0]:
                    return
                _vnf_startup_quote_done[0] = True
                _vnf_log("Auto-dismissing startup quote")
                try:
                    renpy.run(found_enter[1])
                except _CONTROL_EXCEPTIONS:
                    raise
                except Exception:
                    _vnf_log("Failed to dismiss startup quote")
            else:
                # No Enter button found.  If we already started the
                # timer but the button vanished (dismissed manually),
                # or if the main menu is already showing, stop looking.
                if _vnf_startup_quote_deadline[0] > 0:
                    _vnf_startup_quote_done[0] = True
                else:
                    for sname, scr in showing:
                        if sname == "main_menu":
                            _vnf_startup_quote_done[0] = True
                            return
        except _CONTROL_EXCEPTIONS:
            raise
        except Exception:
            pass

    _register_periodic(_vnf_periodic_dismiss_startup_quote, 0.2)

    def _vnf_get_inventory_stats():
        """
        Expose player-visible Roadwarden game state to the LLM bridge.

        Returns only what the character sheet / HUD shows:
        inventory items, vitality, food, armor, appearance, cleanliness,
        class, religion, goal, location, coins, day/time.

        Hidden internal state (quest flags, NPC relationships, area
        unlocks, internal counters) lives in _rw_hidden_stats() in
        roadwarden_progress.rpy.
        """
        try:
            # Build inventory from item variables
            # We only include items with count > 0
            inventory = []

            # Consumables
            consumables = [
                ("item_rations", "Rations"),
                ("item_chicken", "Chicken"),
                ("item_wildplants", "Wild Plants"),
                ("item_spiritrock", "Spirit Rock"),
                ("item_generichealingpotion", "Healing Potion"),
                ("item_magicfruit", "Magic Fruit"),
                ("item_potiondolmen", "Dolmen Potion"),
                ("item_smallhealingpotion", "Small Healing Potion"),
                ("item_sharpeningpotion", "Sharpening Potion"),
            ]
            for var_name, item_name in consumables:
                count = getattr(renpy.store, var_name, 0)
                if count > 0:
                    inventory.append({
                        "name": item_name,
                        "type": "consumable",
                        "quantity": count,
                    })

            # Weapons
            weapons = [
                ("item_asterionspear", "Asterion's Spear"),
                ("item_axe01", "Axe"),
                ("item_axe02", "Axe (second)"),
                ("item_axe03", "Axe (third)"),
                ("item_crossbow", "Crossbow"),
                ("item_crossbowquarrels", "Crossbow Quarrels"),
                ("item_mountainroadspear", "Mountain Road Spear"),
                ("item_trollurine", "Troll Urine"),
                ("item_blindingpowder", "Blinding Powder"),
                ("item_golemglove", "Golem Glove"),
            ]
            for var_name, item_name in weapons:
                count = getattr(renpy.store, var_name, 0)
                if count > 0:
                    inventory.append({
                        "name": item_name,
                        "type": "weapon",
                        "quantity": count,
                    })

            # Armor
            armor_items = [
                ("item_gambeson01", "Gambeson"),
                ("item_gambeson02", "Gambeson (second)"),
                ("item_shield", "Shield"),
            ]
            for var_name, item_name in armor_items:
                count = getattr(renpy.store, var_name, 0)
                if count > 0:
                    inventory.append({
                        "name": item_name,
                        "type": "armor",
                        "quantity": count,
                    })

            # Quest items
            quest_items = [
                ("item_boxfromdolmen", "Box from Dolmen"),
                ("item_oceannecklace", "Ocean Necklace"),
                ("item_bronzerod", "Bronze Rod"),
                ("item_asterionkey", "Asterion's Key"),
                ("item_asteriontablet", "Asterion's Wax Tablet"),
                ("item_oldtunnelkey", "Old Tunnel Key"),
                ("item_trapdoorkeydolmen", "Trapdoor Key"),
                ("item_watchtowerkey", "Watchtower Key"),
                ("item_piershedkey", "Pier's Shed Key"),
                ("item_bonehook", "Bone Hook"),
                ("item_dragonhorn", "Dragon Horn"),
                ("item_lantern", "Lantern"),
                ("item_magicchisel", "Magic Chisel"),
                ("item_travelequipment", "Travel Equipment"),
                ("item_witheringdust", "Withering Dust"),
                ("item_machete", "Machete"),
                ("item_letterwhitemarshes", "Letter from White Marshes"),
                ("item_casket", "Casket"),
                ("item_arrow", "Arrow"),
                ("item_snakebait", "Snake Bait"),
                ("item_thaisletter", "Thais's Letter"),
                ("item_teethset", "Teeth Set"),
                ("item_thyrsusgift", "Thyrsus's Gift"),
                ("item_magicpens", "Magic Pens"),
                ("item_magicalsapling", "Magical Sapling"),
                ("item_cidercask", "Cider Cask"),
                ("item_furlesswolftrophy", "Furless Wolf Trophy"),
                ("item_griffonegg", "Griffon Egg"),
                ("item_asterionbow", "Asterion's Bow"),
                ("item_boartusks", "Boar Tusks"),
                ("item_bonering", "Bone Ring"),
                ("item_spidersilk", "Spider Silk"),
                ("item_wingedhourglass", "Winged Hourglass"),
                ("item_ghoulblood", "Ghoulish Blood"),
                ("item_stingointment", "Sting Ointment"),
                ("item_beholderroot", "Beholder Root"),
                ("item_cavemushroom", "Cave Mushroom"),
            ]
            for var_name, item_name in quest_items:
                count = getattr(renpy.store, var_name, 0)
                if count > 0:
                    inventory.append({
                        "name": item_name,
                        "type": "quest_item",
                        "quantity": count,
                    })

            # Merchandise/tradable items
            merchandise = [
                ("item_antlers", "Antlers"),
                ("item_asterionwine", "Asterion's Wine"),
                ("item_elkfur", "Elk Fur"),
                ("item_harepelt", "Hare Pelt"),
                ("item_sealskin", "Seal Skin"),
                ("item_furlesswolftrophy", "Furless Wolf Trophy"),
                ("item_ironscraps", "Iron Scraps"),
                ("item_ironingot", "Iron Ingot"),
                ("item_linen", "Linen"),
                ("item_spices", "Spices"),
                ("item_stoat", "Stoat"),
                ("item_peltnorthberryclaw", "Peltnorth Berry Claw"),
                ("item_peltnorthberrytools", "Peltnorth Berry Tools"),
                ("item_dragonlingpaw", "Dragonling Paw"),
                ("item_dragonlingclaws", "Dragonling Claws"),
            ]
            for var_name, item_name in merchandise:
                count = getattr(renpy.store, var_name, 0)
                if count > 0:
                    inventory.append({
                        "name": item_name,
                        "type": "merchandise",
                        "quantity": count,
                    })

            # ----- Build stats (player-visible only) -----
            stats = {}
            stats["_inventory_label"] = "Inventory"

            # Core character attributes.
            # The game defaults pc_class to the int 0; it only becomes
            # a meaningful string ("warrior"/"mage"/"scholar") after
            # the player picks in the prologue.  Treat int as unset
            # to avoid misleading agents into thinking a default
            # character already exists.
            pc_class = getattr(renpy.store, "pc_class", None)
            if isinstance(pc_class, str):
                stats["pc_class"] = pc_class
                stats["pc_class_desc"] = pc_class

            # Vitality (health)
            pc_hp = getattr(renpy.store, "pc_hp", None)
            pc_hp_can5 = getattr(renpy.store, "pc_hp_can5", None)
            max_hp = 4  # default
            if pc_hp is not None:
                max_hp = 5 if pc_hp_can5 else 4
                stats["pc_hp"] = pc_hp
                stats["max_hp"] = max_hp
                if pc_hp == 0:
                    stats["hp_desc"] = "critical - you are at death's door"
                elif pc_hp == 1:
                    stats["hp_desc"] = "low - severely weakened"
                elif pc_hp == 2:
                    stats["hp_desc"] = "moderate - battered but functional"
                elif pc_hp == 3:
                    stats["hp_desc"] = "good - reasonably healthy"
                elif pc_hp >= 4:
                    stats["hp_desc"] = "excellent - in peak condition"

            # Mana (mage class only)
            mana = getattr(renpy.store, "mana", None)
            _is_mage = pc_class == 1 or pc_class == "mage"
            if _is_mage and mana is not None:
                stats["mana"] = mana
                stats["max_mana"] = 5

            # Food level
            pc_food = getattr(renpy.store, "pc_food", None)
            if pc_food is not None:
                stats["pc_food"] = pc_food
                if pc_food == 0:
                    stats["food_desc"] = "starving - desperately hungry"
                elif pc_food == 1:
                    stats["food_desc"] = "hungry - stomach growling"
                elif pc_food == 2:
                    stats["food_desc"] = "satisfied - full and content"
                elif pc_food >= 3:
                    stats["food_desc"] = "stuffed - more than full"

            # Character goal
            pc_goal = getattr(renpy.store, "pc_goal", None)
            if pc_goal is not None:
                stats["pc_goal"] = pc_goal
                if pc_goal == "ineedmoney":
                    stats["pc_goal_desc"] = "to gather enough dragon bones to save my sibling from debt collectors"
                elif pc_goal == "iwantmoney":
                    stats["pc_goal_desc"] = "to gather enough dragon bones to retire early and live in prosperity"
                elif pc_goal == "iwanttoberemembered":
                    stats["pc_goal_desc"] = "to be remembered as the hero who brought peace and order"
                elif pc_goal == "iwanttohelp":
                    stats["pc_goal_desc"] = "to help the local villages and make this region safer"
                elif pc_goal == "iwantstatus":
                    stats["pc_goal_desc"] = "to build connections and become a major player in the merchant guild"
                elif pc_goal == "iwanttostartanewlife":
                    stats["pc_goal_desc"] = "to escape my difficult past and start fresh"

            # Religion
            pc_religion = getattr(renpy.store, "pc_religion", None)
            if pc_religion is not None:
                stats["pc_religion"] = pc_religion

            # Day and time
            day = getattr(renpy.store, "day", None)
            if day is not None:
                stats["day"] = day
            hour = getattr(renpy.store, "hour", None)
            if hour is not None:
                stats["hour"] = hour
            timescreen = getattr(renpy.store, "timescreen", None)
            if timescreen is not None:
                stats["timescreen"] = timescreen

            # Compute human-readable time remaining until dusk.
            # 1 quarter = 15 min; world_daylength quarters per day.
            quarters = getattr(renpy.store, "quarters", None)
            world_daylength = getattr(renpy.store, "world_daylength", 84)
            if quarters is not None and world_daylength:
                _rem = world_daylength - quarters
                _rem_h = _rem // 4
                _rem_m = (_rem % 4) * 15
                if _rem_h > 0 and _rem_m > 0:
                    stats["_time_display"] = "{}h {}m before dusk".format(_rem_h, _rem_m)
                elif _rem_h > 0:
                    stats["_time_display"] = "{}h before dusk".format(_rem_h)
                elif _rem_m > 0:
                    stats["_time_display"] = "{}m before dusk".format(_rem_m)
                else:
                    stats["_time_display"] = "dusk"

            # Area (current location).  Keep the raw id for tooling and add
            # the display name the travel map uses, so "where am I" is
            # answerable on every screen and not only inside the map.  The
            # name table covers the peninsula; late-game areas (the northern
            # sea legs, High Island) and intermediate steps are not in it, so
            # an unmapped id is shown verbatim rather than hidden -- it is
            # stable, journallable, and it makes coverage gaps visible.
            pc_area = getattr(renpy.store, "pc_area", None)
            if pc_area is not None:
                stats["pc_area"] = pc_area
                stats["location"] = _vnf_rw_area_display(pc_area)

            # Weather.  Road condition is the variable that governs travel
            # time ("dry roads roughly halved travel times" -- a 40-day agent
            # noticed the pattern only around Day 35), so it belongs in the
            # footer next to the clock.  weathermud / weatherfog are the
            # game's plain flags; the richer weather table is not read here.
            _mud = getattr(renpy.store, "weathermud", None)
            _fog = getattr(renpy.store, "weatherfog", None)
            if _mud is not None:
                _wx = "muddy roads" if _mud else "dry roads"
                if _fog:
                    _wx = _wx + ", fog"
                stats["weather"] = _wx

            # Coins
            _coins = getattr(renpy.store, "coins", None)
            if _coins is not None:
                stats["coins"] = _coins

            # Appearance (derived, 0-5) and cleanliness (stored, 0-3).
            appearance = getattr(renpy.store, "appearance", None)
            cleanliness = getattr(renpy.store, "cleanliness", None)
            if appearance is not None:
                stats["appearance"] = "{}/5".format(appearance)
            if cleanliness is not None:
                stats["cleanliness"] = "{}/3".format(cleanliness)

            # Armor condition -- `armor` is the durability counter,
            # max is 3 (base) or 4 (when armor_can4 flag is set).
            _armor = getattr(renpy.store, "armor", 0)
            _armor_can4 = getattr(renpy.store, "armor_can4", 0)
            _max_armor = 4 if _armor_can4 else 3
            _has_gambeson = getattr(renpy.store, "item_gambeson01", 0) or getattr(renpy.store, "item_gambeson02", 0)
            if _has_gambeson:
                stats["armor"] = "{}/{}".format(_armor, _max_armor)

            # Inventory count (quick reference)
            stats["inventory_count"] = len(inventory)

            # ----- Build compact summary line for brief mode -----
            # Treat int pc_class as unset (pre-prologue default).
            if isinstance(pc_class, str):
                _cls = pc_class.capitalize()
            else:
                _cls = None
            # Include the world deadline (Day X/40) unless casual
            # mode sets it to the sentinel 1000.  Helps agents track
            # the time pressure — they otherwise forget the deadline.
            _deadline = getattr(
                getattr(renpy.store, "persistent", None),
                "difficultypick_advanced_world_deadline", None)
            if day is None:
                _day_str = "Day ?"
            elif _deadline and 1 < _deadline < 999:
                _day_str = "Day {}/{}".format(day, _deadline)
            else:
                _day_str = "Day {}".format(day)
            _parts = [_day_str]

            _location = stats.get("location")
            if _location:
                _parts.append("Location: {}".format(_location))

            # Time -- use _time_display if available, fall back to raw hour.
            _time_disp = stats.get("_time_display")
            if _time_disp:
                _parts.append(_time_disp)
            elif hour is not None:
                _parts.append("Hour {}".format(hour))

            _weather = stats.get("weather")
            if _weather:
                _parts.append("Weather: {}".format(_weather))

            _hp_part = "HP {}/{}".format(
                pc_hp if pc_hp is not None else "?",
                max_hp if pc_hp is not None else "?")
            if _cls:
                _parts.append("{}, {}".format(_cls, _hp_part))
            else:
                _parts.append(_hp_part)

            if _is_mage and mana is not None:
                _parts.append("Mana {}/5".format(mana))

            _food_labels = {0: "starving", 1: "hungry", 2: "satisfied"}
            _fl = _food_labels.get(pc_food, "full" if pc_food and pc_food >= 3 else "?")
            _parts.append("Food: {}".format(_fl))

            if _has_gambeson:
                _parts.append("Armor: {}/{}".format(_armor, _max_armor))

            if appearance is not None:
                _parts.append("Appearance: {}/5".format(appearance))

            if _coins is not None:
                _parts.append("Coins: {}".format(_coins))

            stats["_summary"] = " | ".join(_parts)

            return inventory, stats

        except Exception as e:
            # Log error for debugging but don't crash the game
            import traceback
            _logger = getattr(renpy.store, "_vnf_log", lambda x: None)
            _logger("Roadwarden stat getter error: " + str(e))
            return [], {}

    def _vnf_apply_inventory_changes(changes):
        """
        Apply inventory modifications from an external client.

        Supported actions:
            - add:    Increase item count
            - remove: Decrease item count (min 0)
            - set:    Set item count to specific value

        Example command JSON:
            {
                "name": "inventory_modify",
                "args": {
                    "changes": [
                        {"action": "add", "item": "item_rations", "amount": 1},
                        {"action": "set", "item": "item_chicken", "amount": 0}
                    ]
                }
            }

        Note: In "debug" mode (vnf_player.stat_mode = "debug"), you can also modify internal variables like pc_lies,
              pc_battlecounter, etc. using the stats_modify endpoint instead.
        """
        try:
            added = 0
            removed = 0
            for change in changes:
                action = change.get("action", "")
                item = change.get("item", "")
                amount = change.get("amount", 1)

                # Check if the variable exists
                if hasattr(renpy.store, item):
                    current = getattr(renpy.store, item, 0)
                    if action == "add":
                        setattr(renpy.store, item, current + amount)
                        added += 1
                    elif action == "remove":
                        new_val = max(0, current - amount)
                        setattr(renpy.store, item, new_val)
                        removed += current - new_val
                    elif action == "set":
                        setattr(renpy.store, item, amount)
                        removed += abs(current - amount)
                else:
                    # Try to find by item name (fallback)
                    # This is a simplified approach; in practice, you'd want a mapping
                    pass

            msg = "Inventory: {} items changed".format(added + removed)
            return {"success": True, "message": msg}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def _vnf_apply_stats_changes(changes):
        """
        Apply stat modifications from an external client.

        Only whitelisted game variables can be modified based on the current mode:

          Normal mode (vnf_player.stat_mode = "normal"):
            - Core stats only (pc_hp, pc_food, mana, day)

          Debug mode (vnf_player.stat_mode = "debug"):
            - Also allows internal/hidden variables (pc_lies, weather, etc.)

        Example command JSON (normal mode):
            {
                "name": "stats_modify",
                "args": {
                    "changes": {
                        "pc_hp": 5,
                        "mana": 3,
                        "pc_food": 2
                    }
                }
            }

        Example command JSON (debug mode - modify hidden vars):
            {
                "name": "stats_modify",
                "args": {
                    "changes": {
                        "pc_lies": 5,
                        "weather": 1,
                        "appearance": 3
                    }
                }
            }
        """
        try:
            # Whitelist of modifiable variables with (type, min, max) constraints.
            # None means no clamping (for bools / uncapped values).
            allowed = {
                "pc_hp": (int, 0, 5),
                "pc_food": (int, 0, 5),
                "mana": (int, 0, 5),
                "day": (int, 0, None),
            }

            # Debug mode: expand whitelist with internal variables
            if vnf_player.stat_mode == "debug" or not hasattr(vnf_player, 'stat_mode'):
                allowed.update({
                    "pc_lies": (int, 0, None),
                    "pc_battlecounter": (int, 0, None),
                    "weather": (int, 0, None),
                    "appearance": (int, 0, 10),
                    "cleanliness": (int, 0, 10),
                })

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

    # To switch modes at runtime, set vnf_player.stat_mode in your game's script:
    #   vnf_player_stat_mode = "debug"  # or "normal"
    # Or use the bridge server to update vnf_player.stat_mode via a command.

    # -------------------------------------------------------------------------
    # Achievement at-unlock line (agent-facing half of the two-audience
    # achievement design, 2026-08-19).
    #
    # Roadwarden grants achievements through Ren'Py's standard module
    # (achievement.grant in screens.rpy). For a user the unlock is a small
    # icon; for an agent it was INVISIBLE — the fleet's "faring so-so" read
    # came partly from nobody telling the agent it had earned anything.
    # Wrap grant() and push one past-tense narration line per NEW unlock
    # (a fact already earned cannot spoil). The viewer-facing chronicle
    # records the same grant with a day stamp (roadwarden_progress.rpy).
    # -------------------------------------------------------------------------

    def _vnf_rw_achievement_label(ach_id):
        """Best-effort display label from the achievement id."""
        _s = str(ach_id)
        if _s.startswith("achievement_"):
            _s = _s[len("achievement_"):]
        return _s.replace("_", " ").strip().title() or str(ach_id)

    # Keep the original on the module itself so a script reload (Shift+R
    # re-runs init) cannot wrap the wrapper.
    if not hasattr(achievement, "_vnf_orig_grant"):
        achievement._vnf_orig_grant = achievement.grant

    def _vnf_rw_achievement_grant(name, *args, **kwargs):
        _was_new = False
        try:
            _was_new = not achievement.has(name)
        except Exception:
            _was_new = False
        _r = achievement._vnf_orig_grant(name, *args, **kwargs)
        if _was_new:
            try:
                _label = _vnf_rw_achievement_label(name)
                _vnf_client.push_event(dict(
                    type="narration",
                    text="[Achievement unlocked: {}]".format(_label)))
            except Exception:
                pass
            try:
                # Chronicle hook lives in the progress mod; degrade
                # gracefully if that mod is not installed.
                _rec = getattr(
                    renpy.store, "_vnf_rw_chronicle_achievement", None)
                if _rec is not None:
                    _rec(str(name), _vnf_rw_achievement_label(name))
            except Exception:
                pass
        return _r

    achievement.grant = _vnf_rw_achievement_grant

# Late init: runs after the core shim's init 999 block where
# _VISIBLE_SCRAPE_SKIP is defined.
init 1000 python:

    # -- Expose quick_menu HUD buttons (Map, Inventory, Sleep, etc.) --
    # The core shim skips quick_menu to reduce noise, but Roadwarden's
    # HUD has context-sensitive navigation buttons the agent needs.
    _VISIBLE_SCRAPE_SKIP.discard("quick_menu")
