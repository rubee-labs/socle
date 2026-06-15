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

> Note (v0.2.0) : ces emplacements sont les **défauts de claude-enterprise**, pas une contrainte du plugin. Chaque repo définit ses `pool_roots`/`types_roots`/`output_dir` via `.forge.yaml` (cf. README § Configuration par-repo). Sans config, l'index s'écrit dans `entreprise/` si ce dossier existe, sinon à la racine du repo.

### 4 sous-dossiers — distingués par producteur

| Dossier | `produced_by` | Exemple |
|---|---|---|
| `events/` | `external` (monde / MCPs) | email Simon, vente Amazon, alerte stock |
| `analyses/` | `claude` (Claude seul) | scoring d'un signal externe sur la grille du type |
| `discussions/` | `human_and_claude` (échange) | débat 300m vs 400m |
| `decisions/` | `human` (validation Benjamin) | "commande 300m IP44, acompte 30%" |

---

## Cycle de vie (3 états)

Refondu le 2026-05-10 (cf. `subjects/claude-forge/decisions/2026-05-10-cycle-gamma-refonte-3-etats.yaml`). Le cycle γ historique à 8 états + conviction numérique a été remplacé par un cycle à **3 états**, transitions 100 % manuelles, sans seuil automatique.

```
actif ──► mature ──► archived
   ▲        │
   └────────┘ (retour possible si contre-signal)
```

### États

| État (`forging_state`) | Description |
|---|---|
| `actif` | Subject en accumulation / en cours de réflexion. Sources collectées, opinion encore en formation ou volontairement débattue. |
| `mature` | Subject avec une opinion formée et stable. Peut avoir été confronté (cross-modal-review, stress-test) ou pas — la maturation est jugée par l'humain, pas par un seuil. |
| `archived` | Subject clos. Leçons remontées vers les subjects parents le cas échéant. |

### Transitions

Toutes manuelles, validées explicitement par Benjamin via `/documente` :

- `actif → mature` : « cette opinion est suffisamment ferme pour être référence »
- `mature → actif` : contre-signal détecté, on rouvre la réflexion
- `actif|mature → archived` : subject clos

**Pas de transition automatique.** Le moteur (`forge_engine.py`) ne mute jamais `forging_state` tout seul. Il fournit des informations descriptives (events récents, décisions actives, stats agrégées) qui aident Benjamin à décider, mais la décision lui appartient.

### Rétrocompatibilité avec l'ancien cycle γ

Les subjects existants peuvent contenir un ancien `forging_state` (`seed`, `debating`, `tentative`, `stress_testing`, `doctrine`, `in_service`, `under_review`). Le moteur le mappe automatiquement :

| Ancien | Nouveau |
|---|---|
| `seed`, `debating`, `tentative` | `actif` |
| `stress_testing`, `doctrine`, `in_service`, `under_review` | `mature` |
| `archived` | `archived` |

Pas de migration forcée — les subjects gardent leur ancien `forging_state` jusqu'au prochain `/documente`, qui peut écrire la valeur normalisée.

Les champs `conviction` (0..100), `stress_tests_passed`, `compiled_artifacts` du frontmatter sont **déprécié·e·s** : ignorés par le moteur, conservés en lecture pour ne pas casser l'existant. Les nouveaux subjects ne les écrivent pas.

### Skills du subject pool

| Commande | Statut | Effet |
|---|---|---|
| `/subject-create-type <name>` | actif | Crée un nouveau TYPE (REFERENCE.md + TEMPLATE.md). Validation Benjamin obligatoire. **Invocable directement ou indirectement via `/documente`**. |
| `/subject-create <type> <name>` | actif | Instancie un subject à partir d'un type existant. **Invocable directement ou indirectement via `/documente`** (mode silencieux). |
| `/documente <subject-path> [--type <type>]` | actif | **Orchestrateur unique du subject pool**. Création paresseuse type/instance si absents, capture conversation (discussion + décision), re-synthèse continue (Quick + Détails régénérés, cascade horizontale 1 niveau). **Plus de transitions auto** depuis 2026-05-10. |
| `/subject-merge <A> <B>` | actif | Soudure de 2 subjects (validation Benjamin obligatoire). |
| `/skillify` | actif (depuis 2026-05-10) | Compile un workflow ad hoc en skill réutilisable (SKILL.md + script + tests + fixtures). Compilation continue à l'usage, pattern Garry Tan. **Trigger humain explicite** (« skillify it ») — pas de déclenchement automatique. Hint post-commit suggéré par `/documente` Phase J si workflow ad hoc répété détecté. Voir `bin/skillify_engine.py`. |
| `/cross-modal-review` | actif (depuis 2026-05-10) | Évalue la qualité d'un MEMORY.md re-synthétisé (4 axes : cohérence, complétude, spécificité, citations) via 2-3 modèles distincts (Opus + Sonnet + Haiku). **À invoquer typiquement avant transition `actif → mature`** — pour vérifier que la synthèse tient la route avant de considérer le subject comme stable. Voir `bin/eval_engine.py`. |
| `/stress-test <subject-path>` | optionnel, à la demande | Challenge un subject sous 3 perspectives (contradicteur, steelman, yagni). **Découplé du cycle** depuis 2026-05-10 — invocable à tout moment quand Benjamin doute, sans transition d'état ni mutation de conviction. |
| `/compile-doctrine` | **abandonné** | Skill théorique jamais utilisé en pratique. Sa branche « procédurale → skill » est désormais portée par `/skillify`. Les autres branches (règle / agent SDK / injection / monitor / FK) seront instruites au cas par cas si le besoin émerge. |

