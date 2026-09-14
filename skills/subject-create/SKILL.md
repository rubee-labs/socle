---
name: subject-create
description: >-
  When the user asks to create a new subject (instance) from an existing type.
  Also trigger on "create subject", "instancier un sujet", "nouvelle commande
  Simon", "nouveau projet", "subject-create". To create a new TYPE first, see
  /subject-create-type.
type_anthropic: 5
visibilité: entreprise
auteur: Benjamin
date_creation: 2026-04-29
version: 1.0
tags: [subject-pool, instance, scaffolding, forge]
effort: medium
outils_requis: []
securite_externe: false
---

# Créer un Subject (Instance)

## Objectif

Instancier un nouveau **subject** dans le subject pool à partir d'un **type** existant. Génère le dossier `subjects/<name>/` avec son `MEMORY.md` pré-rempli depuis le `TEMPLATE.md` du type, et la structure `events/ / analyses/ / discussions/ / decisions/`.

Voir `entreprise/config/rules/savoirs.md` § "Subject Pool" pour le modèle conceptuel.

## Quand utiliser

- À chaque nouvelle commande fournisseur, nouvelle campagne marketing, nouvel incident, nouveau client à analyser, etc.
- Quand un agent autonome (futur Tower-Control) détecte un nouveau cycle de vie à tracer
- Quand on veut wrapper un sujet existant éparpillé en un subject structuré (cas particulier : étendre un Lab existant)

**Quand NE PAS utiliser** :
- Si le subject est en réalité une instance d'un type **inexistant** → invoquer `/subject-create-type` d'abord
- Si le sujet existe déjà sous un autre nom (vérifier avec une recherche dans `entreprise/SUBJECTS-INDEX.md` si présent)

## Instructions

### Phase 1 — Identifier le type

Si le type est passé en argument (`/subject-create <type> <name>`), vérifier qu'il existe :

```bash
find /Users/bhamon/Documents/1\ -\ Boulot/Dev/Git/claude-enterprise -type d -name "<type>" -path "*/types/*" 2>/dev/null
```

Sinon, lister tous les types disponibles et demander :

```bash
find /Users/bhamon/Documents/1\ -\ Boulot/Dev/Git/claude-enterprise -type d -path "*/types/*" -mindepth 3 -maxdepth 5 2>/dev/null | sort
```

Présenter à l'utilisateur les types disponibles avec leur description (extraite du frontmatter de chaque REFERENCE.md). Demander quel type instancier.

Si aucun type ne correspond → proposer `/subject-create-type` d'abord.

### Phase 2 — Lire le type sélectionné

Lire intégralement :
- `<chemin>/types/<type>/REFERENCE.md` (pour comprendre les dimensions, events attendus, liens typiques)
- `<chemin>/types/<type>/TEMPLATE.md` (pour utiliser comme base de génération)

### Phase 3 — Recueillir les paramètres de l'instance

Demander à l'utilisateur :

1. **Nom du subject** (kebab-case, anglais ou avec un identifiant numérique parlant : `order-400`, `incident-2026-08-rotterdam`, `customer-acme-corp`, `product-line-guirlande-guinguette`)
2. **Linked subjects obligatoires** (selon `typical_linked_types` du type) : pour chaque type lié obligatoire, demander quel subject existant ou en créer un.
   - Si un linked subject n'existe pas encore (ex: `supplier:simon` mais aucun `subjects/supplier-simon/`), proposer de le créer d'abord (récursif sur `/subject-create supplier supplier-simon`)
3. **Linked records initiaux** (foreign keys MCP connues à la création) — optionnel, peut être enrichi plus tard
4. **Contexte de création** (1-3 phrases) : qu'est-ce qui a déclenché ce subject ?

### Phase 4 — Choisir la localisation

Par défaut, l'instance vit dans `<chemin-du-type>/../subjects/<nom>/` (ex: type dans `services/achats/types/supplier-order/` → instance dans `services/achats/subjects/order-400/`).

Si le type est transverse (`entreprise/types/`), demander dans quel domaine instancier. Si pas évident, proposer `entreprise/subjects/`.

### Phase 5 — Générer MEMORY.md

À partir du `TEMPLATE.md` du type, remplacer les placeholders :

- `<subject-name>` → nom choisi en Phase 3
- `<YYYY-MM-DD>` → date du jour (vérifier la date système avant)
- `linked_subjects:` → liste enrichie en Phase 3
- `linked_records:` → liste enrichie en Phase 3 (vide si pas connue)
- Section `## Quick` → adapter avec le contexte de création
- Section `## Détails` → reprendre le contexte fourni en Phase 3

`forging_state` est initialisé à `actif` (cycle 2 états depuis 2026-09-14 — `seed` est un état legacy, `conviction` un champ déprécié : ne plus écrire ni l'un ni l'autre).

### Phase 6 — Créer la structure de dossiers

