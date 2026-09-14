"""Marcus's schedule is available on the map, not as continuous telemetry."""
from pathlib import Path
from types import SimpleNamespace
import textwrap


def test_marcus_location_follows_map_visibility_without_stale_state():
    source = (Path(__file__).resolve().parents[1] / "echoes_of_tomorrow" / "echoes_of_tomorrow.rpy").read_text(encoding="utf-8")
    start = source.index("    _VNF_EOT_LOCATION_LABELS =")
    end = source.index("    def _vnf_apply_inventory_changes", start)
    screens = set()
    calls = []
    store = SimpleNamespace(long_night_active=True, current_location="lab",
                            evidence_log=["An observed clue"])
    def location():
        calls.append(True)
        return "lab"
    store.eot_marcus_location = location
    renpy = SimpleNamespace(store=store, get_screen=lambda name: object() if name in screens else None)
    namespace = {"renpy": renpy}
    exec(textwrap.dedent(source[start:end]), namespace)
    read = namespace["_vnf_get_inventory_stats"]
    for visible, expected in [
        (set(), False),
        ({"echo_terminal_live"}, False),
        ({"echo_terminal_choice"}, False),
        ({"observatory_map"}, True),
        ({"observatory_map", "echo_terminal_live"}, False),
        ({"observatory_map", "echo_terminal_choice"}, False),
        (set(), False),
    ]:
        screens.clear()
        screens.update(visible)
        before = len(calls)
        inventory, stats = read()
        assert ("marcus_location" in stats) == expected
        assert len(calls) - before == int(expected)
        assert stats["location"] == "Lab"
        assert inventory[0]["name"] == "An observed clue"
        assert "Marcus" not in stats["_summary"]
        if expected:
            assert stats["marcus_location"] == "Lab (map: LAB)"
    screens.add("observatory_map")
    store.long_night_active = False
    assert "marcus_location" not in read()[1]
    store.long_night_active = True
    def unavailable(name):
        raise RuntimeError("screen lookup unavailable")
    renpy.get_screen = unavailable
    inventory, stats = read()
    assert "marcus_location" not in stats
    assert inventory and stats["location"] == "Lab"