Le mot **« forge »** désigne le pattern subject pool et le moteur Python sous-jacent (`forge_engine.py`, `forge_lib.py`, `forge_scanner.py`, `autolink_engine.py`, `skillify_engine.py`, `eval_engine.py`).

### Quand invoquer ces skills (triggers humains attendus)

Aucun de ces skills n'a de déclencheur automatique — la décision reste humaine. Voici les **triggers naturels** où Benjamin doit y penser :

| Trigger | Skill suggéré |
|---|---|
| Tu viens de faire à la main un workflow que tu sais que tu vas refaire (≥ 2 occurrences déjà observées) | `/skillify` |
| Tu envisages de passer un subject de `actif` à `mature` | `/cross-modal-review` (vérifier la qualité de la synthèse) |
| Tu doutes d'un subject `mature` (la conclusion tient-elle sous adversité ?) | `/stress-test` |
| Un contre-signal apparaît sur un subject `mature` (data nouvelle qui contredit) | repasser le subject à `actif` via `/documente` (transition manuelle) |
| Un workflow révèle que 2 subjects sont en réalité la même entité | `/subject-merge` |
| Un nouveau pattern de subject émerge qui n'a pas de type | `/subject-create-type` (souvent invoqué via `/documente` lazy) |

`/documente` Phase J post-commit affiche des **hints** sur `/skillify` et `/cross-modal-review` quand les conditions sont remplies — pas d'exécution auto, juste un rappel pédagogique.

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
- `## Détails` n'est **PAS** modifié en cascade (réservé à l'invocation directe `/documente` sur ce subject — pour éviter qu'une cascade avec vue partielle écrase un détail riche)
- **Pas de transition d'état automatique** (depuis 2026-05-10) — `forging_state` n'est jamais muté par le moteur, seulement par décision humaine via `/documente`

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
| Champs frontmatter (`type`, `name`, `forging_state`, `linked_subjects`…) | Valeurs de `analysis_dimensions` (ex: `tresorerie`, `delai`) |
| Valeurs de `forging_state` (`actif`, `mature`, `archived`) | Valeurs de `expected_events` (ex: `alerte_stock`, `email_fournisseur_disponibilite`) |
| Valeurs de `produced_by` (`external`, `claude`, `human_and_claude`, `human`) | Tags personnels |
| Valeurs de `horizon` (`bounded`, `permanent`, `unbounded`, `cyclic`) | Contenu narratif (Quick, Détails) |
| Noms de **types** (`supplier-order`, `incident`, `marketing-campaign`…) | Suffixes identifiants des subjects (ex: `simon`, `400`, `2026-q2-brumeaux`) |
| Noms de dossiers structuraux (`subjects/`, `types/`, `events/`, `analyses/`…) | Slugs de discussions / décisions |

**Pourquoi bilingue** : le squelette anglais permet à n'importe quel skill ou outil tiers de raisonner sur le pattern (un `forging_state: mature` est identifiable partout). Le contenu français permet à Benjamin et à l'équipe Rubee de lire et utiliser naturellement les dimensions métier sans traduction mentale.

**Convention dates** : `*_at` (verbe au passé), statuts au présent.

### Champs du frontmatter d'un subject (instance)

