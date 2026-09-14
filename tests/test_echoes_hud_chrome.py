"""Echoes chrome filtering preserves story, controls, and unique status."""
from pathlib import Path
import textwrap


SOURCE = (Path(__file__).resolve().parents[1] / "echoes_of_tomorrow.rpy").read_text(encoding="utf-8")
START = SOURCE.index("    def _vnf_eot_hud_chrome_text(")
END = SOURCE.index("    _vnf_add_screen_transform(_vnf_eot_hud_chrome_text", START)
namespace = {}
exec(textwrap.dedent(SOURCE[START:END]), namespace)
transform = namespace["_vnf_eot_hud_chrome_text"]


def test_nvl_chrome_only_before_story_boundary():
    texts = ["STATION STATUS", "SIGNAL  85%", "ARIA COHERENCE  61%",
             "STORM 3/3  PEAK 49m", "POWER  BALANCED", "THERMAL SEVERE COLD",
             "Incident: Antenna module 2 offline", "PASSIVE RUNS",
             "CARRIER REBUILD  50%", "NO KNOWN RUNS",
             "AETHON OBSERVATORY  //  PERSONAL LOG", "E. VOSS \u00b7 05 MAR 2047",
             "SIGNAL  85%", "A line of narration."]
    scr = {"_tag": "nvl", "texts": texts, "buttons": [{"label": "KIT"}],
           "_text_sections": list(range(len(texts))),
           "_text_paths": [(i,) for i in range(len(texts))]}
    transform([scr])
    expected = [5, 6, 8, 12, 13]
    assert scr["texts"] == [texts[i] for i in expected]
    assert scr["_text_sections"] == expected
    assert scr["_text_paths"] == [(i,) for i in expected]
    assert scr["buttons"] == [{"label": "KIT"}]


def test_hud_buttons_and_incidents_survive_without_log_header():
    scr = {"_tag": "observatory_hud", "texts": [
        "STATION STATUS", "STORM PEAK IN  4h 55m",
        "Antenna module 2: permanent repair"],
        "buttons": [{"label": "KIT"}, {"label": "LOG"}],
        "_text_paths": [(0,)]}
    transform([scr])
    assert scr["texts"] == ["Antenna module 2: permanent repair"]
    assert len(scr["buttons"]) == 2
    assert scr["_text_paths"] == []


def test_terminal_panels_and_plain_nvl_are_not_filtered():
    for tag in ("echo_terminal_live", "echo_terminal_choice", "evidence_screen",
                "equipment_screen", "nvl", "say"):
        texts = ["STATION STATUS", "SIGNAL  85%", "An actual log entry."]
        scr = {"_tag": tag, "texts": texts[:]}
        assert transform([scr])[0]["texts"] == texts


def test_advisory_header_and_body_are_separated():
    scr = {"_tag": "nvl", "texts": [
        "AETHON OBSERVATORY  //  STATION ADVISORY",
        "E. VOSS \u00b7 05 MAR 2047", "STATION STATUS"]}
    transform([scr])
    assert scr["texts"] == ["STATION STATUS"]
