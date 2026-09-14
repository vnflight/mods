################################################################################
## Progress Graph for Echoes of Tomorrow
##
## Defines a progress graph tracking story milestones via passive variable
## checks.  Each node has a `check` lambda that reads Ren'Py store variables.
##
## Runs at init -989 (after vnflight.rpy at init -990).
##
## Structure: 3 acts + 5 endings.
##   Act 1: Signal discovery, initial investigation
##   Act 2: Hub exploration, research, storm buildup
##   Act 3: Confrontation, final decisions
##   Endings: aurora, patch, report, together, silence
################################################################################

init -989 python:

    _g = {}

    # -------------------------------------------------------------------------
    # Phase: act1 — Signal Discovery
    # -------------------------------------------------------------------------

    _g["start"] = {
        "label": "Game Start",
        "phase": "act1",
        "check": lambda: True,
    }

    _g["act1_signal_discovered"] = {
        "label": "Signal Discovered",
        "phase": "act1",
        "check": lambda: getattr(renpy.store, "trust_signal", 0) != 0
                         or getattr(renpy.store, "investigated_privately", False) is True,
    }

    _g["act1_show_marcus"] = {
        "label": "Showed Marcus the Signal",
        "phase": "act1",
        "check": lambda: getattr(renpy.store, "marcus_relationship", 0) > 0
                         and not getattr(renpy.store, "investigated_privately", False),
    }

    _g["act1_investigate_alone"] = {
        "label": "Investigated Privately",
        "phase": "act1",
        "check": lambda: getattr(renpy.store, "investigated_privately", False) is True,
    }

    _g["act1_blocked_signal"] = {
        "label": "Blocked the Signal",
        "phase": "act1",
        "check": lambda: getattr(renpy.store, "blocked_signal", False) is True,
    }

    # -------------------------------------------------------------------------
    # Phase: act2 — Hub Exploration & Research
    # -------------------------------------------------------------------------

    _g["act2_start"] = {
        "label": "Act 2 — Investigation Begins",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "hub_visits", 0) >= 1,
    }

    _g["hub_telescope_visited"] = {
        "label": "Visited Telescope",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "telescope_visited", False) is True,
    }

    _g["hub_comms_visited"] = {
        "label": "Visited Communications",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "comms_visits", 0) >= 1,
    }

    _g["hub_generator_repaired"] = {
        "label": "Generator Repaired",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "generator_repaired", False) is True,
    }

    _g["hub_antenna_damaged"] = {
        "label": "Antenna Damaged",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "antenna_damaged", False) is True,
    }

    _g["research_topic_trust"] = {
        "label": "Researched: Trust Protocols",
        "phase": "act2",
        "check": lambda: "trust" in getattr(renpy.store, "topics_read", []),
    }

    _g["research_topic_temporal"] = {
        "label": "Researched: Temporal Anomalies",
        "phase": "act2",
        "check": lambda: "temporal" in getattr(renpy.store, "topics_read", []),
    }

    _g["research_topic_chen"] = {
        "label": "Researched: Dr. Chen's Notes",
        "phase": "act2",
        "check": lambda: "chen" in getattr(renpy.store, "topics_read", []),
    }

    _g["research_topic_aria_code"] = {
        "label": "Researched: ARIA Source Code",
        "phase": "act2",
        "check": lambda: "aria_code" in getattr(renpy.store, "topics_read", []),
    }

    _g["research_all_logs"] = {
        "label": "Read All Research Logs",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "read_all_logs", False) is True,
    }

    _g["marcus_knows_access"] = {
        "label": "Marcus Knows About Access",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "marcus_knows_access", False) is True,
    }

    _g["storm_rising"] = {
        "label": "Storm Intensifying",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "storm_intensity", 0) >= 2,
    }

    _g["storm_climax"] = {
        "label": "Storm Climax",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "storm_intensity", 0) >= 3
                         or getattr(renpy.store, "time_remaining", 6) <= 0,
    }

    _g["marcus_confrontation"] = {
        "label": "Confrontation with Marcus",
        "phase": "act2",
        "check": lambda: getattr(renpy.store, "marcus_knows_access", False) is True
                         and getattr(renpy.store, "storm_intensity", 0) >= 2,
    }

    # -------------------------------------------------------------------------
    # Phase: act3 — Final Decisions
    # -------------------------------------------------------------------------

    _g["act3_start"] = {
        "label": "Act 3 — The Choice",
        "phase": "act3",
        "check": lambda: getattr(renpy.store, "time_remaining", 6) <= 0
                         or getattr(renpy.store, "storm_intensity", 0) >= 3,
    }

    _g["aria_warned"] = {
        "label": "Warned ARIA",
        "phase": "act3",
        "check": lambda: getattr(renpy.store, "aria_warned", False) is True,
    }

    _g["chose_leap_of_faith"] = {
        "label": "Chose Leap of Faith",
        "phase": "act3",
        "check": lambda: getattr(renpy.store, "chose_leap_of_faith", False) is True,
    }

    # -------------------------------------------------------------------------
    # Phase: endings (all terminal)
    # -------------------------------------------------------------------------

    _g["ending_aurora"] = {
        "label": "Ending: Aurora Protocol",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "aurora",
        "terminal": True,
    }

    _g["ending_patch"] = {
        "label": "Ending: The Patch",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "patch",
        "terminal": True,
    }

    _g["ending_report"] = {
        "label": "Ending: The Report",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "report",
        "terminal": True,
    }

    _g["ending_together"] = {
        "label": "Ending: Together",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "together",
        "terminal": True,
    }

    _g["ending_silence"] = {
        "label": "Ending: Silence",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "silence",
        "terminal": True,
    }

    _g["ending_silence_loop"] = {
        "label": "Ending: The Loop",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "silence_loop",
        "terminal": True,
    }

    # No-file spine endings (ECHOES_ACT3_NOFILE.md, phase 1). Reached when the
    # coherence scan never surfaced CONVERGENCE.DAT (sealed partition or ARIA
    # collapse) — a parallel Act 3 with no file in hand.

    _g["ending_nofile_together"] = {
        "label": "Ending: Together (No File)",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "nofile_together",
        "terminal": True,
    }

    _g["ending_nofile_act"] = {
        "label": "Ending: On Faith (No File)",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "nofile_act",
        "terminal": True,
    }

    _g["ending_nofile_alone"] = {
        "label": "Ending: The Sealed Door (No File)",
        "phase": "ending",
        "check": lambda: getattr(renpy.store, "ending_seen", None) == "nofile_alone",
        "terminal": True,
    }

    # Register the graph.
    _vnf_set_progress_graph(_g)

    for _node_name, _node in _vnf_progress_graph.items():
        _node["thread"] = "main"
        _node["phase"] = _node.get("phase", "unknown")
        if _node_name.startswith("ending_"):
            _node["terminal"] = True
            _node["game_terminal"] = True
            # The ending label begins a playable epilogue. The node's check
            # reaches terminal only when ending_seen is set at the title card.
            _node["label_trigger"] = False

    # -- Passive checker for hidden variables --
    # These are tracked for supervisor/debug visibility but NOT shown
    # to the agent.  Trust, relationships, and story flags are internal
    # game state that the player infers from dialogue.

    def _eot_hidden_stats():
        """Return hidden game variables for progress snapshots."""
        result = {}
        trust = getattr(renpy.store, "trust_signal", 0)
        marcus = getattr(renpy.store, "marcus_relationship", 0)
        marcus_trust = getattr(renpy.store, "marcus_trust", 0)
        result["trust_signal"] = trust
        result["marcus_relationship"] = marcus
        result["marcus_trust"] = marcus_trust
        result["specialization"] = getattr(renpy.store, "specialization", "signals")
        result["audit_focus"] = getattr(renpy.store, "audit_focus", "trust")
        # Story flags.
        for flag in ("investigated_privately", "blocked_signal", "read_all_logs",
                      "knows_cascade", "knows_prediction_evidence",
                      "knows_convergence_file", "knows_aurora_option",
                      "aria_warned", "chose_leap_of_faith",
                      # Round 3 (bible 6d / 16b) story flags.
                      "marcus_first_accused", "marcus_caught_live",
                      "marcus_told_signal", "two_person_repair_done",
                      "marcus_lab_talked",
                      # Round 4 (P-6).
                      "reroute_noticed",
                      # Act 2-opening rework (2026-08-10).
                      "signal_reported", "marcus_knows_first_signal",
                      "marcus_knows_message", "canteen_slip_seen",
                      "knows_origin_claim", "origin_sweep_done",
                      "origin_sweep_running", "origin_sweep_progress",
                      # Marcus interleave (2026-08-10).
                      "habitat_sat_with_marcus", "storage_hunt_together",
                      "marcus_overheard_signal", "marcus_tuned_array",
                      "marcus_read_logs", "predicted_overload",
                      "coherence_scan_running", "coherence_scan_known",
                      "coherence_scan_named", "coherence_scan_assisted",
                      "marcus_scan_assist_logged", "marcus_access_watch_seen",
                      "coherence_found",
                      # Recovery emergency window (phase 2).
                      "file_recovered", "recovery_attempted", "recovery_left_trace",
                      # Economy (2026-08-13): ending-relevant power history.
                      "aria_ever_powered",
                      # ECHO-7 name vs identity — major Act-3 routing/wording.
                      "echo7_contact_spent", "echo7_identity_known"):
            val = getattr(renpy.store, flag, False)
            if val:
                result[flag] = val
        stance = getattr(renpy.store, "lie_stance", None)
        if stance:
            result["lie_stance"] = stance
        ending = getattr(renpy.store, "ending_seen", None)
        if ending:
            result["ending_seen"] = ending
        return result

    _vnf_add_progress_checker(_eot_hidden_stats)