| Champ | Type | Description |
|---|---|---|
| `name` | str | Nom du subject |
| `type` | str | Référence au type parent |
| `forging_state` | enum | État du cycle de vie γ |
| ~~`conviction`~~ | ~~int~~ | **déprécié** depuis 2026-05-10. Conservé en lecture sur les anciens subjects, ignoré. |
| `horizon` | enum | `bounded`, `permanent`, `unbounded`, `cyclic` |
| `created_at` | date | Date de création |
| `archived_at` | date or null | Date d'archivage |
| `linked_subjects` | list[str] | Liens vers d'autres subjects |
| `linked_records` | list[obj] | Foreign keys MCP `{type, value, source}` |
| `active_decisions` | list[ref] | Décisions actives |
| `open_discussions` | list[ref] | Discussions ouvertes |
| `last_event` | obj | Dernier event `{date, type, ref}` |
| ~~`stress_tests_passed`~~ | ~~int~~ | **déprécié** depuis 2026-05-10. /stress-test découplé du cycle. |
| ~~`compiled_artifacts`~~ | ~~list[ref]~~ | **déprécié** depuis 2026-05-10. Plus de cycle de compilation par seuil. |
| `linked_skills` | list[str] | (optionnel) skills produits via `/skillify` à partir de ce subject |
| `linked_evals` | list[ref] | (optionnel) cross-modal-reviews effectuées (`analyses/<date>-cross-modal-eval.md`) |
| `quick_produced_from` | obj | (optionnel) provenance backward du `## Quick` régénéré par `/documente` Phase F. Liste les sources qui ont produit la synthèse courante : `{events: [...], analyses: [...], decisions: [...], generated_at: <iso8601>}`. Permet de remonter du Quick aux fichiers sources sans deviner. Ajouté 2026-05-21 (analyse Forge-Lab cognee). |
| `title` | str | (optionnel, OKF v0.1) Nom lisible du subject pour les UI tierces (viewers OKF, Obsidian Dataview, Notion). Si absent, les consumers OKF dérivent du filename. |
| `description` | str | (optionnel, OKF v0.1) Résumé court (1 ligne) pour les indexes et previews OKF. |
| `resource` | str (URI) | (optionnel, OKF v0.1) URI canonique de l'asset externe que le subject décrit (ex: lien BigQuery table, console Cloud, dashboard). |
| `tags` | list[str] | (optionnel, OKF v0.1) Étiquettes libres pour filtrage cross-cutting dans les viewers OKF. |
| `timestamp` | iso8601 | (optionnel, OKF v0.1) Dernière révision significative. Alias de `last_event.date` si présent. |

---

## Lecture en cascade (rapidité de Claude)

| Niveau | Fichier | Quand |
|---|---|---|
| 1 | `<output_dir>/SUBJECTS-INDEX.md` (défaut `entreprise/` si présent, sinon racine du pool) | Toujours, au démarrage de session (carte des subjects actifs) |
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
forging_state: mature
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
linked_skills: []
linked_evals: []
quick_produced_from:
  events: [2026-04-15-eta-update.md, 2026-06-18-booking-container.md]
  analyses: [2026-04-13-restock-analysis.md]
  decisions: [2026-04-16-order-300m-guinguette.yaml, 2026-04-17-acompte-30.yaml]
  generated_at: 2026-06-19T08:30:00Z
---

## Quick

État : mature
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
date: 2026-04-15                  # recorded_at : quand on a appris / écrit l'event
valid_at: 2026-08-22              # (optionnel) quand le fait est valide dans le monde
                                   # ex: ETA annoncée, date d'effet d'une décision, deadline
                                   # Distinct de `date` (recorded_at). Si absent : valid_at = date.
                                   # Ajouté 2026-05-21 (analyse Forge-Lab cognee, Q3 bi-temporal).
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
3. **Cycle de vie (3 états)** : `actif` / `mature` / `archived`. Toutes les transitions sont **manuelles**, validées explicitement par Benjamin via `/documente`. Le moteur ne mute jamais `forging_state` automatiquement (depuis refonte 2026-05-10). Les anciens états (`seed`, `debating`, `tentative`, `stress_testing`, `doctrine`, `in_service`, `under_review`) sont mappés en lecture par le moteur — pas de migration forcée.
4. **Stress test** : skill `/stress-test` est **optionnel et à la demande**. Confronte un subject sous 3 perspectives (contradicteur, steelman, yagni). **Pas de mutation de `forging_state`** ni de `conviction`. Sortie : analyse adversariale dans `<subject>/analyses/<date>-stress-test.md`. Décision finale humaine.
5. **Soudure (fusion)** : skill `/subject-merge <A> <B>` après validation humaine obligatoire. Les sources sont archivées avec pointeur `merged_into` vers le nouveau subject consolidé. Les liens entrants sont redirigés.
6. **Compilation en exécutable** (refonte 2026-05-10) : `/compile-doctrine` est **abandonné** (théorique, jamais utilisé). La compilation continue à l'usage est portée par `/skillify` pour le pattern « procédurale → skill ». Les autres patterns historiquement listés (déclarative → règle, comportementale → agent SDK, évitement → injection, métrique → monitor, routing → FK) restent à instruire au cas par cas si le besoin émerge concrètement — pas d'API générique pré-construite.
7. **Pas de migration forcée** : les anciens `MEMORY.md` / `discussions/` / `decisions/` sans frontmatter étendu restent valides. Adoption opportuniste (lors de modification).
8. **Producteur (`produced_by`)** : `external` (monde/MCP), `claude` (Claude seul), `human_and_claude` (échange), `human` (Benjamin valide).
9. **Lecture en cascade** : niveau 1 = `<output_dir>/SUBJECTS-INDEX.md` (défaut `entreprise/`, cf. `.forge.yaml`) toujours, niveau 2 = `MEMORY.md` du subject, niveau 3 = un fichier précis à la demande.

