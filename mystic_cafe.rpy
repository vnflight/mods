################################################################################
## Progress Tracking for Mystic Café
##
## Passive checker reads game variables (trust, kindness, etc.)
## Active tracker uses label history to map story progression.
## Interpreter combines both into a progress report with game-end detection.
##
## Runs at init -989 (after vnflight.rpy at init -990).
################################################################################

init -989 python:

    # -------------------------------------------------------------------------
    # Passive checker: read game variables
    # -------------------------------------------------------------------------

    def _mystic_cafe_check_state():
        """Read Mystic Café game variables and return current state."""
        return {
            "trust": getattr(renpy.store, "trust", 0),
            "curiosity": getattr(renpy.store, "curiosity", 0),
            "kindness": getattr(renpy.store, "kindness", 0),
            "has_locket": getattr(renpy.store, "has_locket", False),
            "knows_secret": getattr(renpy.store, "knows_secret", False),
            "helped_old_man": getattr(renpy.store, "helped_old_man", False),
            "player_name": getattr(renpy.store, "player_name", "Alex"),
        }

    _vnf_add_progress_checker(_mystic_cafe_check_state)

    # -------------------------------------------------------------------------
    # Interpreter: combine passive + active into progress report
    # -------------------------------------------------------------------------

    # Story beat mapping: label -> human-readable description.
    _MYSTIC_CAFE_BEATS = {
        "start": "Game started",
        "keep_walking": "Walked past the café",
        "peek_window": "Peered through the window",
        "enter_cafe": "Entered the café",
        "help_old_man": "Helped the old man",
        "after_old_man": "After the old man left",
        "garden_path": "Chose the silver key (Garden of Memories)",
        "garden_sit": "Sat beside younger self",
        "garden_watch": "Watched from a distance",
        "garden_return": "Returned from the garden",
        "room_path": "Chose the gold key (Room of Possibilities)",
        "orb_bright": "Reached for the brightest orb",
        "orb_flickering": "Reached for the flickering orb",
        "orb_dim": "Reached for the dim orb",
        "room_return": "Returned from the room",
        "stay_path": "Chose to stay in the café",
        "finale": "The finale",
        "ending_true": "Ending: A Place to Belong (True Ending)",
        "ending_locket": "Ending: The Locket's Light",
        "ending_friend": "Ending: A Passing Warmth",
        "ending_seeker": "Ending: The Seeker's Path",
        "ending_wanderer": "Ending: The Road Not Taken",
    }

    _MYSTIC_CAFE_ENDINGS = {
        "ending_true", "ending_locket", "ending_friend",
        "ending_seeker", "ending_wanderer",
    }

    # -------------------------------------------------------------------------
    # Progress graph: nodes and edges
    # -------------------------------------------------------------------------

    _vnf_set_progress_graph({
        "start":          {"next": ["keep_walking", "peek_window", "enter_cafe"],
                           "label": "Game started"},
        "keep_walking":   {"next": ["ending_wanderer"],
                           "label": "Walked past the café", "terminal": False},
        "peek_window":    {"next": ["enter_cafe"],
                           "label": "Peered through the window"},
        "enter_cafe":     {"next": ["help_old_man", "after_old_man"],
                           "label": "Entered the café"},
        "help_old_man":   {"next": ["after_old_man"],
                           "label": "Helped the old man"},
        "after_old_man":  {"next": ["garden_path", "room_path", "stay_path"],
                           "label": "After the old man left"},
        "garden_path":    {"next": ["garden_sit", "garden_watch"],
                           "label": "Chose the silver key"},
        "garden_sit":     {"next": ["garden_return"],
                           "label": "Sat beside younger self"},
        "garden_watch":   {"next": ["garden_return"],
                           "label": "Watched from a distance"},
        "garden_return":  {"next": ["finale"],
                           "label": "Returned from the garden"},
        "room_path":      {"next": ["orb_bright", "orb_flickering", "orb_dim"],
                           "label": "Chose the gold key"},
        "orb_bright":     {"next": ["room_return"],
                           "label": "Reached for the brightest orb"},
        "orb_flickering": {"next": ["room_return"],
                           "label": "Reached for the flickering orb"},
        "orb_dim":        {"next": ["room_return"],
                           "label": "Reached for the dim orb"},
        "room_return":    {"next": ["finale"],
                           "label": "Returned from the room"},
        "stay_path":      {"next": ["finale"],
                           "label": "Chose to stay in the café"},
        "finale":         {"next": ["ending_true", "ending_locket", "ending_friend",
                                    "ending_seeker", "ending_wanderer"],
                           "label": "The finale"},
        "ending_true":    {"next": [], "terminal": True,
                           "label": "Ending: A Place to Belong (True Ending)"},
        "ending_locket":  {"next": [], "terminal": True,
                           "label": "Ending: The Locket's Light"},
        "ending_friend":  {"next": [], "terminal": True,
                           "label": "Ending: A Passing Warmth"},
        "ending_seeker":  {"next": [], "terminal": True,
                           "label": "Ending: The Seeker's Path"},
        "ending_wanderer":{"next": [], "terminal": True,
                           "label": "Ending: The Road Not Taken"},
    })

    # Story phases for grouping.
    _MYSTIC_CAFE_PHASES = {
        "start": "arrival",
        "keep_walking": "departure",
        "peek_window": "arrival",
        "enter_cafe": "café",
        "help_old_man": "café",
        "after_old_man": "café",
        "garden_path": "garden",
        "garden_sit": "garden",
        "garden_watch": "garden",
        "garden_return": "garden",
        "room_path": "room",
        "orb_bright": "room",
        "orb_flickering": "room",
        "orb_dim": "room",
        "room_return": "room",
        "stay_path": "stay",
        "finale": "finale",
        "ending_true": "ending",
        "ending_locket": "ending",
        "ending_friend": "ending",
        "ending_seeker": "ending",
        "ending_wanderer": "ending",
    }

    for _node_name, _node in _vnf_progress_graph.items():
        _node["thread"] = "main"
        _node["phase"] = _MYSTIC_CAFE_PHASES.get(_node_name, "unknown")
        if _node_name in _MYSTIC_CAFE_ENDINGS:
            _node["terminal"] = True
            _node["game_terminal"] = True

    def _mystic_cafe_interpret(passive_results, label_history, graph_state=None):
        """Combine passive state + label history + graph into a progress report."""
        state = passive_results[0] if passive_results else {}

        # Extract story labels (filter system/internal).
        story_labels = []
        for label, ts in label_history:
            if label in _MYSTIC_CAFE_BEATS:
                story_labels.append(label)

        # Current position is derived only for display. The canonical
        # progress model is graph_state["nodes"] + graph_state["threads"].
        current_label = story_labels[-1] if story_labels else "start"
        current_phase = _MYSTIC_CAFE_PHASES.get(current_label, "unknown")

        # Path taken (unique beats in order).
        seen = set()
        path = []
        for label in story_labels:
            if label not in seen:
                seen.add(label)
                path.append(_MYSTIC_CAFE_BEATS.get(label, label))

        # Key choices made.
        choices = {}
        if "keep_walking" in seen:
            choices["café_entrance"] = "walked_past"
        elif "peek_window" in seen:
            choices["café_entrance"] = "peeked"
        elif "enter_cafe" in seen:
            choices["café_entrance"] = "entered"

        if "garden_path" in seen:
            choices["key"] = "silver"
        elif "room_path" in seen:
            choices["key"] = "gold"
        elif "stay_path" in seen:
            choices["key"] = "stayed"

        if "orb_bright" in seen:
            choices["orb"] = "bright"
        elif "orb_flickering" in seen:
            choices["orb"] = "flickering"
        elif "orb_dim" in seen:
            choices["orb"] = "dim"

        if "garden_sit" in seen:
            choices["garden_choice"] = "sat_beside"
        elif "garden_watch" in seen:
            choices["garden_choice"] = "watched"

        # Terminal detection.
        game_terminal = bool(seen & _MYSTIC_CAFE_ENDINGS)
        ending = None
        for label in reversed(story_labels):
            if label in _MYSTIC_CAFE_ENDINGS:
                ending = _MYSTIC_CAFE_BEATS[label]
                break

        # Merge graph data if available.
        nodes = {}
        threads = {}
        available_next = []
        completion = 0.0
        if graph_state:
            nodes = graph_state.get("nodes", {})
            threads = graph_state.get("threads", {})
            available_next = graph_state.get("available_next", [])
            completion = graph_state.get("completion", 0.0)
            # Latch: once an ending label has been seen (or the graph reports
            # terminal), stay terminal. Don't let a later sample at a non-
            # terminal node (e.g. back at the main menu after the ending)
            # override the cumulative signal back to False.
            game_terminal = game_terminal or bool(graph_state.get("game_terminal", False))

        return {
            "game": "mystic_cafe",
            "phase": current_phase,
            "nodes": nodes,
            "threads": threads,
            "path": path,
            "choices": choices,
            "stats": state,
            "ending": ending,
            "game_terminal": game_terminal,
            "terminal": game_terminal,
            "available_next": available_next,
            "completion": completion,
        }

    _vnf_set_progress_interpreter(_mystic_cafe_interpret)
