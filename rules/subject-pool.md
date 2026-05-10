# Subject Pool — réacteur de connaissance

Le **subject pool** est l'infrastructure de stockage et de maturation de la connaissance dans Claude Enterprise. C'est le **cœur opérationnel** où la matière brute (events, observations, signaux) se transforme par cycles de forge en doctrine exécutable (règles, skills, agents SDK, monitors).

Il généralise le pattern CE-Lab / WM-Lab / Alter-Lab à tous les sujets de l'entreprise.

---

## Modèle conceptuel

### Définitions

- **Subject** : réceptacle persistant qui accumule sur un thème. Exemples : CE, WM, supplier-simon, product-line-guirlande-guinguette, order-400.
- **Type** : patron partagé entre subjects similaires. Exemples : `supplier-order`, `supplier`, `product-line`, `marketing-campaign`, `incident`, `strategic-vision`. Définit la grille d'analyse (`REFERENCE.md`) et le squelette d'instanciation (`TEMPLATE.md`).
- **Instance** : un subject qui hérite d'un type. `order-400` est une instance de `supplier-order`.

### Localisation

```
services/<X>/
├── types/                         ← grilles partagées
│   └── <type-name>/
│       ├── REFERENCE.md
│       └── TEMPLATE.md
└── subjects/                      ← instances
    └── <subject-name>/
        ├── MEMORY.md              ← synthèse compacte (Quick + Détails)
        ├── INDEX.md               ← chronologique simple (regen par hook)
        ├── events/                ← produced_by: external
        ├── analyses/              ← produced_by: claude (optionnel)
        ├── discussions/           ← produced_by: human_and_claude
        └── decisions/             ← produced_by: human
```

`entreprise/types/` et `entreprise/subjects/` pour transverses. `humains/<nom>/subjects/` pour perso.

### 4 sous-dossiers — distingués par producteur

| Dossier | `produced_by` | Exemple |
|---|---|---|
| `events/` | `external` (monde / MCPs) | email Simon, vente Amazon, alerte stock |
| `analyses/` | `claude` (Claude seul) | scoring d'un signal externe sur la grille du type |
| `discussions/` | `human_and_claude` (échange) | débat 300m vs 400m |
| `decisions/` | `human` (validation Benjamin) | "commande 300m IP44, acompte 30%" |

---

## Cycle de vie γ (la forge)

Porté par le frontmatter du `MEMORY.md` du subject :

```
seed ──► debating ──► tentative ──► stress_testing ──► doctrine ──► in_service
                       │ (bump            │ (+10 si             │ (compile artefact :
                       │  conviction      │  passé,             │  règle/skill/agent
                       │  à 50)           │  -15 si raté)       │  SDK/monitor/...)
                       │                  │                     │
                       │                  ▼                     ▼
                       └──── debating si stress raté        under_review
                                                            (contre-signal)
                                                                       │
                                                                       ▼ ou
                                                                  archived
```

### États

| État (`forging_state`) | Description |
|---|---|
| `seed` | Signal entrant, pas encore traité |
| `debating` | En cours de raisonnement, hésitations |
| `tentative` | Opinion formée mais pas testée |
| `stress_testing` | En cours de confrontation (skill /stress-test) |
| `doctrine` | Opinion solide, prête à être compilée en exécutable |
| `in_service` | Doctrine en application, artefact compilé |
| `under_review` | Contre-signal détecté, retour en débat |
| `archived` | Subject clos, leçons remontées vers les subjects parents |

### Conviction

`conviction` (0..100) :
- **Bump à 50** lors de la transition `debating → tentative` (opinion formée a une base de confiance).
- **+10** par stress test passé (`survived: true`).
- **−15** par contre-signal qui force `under_review`.
- **Seuils** : ≥ 60 pour passer en `doctrine`, ≥ 80 pour invoquer `/compile-doctrine`.

### Skills