---

## Rapport au pattern existant

- **CE-Lab / WM-Lab / Alter-Lab** continuent d'exister sans modification. Ces 3 Labs sont des subjects matures (instances du type `strategic-vision`). `/CE-analyse`, `/WM-analyse`, `/alter-analyse` restent inchangés.
- **`discussions/` + `decisions/` répartis** dans les services restent valides (cf. `entreprise/config/rules/savoirs.md` § Stockage réparti). Les nouveaux fichiers utilisent le frontmatter étendu, les anciens migrent **opportunistiquement** quand on les touche.
- **`savoirs/`** reste pour les savoirs procéduraux établis (glossaires, SOP). Les subjects sont pour les sujets en cours d'accumulation et de maturation.

---

## Conformance Open Knowledge Format (OKF v0.1)

Depuis le 2026-06-15 (analyse Forge-Lab #8), un subject pool Forge est **conformant OKF v0.1** — la spec ouverte publiée par Google Cloud Data Cloud le 2026-06-12 ([repo](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf), [SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)).

OKF formalise le pattern « LLM wiki » qui sous-tend Forge depuis sa Phase 0. Forge couvre les 3 conditions de conformance :

1. **Markdown + YAML frontmatter** — Format natif de chaque `MEMORY.md` (et des sous-fichiers `events/`, `analyses/`, `discussions/`, `decisions/`).
2. **Champ `type` obligatoire** — Présent dans le frontmatter de chaque subject (référence au type parent).
3. **Cross-links dans le body** — Émis par `forge okf-sync` dans une section `## Liens` entourée de markers HTML idempotents.

Conséquence pratique : un consumer OKF tiers (le visualizer Google Cytoscape.js, Obsidian, Notion, MkDocs, Hugo, n'importe quel parser markdown + frontmatter) **lit directement** un bundle Forge sans translation. Inversement, Forge peut absorber un bundle OKF tiers sans modification.

### Couches Forge au-dessus d'OKF (spécifiques, non-OKF)

- **Cycle de vie γ 3 états** (`actif` / `mature` / `archived`)
- **4 sous-dossiers par producteur** (`events/` / `analyses/` / `discussions/` / `decisions/`)
- **Autolink typed déterministe** via `typical_linked_types` enrichi
- **Compilation continue** via `/skillify`
- **Cross-modal review** via `/cross-modal-review`
- **Orchestrateur unique** `/documente`
- **Bilingue squelette anglais / contenu français**
- **Lecture en cascade** SUBJECTS-INDEX → MEMORY.md → fichier

Ces couches restent **Forge-spécifiques** et ne sont ni requises ni interdites par OKF — la spec définit l'interopérabilité, pas le content model (« Extensions: Producers MAY include any additional keys. Consumers SHOULD preserve unknown keys when round-tripping »).

### `forge okf-sync` — maintien de la section `## Liens`

Le binaire `forge okf-sync` synchronise les `linked_subjects:` du frontmatter avec des markdown links inline dans le body de chaque `MEMORY.md`, entourés de markers `<!-- okf-links:start -->` / `<!-- okf-links:end -->` pour idempotence. Les paths sont relatifs au MEMORY.md émetteur (OKF §5.2) pour rester valides quel que soit le choix de bundle root du consumer.

```bash
forge okf-sync sync           # régénère tous les MEMORY.md
forge okf-sync sync --dry-run # voir ce qui changerait
forge okf-sync check          # liste les MEMORY.md où la section est absente ou périmée
```

**Déclenchement à la demande (décision 2026-06-15)** : la section `## Liens` n'est lue par AUCUN composant Forge (Claude, autolink, cascade lisent tous le `linked_subjects:` du frontmatter, toujours frais). Elle ne sert qu'aux **consommateurs OKF externes** (viewer Google, Obsidian). Donc `okf-sync` n'est **pas** câblé dans `/documente` (ce serait ~2s payés à chaque run pour un artefact que la boucle Claude ne consomme pas, et ça casserait l'atomicité du commit).

À la place, `forge graph render` **rafraîchit automatiquement** les liens inline avant de produire le HTML (« ouvrir un viewer » = le moment naturel de resync). Désactivable via `forge graph render --no-sync` pour un render rapide. Pour un usage hors `graph render` (ex: avant d'ouvrir le bundle dans Obsidian ou le viewer Google), lancer `forge okf-sync sync` manuellement.

Idempotent : invocation multiple sans effet si rien n'a changé.
