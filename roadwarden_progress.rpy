################################################################################
## Progress Graph & Hidden Stats for Roadwarden
##
## Defines a progress graph that tracks game milestones via passive variable
## checks.  Each node has a `check` lambda that reads Ren'Py store variables
## to determine whether the milestone has been reached.
##
## Also provides _rw_hidden_stats() -- returns internal game state that is
## NOT shown on the character sheet (quest flags, NPC relationships, area
## unlocks, internal counters, story flags, weather, etc.).  This is the
## companion to _vnf_get_inventory_stats() in roadwarden.rpy, which returns
## only player-visible data.
##
## Runs at init -989 (after vnflight.rpy at init -990).
##
## NOTE: Roadwarden runs Ren'Py 7 / Python 2 — no f-strings allowed.
################################################################################

init -989 python:

    # Build graph dict.
    _g = {}

    # -------------------------------------------------------------------------
    # Phase: early_game
    # -------------------------------------------------------------------------

    _g["start"] = {
        "label": "Game started",
        "phase": "early_game",
        "check": lambda: getattr(renpy.store, "day", 0) >= 1,
    }

    _g["prologue_complete"] = {
        "label": "Prologue complete",
        "phase": "early_game",
        # militarycamp_destroyed_firsttime is set to False on first visit
        # (persists even after leaving the area).
        "check": lambda: getattr(renpy.store, "militarycamp_destroyed_firsttime", None) is not None,
    }

    _g["militarycamp_firsttime"] = {
        "label": "Military camp (first visit)",
        "phase": "early_game",
        "check": lambda: getattr(renpy.store, "militarycamp_destroyed_firsttime", None) is False,
    }

    _g["southerncrossroads_unlocked"] = {
        "label": "Southern crossroads unlocked",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "southerncrossroads_unlocked", None)),
    }

    _g["peltnorth_firsttime"] = {
        "label": "Pelt North (first visit)",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "peltnorth_firsttime", None)),
    }

    _g["creeks_firsttime"] = {
        "label": "Creeks (first visit)",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "creeks_firsttime", None)),
    }

    _g["galerocks_firsttime"] = {
        "label": "Gale Rocks (first visit)",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "galerocks_firsttime", None)),
    }

    _g["banditshideout_firsttime"] = {
        "label": "Bandits' hideout (first visit)",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "banditshideout_firsttime", None)),
    }

    _g["whitemarshes_destroyed"] = {
        "label": "White Marshes destroyed",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "whitemarshes_destroyed", None)),
    }

    _g["orentius_banished"] = {
        "label": "Orentius banished",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "orentius_banished", None)),
    }

    _g["orentius_convinced"] = {
        "label": "Orentius convinced",
        "phase": "early_game",
        "check": lambda: bool(getattr(renpy.store, "orentius_convinced", None)),
    }

    # -------------------------------------------------------------------------
    # Phase: mid_game
    # -------------------------------------------------------------------------

    _g["howlersdell_firsttime"] = {
        "label": "Howlers' Dell (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "howlersdell_firsttime", None)),
    }

    _g["ruinedvillage_firsttime"] = {
        "label": "Ruined village (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "ruinedvillage_firsttime", None)),
    }

    _g["oldpagos_firsttime"] = {
        "label": "Old Pagos (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "oldpagos_firsttime", None)),
    }

    _g["monastery_firsttime"] = {
        "label": "Monastery (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "monastery_firsttime", None)),
    }

    _g["watchtower_firsttime"] = {
        "label": "Watchtower (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "watchtower_firsttime", None)),
    }

    _g["ghoulcave_firsttime"] = {
        "label": "Ghoul cave (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "ghoulcave_firsttime", None)),
    }

    _g["foggylake_firsttime"] = {
        "label": "Foggy Lake (first visit)",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "foggylake_firsttime", None)),
    }

    _g["highisland_prep"] = {
        "label": "High Island journey in progress",
        "phase": "mid_game",
        "check": lambda: bool(getattr(renpy.store, "highisland_journey_inprogress", None)),
    }

    # -------------------------------------------------------------------------
    # Quest nodes (started=1, complete=2)
    # -------------------------------------------------------------------------

    _g["quest_spyonwhitemarshes_started"] = {
        "label": "Quest: Spy on White Marshes (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_spyonwhitemarshes", 0) == 1,
    }

    _g["quest_spyonwhitemarshes_complete"] = {
        "label": "Quest: Spy on White Marshes (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_spyonwhitemarshes", 0) == 2,
    }

    _g["quest_runaway_started"] = {
        "label": "Quest: Runaway (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_runaway", 0) == 1,
    }

    _g["quest_runaway_complete"] = {
        "label": "Quest: Runaway (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_runaway", 0) == 2,
    }

    _g["quest_ruins_started"] = {
        "label": "Quest: Ruins (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_ruins", 0) == 1,
    }

    _g["quest_ruins_complete"] = {
        "label": "Quest: Ruins (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_ruins", 0) == 2,
    }

    _g["quest_asterion_started"] = {
        "label": "Quest: Asterion (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_asterion", 0) == 1,
    }

    _g["quest_asterion_complete"] = {
        "label": "Quest: Asterion (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_asterion", 0) == 2,
    }

    _g["quest_easternpath_started"] = {
        "label": "Quest: Eastern Path (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_easternpath", 0) == 1,
    }

    _g["quest_easternpath_complete"] = {
        "label": "Quest: Eastern Path (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_easternpath", 0) == 2,
    }

    _g["quest_missinghunters_started"] = {
        "label": "Quest: Missing Hunters (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_missinghunters", 0) == 1,
    }

    _g["quest_missinghunters_complete"] = {
        "label": "Quest: Missing Hunters (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_missinghunters", 0) == 2,
    }

    _g["quest_matchmaking_started"] = {
        "label": "Quest: Matchmaking (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_matchmaking", 0) == 1,
    }

    _g["quest_matchmaking_complete"] = {
        "label": "Quest: Matchmaking (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_matchmaking", 0) == 2,
    }

    _g["quest_intelforpeltnorth_started"] = {
        "label": "Quest: Intel for Pelt North (started)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_intelforpeltnorth", 0) == 1,
    }

    _g["quest_intelforpeltnorth_complete"] = {
        "label": "Quest: Intel for Pelt North (complete)",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_intelforpeltnorth", 0) == 2,
    }

    _g["quest_ruins_thais_defeated"] = {
        "label": "Quest: Ruins - Thais defeated",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_ruins_choice", None) == "thais_defeated",
    }

    _g["quest_ruins_thais_won"] = {
        "label": "Quest: Ruins - Thais won",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_ruins_choice", None) == "thais_won",
    }

    _g["quest_ruins_thais_alliance"] = {
        "label": "Quest: Ruins - Thais alliance",
        "phase": "mid_game",
        "check": lambda: getattr(renpy.store, "quest_ruins_choice", None) == "thais_alliance",
    }

    # -------------------------------------------------------------------------
    # Phase: late_game
    # -------------------------------------------------------------------------

    _g["highisland_journey"] = {
        "label": "High Island journey",
        "phase": "late_game",
        "check": lambda: getattr(renpy.store, "highisland_mode", None) in ("solo", "howlers", "crew"),
    }

    _g["asterion_found"] = {
        "label": "Asterion found",
        "phase": "late_game",
        "check": lambda: bool(getattr(renpy.store, "asterion_found", None)),
    }

    _g["asterion_found_burnt"] = {
        "label": "Asterion found (burnt)",
        "phase": "late_game",
        "check": lambda: bool(getattr(renpy.store, "asterion_found_burnt", None)),
    }

    _g["hovlavan_arrival"] = {
        "label": "Hovlavan arrival",
        "phase": "late_game",
        "check": lambda: getattr(renpy.store, "quest_pc_goal", 0) == 2,
    }

    # -------------------------------------------------------------------------
    # Phase: endgame (terminal nodes)
    # -------------------------------------------------------------------------

    _g["ending_success1"] = {
        "label": "Ending: Success 1",
        "phase": "endgame",
        "check": lambda: getattr(renpy.store, "quest_explorepeninsula_result", None) == "success1",
        "terminal": True,
    }

    _g["ending_success2"] = {
        "label": "Ending: Success 2",
        "phase": "endgame",
        "check": lambda: getattr(renpy.store, "quest_explorepeninsula_result", None) == "success2",
        "terminal": True,
    }

    _g["ending_success3"] = {
        "label": "Ending: Success 3",
        "phase": "endgame",
        "check": lambda: getattr(renpy.store, "quest_explorepeninsula_result", None) == "success3",
        "terminal": True,
    }

    _g["ending_fail1"] = {
        "label": "Ending: Failure 1",
        "phase": "endgame",
        "check": lambda: getattr(renpy.store, "quest_explorepeninsula_result", None) == "fail1",
        "terminal": True,
    }

    _g["ending_fail2"] = {
        "label": "Ending: Failure 2",
        "phase": "endgame",
        "check": lambda: getattr(renpy.store, "quest_explorepeninsula_result", None) == "fail2",
        "terminal": True,
    }

    _g["ending_pc_dead"] = {
        "label": "Ending: Player character dead",
        "phase": "endgame",
        "check": lambda: bool(getattr(renpy.store, "pc_dead", None)),
        "terminal": True,
    }

    # -------------------------------------------------------------------------
    # Register the graph with the vnflight shim.
    # -------------------------------------------------------------------------

    _vnf_set_progress_graph(_g)

    def _rw_progress_thread(node_name):
        if node_name.startswith("ending_"):
            return "game"
        if node_name.startswith("quest_ruins_"):
            return "quest_ruins"
        if node_name.startswith("quest_"):
            parts = node_name.split("_")
            if len(parts) >= 3:
                return "quest_" + parts[1]
            return node_name
        if node_name.startswith("highisland"):
            return "highisland"
        if node_name.endswith("_firsttime") or node_name.endswith("_unlocked"):
            return "exploration"
        return "main"

    for _node_name, _node in _vnf_progress_graph.items():
        _node["thread"] = _rw_progress_thread(_node_name)
        _node["phase"] = _node.get("phase", "unknown")
        if _node_name.startswith("ending_"):
            _node["terminal"] = True
            _node["game_terminal"] = True
        elif (
            _node_name.startswith("quest_")
            and (
                _node_name.endswith("_complete")
                or _node_name.startswith("quest_ruins_thais_")
            )
        ):
            _node["terminal"] = True
            _node["game_terminal"] = False
        elif _node["thread"] == "exploration":
            # First-visit / unlock nodes are one-shot milestones. They should
            # not remain active forever, but they also do not end the game.
            _node["terminal"] = True
            _node["game_terminal"] = False

    for _node_name, _node in _vnf_progress_graph.items():
        if _node_name.endswith("_started"):
            _complete = _node_name[:-8] + "_complete"
            if _complete in _vnf_progress_graph:
                _node["next"] = [_complete]

    if "start" in _vnf_progress_graph:
        _vnf_progress_graph["start"]["next"] = ["prologue_complete"]
    if "prologue_complete" in _vnf_progress_graph:
        _vnf_progress_graph["prologue_complete"]["next"] = [
            "militarycamp_firsttime",
            "southerncrossroads_unlocked",
        ]

    # -------------------------------------------------------------------------
    # Hidden stats checker -- internal game state not shown on the character
    # sheet.  Called by the supervisor / progress tools, NOT by the bridge's
    # periodic stat scrape.
    #
    # Returns a dict with sections: quest_state, npc_relationships,
    # unlocked_areas, internal_counters, story_flags.
    # -------------------------------------------------------------------------

    def _rw_hidden_stats():
        """Return hidden game-state variables for supervisor / progress use.

        Everything here is internal -- the player would NOT see these values
        on the character sheet or HUD.  The function is safe to call at any
        time; missing variables silently default.
        """
        out = {}

        # -- Quest state variables (0=not started, 1=started, 2=complete) ----
        quest_vars = [
            "quest_ruins",
            "quest_asterion",
            "quest_spyonwhitemarshes",
            "quest_runaway",
            "quest_easternpath",
            "quest_missinghunters",
            "quest_matchmaking",
            "quest_intelforpeltnorth",
            "quest_pc_goal",
            "quest_explorepeninsula_result",
            "quest_ruins_choice",
        ]
        quest_state = {}
        for qv in quest_vars:
            val = getattr(renpy.store, qv, None)
            if val is not None:
                quest_state[qv] = val

        # Quest sub-flags (booleans)
        quest_flags = [
            "elah_quest_easternpath_lumberjacks",
            "elah_quest_easternpath_hint1",
            "elah_quest_easternpath_hint2",
            "elah_quest_easternpath_lies",
            "elah_quest_easternpath_reward",
            "foggy_quest_iason_trade",
            "foggy_quest_whitemarshes_details",
            "akakios_quest_healingpotion_generic",
        ]
        for flag in quest_flags:
            val = getattr(renpy.store, flag, None)
            if val is not None and val:
                quest_state[flag] = val

        if quest_state:
            out["quest_state"] = quest_state

        # -- NPC relationships (friendship counters) -------------------------
        npc_relationships = {
            "elah": "elah_friendship",
            "efren": "efren_friendship",
            "eudocia": "eudocia_friendship",
            "galerocks_navica": "galerocks_navica_friendship",
            "galerocks_photios": "galerocks_photios_friendship",
            "glaucia": "glaucia_friendship",
            "oldhava": "oldhava_friendship",
            "orentius": "orentius_friendship",
            "pyrrhos": "pyrrhos_friendship",
            "quintus": "quintus_friendship",
            "severina": "severina_friendship",
            "thais": "thais_friendship",
            "iason": "iason_friendship",
            "tulia": "tulia_friendship",
            "foragers": "foragers_friendship",
            "foragers_caius": "foragers_caius_friendship",
            "druidcave_druid": "druidcave_druid_friendship",
            "foggy": "foggy_friendship",
            "akakios": "howlersdell_akakios_friendship",
            "elpis": "howlersdell_elpis_friendship",
            "sailor": "howlersdell_sailor_friendship",
            "aegidia": "aegidia_friendship",
        }
        rels = {}
        for npc_name, var_name in npc_relationships.items():
            value = getattr(renpy.store, var_name, None)
            if value is not None:
                rels[npc_name] = value
        if rels:
            out["npc_relationships"] = rels

        # -- Area unlock flags -----------------------------------------------
        unlocked_areas = [
            "peltnorth_unlocked",
            "prologuemilitarycamp_unlocked",
            "southerncrossroads_unlocked",
            "ruinedvillage_unlocked",
            "beholder_unlocked",
            "howlersdell_unlocked",
            "druidcave_unlocked",
            "rockslide_unlocked",
            "westerncrossroads_unlocked",
            "westgate_unlocked",
            "fishinghamlet_unlocked",
            "oldpagos_unlocked",
            "monastery_unlocked",
            "ford_unlocked",
            "bogentrance_unlocked",
            "bogcrossroads_unlocked",
            "bogroad_unlocked",
            "peatfield_unlocked",
            "vines_unlocked",
            "whitemarshes_unlocked",
            "ruinedshelter_unlocked",
            "northernroad_unlocked",
            "howlerslair_unlocked",
            "oldtunnel_unlocked",
            "galerocks_unlocked",
            "beach_unlocked",
            "dolmen_unlocked",
            "fallentree_unlocked",
            "watchtower_unlocked",
            "eudociahouse_unlocked",
            "stonebridge_unlocked",
            "stonesign_unlocked",
            "huntercabin_unlocked",
            "ghoulcave_unlocked",
            "giantstatue_unlocked",
            "mountainroad_unlocked",
            "greenmountaintribe_unlocked",
            "foragingground_unlocked",
            "wanderer_unlocked",
            "foggylake_unlocked",
            "creeks_unlocked",
        ]
        areas = {}
        for area in unlocked_areas:
            val = getattr(renpy.store, area, None)
            if val is not None and val == 1:
                areas[area] = True
        if areas:
            out["unlocked_areas"] = areas
            out["unlocked_areas_count"] = len(areas)

        # -- First-visit trackers --------------------------------------------
        first_visit_flags = [
            "peltnorth_firsttime",
            "creeks_firsttime",
            "galerocks_firsttime",
            "banditshideout_firsttime",
            "howlersdell_firsttime",
            "ruinedvillage_firsttime",
            "oldpagos_firsttime",
            "monastery_firsttime",
            "watchtower_firsttime",
            "ghoulcave_firsttime",
            "foggylake_firsttime",
            "militarycamp_destroyed_firsttime",
            "travel_firsttime",
        ]
        visits = {}
        for flag in first_visit_flags:
            val = getattr(renpy.store, flag, None)
            if val is not None:
                visits[flag] = val
        if visits:
            out["first_visits"] = visits

        # -- Internal story flags --------------------------------------------
        story_flags = [
            "orentius_banished",
            "orentius_convinced",
            "whitemarshes_destroyed",
            "asterion_found",
            "asterion_found_burnt",
            "highisland_journey_inprogress",
            "highisland_mode",
            "pc_dead",
            "pc_home_druid",
        ]
        story = {}
        for flag in story_flags:
            val = getattr(renpy.store, flag, None)
            if val is not None:
                story[flag] = val
        if story:
            out["story_flags"] = story

        # -- Internal counters / hidden stats --------------------------------
        counter_vars = [
            ("pc_battlecounter", None),
            ("pc_gamblingxp", None),
            ("pc_gamblingxp_scholarbonus", None),
            ("pc_lies", None),
            ("pc_faithpoints", None),
            ("pc_faithpoints_opportunities", None),
            ("pc_goal_iwanttohelppoints", None),
            ("pc_goal_iwanttoberememberedpoints", None),
            ("pc_goal_iwantstatuspoints", None),
            ("pc_goal_lost100coins", None),
            ("pc_hp_can5", None),
            ("appearance_charisma", None),
            ("appearance_price", None),
            ("pcname", None),
            ("horsename", None),
        ]
        counters = {}
        for var_name, default in counter_vars:
            val = getattr(renpy.store, var_name, default)
            if val is not None:
                counters[var_name] = val
        if counters:
            out["internal_counters"] = counters

        # -- Goal sub-flags (new-life tracking) ------------------------------
        goal_newlife_vars = [
            "pc_goal_iwantnewlife_howlersdell",
            "pc_goal_iwantnewlife_creeks",
            "pc_goal_iwantnewlife_monastery",
            "pc_goal_iwantnewlife_monastery_rejected",
            "pc_goal_iwantnewlife_monastery_discarded",
            "pc_goal_iwantnewlife_monastery_about",
            "pc_goal_iwantnewlife_monastery_about2",
            "pc_goal_iwantnewlife_bandits",
            "pc_goal_iwantnewlife_galerocks",
        ]
        goal_flags = {}
        for var_name in goal_newlife_vars:
            val = getattr(renpy.store, var_name, None)
            if val is not None:
                goal_flags[var_name] = val
        if goal_flags:
            out["goal_flags"] = goal_flags

        # -- Weather (internal) ----------------------------------------------
        weather_vars = [
            "weather",
            "weathermud",
            "weatherfogtotalcounter",
            "weatherfog",
        ]
        weather = {}
        for var_name in weather_vars:
            val = getattr(renpy.store, var_name, None)
            if val is not None:
                weather[var_name] = val
        if weather:
            out["weather"] = weather

        # -- Time internals --------------------------------------------------
        time_vars = [
            "dayclock",
            "quarters",
            "total_hours",
            "minutes",
        ]
        time_internals = {}
        for var_name in time_vars:
            val = getattr(renpy.store, var_name, None)
            if val is not None:
                time_internals[var_name] = val
        if time_internals:
            out["time_internals"] = time_internals

        # -- UI state flags --------------------------------------------------
        ui_flags = [
            "isinventory",
            "isjournal",
            "ischaractersheet",
            "game_menu_screen",
        ]
        ui = {}
        for flag in ui_flags:
            val = getattr(renpy.store, flag, None)
            if val is not None:
                ui[flag] = val
        if ui:
            out["ui_state"] = ui

        return out

    _vnf_add_progress_checker(_rw_hidden_stats)

    # -------------------------------------------------------------------------
    # Run chronicle — VIEWER-ONLY sections of the progress payload.
    #
    # Two audiences, one tool surface (design settled 2026-08-19): the agent
    # gets only the transient at-unlock line (achievement.grant hook in
    # roadwarden.rpy); viewers get this chronicle — quests/milestones and
    # achievements IN FIRST-SEEN ORDER with in-game day stamps — through the
    # progress payload for the dashboard, timeline widget, and the publishing
    # pipeline (auto-chapter markers for VODs).
    #
    # The "_chronicle" key is underscore-prefixed ON PURPOSE:
    # strip_internal_result_fields() removes underscore keys from all
    # agent-facing MCP output, while raw bridge consumers (hub, dashboard)
    # see the full payload. No new tools, no restarts.
    #
    # Day stamps are sampled on every scrape,
    # not at progress-call time, so a milestone crossed on day 12 is stamped
    # day 12 even if nobody polls progress until day 30.
    # -------------------------------------------------------------------------

    import time as _rw_time

    _vnf_rw_chronicle = {
        "milestones": [],    # graph nodes, first-seen order
        "achievements": [],  # from the achievement.grant hook
    }
    _vnf_rw_chronicle_seen = set()
    _vnf_rw_chronicle_last_day = [None]

    def _vnf_rw_chronicle_node_order():
        """Stable topological order for milestones first observed together."""
        _order = []
        _remaining = set(_vnf_progress_graph.keys())
        _incoming = dict((_name, 0) for _name in _remaining)
        for _node in _vnf_progress_graph.values():
            for _next in (_node.get("next") or []):
                if _next in _incoming:
                    _incoming[_next] += 1
        while _remaining:
            _ready = sorted(
                _name for _name in _remaining if _incoming[_name] == 0)
            if not _ready:
                # A malformed cycle should not make the chronicle disappear.
                _ready = [sorted(_remaining)[0]]
            for _name in _ready:
                _remaining.remove(_name)
                _order.append(_name)
                for _next in (
                        _vnf_progress_graph[_name].get("next") or []):
                    if _next in _remaining:
                        _incoming[_next] -= 1
        return _order

    _vnf_rw_chronicle_order = _vnf_rw_chronicle_node_order()

    def _vnf_rw_chronicle_day():
        try:
            return int(getattr(renpy.store, "day", 0) or 0)
        except Exception:
            return 0

    def _vnf_rw_chronicle_achievement(ach_id, label):
        """Record an achievement grant. Called by the grant hook."""
        _vnf_rw_chronicle_reset_if_rewound()
        _vnf_rw_chronicle["achievements"].append({
            "id": ach_id,
            "label": label,
            "day": _vnf_rw_chronicle_day(),
            "at": _rw_time.time(),
        })

    def _vnf_rw_chronicle_reset_if_rewound():
        """A day rollback starts a new/loaded timeline in this process."""
        _day = _vnf_rw_chronicle_day()
        _previous = _vnf_rw_chronicle_last_day[0]
        if _previous is not None and _day < _previous:
            _vnf_rw_chronicle["milestones"][:] = []
            _vnf_rw_chronicle["achievements"][:] = []
            _vnf_rw_chronicle_seen.clear()
        _vnf_rw_chronicle_last_day[0] = _day
        return _day

    def _vnf_rw_chronicle_reset():
        _vnf_rw_chronicle["milestones"][:] = []
        _vnf_rw_chronicle["achievements"][:] = []
        _vnf_rw_chronicle_seen.clear()
        _vnf_rw_chronicle_last_day[0] = _vnf_rw_chronicle_day()

    def _vnf_rw_chronicle_on_label(label_name, abnormal=False):
        # A second New Game in the same Ren'Py process may start on the same
        # day as an abandoned run, so day rollback alone cannot identify it.
        if label_name == "start":
            _vnf_rw_chronicle_reset()

    if hasattr(renpy.config, "label_callbacks"):
        if _vnf_rw_chronicle_on_label not in renpy.config.label_callbacks:
            renpy.config.label_callbacks.append(_vnf_rw_chronicle_on_label)

    def _vnf_rw_chronicle_sample(force=False):
        """Record newly-crossed progress-graph nodes with day stamps."""
        now = _rw_time.time()
        _day = _vnf_rw_chronicle_reset_if_rewound()
        for _name in _vnf_rw_chronicle_order:
            _node = _vnf_progress_graph[_name]
            if _name in _vnf_rw_chronicle_seen:
                continue
            _chk = _node.get("check")
            _hit = False
            if _chk is not None:
                try:
                    _hit = bool(_chk())
                except Exception:
                    _hit = False
            if _hit:
                _vnf_rw_chronicle_seen.add(_name)
                _vnf_rw_chronicle["milestones"].append({
                    "node": _name,
                    "label": _node.get("label", _name),
                    "thread": _node.get("thread", "main"),
                    "phase": _node.get("phase"),
                    "day": _day,
                    "at": now,
                })

    def _vnf_rw_chronicle_transform(per_screen):
        # Piggyback on the scrape loop. The core already controls scrape
        # cadence, so another wall-clock throttle only loses fast/turbo beats.
        try:
            _vnf_rw_chronicle_sample()
        except Exception:
            pass
        return per_screen

    _vnf_add_screen_transform(_vnf_rw_chronicle_transform, priority=99)

    def _vnf_rw_chronicle_checker():
        """Progress checker: viewer-only chronicle under an internal key."""
        _vnf_rw_chronicle_sample(force=True)
        return {"_chronicle": {
            "milestones": list(_vnf_rw_chronicle["milestones"]),
            "achievements": list(_vnf_rw_chronicle["achievements"]),
        }}

    _vnf_add_progress_checker(_vnf_rw_chronicle_checker)
