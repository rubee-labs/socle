---
name: subject-create-type
description: >-
  When the user asks to create a new subject type — the "class" that defines
  analysis dimensions, expected events, and associated skills for a family of
  similar subjects. Also trigger on "create type", "nouveau type de sujet",
  "type subject", "subject type", "créer un type". For instantiating a subject
  from an existing type, see /subject-create.
type_anthropic: 5
visibilité: entreprise
auteur: Benjamin
date_creation: 2026-04-29
version: 1.0
tags: [subject-pool, type, scaffolding, forge]
effort: medium
outils_requis: []
securite_externe: false
---

# Créer un Type de Subject

## Objectif

Créer un nouveau **type** dans le subject pool. Un type définit la grille d'analyse partagée par toutes ses instances : dimensions de scoring, events attendus, types liés typiques, skills associés. Voir `entreprise/config/rules/savoirs.md` § "Subject Pool" pour le modèle conceptuel.

## Quand utiliser

- Quand un pattern de subjects revient suffisamment pour mériter une grille partagée (ex : 3+ commandes fournisseur traitées séparément → créer le type `supplier-order`)
- Quand le scanner forge a détecté un cluster sans type explicite et propose la promotion (alerte au démarrage de session)
- Quand on démarre un nouveau domaine et qu'on veut poser la grille d'analyse en amont (ex : créer le type `marketing-campaign` avant la première campagne)

**Quand NE PAS utiliser** : si un type proche existe déjà, mieux vaut l'étendre (ajouter une dimension, un event) que créer un type quasi-doublon.

## Instructions

### Phase 1 — Vérifier qu'un type proche n'existe pas déjà

Avant tout, lister les types existants :

```bash
find /Users/bhamon/Documents/1\ -\ Boulot/Dev/Git/claude-enterprise -type d -name "types" -not -path "*/node_modules/*" 2>/dev/null
```

Pour chaque dossier `types/<existing-type>/`, lire le `REFERENCE.md` et présenter à l'utilisateur la liste avec leur description courte. Demander : « Le type que tu veux créer ressemble-t-il à un de ceux-là ? »

Si oui → recommander d'étendre l'existant, ne pas créer de doublon. Stopper le skill.

### Phase 2 — Recueillir les paramètres du type

⚠️ **Règle bilingue** (cf. `entreprise/config/rules/savoirs.md` § Nomenclature) :
- **Squelette/taxonomie** = anglais snake_case : nom du type, parent_type, horizon, typical_linked_types, skills.
- **Contenu métier** = langue de l'utilisateur (français pour Rubee), snake_case pareil : `analysis_dimensions`, `expected_events`.

Poser les questions une par une (AskUserQuestion ou directement, selon contexte) :

