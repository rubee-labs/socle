# Obsidian Forge Bridge

Obsidian plugin that exposes a Claude-Forge subject pool inside Obsidian's
native UX. Parses `linked_subjects` from `MEMORY.md` frontmatters and renders a
single index file (`_forge-index.md` by default) of native wikilinks — so
Obsidian's graph view, backlinks panel, quick switcher, and search all discover
Forge relationships without any extra configuration.

## Why

Forge stores subjects as plain Markdown (`MEMORY.md` per subject + 4
producer-typed subfolders + a YAML frontmatter referencing peers via
`linked_subjects:`). That format is great for agents (deterministic, grep-able,
git-friendly) but bare for humans — opening a folder in VS Code does not feel
like an *application*.

Obsidian solves the human side: a visual graph, fast navigation, backlinks,
themes, plugins, and a mobile app. This bridge does **not** migrate Forge to
Obsidian — Forge stays the source of truth on disk. The plugin just makes
Forge's relationships visible inside Obsidian.

This is the "Obsidian as a reader for Forge" scenario discussed in the
2026-05-26 Forge-Lab analysis [Optimike Obsidian MCP][analysis] — a lightweight
alternative to adopting a full Obsidian MCP server.

[analysis]: https://github.com/rubee-labs/benjamin-perso/blob/main/Forge-lab/analyses/2026-05-26-optimike-obsidian-mcp-bridge.md

## Status

Version 0.1.0 — minimum viable plugin. Read-only. No writes back to subject
files. Intentionally tiny: ~250 LoC of TypeScript.

## Install

This plugin is not published in the community plugins gallery. Install it
manually:

```bash
# From the integration folder
npm install
npm run build

# Then in your vault
mkdir -p .obsidian/plugins/obsidian-forge-bridge
cp main.js manifest.json .obsidian/plugins/obsidian-forge-bridge/
```

Restart Obsidian, enable "Forge Bridge" under Settings → Community plugins, and
the commands below become available.

## Usage

Open a vault that contains Forge subjects (anywhere in the tree). A subject is
recognised by a `MEMORY.md` file with a `forging_state` key in its frontmatter.

Run the command:

- **Forge: Refresh Forge subject index** — scans the vault, parses every Forge
  `MEMORY.md`, and rewrites `_forge-index.md` at the vault root with one entry
  per subject grouped by cycle γ state (`actif` / `mature` / `archived`). Each
  entry exposes both the file link and the linked subjects as native
  `[[wikilinks]]`.

The graph view immediately picks up the new wikilinks, so a subject's
`linked_subjects: [supplier:weifang]` shows up as a real edge — the same way a
hand-written `[[supplier:weifang]]` would.

- **Forge: Show Forge subject pool stats** — pops a quick toast with counts
  per state, per type, and the total number of edges. Useful before/after a
  bulk subject migration to verify nothing was missed.

## Settings

- **Index file name** — default `_forge-index.md`. Change if you want it stored
  in a subfolder (e.g. `Index/forge.md`).
- **Auto-refresh on MEMORY.md modify** — off by default. Turn on to regenerate
  the index whenever a Forge file is touched. Adds a small overhead on every
  save, so leave it off for large vaults.
- **Scan only MEMORY.md files** — on by default to match the Forge convention.
  Turn off to scan every markdown file that carries a `forging_state` key in
  its frontmatter.

## What this plugin does *not* do

- It does **not** modify Forge files. The index file is the only thing it
  writes.
- It does **not** replace `forge documente`, `forge bench`, or any other CLI
  primitive. Those still live in the `bin/` folder of the source repository.
- It does **not** require a backend, a server, an embedding model, or a
  network connection.
- It does **not** support `linked_records` (foreign keys to external systems).
  Only `linked_subjects` (subject-to-subject edges) are rendered.

For an industrial alternative that exposes the vault as a full MCP surface
(notes/Bases/Tasks/semantic), see [Optimike Obsidian MCP][optimike].

[optimike]: https://github.com/optimikelabs/optimike-obsidian-mcp

## Development

```bash
npm install
npm run dev      # esbuild in watch mode
npm run build    # production build (outputs main.js)
npm run check    # TypeScript-only type check
```

## License

MIT — see the parent repository for the full text.
