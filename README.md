# vnflight compatibility adapters

Project-owned adapter code is licensed under [MIT](LICENSE).
Manifest SHA-256 hashes verify file integrity, not publisher identity. Obtain
the repository and manifest from a trusted source.

Each `.rpy` file here is a **compatibility adapter** ("mod") for one game: a
small Ren'Py file that vnflight installs next to its shim so an agent can
read that game. Adapters name image-only buttons, filter noise, expose
stats and inventory, register overlay screens and add game-specific
commands. They contain no game assets.

Adapters contain executable Python code that runs inside the game process,
with the game's access to your computer. Review unfamiliar adapters and
install only code from sources you trust. Manifest hashes check that the
files match the manifest; they do not establish that the code is safe.

`manifest.json` lists, per game id, the adapter files, the name each is
installed under (`vnf_*.rpy`) and a sha256 hash of the file. Point
`vnflight.json` at it once, with a top-level
`"mods_manifest": "<path to this dir>/manifest.json"` (absolute, or relative to
`vnflight.json`): a game entry without a `mods` key then gets the adapters
listed here for its id, each verified against its hash before install. A game
entry can still map files itself with
`"mods": [{"source": "<path to this dir>/<file>", "target": "<vnf_ name>"}]`,
and that list wins. See the vnflight user guide.

Alternatively, use the core's `fetch-mods` command with an HTTPS URL for
`manifest.json`, a trusted manifest SHA-256, and a new output directory.
The manifest's `license` entry pins the accompanying MIT license; remote
snapshots include it as well as the adapters. Use immutable commit URLs.

Adapter files use LF line endings on every platform: `.gitattributes` preserves
the exact bytes covered by the manifest hashes. After changing an adapter,
update its SHA-256 in every matching manifest entry and run
`python -m unittest discover -s tests` before committing.

Adapters are catalogued one folder per game id, each folder with its own
README saying what the adapter provides and which engine versions it was
played on; `manifest.json` names them as `<folder>/<file>.rpy`.

| Game | Adapters |
|---|---|
| [Echoes of Tomorrow](https://github.com/vnflight/echoes_of_tomorrow) | `echoes_of_tomorrow/echoes_of_tomorrow.rpy`, `echoes_of_tomorrow/echoes_progress.rpy` |
| [Mystic Cafe](https://github.com/vnflight/mystic_cafe) | `mystic_cafe/mystic_cafe.rpy` |
| Roadwarden | `roadwarden/roadwarden.rpy`, `roadwarden/roadwarden_progress.rpy` |
| Long Live the Queen | `long_live_the_queen/long_live_the_queen.rpy` |

## Notice for commercial-game adapters

The adapters that target commercial games are unofficial compatibility
packs:

- **Unofficial and unaffiliated.** They are not affiliated with,
  authorized by, or endorsed by the respective game creators or
  publishers.
- **No game assets or source are redistributed.** An adapter never ships
  a game's art, audio, scripts, or other assets.
- **For locally owned copies only.** Adapters are intended to run against
  a copy of a game that you legally own.
- **Removal on request.** If a game's creator or authorized representative
  objects, we will remove its adapter from the current catalog and future
  releases we publish. Please open an issue to request removal. This does
  not remove historical copies or third-party forks.