1. **Nom du type** (anglais kebab-case strict, ex: `supplier-order`, `incident`, `marketing-campaign`). Refuser le français et le snake_case ici. C'est de la taxonomie.
2. **Parent type** : `bounded-subject` (cycle de vie fini), `permanent-subject` (jamais archivé), `cyclic-subject` (récurrent par saison/Q). Anglais imposé.
3. **Horizon** : `bounded` (jusqu'à 1 an), `permanent` (∞), `cyclic` (récurrent). Anglais imposé.
4. **Typical duration** (si bounded) : durée typique en jours/semaines (ex: `90d`).
5. **Analysis dimensions** (4 à 8 dimensions) : **EN FRANÇAIS snake_case** car contenu métier. Pour chaque dimension : la formuler comme une **question** que l'analyste se pose en notant 0..10. Ex: `tresorerie` → "La commande charge-t-elle la trésorerie au bon moment ?". Refuser les valeurs anglaises (`cash_flow` → recommander `tresorerie`).
6. **Expected events** : liste typique des events (ordre chronologique préféré), **EN FRANÇAIS snake_case**. Ex pour une commande : `alerte_stock`, `email_fournisseur_disponibilite`, `paiement`, `email_bl_pret`. Refuser les valeurs anglaises.
7. **Typical linked types — paires {nom_de_relation, type_cible}** : autres types vers lesquels une instance pointera typiquement, **avec le nom de la relation** pour chaque cible. **Anglais snake_case imposé** car ce sont des taxonomies. Pour chaque type cible, demander à l'utilisateur la sémantique de la relation :
   - Ex pour un type `supplier-order` : `{name: ordered_from, type: supplier}`, `{name: contains, type: product-line}`, `{name: shipped_via, type: freight-forwarder}`.
   - Ex pour un type `marketing-campaign` : `{name: promotes, type: product-line}`, `{name: depends_on_supplier, type: supplier}`.
   - Le nom de la relation doit décrire **ce que fait l'instance source vis-à-vis de la cible**. Préférer des verbes au passé ou présent (`ordered_from`, `produces`, `shipped_via`, `handled_by`, `promotes`) plutôt que des génériques (`linked`, `related`).
   - Si l'utilisateur hésite ou propose juste une liste plate de types, le format ancien `[supplier, product-line]` reste accepté en rétrocompatibilité (le moteur autolink fera fallback `name == type`), mais on perd la sémantique métier — toujours pousser pour le format enrichi.
8. **Skills associés** : au minimum `analyze` (équivalent /CE-analyse) et `archive` (clôture du subject avec remontée des leçons). Noms slash-command en français OK.
9. **Localisation** : où vit ce type ?
   - `services/<X>/types/<nom>/` si rattaché à un service
   - `entreprise/types/<nom>/` si transverse
   - `humains/<nom>/types/<nom>/` si perso

### Phase 3 — Générer REFERENCE.md

Composer le fichier en suivant la structure validée du type d'exemple `services/achats/types/supplier-order/REFERENCE.md`. Sections obligatoires :

- **Frontmatter YAML** : `type, parent_type, horizon, typical_duration, analysis_dimensions, expected_events, typical_linked_types, skills`
- **Format de `typical_linked_types`** : liste YAML de paires inline `{name, type}`, une entrée par ligne. Exemple :
  ```yaml
  typical_linked_types:
    - {name: ordered_from, type: supplier}
    - {name: contains, type: product-line}
    - {name: shipped_via, type: freight-forwarder}
  ```
  Ne pas utiliser le format ancien (liste plate de strings) sauf si l'utilisateur a refusé de nommer les relations en Phase 2.
- **Définition** (1 paragraphe : ce que ce type représente)
- **Quand utiliser** + **Quand NE PAS utiliser**
- **Dimensions d'analyse** (table : dimension, échelle, question)
- **Events attendus** (liste numérotée chronologique)
- **Liens typiques** (subjects + linked_records foreign keys)
- **Cycle de vie typique** (parcours des forging_state attendu)
- **Skills associés** (description de chaque skill)
- **Doctrine applicable** (règles internes Rubee si pertinentes)

### Phase 4 — Générer TEMPLATE.md

Un squelette de `MEMORY.md` vide à instancier par `/subject-create`. Doit contenir :

- Frontmatter avec valeurs **par défaut** (forging_state: seed, conviction: 0, archived_at: null, listes vides)
- Placeholders explicites avec `<...>` (ex: `name: <subject-name>`, `created_at: <YYYY-MM-DD>`)
- Section `## Quick` pré-formatée (état initial, prochaines étapes, risques, liens)
- Section `## Détails` avec sous-sections suggérées (Contexte, Paramètres, Stress tests à prévoir, Notes libres)

### Phase 5 — Valider et écrire

1. Présenter à l'utilisateur les 2 fichiers en preview (récap des dimensions, events, skills)
2. Demander validation explicite ("OK pour créer ce type ?")
3. Si OK :
   - Créer le dossier `<localisation>/types/<nom>/`
   - Écrire `REFERENCE.md` et `TEMPLATE.md`
   - Confirmer création + chemin absolu
4. Si NON OK : ajuster selon retours, reproposer

### Phase 6 — Suite proposée

Une fois le type créé, proposer :
- `/subject-create <type> <name>` pour créer la première instance
- `/subject-promote-pattern` si Benjamin avait des subjects existants à rattacher rétroactivement à ce type

## Exemples

### Input

> "Crée un type pour les incidents douane qu'on subit régulièrement"

### Output (résumé)

```
Type créé : services/achats/types/customs-incident/
├── REFERENCE.md     (parent: bounded-subject, horizon: bounded ~30d,
│                     dimensions: severity, financial_impact, delay_added,
│                                 root_cause_clarity, recoverability, recurrence_risk,
│                     events: customs_block, customs_request, payment_settled,
│                             release_authorized, container_released)
└── TEMPLATE.md      (squelette d'instance)

Suite : /subject-create customs-incident incident-2026-08-rotterdam
```

## Gotchas

- **Un type mal défini pollue toutes ses instances**. Mieux vaut prendre 30 min à bien définir les dimensions qu'à les corriger sur 20 instances plus tard.
- **Ne JAMAIS créer un type "fourre-tout"** ("various", "misc", "general"). Si tu hésites, c'est qu'il y a 2 types qui se cachent — refuse et demande à découper.
- **Le nom du type doit être au singulier en anglais kebab-case strict**. Pas de pluriel (`supplier-orders` ❌), pas de snake_case (`supplier_order` ❌), pas de français (`commande-fournisseur` ❌).
- **Bilingue strict : ne JAMAIS proposer des `analysis_dimensions` ou `expected_events` en anglais**. C'est du contenu métier qui doit être dans la langue de l'utilisateur. Si l'utilisateur propose `cash_flow`, recommander `tresorerie`. Si `stock_alert`, recommander `alerte_stock`. La règle vit dans `entreprise/config/rules/savoirs.md` § Nomenclature.
- **Ne pas confondre type et instance**. Le type est `supplier-order`, l'instance est `order-400`. Une erreur classique : créer un type `commande-simon-300m` (= une instance déguisée).
- **Refuser silencieusement la création d'un type existant** est un bug. Si l'utilisateur insiste après l'avertissement Phase 1, alors créer mais avec suffixe `-v2` et expliquer.
- **Validation Benjamin obligatoire** avant écriture. Pas de création silencieuse.

## Critères d'évaluation

- **EVAL 1** : Le type créé n'existe-t-il pas déjà sous un autre nom proche ? (Pass si Phase 1 exécutée et type-doublon confirmé absent / Fail si doublon détecté en post-creation)
- **EVAL 2** : Toutes les `analysis_dimensions` ont-elles une question binaire associée dans REFERENCE.md ET sont-elles dans la langue de l'utilisateur (français pour Rubee) ? (Pass si chaque dimension a sa question + en français / Fail sinon, notamment si valeurs anglaises type `cash_flow`)
- **EVAL 2bis** : Les `expected_events` sont-ils en français snake_case ? (Pass si en français / Fail si valeurs anglaises type `stock_alert`)
- **EVAL 2ter** : Les `typical_linked_types` utilisent-ils le format enrichi `[{name, type}]` avec un nom de relation explicite par cible ? (Pass si chaque entrée est une paire `{name: <verbe>, type: <type-cible>}` / Warn si liste plate de strings — accepté pour rétrocompatibilité mais à pousser au format enrichi)
- **EVAL 3** : Le `TEMPLATE.md` est-il bien un squelette générique (sans valeurs spécifiques d'une instance) ? (Pass si tous les champs de valeur sont en `<placeholder>` ou `null` ou listes vides / Fail si valeurs en dur)
- **EVAL 4** : La localisation choisie respecte-t-elle la règle "au plus près du domaine principal" ? (Pass si type dans le service principal d'usage / Fail si dans `entreprise/` alors qu'un seul service l'utilise)
- **EVAL 5** : Validation Benjamin a-t-elle été obtenue avant écriture ? (Pass si confirmation explicite reçue / Fail si fichiers créés sans validation)
