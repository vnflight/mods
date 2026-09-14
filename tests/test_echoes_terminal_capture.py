"""Boundary scheduling tests; no Ren'Py installation is required."""
from pathlib import Path
from types import SimpleNamespace
import textwrap
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / "echoes_of_tomorrow.rpy").read_text(encoding="utf-8")
START = SOURCE.index("    def _vnf_eot_terminal_before_say(")
END = SOURCE.index("    def _vnf_eot_install_terminal_hide_capture", START)
HOOK = textwrap.dedent(SOURCE[START:END])
HIDE_END = SOURCE.index("    _vnf_eot_prior_auto_skip_predicate =", END)
HIDE_HOOK = textwrap.dedent(SOURCE[END:HIDE_END])


class TerminalCaptureTests(unittest.TestCase):
    def make_environment(self, *, nvl=True):
        events = []
        visible = {"echo_terminal_live"}

        def publish(event, interact, **kwargs):
            if event == "begin":
                events.append("reaction")

        config = SimpleNamespace(all_character_callbacks=[publish])
        if nvl:
            config.all_nvl_callbacks = [publish]
        namespace = {
            "renpy": SimpleNamespace(
                config=config,
                get_screen=lambda tag: object() if tag in visible else None),
            "vnf_player": SimpleNamespace(enabled=True, scrape_screens=True),
            "_vnf_scrape_visible_screens": lambda **kw: events.append(("scrape", kw)),
        }
        exec(HOOK, namespace)
        return namespace, config, visible, events

    def test_both_callback_apis_capture_before_say(self):
        namespace, config, visible, events = self.make_environment()
        for callbacks in (config.all_character_callbacks, config.all_nvl_callbacks):
            events.clear()
            for callback in callbacks:
                callback("begin", True)
            self.assertEqual(events, [("scrape", {"force": True}), "reaction"])

    def test_reload_replaces_hook_without_stacking(self):
        namespace, config, visible, events = self.make_environment(nvl=False)
        first = config.all_character_callbacks[0]
        exec(HOOK, namespace)
        self.assertEqual(len(config.all_character_callbacks), 2)
        self.assertIsNot(first, config.all_character_callbacks[0])
        for callback in config.all_character_callbacks:
            callback("begin", True)
        self.assertEqual(events, [("scrape", {"force": True}), "reaction"])

    def test_choice_terminal_is_also_captured(self):
        namespace, config, visible, events = self.make_environment()
        visible.clear()
        visible.add("echo_terminal_choice")
        config.all_character_callbacks[0]("begin", False)
        self.assertEqual(events, [("scrape", {"force": True})])

    def test_hidden_disabled_and_non_begin_do_not_scrape(self):
        namespace, config, visible, events = self.make_environment()
        hook = config.all_character_callbacks[0]
        hook("end", True)
        visible.clear()
        hook("begin", True)
        visible.add("echo_terminal_live")
        namespace["vnf_player"].enabled = False
        hook("begin", True)
        namespace["vnf_player"].enabled = True
        namespace["vnf_player"].scrape_screens = False
        hook("begin", True)
        self.assertEqual(events, [])

    def test_scrape_failure_does_not_block_dialogue(self):
        namespace, config, visible, events = self.make_environment()

        def fail(**kwargs):
            raise RuntimeError("screen is unavailable")

        namespace["_vnf_scrape_visible_screens"] = fail
        for callback in config.all_character_callbacks:
            callback("begin", True)
        self.assertEqual(events, ["reaction"])

    def test_no_frame_readiness_bypass(self):
        namespace, config, visible, events = self.make_environment()
        ready = [False]

        def guarded_scrape(force=False):
            if ready[0]:
                events.append("terminal")

        namespace["_vnf_scrape_visible_screens"] = guarded_scrape
        for callback in config.all_character_callbacks:
            callback("begin", True)
        self.assertEqual(events, ["reaction"])
        # The hook schedules capture, but cannot promise pre-say publication
        # when the engine has not produced a coherent screen/focus snapshot.

    def test_hide_captures_before_removing_terminal_and_preserves_arguments(self):
        namespace, config, visible, events = self.make_environment()

        def original(tag, *args, **kwargs):
            events.append(("hide", tag, args, kwargs))
            visible.clear()
            return "hidden"

        namespace["renpy"].hide_screen = original
        exec(HIDE_HOOK, namespace)
        hide = namespace["renpy"].hide_screen
        self.assertEqual(hide("echo_terminal_live", "screens", immediately=True), "hidden")
        self.assertEqual(events, [
            ("scrape", {"force": True}),
            ("hide", "echo_terminal_live", ("screens",), {"immediately": True}),
        ])

    def test_hide_reload_does_not_stack_and_other_screens_are_untouched(self):
        namespace, config, visible, events = self.make_environment()
        namespace["renpy"].hide_screen = lambda *a, **kw: events.append("hidden")
        exec(HIDE_HOOK, namespace)
        exec(HIDE_HOOK, namespace)
        namespace["renpy"].hide_screen("other_screen")
        self.assertEqual(events, ["hidden"])
        events.clear()
        namespace["renpy"].hide_screen(("echo_terminal_live",))
        self.assertEqual(events, [("scrape", {"force": True}), "hidden"])


if __name__ == "__main__":
    unittest.main()
