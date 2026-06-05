---
name: forge-init
description: >-
  Initialise le subject pool claude-forge dans le repo courant : choisit
  l'emplacement de stockage, écrit le `.forge.yaml`, et scaffolde `subjects/`
  + `types/`. Porte d'entrée pour un nouveau repo (client ou perso) qui adopte
  claude-forge. Trigger sur "forge init", "initialise le pool", "configure
  claude-forge ici", "où stocker ma mémoire forge", après le nudge SessionStart.
type_anthropic: 4
visibilite: public
auteur: Benjamin
date_creation: 2026-06-05
version: 1.0
tags: [forge, subject-pool, init, onboarding, config]
effort: low
outils_requis: []
securite_externe: false
---

# forge-init

## Objectif

Configurer claude-forge dans le repo courant de façon **explicite et propre au repo** — sans hériter de l'arborescence d'un autre projet. Écrit un `.forge.yaml` à la racine du pool et crée la structure `subjects/` + `types/`.

C'est la réponse au nudge SessionStart « un pool subjects/ existe ici mais n'est pas configuré ».

## Quand utiliser

- Premier usage de claude-forge dans un repo (le `.forge.yaml` n'existe pas encore).
- L'utilisateur veut changer l'emplacement de stockage (relancer avec `--force`).

## Workflow

### Phase 1 — Détecter le contexte

```bash
forge init --help >/dev/null 2>&1   # vérifie que le binaire est dispo
```

Inspecter le repo : un dossier `entreprise/` existe-t-il (hôte legacy) ? Un `subjects/` est-il déjà présent quelque part ? En déduire une proposition de défaut.

### Phase 2 — Demander l'emplacement (AskUserQuestion)

Poser **une** question à l'utilisateur : où stocker la mémoire forge ?

- **Racine du repo** (défaut pour un repo dédié) : `output_dir: .`, `pool_roots: ["."]`. Index et fiches vivent à la racine.
- **Sous-dossier dédié** (ex: `memoire/`, `forge/`) : `output_dir: <dossier>`, `pool_roots: ["<dossier>"]`. Garde la racine propre.
- **Profil legacy `entreprise/`** (uniquement si le repo a déjà cette structure) : `output_dir: entreprise`, `pool_roots: [services, entreprise, humains]`.

### Phase 3 — Écrire la config + scaffolder

```bash
forge init --output-dir <X> --pool-root <Y> [--types-root <Z>] [--skill-visibility <V>]
```

Sans flags, `forge init` applique l'auto-détection (output_dir = `entreprise/` si présent sinon racine ; pool_root = `.`). Le binaire :
- écrit `<repo>/.forge.yaml` (refuse d'écraser un existant sauf `--force`),
- crée `<pool-root>/subjects/` + `<types-root>/types/` avec `.gitkeep`,
- retourne un JSON `{ok, written, scaffolded}`.

### Phase 4 — Confirmer

Afficher à l'utilisateur le `.forge.yaml` écrit et les dossiers créés. Suggérer la suite : créer un premier type (`/subject-create-type`) puis un premier subject (`/subject-create`), ou documenter directement via `/documente`.

## Gotchas

- **Idempotent par le `.forge.yaml`** : une fois le fichier écrit, le nudge SessionStart se tait. Relancer n'a de sens qu'avec `--force` (changer d'emplacement).
- **CE n'a pas besoin de ce skill** : claude-enterprise marche en zéro-config (auto-détection `entreprise/`). Ne pas y créer de `.forge.yaml`.
- **Le `.forge.yaml` est versionné** : il suit le repo, c'est volontaire (la config de stockage fait partie du projet).

## Critères d'évaluation

EVAL 1 : `.forge.yaml` écrit à la racine du pool avec l'emplacement choisi.
EVAL 2 : `subjects/` et `types/` créés (avec `.gitkeep`).
EVAL 3 : Refus d'écraser un `.forge.yaml` existant sans `--force`.
EVAL 4 : Aucun dossier `entreprise/` parasite créé dans un repo qui n'en a pas.
