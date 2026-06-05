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

## Configuration par-repo (`.forge.yaml`)

claude-forge ne suppose **aucune** arborescence imposée : chaque repo décide où il stocke sa mémoire, via un fichier `.forge.yaml` (optionnel) à la racine du pool. Le plugin est ainsi distribuable à n'importe quel repo sans hériter de la structure d'un autre.

### Mise en route

Dans un nouveau repo, lance une fois :

```bash
forge init                      # auto-détection (écrit .forge.yaml + crée subjects/ + types/)
forge init --output-dir memoire --pool-root memoire   # emplacement explicite
```

Ou utilise le skill guidé `/forge-init`. Un hook SessionStart *nudge* te le rappelle si un pool `subjects/` existe sans config.

### Schéma `.forge.yaml`

```yaml
output_dir: .                 # où écrire SUBJECTS-INDEX.md + SUBJECT-POOL-METRICS.md ("." = racine)
pool_roots: ["."]             # dossiers sous lesquels vivent <root>/subjects/
types_roots: ["."]            # idem pour <root>/types/ (défaut = pool_roots)
domain_roots: []              # préfixes regroupés sur 2 segments dans les metrics (cosmétique)
skill_visibility: mon-projet  # valeur injectée dans le frontmatter des SKILL.md générés
```

Toutes les clés sont **optionnelles**. Sans `.forge.yaml`, l'auto-détection s'applique : `output_dir` = `entreprise/` **si ce dossier existe** (compat claude-enterprise), sinon la racine du repo — jamais un `entreprise/` fantôme. La découverte des subjects se fait par `os.walk`, indépendante de la structure.

Exemple — repo plat (un projet dédié) : `output_dir: .`, `pool_roots: ["."]`.
Exemple — claude-enterprise : aucun `.forge.yaml` requis (zéro config, comportement historique).

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
