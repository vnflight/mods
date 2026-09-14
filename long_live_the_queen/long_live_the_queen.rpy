## Long Live the Queen helpers for vnflight.
##
## Keep this file runtime-driven.  The initial transforms are based on bridge
## screen/action metadata, not game source inspection.

init -989 python:

    def _vnf_lltq_action_field(action_str):
        """Extract a SetField field name from a rendered action string."""
        if "field=" not in action_str:
            return None
        raw = action_str.split("field=", 1)[1]
        return raw.split()[0].strip()

    def _vnf_lltq_action_value(action_str):
        """Extract a SetField value from a rendered action string."""
        if "value=" not in action_str:
            return None
        raw = action_str.split("value=", 1)[1]
        return raw.strip()

    def _vnf_lltq_class_choice_context(action_strs):
        """Return label prefix/category implied by LLtQ class chooser actions."""
        for action_str in action_strs:
            field = _vnf_lltq_action_field(action_str)
            if field == "current_morning_activity_group":
                return ("Morning category", "lltq_morning_groups", field,
                        _vnf_lltq_action_value(action_str))
            if field == "current_evening_activity_group":
                return ("Evening category", "lltq_evening_groups", field,
                        _vnf_lltq_action_value(action_str))
            if field == "current_morning_activity":
                return ("Morning", "lltq_morning_classes", field,
                        _vnf_lltq_action_value(action_str))
            if field == "current_evening_activity":
                return ("Evening", "lltq_evening_classes", field,
                        _vnf_lltq_action_value(action_str))
        return None

    def _vnf_lltq_class_choice_prefix(action_strs):
        context = _vnf_lltq_class_choice_context(action_strs)
        return context[0] if context else None

    def _vnf_lltq_class_choice_is_active(field, label, value):
        active_value = value if value is not None else label
        current = getattr(renpy.store, field, None)
        if active_value is not None and str(current) == str(active_value):
            return True
        if field.startswith("current_morning_"):
            lesson = _vnf_lltq_current_lesson("morning")
        elif field.startswith("current_evening_"):
            lesson = _vnf_lltq_current_lesson("evening")
        else:
            return False
        if field.endswith("_group"):
            return lesson == "not selected (category: {})".format(label)
        return lesson == label

    def _vnf_lltq_jump_label(action_str):
        """Extract a Jump label from a rendered action string."""
        if "Jump label=" not in action_str:
            return None
        raw = action_str.split("Jump label=", 1)[1]
        return raw.split()[0].strip()

    _VNF_LLTQ_SIDEBAR_LABELS = {
        "skills_page": "Skills",
        "mood_page": "Mood",
        "room_nofade_page": "Room",
        "outfit_page": "Outfit",
        "outfit_nofade_page": "Outfit",
        "schedule_page": "Classes",
        "log_page": "Log",
    }

    def _vnf_lltq_sidebar_label(action_strs, label):
        """Return the destination label for an LLtQ sidebar button."""
        for action_str in action_strs:
            jump_label = _vnf_lltq_jump_label(action_str)
            mapped = _VNF_LLTQ_SIDEBAR_LABELS.get(jump_label)
            if mapped:
                return mapped
        if label == "[unlabelled]" and "function" in action_strs:
            return "Menu"
        return None

    def _vnf_lltq_label_sidebar(per_screen):
        """Label LLtQ sidebar buttons by destination rather than current text."""
        for scr in per_screen:
            if scr.get("_tag") != "sidebar":
                continue
            for btn in scr.get("buttons", []):
                btn["_category"] = "lltq_week_menu"
                label = btn.get("label", "")
                action_strs = btn.get("action_strs", [])
                mapped = _vnf_lltq_sidebar_label(action_strs, label)
                if not mapped or label == mapped:
                    continue
                btn["original_label"] = label
                btn["label"] = mapped
        return per_screen

    def _vnf_lltq_label_class_chooser(per_screen):
        """Disambiguate Morning/Evening class chooser buttons."""
        for scr in per_screen:
            if scr.get("_tag") != "class_chooser":
                continue
            for btn in scr.get("buttons", []):
                label = btn.get("label", "")
                if label == "Done":
                    # Confirming the week's classes runs script: the day
                    # plays out before the next decision.  _story_entry says
                    # so; _wait_after_action stays for the UI rebuild.
                    btn["_wait_after_action"] = True
                    btn["_story_entry"] = True
                    btn["_category"] = "lltq_ui"
                    continue
                if not label:
                    continue
                context = _vnf_lltq_class_choice_context(
                    btn.get("action_strs", []))
                if not context:
                    continue
                prefix, category, field, value = context
                btn["_category"] = category
                if _vnf_lltq_class_choice_is_active(field, label, value):
                    btn["annotation"] = "active"
                if label.startswith(prefix + ": "):
                    continue
                btn["original_label"] = label
                btn["label"] = "{}: {}".format(prefix, label)
        return per_screen

    _VNF_LLTQ_TUTORIAL_CHOICES = set([
        "Tell me more",
        "I've played this before",
    ])

    def _vnf_lltq_current_week():
        week = getattr(renpy.store, "weeknum_shown", None)
        if isinstance(week, (int, float)) and week >= 1:
            return week
        week = getattr(renpy.store, "week", None)
        try:
            if float(week) >= 1:
                return week
        except Exception:
            pass
        weeknum = getattr(renpy.store, "weeknum", None)
        if isinstance(weeknum, (int, float)):
            return weeknum + 1
        return None

    def _vnf_lltq_is_late_week():
        try:
            return float(_vnf_lltq_current_week()) > 1
        except Exception:
            return False

    _VNF_LLTQ_WEEKEND_MAP_LABELS = {
        "toys": "Play with Toys (+1 Yielding, +1 Lonely, +1 Cheerful)",
        "sneak": "Sneak Out (+2 Willful, +1 Lonely)",
        "garden": "Walk in the Gardens (+1 Lonely, +1 Cheerful)",
        "court": "Attend Court (+2 Yielding)",
        "treasury": "Visit Treasury (unknown effect)",
        "sports": "Play Sports (+1 Angry)",
        "barracks": "Tour Barracks (+1 Yielding, +1 Pressured)",
        "sabine": "Talk to Sabine (unknown effect)",
        "father": "Talk to Father (unknown effect)",
        "service": "Attend Service (-1 Depressed)",
        "tomb": "Visit Tomb (+1 Depressed, +1 Afraid)",
        "dungeons": "Visit Dungeons (No Effect)",
        "explore": "Explore Castle (+1 Lonely, +1 Afraid)",
        "ursul": "Visit Julianna of Ursul (unknown effect)",
        "charlotte": "Visit Charlotte, Lady Merva (unknown effect)",
    }

    def _vnf_lltq_partial_value(action_strs):
        for action_str in action_strs:
            if not action_str.startswith("Partial value="):
                continue
            return action_str.split("=", 1)[1].strip()
        return None

    def _vnf_lltq_label_weekend_map(per_screen):
        """Expose LLtQ weekend map mood effects from stable action values."""
        for scr in per_screen:
            has_map_actions = False
            for btn in scr.get("buttons", []):
                value = _vnf_lltq_partial_value(btn.get("action_strs", []))
                mapped = _VNF_LLTQ_WEEKEND_MAP_LABELS.get(value)
                if not mapped:
                    continue
                has_map_actions = True
                label = btn.get("label", "")
                if label == mapped:
                    continue
                btn["original_label"] = label
                btn["label"] = mapped
                btn["_category"] = "castle"
            if not has_map_actions:
                continue
            for btn in scr.get("buttons", []):
                label = btn.get("label", "")
                if label in ("Hide Tooltips", "Show Tooltips", "Mood"):
                    btn["_category"] = "options"
        return per_screen

    def _vnf_lltq_label_weekend_map_actions(actions, context):
        """Relabel fallback focus-list map actions after action collection."""
        has_map_actions = False
        for action in actions:
            value = _vnf_lltq_partial_value(action.get("action_strs", []))
            mapped = _VNF_LLTQ_WEEKEND_MAP_LABELS.get(value)
            if mapped:
                has_map_actions = True
                label = action.get("label", "")
                if label != mapped:
                    action["original_label"] = label
                    action["label"] = mapped
                action["_category"] = "castle"
        if not has_map_actions:
            return actions
        for action in actions:
            label = action.get("label", "")
            if label in ("Hide Tooltips", "Show Tooltips", "Mood"):
                action["_category"] = "options"
        return actions

    def _vnf_lltq_hide_intro_help_chrome(actions, context):
        """Hide LLtQ's tutorial help chrome when the actionable skip is present."""
        has_skip_ahead = any(
            action.get("source") == "button"
            and action.get("screen") == "_focus_list"
            and action.get("label") == "Skip Ahead"
            for action in actions
        )
        if not has_skip_ahead:
            return actions
        for action in actions:
            if (
                action.get("source") == "button"
                and action.get("screen") == "_focus_list"
                and action.get("label") == "?"
            ):
                action["hidden"] = True
        return actions

    def _vnf_lltq_hide_stale_skip_ahead(actions, context):
        """Hide stale intro skip chrome when a real non-tutorial choice is live."""
        choice_labels = set(context.get("choice_labels", []))
        late_week = _vnf_lltq_is_late_week()
        if (
            not choice_labels
            or choice_labels == _VNF_LLTQ_TUTORIAL_CHOICES
        ) and not late_week:
            return actions
        for action in actions:
            if action.get("label") == "Skip Ahead":
                action["hidden"] = True
                action["_suppress_pending_action"] = True
        return actions

    def _vnf_lltq_hide_stale_tutorial_choices(actions, context):
        """Hide tutorial choices once the live weekly UI is visible."""
        choice_labels = set(context.get("choice_labels", []))
        if choice_labels != _VNF_LLTQ_TUTORIAL_CHOICES:
            return actions
        live_screens = set([
            a.get("screen", "") for a in actions
            if a.get("source") == "button"
        ])
        if not live_screens.intersection(set(["sidebar", "class_chooser"])):
            return actions
        for action in actions:
            if (
                action.get("source") == "choice"
                and action.get("label") in _VNF_LLTQ_TUTORIAL_CHOICES
            ):
                action["hidden"] = True
        return actions

    def _vnf_lltq_clean_value(value):
        if value in (None, "", "None"):
            return None
        return str(value)

    def _vnf_lltq_current_lesson(period):
        activity = _vnf_lltq_clean_value(getattr(
            renpy.store, "current_{}_activity".format(period), None))
        group = _vnf_lltq_clean_value(getattr(
            renpy.store, "current_{}_activity_group".format(period), None))
        if activity:
            return activity
        if group:
            return "not selected (category: {})".format(group)
        return "not selected"

    def _vnf_lltq_skill_values():
        """Return visible LLtQ skill values keyed by readable skill name."""
        result = {}
        groups = [
            "social_skills",
            "intellectual_skills",
            "physical_skills",
            "mystical_skills",
        ]
        for group_name in groups:
            group = getattr(renpy.store, group_name, None)
            for subgroup in getattr(group, "groups", []) or []:
                for stat in getattr(subgroup, "stats", []) or []:
                    label = getattr(stat, "name", None)
                    varname = getattr(stat, "varname", None)
                    if not label or not varname:
                        continue
                    value = getattr(renpy.store, varname, None)
                    if isinstance(value, (int, float)):
                        result[str(label)] = value
        return result

    def _vnf_lltq_format_skill_value(value):
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if abs(value - round(value)) < 0.0001:
                return str(int(round(value)))
            return "{:.1f}".format(value)
        return str(value)

    def _vnf_lltq_state_stats():
        """Build a compact LLtQ state header from runtime store variables."""
        week = _vnf_lltq_current_week()
        mood = _vnf_lltq_clean_value(getattr(renpy.store, "mood", None))
        morning = _vnf_lltq_current_lesson("morning")
        evening = _vnf_lltq_current_lesson("evening")
        skills = _vnf_lltq_skill_values()
        trained = {
            name: value for name, value in skills.items()
            if isinstance(value, (int, float)) and value
        }
        top_skills = sorted(
            trained.items(), key=lambda item: (-item[1], item[0]))[:5]
        stats = {
            "week": week,
            "mood": mood,
            "morning": morning,
            "evening": evening,
            "trained_skills": len(trained),
        }
        if top_skills:
            stats["top_skills"] = ", ".join([
                "{} {}".format(name, _vnf_lltq_format_skill_value(value))
                for name, value in top_skills
            ])
        summary = (
            "Week {week} | Mood: {mood} | Morning: {morning} | "
            "Evening: {evening}"
        ).format(
            week=week if week is not None else "?",
            mood=mood or "unknown",
            morning=morning,
            evening=evening,
        )
        if top_skills:
            summary += " | Top skills: " + stats["top_skills"]
        screen_summary = _vnf_lltq_screen_summary()
        if screen_summary:
            summary += " | " + screen_summary
        stats["_summary"] = summary
        return stats

    _vnf_lltq_base_get_inventory_stats = _vnf_get_inventory_stats

    def _vnf_get_inventory_stats():
        inventory, stats = _vnf_lltq_base_get_inventory_stats()
        if not _vnf_is_mapping(stats):
            stats = {}
        stats.update(_vnf_lltq_state_stats())
        return inventory, stats

    def _vnf_lltq_progress():
        stats = _vnf_lltq_state_stats()
        return {
            "phase": "week_{}".format(stats.get("week") or "?"),
            "stats": stats,
        }

    def _vnf_lltq_skill_summary(limit=None):
        trained = [
            (name, value) for name, value in _vnf_lltq_skill_values().items()
            if isinstance(value, (int, float)) and value
        ]
        trained = sorted(trained, key=lambda item: (-item[1], item[0]))
        if limit:
            trained = trained[:limit]
        if not trained:
            return "No trained skills yet."
        return ", ".join([
            "{} {}".format(name, _vnf_lltq_format_skill_value(value))
            for name, value in trained
        ])

    def _vnf_lltq_mood_summary():
        mood = _vnf_lltq_clean_value(getattr(
            renpy.store, "mood", None)) or "unknown"
        willful = getattr(renpy.store, "willful", None)
        cheerful = getattr(renpy.store, "cheerfulness", None)
        parts = ["Mood screen: current mood is " + mood]
        if isinstance(willful, (int, float)) and isinstance(cheerful, (int, float)):
            parts.append("axes: Willful/Yielding {}, Cheerful/Depressed {}".format(
                _vnf_lltq_format_skill_value(willful),
                _vnf_lltq_format_skill_value(cheerful),
            ))
        bonuses = getattr(renpy.store, "mood_bonuses", {}) or {}
        penalties = getattr(renpy.store, "mood_penalties", {}) or {}
        bonus = bonuses.get(mood) or ()
        penalty = penalties.get(mood) or ()
        if bonus:
            parts.append("bonuses: " + ", ".join([str(item) for item in bonus]))
        if penalty:
            parts.append("penalties: " + ", ".join([str(item) for item in penalty]))
        return "; ".join(parts)

    def _vnf_lltq_screen_summary():
        """Return extra agent-facing state for graphical info screens."""
        try:
            get_screen = getattr(renpy, "get_screen", None)
            if not get_screen:
                return None
            if get_screen("stats"):
                return "Skills screen: " + _vnf_lltq_skill_summary()
            if get_screen("moods"):
                return _vnf_lltq_mood_summary()
        except Exception:
            pass
        return None

    def _vnf_lltq_original_label_aliases(interactions):
        for interaction in interactions:
            original = interaction.get("original_label")
            if not original:
                continue
            aliases = interaction.setdefault("aliases", [])
            if original not in aliases:
                aliases.append(original)
        return interactions

    _vnf_add_screen_transform(_vnf_lltq_label_sidebar, priority=9)
    _vnf_add_screen_transform(_vnf_lltq_label_class_chooser, priority=10)
    _vnf_add_screen_transform(_vnf_lltq_label_weekend_map, priority=11)
    _vnf_register_button_category("lltq_morning_groups", "MORNING CATEGORIES")
    _vnf_register_button_category("lltq_morning_classes", "MORNING CLASSES")
    _vnf_register_button_category("lltq_evening_groups", "EVENING CATEGORIES")
    _vnf_register_button_category("lltq_evening_classes", "EVENING CLASSES")
    _vnf_register_button_category("lltq_ui", "UI", compact=True)
    _vnf_register_button_category("lltq_week_menu", "WEEK MENU", compact=True)
    _vnf_register_button_category("castle", "CASTLE")
    _vnf_register_button_category("options", "OPTIONS")
    _vnf_add_alias_provider(_vnf_lltq_original_label_aliases, priority=50)
    _vnf_add_action_transform(_vnf_lltq_label_weekend_map_actions, priority=20)
    _vnf_add_action_transform(_vnf_lltq_hide_intro_help_chrome, priority=24)
    _vnf_add_action_transform(_vnf_lltq_hide_stale_skip_ahead, priority=24)
    _vnf_add_action_transform(_vnf_lltq_hide_stale_tutorial_choices, priority=25)
    _vnf_add_progress_checker(_vnf_lltq_progress)
