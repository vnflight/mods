"""Run with python -m unittest discover -s tests."""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_license_matches_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        entry = manifest["license"]
        self.assertEqual(entry["file"], "LICENSE")
        data = (ROOT / "LICENSE").read_bytes()
        self.assertNotIn(b"\r", data)
        self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])

    def test_every_adapter_matches_its_manifest(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        for game, entry in manifest["games"].items():
            for adapter in entry["mods"]:
                with self.subTest(game=game, file=adapter["file"]):
                    data = (ROOT / adapter["file"]).read_bytes()
                    self.assertNotIn(b"\r", data)
                    self.assertEqual(hashlib.sha256(data).hexdigest(), adapter["sha256"])


if __name__ == "__main__":
    unittest.main()