```
<chemin>/subjects/<name>/
├── MEMORY.md                ← généré
├── INDEX.md                 ← stub : "(régénéré par hook scanner forge)"
├── events/                  ← dossier vide
├── analyses/                ← dossier vide (créé seulement si type le prévoit)
├── discussions/             ← dossier vide
└── decisions/               ← dossier vide
```

Le dossier `analyses/` est créé seulement si le type a `skills.analyze` défini (la plupart des types l'ont).

### Phase 7 — Mettre à jour les linked_subjects existants

Pour chaque `linked_subject` cité dans le MEMORY.md, ouvrir leur `MEMORY.md` parent et ajouter une référence inverse dans leur `linked_subjects` (lien bidirectionnel).

Exemple : si `order-400` lie `supplier:simon`, alors le MEMORY.md de `supplier-simon` doit avoir `order-400` dans ses `linked_subjects`.

### Phase 8 — Confirmer et proposer la suite

Afficher à l'utilisateur :
- Chemin absolu du subject créé
- Aperçu du `MEMORY.md` Quick section
- Suites possibles :
  - `/documente <chemin>` pour re-synthétiser le subject dès qu'un event ou une discussion arrive
  - Ajouter un premier event manuellement dans `events/` (si déjà connu)
  - Démarrer une discussion dans `discussions/` via `/documente`

## Exemples

### Input

> `/subject-create supplier-order order-400`

### Output (résumé)

```
Subject créé : services/achats/subjects/order-400/
├── MEMORY.md     (forging_state: actif,
│                  linked_subjects: [supplier:simon, product-line:guirlande-guinguette],
│                  created_at: 2026-04-29)
├── INDEX.md
├── events/
├── analyses/
├── discussions/
└── decisions/

Linked subjects mis à jour :
  - supplier:simon (linked_subjects ← order-400)
  - product-line:guirlande-guinguette (linked_subjects ← order-400)

Suite suggérée : /documente services/achats/subjects/order-400/
```

## Gotchas

- **Vérifier la date système avant** d'écrire `created_at`. Ne JAMAIS deviner la date — utiliser `date '+%Y-%m-%d'` ou consulter le contexte.
- **Linked subjects manquants** : si un linked_subject obligatoire n'existe pas (ex: `supplier:simon` non créé), STOP et propose de le créer d'abord. Ne pas créer un subject avec un lien cassé.
- **Lien bidirectionnel** : la Phase 7 est obligatoire. Sans elle, l'INDEX-CONCEPT global ne reflète pas le graphe complet.
- **Pas d'instance d'un type qui n'existe pas** : si l'utilisateur force un type inexistant, redirige vers `/subject-create-type`. Ne pas créer en silence.
- **Slugs cohérents** : si le type est `supplier-order`, l'instance peut être `order-400` ou `order-simon-2026-04-300m`. Mais si l'utilisateur propose `supplier-order-400` (préfixe redondant), suggérer le slug court.
- **Ne pas pré-remplir trop** : `forging_state: actif` est la seule valeur valide à la création (cycle 2 états 2026-09-14). Ne JAMAIS écrire un état legacy (`seed`, `debating`, `tentative`, `mature`…) ni le champ déprécié `conviction` — incident mesuré le 2026-09-14 : ce skill a écrit `seed` pendant 4 mois post-refonte, laissant 18 subjects en vocabulaire aboli.
- **Mode silencieux quand appelé depuis `/documente`** (v2.1+) : si la Phase 0 de `/documente` invoque ce skill pour création paresseuse, **minimiser les prompts** : appliquer des valeurs par défaut (`linked_subjects: []`, `linked_records: []` si aucun signal disponible, localisation déduite du `<subject-path>` passé), créer le subject sans demander de confirmation Benjamin. Les linked_subjects/records seront enrichis ultérieurement (par /control-tower au prochain event, par décision Benjamin, par cascade). Ce mode silencieux est détectable via : invocation depuis le tool `Skill` avec un argument complet `<subject-path>` non `subjects/<X>/` qui contient déjà la localisation finale.

## Critères d'évaluation

- **EVAL 1** : Le type passé en argument existe-t-il bien (REFERENCE.md + TEMPLATE.md présents) ? (Pass si vérifié / Fail si écriture sans vérification)
- **EVAL 2** : Le `MEMORY.md` généré a-t-il bien tous les placeholders du TEMPLATE remplacés ? (Pass si aucun `<placeholder>` restant / Fail sinon)
- **EVAL 3** : `forging_state: actif` à la création, sans état legacy ni champ `conviction` ? (Pass / Fail)
- **EVAL 4** : Les liens bidirectionnels ont-ils été mis à jour dans les linked_subjects parents ? (Pass si chaque lien a son inverse / Fail sinon)
- **EVAL 5** : La structure de dossiers (`events/, discussions/, decisions/, analyses/ si applicable`) est-elle complète ? (Pass / Fail)