| Commande | Effet |
|---|---|
| `/subject-create-type <name>` | Crée un nouveau TYPE (REFERENCE.md + TEMPLATE.md). Validation humaine obligatoire. **Invocable directement ou indirectement via `/documente`** (qui demande validation avant de l'invoquer). |
| `/subject-create <type> <name>` | Instancie un subject à partir d'un type existant. **Invocable directement ou indirectement via `/documente`** (mode silencieux, 0 intervention). |
| `/documente <subject-path> [--type <type>]` | **Orchestrateur unique du subject pool** (v2.1+). Combine 4 rôles : (1) création paresseuse du type via `/subject-create-type` si absent (avec validation Benjamin) ; (2) création paresseuse de l'instance via `/subject-create` si absente (silencieuse) ; (3) capture conversation (discussion + décision) ; (4) re-synthèse continue (Quick + Détails régénérés, cascade horizontale 1 niveau, transitions γ auto `seed→debating` et `debating→tentative`). Entry point unique côté utilisateur — invocable manuellement ou par `/control-tower`, `/optimisation-campagne-google`, etc. après chaque event/décision. L'argument optionnel `--type` est utilisé par les skills appelants pour éviter l'inférence. |
| `/stress-test <subject-path>` | Confronte le subject (3 perspectives : contradicteur, steelman, yagni). |
| `/subject-merge <A> <B>` | Soudure de 2 subjects (validation humaine obligatoire). |
| `/compile-doctrine <subject-path>` | Génère l'artefact exécutable (règle/skill/agent SDK/monitor/injection/routing). |

Le mot **« forge »** désigne le cycle de vie γ et le moteur Python sous-jacent (`forge_engine.py`, `forge_lib.py`, `forge_scanner.py`) — il n'existe plus de skill `/forge` séparé.

Le scanner `forge scanner` (binaire claude-forge) peut tourner en hook SessionStart pour régénérer un index global des subjects (par exemple `SUBJECTS-INDEX.md` à la racine du repo). Configuration spécifique au projet — voir le hook intégrateur côté repo consommateur.

### Création paresseuse via `/documente` (v2.1+)

`/documente` est l'**entry point unique** : tu n'as jamais à invoquer `/subject-create-type` ou `/subject-create` directement (sauf cas particulier). Quand tu (ou un skill appelant) invoques `/documente <path> [--type <type>]` :

1. **Si le subject existe** → re-synthèse normale (Phases 1-9).
2. **Si le subject n'existe pas mais le type existe** → `/subject-create` invoqué silencieusement, puis re-synthèse continue.
3. **Si ni le subject ni le type n'existent** → `/documente` te demande explicitement de valider la création du type. Si tu valides, `/subject-create-type` tourne en mode interactif (analysis_dimensions, expected_events, etc.), puis `/subject-create` silencieux, puis re-synthèse.

Cette logique est ancrée dans `/documente` Phase 0a-0e. Les skills appelants (`/control-tower`, `/optimisation-campagne-google`) n'ont qu'à invoquer `/documente <path> --type <type>` — la création paresseuse est transparente.

**Cas exceptionnels où invoquer `/subject-create-type` ou `/subject-create` directement** :
- Création préventive d'un type avant que le premier subject n'arrive (ex: anticiper un nouveau service).
- Création d'un subject sans `/documente` derrière (rare, ex: import depuis une source externe).
Dans ces cas-là, les skills restent invocables individuellement comme avant.

---

## Compilation horizontale (cascade)

Quand un subject est passé à `/documente`, la mise à jour se propage à ses `linked_subjects` **sur 1 niveau strict** (pas de récursion). Pour chaque link résolu :

- `last_event` est mis à jour avec une référence vers l'event déclencheur
- Stats agrégées recalculées (selon le type — cf. REFERENCE.md)
- `## Quick` régénéré pour refléter la nouvelle activité
- Transition γ auto appliquée si conditions remplies (`seed→debating`, `debating→tentative` uniquement)
- `## Détails` n'est **PAS** modifié en cascade (réservé à l'invocation directe `/documente` sur ce subject — pour éviter qu'une cascade avec vue partielle écrase un détail riche)

Format des `linked_subjects` : `<type>:<name>` (ex: `supplier:weifang`). Le moteur résout via heuristique tolérante (slug exact → `<type>-<name>` → grep par `name`) — un link non résolu produit un warning, pas une erreur.

La cascade 1-niveau est un choix de doctrine pour préserver la rapidité (<30s/invocation incluant la cascade). Une cascade multi-niveau émerge naturellement si Benjamin invoque `/documente` sur un subject central après une session de control-tower (les enfants déjà touchés ont leur Quick MAJ, le parent re-synthétisé propage à son tour).

---

## Typed graph (auto-link déterministe)

Depuis 2026-05-10, les `linked_subjects` d'une instance peuvent être **typés** par la sémantique métier de la relation (ex: `ordered_from`, `contains`, `shipped_via`). Le moteur `bin/autolink_engine.py` est l'extracteur déterministe (zéro LLM, regex + frontmatter) qui croise :

- les `linked_subjects` de l'instance (frontmatter du `MEMORY.md`)
- avec les `typical_linked_types` du type parent (frontmatter du `REFERENCE.md`)

Pour produire un graph typé : pour chaque `linked_subject`, retrouver le type cible et lui attribuer le nom de relation déclaré dans le type parent.

### Format `typical_linked_types`

Deux formats acceptés (le second en rétrocompatibilité) :

**Format enrichi (recommandé, depuis 2026-05-10)** — paires `{name, type}` :

```yaml
typical_linked_types:
  - {name: ordered_from, type: supplier}
  - {name: contains, type: product-line}
  - {name: shipped_via, type: freight-forwarder}
```

`name` = nom de la relation (verbe au passé/présent, snake_case anglais). `type` = type cible (kebab-case anglais).

**Format ancien (rétrocompatibilité)** — liste plate de strings :

```yaml
typical_linked_types: [supplier, product-line, freight-forwarder]
```

Le parser fait un fallback `name == type` (relation = nom du type), ce qui permet aux types historiques de continuer à fonctionner sans migration. Mais on perd la sémantique métier.

### Commandes `forge autolink`

| Commande | Effet |
|---|---|
| `forge autolink extract <subject-path>` | Extrait les typed edges sortants d'un subject. JSON : `edges: [{name, target_slug, target_type, target_name}, ...]` + `warnings`. |
| `forge autolink graph-query <slug> [--type X] [--direction in/out/both] [--depth N]` | Parcourt le graph depuis un slug. Filtre optionnel sur le nom de la relation. BFS limité par `--depth`. |
| `forge autolink reconcile <subject-path>` | Équivalent à `extract` (idempotent par construction — pas de stockage du graph, recalcul à la volée). |

### Intégration au flow `/documente`

`/documente` invoque `forge autolink extract` automatiquement :

- **Phase F** : pour enrichir le `## Quick` du subject avec une ligne `Liens forts` listant les typed edges (ex: `Liens forts : ordered_from supplier:weifang ; contains product-line:guirlande-guinguette`).
- **Phase H.5 (validation pré-commit, non bloquante)** : pour signaler les `linked_subjects` orphelins ou les types cibles absents de `typical_linked_types` (suggestion d'enrichir le type).

Le graph **n'est pas persisté** (ni dans le frontmatter, ni dans un sidecar) — il est recalculé à la volée à chaque invocation. Doctrine de simplicité : une seule source de vérité (les `MEMORY.md` + `REFERENCE.md`), pas de cache à invalider.

---

## Nomenclature bilingue

**Règle stricte** : la **taxonomie/squelette** est en **anglais** (universel, partagée par toute l'équipe), mais le **contenu métier** reste en **langue de l'utilisateur** (français pour Rubee). Tous les identifiants utilisent snake_case.

| Squelette / taxonomie (anglais) | Contenu métier (français) |
|---|---|
| Champs frontmatter (`type`, `name`, `conviction`, `forging_state`, `linked_subjects`…) | Valeurs de `analysis_dimensions` (ex: `tresorerie`, `delai`) |
| Valeurs de `forging_state` (`seed`, `debating`, `tentative`, `doctrine`…) | Valeurs de `expected_events` (ex: `alerte_stock`, `email_fournisseur_disponibilite`) |
| Valeurs de `produced_by` (`external`, `claude`, `human_and_claude`, `human`) | Tags personnels |
| Valeurs de `horizon` (`bounded`, `permanent`, `unbounded`, `cyclic`) | Contenu narratif (Quick, Détails) |
| Noms de **types** (`supplier-order`, `incident`, `marketing-campaign`…) | Suffixes identifiants des subjects (ex: `simon`, `400`, `2026-q2-brumeaux`) |
| Noms de dossiers structuraux (`subjects/`, `types/`, `events/`, `analyses/`…) | Slugs de discussions / décisions |

**Pourquoi bilingue** : le squelette anglais permet à n'importe quel skill ou outil tiers de raisonner sur le pattern (un `forging_state: doctrine` est identifiable partout). Le contenu français permet à Benjamin et à l'équipe Rubee de lire et utiliser naturellement les dimensions métier sans traduction mentale.

**Convention dates** : `*_at` (verbe au passé), statuts au présent.

### Champs du frontmatter d'un subject (instance)

| Champ | Type | Description |
|---|---|---|
| `name` | str | Nom du subject |
| `type` | str | Référence au type parent |
| `forging_state` | enum | État du cycle de vie γ |
| `conviction` | int | Solidité 0..100 |
| `horizon` | enum | `bounded`, `permanent`, `unbounded`, `cyclic` |
| `created_at` | date | Date de création |
| `archived_at` | date or null | Date d'archivage |
| `linked_subjects` | list[str] | Liens vers d'autres subjects |
| `linked_records` | list[obj] | Foreign keys MCP `{type, value, source}` |
| `active_decisions` | list[ref] | Décisions actives |
| `open_discussions` | list[ref] | Discussions ouvertes |
| `last_event` | obj | Dernier event `{date, type, ref}` |
| `stress_tests_passed` | int | Compteur |
| `compiled_artifacts` | list[ref] | Artefacts exécutables produits |

---

## Lecture en cascade (rapidité de Claude)

| Niveau | Fichier | Quand |
|---|---|---|
| 1 | `entreprise/SUBJECTS-INDEX.md` | Toujours, au démarrage de session (carte des subjects actifs) |
| 2 | `<chemin>/<subject>/MEMORY.md` | Si subject concerné par la tâche |
| 3 | `events/`, `analyses/`, `discussions/`, `decisions/` | Rare, à la demande sur un fichier précis |

`MEMORY.md` est une **synthèse compacte** (Quick <100 mots + Détails rédigés), pas un log d'events. Les events vivent dans `events/`, jamais listés exhaustivement dans le frontmatter.

---

## Format des fichiers

### Type — REFERENCE.md

Grille d'analyse partagée par toutes les instances du type. Quasi-figée (évolue rarement).

```yaml
---
# Squelette/taxonomie : anglais
type: supplier-order
parent_type: bounded-subject
horizon: bounded                  # bounded | permanent | unbounded | cyclic
typical_duration: 90d
# Contenu métier : langue de l'utilisateur (ici français)
analysis_dimensions:              # grille de scoring partagée
  - tresorerie
  - delai
  - qualite
  - cout_total
  - risques
  - conformite_doctrine
expected_events:
  - alerte_stock
  - email_fournisseur_disponibilite
  - decision_acompte
  - paiement
  - email_bl_pret
  - booking_container
  - reception_entrepot
# Liens vers autres types : anglais (taxonomie). Format enrichi recommandé (paires {name, type})
# qui permet à `forge autolink` d'inférer un graph typé. Format ancien (liste plate) accepté
# en rétrocompatibilité (fallback : name == type).
typical_linked_types:
  - {name: ordered_from, type: supplier}
  - {name: contains, type: product-line}
  - {name: shipped_via, type: freight-forwarder}
skills:
  analyze: /supplier-order-analyze
  archive: /supplier-order-archive
---

# supplier-order — grille d'analyse

[description longue : ce que ce type représente, quand l'utiliser]
```

### Type — TEMPLATE.md

Squelette pré-rempli pour instancier un nouveau subject. Utilisé par `/subject-create` pour générer le `MEMORY.md` initial avec les champs de base et les sections vides à compléter.

### Instance — MEMORY.md

État compact du subject. Frontmatter + Quick section (<100 mots) + Détails rédigés.

```yaml
---
name: order-400
type: supplier-order
forging_state: in_service
conviction: 80
horizon: bounded
created_at: 2026-04-12
archived_at: null
linked_subjects: [supplier-simon, product-line-guirlande-guinguette]
linked_records:
  - {type: order_id, value: 1234, source: mcp_achats}
  - {type: payment_id, value: stripe_xyz, source: mcp_treasury}
active_decisions: [2026-04-16-order-300m, 2026-04-17-acompte-30]
open_discussions: []
last_event:
  date: 2026-06-18
  type: booking_container
  ref: events/2026-06-18-booking-container.md
stress_tests_passed: 1
compiled_artifacts: []
---

## Quick

État : in_service, conviction 80
Statut : prod terminée, container en route, ETA 2026-08-22
Prochaines étapes : suivi douane, réception entrepôt
Risques : -
Liens forts : supplier-simon, product-line-guirlande-guinguette

## Détails

[synthèse rédigée du subject]
```

### Mini-frontmatter sur les sous-fichiers

```yaml
# events/<date>-<slug>.md
---
date: 2026-04-15
type: email                       # email | mcp_event | external_capture | ...
produced_by: external
source: imap
author: simon
linked_records: [{type: imap_thread, value: "<msg-id>"}]
---

# analyses/<date>-<slug>.md
---
date: 2026-04-13
type: analysis
produced_by: claude
invoked_skill: /restock
source_events: [2026-04-12-alerte-stock-sku-9016.md]
scoring:                          # selon la grille du type (français)
  tresorerie: 7
  delai: 8
  qualite: 9
  cout_total: 8
recommendation: "..."
---

# discussions/<date>-<slug>.md
---
date: 2026-04-15
type: discussion
produced_by: human_and_claude
participants: [benjamin, claude]
status: closed                    # open | closed
resulting_decision: 2026-04-16-order-300m-guinguette.yaml
---

# decisions/<date>-<slug>.yaml
---
date: 2026-04-16
type: decision
produced_by: human
decided_by: benjamin
parameters: {quantite: 1500, prix_unitaire_fob_eur: 10.0}
upstream_discussions: [2026-04-15-mix-300m-vs-400m.md]
upstream_analyses: [2026-04-13-restock-need.md]
status: active                    # active | archived
---
```

---

## Règles de gestion

1. **Création de type** : skill `/subject-create-type`, validation Benjamin obligatoire. Un type mal défini pollue toutes ses instances. Les `analysis_dimensions` et `expected_events` doivent être en français snake_case (contenu métier).
2. **Création d'instance** : skill `/subject-create <type> <name>`. Pré-remplit `MEMORY.md` depuis le `TEMPLATE.md` du type. Met à jour les liens bidirectionnels avec les `linked_subjects` parents.
3. **Cycle de vie γ** : la maturation est portée par le skill `/documente` (ex-`/forge`). Les transitions `seed → debating` et `debating → tentative` sont **automatiques** quand les conditions sont remplies (≥1 event ou discussion ouverte ; ≥1 décision active). La transition `debating → tentative` bump conviction à 50. Les transitions vers `stress_testing`, `doctrine`, `in_service`, `under_review`, `archived` restent manuelles et passent par `/stress-test`, `/compile-doctrine`, ou décision Benjamin. Le mot « forge » reste utilisé pour désigner le cycle γ et le moteur Python sous-jacent, mais il n'y a plus de skill `/forge` côté utilisateur.
4. **Stress test** : skill `/stress-test` réutilise `/council` (multi-perspective contradicteur/steelman/yagni). Met à jour `conviction` (+10 si passé, −15 si raté). Décision finale humaine — le skill ne tranche jamais seul.
5. **Soudure (fusion)** : skill `/subject-merge <A> <B>` après validation humaine obligatoire. Les sources sont archivées avec pointeur `merged_into` vers le nouveau subject consolidé. Les liens entrants sont redirigés.
6. **Compilation en exécutable** : skill `/compile-doctrine` actif uniquement si `forging_state: doctrine && conviction ≥ 80`. Génère selon le type de doctrine :
   - **Déclarative** ("X est vrai") → règle dans `MEMORY.md` du domaine
   - **Procédurale** ("voici comment faire X") → skill auto-généré
   - **Comportementale** ("surveiller X et agir si Y") → agent SDK (archi C)
   - **Évitement** ("ne jamais Y") → injection skill ou negative keyword
   - **Métrique/seuil** → monitor + alerte
   - **Routing** → foreign key dans agent existant
7. **Pas de migration forcée** : les anciens `MEMORY.md` / `discussions/` / `decisions/` sans frontmatter étendu restent valides. Adoption opportuniste (lors de modification).
8. **Producteur (`produced_by`)** : `external` (monde/MCP), `claude` (Claude seul), `human_and_claude` (échange), `human` (Benjamin valide).
9. **Lecture en cascade** : niveau 1 = `entreprise/SUBJECTS-INDEX.md` toujours, niveau 2 = `MEMORY.md` du subject, niveau 3 = un fichier précis à la demande.

---

## Rapport au pattern existant

- **CE-Lab / WM-Lab / Alter-Lab** continuent d'exister sans modification. Ces 3 Labs sont des subjects matures (instances du type `strategic-vision`). `/CE-analyse`, `/WM-analyse`, `/alter-analyse` restent inchangés.
- **`discussions/` + `decisions/` répartis** dans les services restent valides (cf. `entreprise/config/rules/savoirs.md` § Stockage réparti). Les nouveaux fichiers utilisent le frontmatter étendu, les anciens migrent **opportunistiquement** quand on les touche.
- **`savoirs/`** reste pour les savoirs procéduraux établis (glossaires, SOP). Les subjects sont pour les sujets en cours d'accumulation et de maturation.
