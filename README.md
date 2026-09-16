# SOCLE

**La mémoire d'entreprise structurée pour Claude Code** — la 4ème couche de mémoire, après le contexte de session, l'auto-memory et `CLAUDE.md`.

- 🇫🇷 **S**ynthèse et **O**rganisation des **C**onnaissances et **L**eçons d'**E**ntreprise
- 🇬🇧 **S**tructured **O**rganizational **C**ontext & **L**ifecycle **E**ngine

SOCLE ajoute au harnais Claude Code une primitive qui lui manque : **la mémoire structurée par sujets, avec cycle de vie et cascade entre sujets liés**. Là où l'auto-memory et `CLAUDE.md` stockent du markdown libre, SOCLE structure les décisions, discussions, événements en artefacts typés validés par Python.

> Anciennement `claude-forge` (renommé le 2026-09-16 — un plugin tiers ne doit pas laisser croire qu'il est édité par Anthropic). Les anciennes URLs GitHub redirigent. Le binaire s'appelle toujours `forge` : c'est l'outil, SOCLE est le produit.

## Différence avec claude-mem

| Dimension | claude-mem | SOCLE |
|---|---|---|
| Axe | Temporel (continuité session-à-session) | Structurel (typage des décisions) |
| Format | SQLite + Chroma + CLAUDE.md auto | `subjects/<name>/MEMORY.md` typés |
| Auteur | Claude (auto) | **Co-écrit** humain + Claude |
| Cycle de vie | aucun | 2 états (`actif` → `archived`), transitions manuelles |
| Linked subjects, cascade | aucun | oui |
| Décisions vs discussions | aucun | deux artefacts distincts |
| Validation Python | aucune | oui (frontmatter typé) |

Les deux sont complémentaires.

## Installation

```
/plugin marketplace add rubee-labs/socle
/plugin install socle@rubee-labs
```

## Configuration par-repo (`.forge.yaml`)

socle ne suppose **aucune** arborescence imposée : chaque repo décide où il stocke sa mémoire, via un fichier `.forge.yaml` (optionnel) à la racine du pool. Le plugin est ainsi distribuable à n'importe quel repo sans hériter de la structure d'un autre.

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
socle/
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
    └── socle/       Le subject qui décrit ce projet
```

## État

v0.1.0 — extraction initiale depuis claude-enterprise (2026-05-05).

## Auteur

Benjamin Hamon (Rubee Labs).

## Licence

**PolyForm Shield 1.0.0** — voir [LICENSE.md](LICENSE.md).

Source visible, usage libre y compris commercial **en interne**. Seule interdiction : s'en servir pour proposer un produit ou un service **concurrent** de SOCLE ou des prestations de Rubee Labs bâties dessus. Ce n'est donc pas une licence open source au sens de l'OSI.
