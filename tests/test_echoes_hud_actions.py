"""The screen-only pass must not erase live-menu HUD controls."""
from pathlib import Path
import textwrap


def test_hud_controls_survive_both_passes_only_during_menu():
    source = (Path(__file__).resolve().parents[1] / "echoes_of_tomorrow" / "echoes_of_tomorrow.rpy").read_text(encoding="utf-8")
    start = source.index("    def _vnf_eot_hud_actions_at_decisions(")
    end = source.index("    _vnf_add_action_transform(", start)
    menu = [None]
    namespace = {"_vnf_current_menu_context": menu}
    exec(textwrap.dedent(source[start:end]), namespace)
    transform = namespace["_vnf_eot_hud_actions_at_decisions"]
    buttons = [{"source": "button", "screen": "observatory_hud", "label": label}
               for label in ("KIT", "LOG")]
    choice = {"source": "choice", "label": "Leave"}

    assert transform(buttons, {"has_choices": False}) == []
    menu[0] = {"req_id": "room-menu", "choices": [choice]}
    scraped = transform(buttons, {"has_choices": False})
    combined = transform([choice] + scraped, {"has_choices": True})
    assert combined == [choice] + buttons
    # The wrapper exits on a selection, exception, or load. Old choices must
    # not turn the persistent HUD into a decision during the following say.
    menu[0] = None
    assert transform(buttons, {"has_choices": False}) == []
    map_actions = [{"screen": "observatory_map", "label": "LAB"}] + buttons
    assert transform(map_actions, {"has_choices": False}) == map_actions
