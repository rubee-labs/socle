# claude-forge

Couche de mémoire structurée pour Claude Code — la 4ème couche, après le contexte de session, l'auto-memory et `CLAUDE.md`.

claude-forge ajoute au harnais Claude Code une primitive qui lui manque : **la mémoire structurée par sujets, avec cycle de vie γ et cascade entre sujets liés**. Là où l'auto-memory et `CLAUDE.md` stockent du markdown libre, claude-forge structure les décisions, discussions, événements en artefacts typés validés par Python.

## Différence avec claude-mem

| Dimension | claude-mem | claude-forge |
|---|---|---|
| Axe | Temporel (continuité session-à-session) | Structurel (typage des décisions) |
| Format | SQLite + Chroma + CLAUDE.md auto | `subjects/<name>/MEMORY.md` typés |
| Auteur | Claude (auto) | **Co-écrit** humain + Claude |
| Cycle de vie | aucun | γ (seed → debating → tentative → stress_testing → doctrine) |
| Linked subjects, cascade | aucun | oui |
| Décisions vs discussions | aucun | deux artefacts distincts |
| Validation Python | aucune | oui (frontmatter typé) |

Les deux sont complémentaires.

## Installation

À documenter — `npx claude-forge install` ou équivalent.

## Architecture

```
claude-forge/
├── bin/                    Binaires Python (engines)
│   ├── forge               CLI dispatcher
│   ├── documente_engine.py
│   ├── forge_engine.py
│   ├── forge_scanner.py
│   └── lib/                Libs internes
├── skills/                 Skills Claude Code
│   ├── documente/
│   ├── subject-create/
│   ├── subject-create-type/
│   └── subject-merge/
├── commands/               Slash commands
├── templates/              Templates de subjects
├── rules/                  Règles d'usage
├── tests/                  Tests des engines
└── subjects/               Méta-réflexion (dogfooding)
    └── claude-forge/       Le subject qui décrit ce projet
```

## État

v0.1.0 — extraction initiale depuis claude-enterprise (2026-05-05).

## Auteur

Benjamin Hamon (Rubee Labs).
