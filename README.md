# SOCLE

**La mémoire d'entreprise structurée pour Claude Code.** C'est la 4ᵉ couche de mémoire, après le contexte de session, l'auto-memory et `CLAUDE.md`.

- 🇫🇷 **S**ynthèse et **O**rganisation des **C**onnaissances et **L**eçons d'**E**ntreprise
- 🇬🇧 **S**tructured **O**rganizational **C**ontext & **L**ifecycle **E**ngine

L'auto-memory et `CLAUDE.md` stockent du markdown libre. SOCLE range la connaissance **par sujet** : un skill, un outil, un service, un projet, un fournisseur, une commande. Chaque sujet a sa mémoire bornée (`MEMORY.md`), ses discussions, ses décisions et ses événements. Cette mémoire s'enrichit au fil du temps : à chaque passage de `/documente`, la conversation est capturée en fichiers typés et le `MEMORY.md` est re-synthétisé. SOCLE fait aussi respecter une checklist de fin de bloc (discussion, décision, mémoire, commit, push), vérifiée par un hook.

Anciennement `claude-forge`, renommé le 2026-09-16 : un plugin tiers ne doit pas laisser croire qu'il est édité par Anthropic. Les anciennes URL GitHub redirigent. Le binaire s'appelle toujours `forge` : c'est l'outil, SOCLE est le produit.

## Démarrage rapide

```
/plugin marketplace add rubee-labs/socle
/plugin install socle@rubee-labs
```

Puis, une fois dans chaque dépôt qui adopte SOCLE :

```
/forge-init
```

`/forge-init` choisit où ranger la mémoire, écrit le `.forge.yaml` et active la checklist post-bloc. Ensuite, en fin de travail :

```
/documente <dossier>
```

`/documente` crée le `MEMORY.md` du dossier s'il n'existe pas, convertit un ancien `MEMORY.md` au format SOCLE, écrit la discussion et la décision de la session, re-synthétise la mémoire et committe. Il ne pose aucune question : les agents autonomes peuvent le lancer en fin de cycle.

**Prérequis** : `git`, `bash` et `python3` (bibliothèque standard uniquement, aucune dépendance à installer). Sous Windows : Git Bash et une commande `python3` disponible.

## Concepts

### Subject

**Tout dossier qui contient un `MEMORY.md` dont l'en-tête porte `forging_state` est un subject**, où qu'il soit dans le dépôt. Le chemin ne décide de rien : `skills/facturation/`, `services/achats/` ou `subjects/order-412/` sont des subjects au même titre.

Chaque subject peut contenir quatre dossiers, distingués par qui produit le contenu :

| Dossier | Producteur | Contenu |
|---|---|---|
| `events/` | le monde extérieur (email, MCP, API) | ce qui arrive au sujet |
| `analyses/` | Claude | analyses, stress tests, évaluations |
| `discussions/` | l'humain et Claude | le cheminement : pourquoi, alternatives |
| `decisions/` | l'humain | le résultat : quoi, paramètres, preuve d'application |

Un sujet peut aussi avoir un dossier `rapports/` : un run ou un journal y écrit son compte rendu, jamais dans le `MEMORY.md`.

### Type et capacités

Le type d'un subject est lu dans cet ordre, la première source qui répond gagne :

1. le champ `type:` de l'en-tête du `MEMORY.md` ;
2. la table `type_by_path` du `.forge.yaml`, si le dépôt en a une ;
3. sinon, Claude choisit parmi les types déclarés dans le dépôt et l'écrit dans l'en-tête.

Une fois écrit, le type n'est jamais recalculé.

Chaque type déclare ses **capacités** dans son `types/<type>/REFERENCE.md`. `/documente` saute sans erreur les étapes dont la capacité est absente.

| Capacité | Ce qu'elle active |
|---|---|
| `memory` | un `MEMORY.md` borné |
| `decisions` | les dossiers `discussions/` et `decisions/` |
| `lifecycle` | l'état `actif` / `archived` |
| `events` | `last_event` et l'alerte de stagnation |
| `links` | `linked_subjects`, la section `## Liens` et la propagation aux sujets liés |

Types génériques livrés dans `types/` :

| Type | Capacités |
|---|---|
| `skill`, `skill-cas`, `tool`, `agent`, `service` | memory, decisions, lifecycle |
| `projet` | les cinq |

Un dépôt peut surcharger ces types ou créer les siens (`/subject-create-type`), par exemple `supplier`, `supplier-order` ou `marketing-campaign`, avec leur grille d'analyse et le modèle de nommage de leurs instances. Un type inconnu reçoit memory, decisions et lifecycle, et le scanner le signale.

### Format du `MEMORY.md`

En-tête : `name`, `type` et `forging_state` (obligatoires), `derniere_maj`, `memory_max_kb` (facultatif, 8 Ko par défaut), `linked_subjects` (si `links`), `last_event` (si `events`).

Corps, dans cet ordre :

1. `## Quick` : moins de 100 mots, lu en premier par Claude.
2. `## Doctrine en vigueur` : une ligne par règle.
3. `## Décisions actives` : au plus 10, chacune en pointeur vers son fichier.
4. `## Règles apprises`.
5. `## Détails` : facultatif, borné, sans sous-sections datées.
6. `## Liens` : seulement si le type a `links`.

La mémoire est **bornée** : au-delà du plafond, ou si un journal daté s'y est glissé, `/documente` remplace les recopies de décisions par des pointeurs et déplace le reste, à l'identique, dans `rapports/`.

### Discussions et décisions

Une discussion (`discussions/AAAA-MM-JJ-<slug>.md`) garde le cheminement. Une décision (`decisions/AAAA-MM-JJ-<slug>.yaml`) garde le résultat. Elle porte deux champs inspirés de MADR (modèle : `templates/decision.body.yaml`) :

- `options_considerees` : les alternatives écartées et pourquoi. Une décision sans alternative écartée n'est qu'un constat.
- `confirmation` : la preuve qu'elle est appliquée et son échéance. Passé l'échéance sans verdict, le scanner lève l'alerte `decision_echue`.

L'en-tête des deux fichiers est écrit par Python, jamais à la main.

### État et historique

Un subject est `actif` ou `archived`. Le passage de l'un à l'autre est toujours manuel. Le « cycle de vie » de SOCLE, c'est l'historique cumulatif du sujet : événements, discussions et décisions s'accumulent, et la mémoire est re-synthétisée à chaque étape.

### Liens entre sujets

Un type qui a `links` relie ses sujets par `linked_subjects` (par exemple, une commande liée à son fournisseur et à son transitaire). Quand un sujet bouge, `/documente` propage son dernier événement et régénère le `## Quick` des sujets liés, sur un seul niveau. Les liens sont résolus par le `name` de l'en-tête, puis par le nom du dossier ; deux sujets homonymes bloquent la résolution et lèvent l'alerte `duplicate_name`. Si le type déclare ses relations (`typical_linked_types`), les liens deviennent un graphe typé (`ordered_from`, `shipped_via`…).

## Checklist post-bloc

Un bloc se termine quand quelque chose a abouti : une décision, un document, un skill corrigé, une analyse conclue. La checklist (`rules/post-bloc.md`) demande alors cinq étapes, dans l'ordre et sans demander : discussion, décision, mémoire (`/documente`), commit, push. Claude affiche la preuve en fin de réponse :

```
✅ discussion   (ou ⏭️ raison en 1 ligne)
✅ décision     (ou ⏭️ raison en 1 ligne)
✅ memory
✅ commit       <hash-court>
✅ push
```

Deux hooks la font respecter dans les dépôts où `post_bloc: true` figure au `.forge.yaml` (écrit par défaut par `/forge-init`) :

- **SessionStart** : charge la règle dans le contexte de Claude au démarrage, après `/clear` et après une compaction. Rien à recopier dans le `CLAUDE.md`.
- **Stop** : bloque une seule fois la fin de réponse si un fichier modifié pendant la session n'est pas committé, ou si le `MEMORY.md` du sujet concerné n'est pas daté du jour. Claude finit la checklist ou justifie l'exception en une ligne.

Un dépôt sans `.forge.yaml` n'est jamais concerné : le plugin est installé pour l'utilisateur, donc chargé dans tous ses projets. Pour couper la checklist dans un dépôt : `post_bloc: false`.

## Skills

| Skill | Rôle |
|---|---|
| `/documente [<dossier>]` | Point d'entrée unique : capture, écriture, re-synthèse bornée, propagation, commit. Sans question. |
| `/forge-init` | Configure SOCLE dans un dépôt (`.forge.yaml`, `subjects/`, `types/`, checklist). |
| `/subject-create-type` | Crée un type : grille d'analyse, événements attendus, relations, capacités. |
| `/subject-create` | Crée un subject à partir d'un type existant. |
| `/subject-merge` | Fusionne deux subjects qui décrivent le même objet, après validation humaine. |
| `/skillify` | Transforme une procédure faite à la main en skill testé, avec sa provenance (`source_subjects`). |
| `/cross-modal-review` | Fait noter la synthèse d'un subject par plusieurs modèles (cohérence, complétude, spécificité, citations). |

## Binaire `forge`

Les skills délèguent toute la mécanique à `forge`, qui répond en JSON (`{"ok": true|false, ...}`).

| Commande | Rôle |
|---|---|
| `forge init` | Écrit le `.forge.yaml` et crée `subjects/` + `types/` (`--no-post-bloc`, `--force`). |
| `forge documente <cmd>` | Moteur de `/documente` : `prepare`, `convert`, `write-capture`, `check-memory`, `patch-section`, `patch-frontmatter`, `cascade-last-event`, `scan-impacted`, `commit-atomic`… |
| `forge migrate --dry-run` | Liste les `MEMORY.md` encore à l'ancien format et le type que chacun recevrait. N'écrit rien. |
| `forge engine <dossier>` | Calcule l'état d'un subject (événements, décisions, propagation). |
| `forge scanner` | Régénère `SUBJECTS-INDEX.md` et `SUBJECT-POOL-METRICS.md`, et lève les alertes : `stagnation`, `decision_echue`, `duplicate_name`, `unknown_type`, `merger_candidate`. |
| `forge autolink <cmd>` | Graphe typé : `extract`, `graph-query`, `reconcile`. |
| `forge graph render` | Graphe interactif des subjects en HTML (filtres par type et état). |
| `forge okf-sync <cmd>` | Écrit les liens dans le corps des `MEMORY.md` (section `## Liens`), lisibles par un lecteur de l'Open Knowledge Format (OKF). |
| `forge skillify <cmd>` | `scaffold`, `check`, `audit` des skills compilés. |
| `forge eval <cmd>` | Moteur de `/cross-modal-review`. |
| `forge bench <cmd>` | Mesure la précision de la recherche dans la mémoire. |

## Configuration (`.forge.yaml`)

Toutes les clés sont facultatives. Sans `.forge.yaml`, SOCLE s'auto-détecte, mais la checklist post-bloc reste inactive.

```yaml
output_dir: .                 # où écrire SUBJECTS-INDEX.md et SUBJECT-POOL-METRICS.md ("." = racine)
types_roots: ["."]            # où chercher les <root>/types/ propres au dépôt
pool_roots: ["."]             # compatibilité : ne limite plus la découverte, défaut de types_roots
domain_roots: []              # préfixes regroupés dans les métriques (cosmétique)
skill_visibility: mon-projet  # valeur écrite dans l'en-tête des skills générés par /skillify

type_by_path:                 # emplacement → type, le premier motif qui correspond gagne
  - pattern: "*/skills/*"
    type: skill
  - pattern: "*/tools/*"
    type: tool
  - pattern: "services/*"
    type: service

post_bloc: true               # checklist post-bloc (écrit par /forge-init)
post_bloc_exclusions: ["data/cache/"]   # préfixes ignorés par le hook Stop
```

`type_by_path` ne s'applique pas sous `subjects/` : là, seuls l'en-tête ou Claude décident du type. Le plafond de taille se règle par sujet, dans l'en-tête du `MEMORY.md` (`memory_max_kb`).

## Adopter SOCLE dans un dépôt existant

Pas de migration en masse. La première fois que `/documente` touche un `MEMORY.md` à l'ancien format, il le convertit sur place dans le même commit : en-tête complété (`name`, `type`, `forging_state: actif`), contenu rangé dans les sections du format, rien de supprimé. Un `MEMORY.md` non converti n'apparaît ni dans l'index ni dans les alertes. `forge migrate --dry-run` montre ce qui reste à convertir.

## Intégrations

- **Obsidian** : `integrations/obsidian-forge-bridge/` est un plugin Obsidian en lecture seule. Il transforme les `linked_subjects` en wikilinks, pour profiter du graphe, des rétroliens et de la recherche d'Obsidian.
- **OKF** : `forge okf-sync` écrit les liens au format attendu par l'Open Knowledge Format.
- **Graphe HTML** : `forge graph render` produit une page autonome, sans Obsidian.

## Différence avec claude-mem

| Dimension | claude-mem | SOCLE |
|---|---|---|
| Axe | temporel (continuité d'une session à l'autre) | structurel (mémoire par sujet) |
| Format | SQLite + Chroma + CLAUDE.md automatique | `MEMORY.md` borné par sujet + fichiers typés |
| Auteur | Claude, automatiquement | humain et Claude ensemble |
| Historique | aucun | cumulatif par sujet, archivage manuel |
| Liens entre sujets | aucun | graphe typé, propagation sur 1 niveau |
| Décisions et discussions | non distinguées | deux artefacts distincts, décisions avec preuve et échéance |
| Discipline de fin de travail | aucune | checklist post-bloc vérifiée par hook |

Les deux sont complémentaires.

## Architecture

```
socle/
├── .claude-plugin/   manifeste du plugin et de la marketplace
├── bin/              binaire forge et moteurs Python
├── commands/         commande /documente
├── hooks/            SessionStart (règle post-bloc, rappel /forge-init) et Stop (checklist)
├── skills/           documente, forge-init, subject-create, subject-create-type,
│                     subject-merge, skillify, cross-modal-review
├── types/            types génériques (skill, skill-cas, tool, agent, service, projet)
├── rules/            subject-pool.md (doctrine complète), post-bloc.md
├── templates/        modèles de MEMORY.md et de décision
├── integrations/     pont Obsidian
├── docs/             spécifications de conception
└── tests/            tests des moteurs et des hooks (pytest)
```

La doctrine complète du modèle est dans [`rules/subject-pool.md`](rules/subject-pool.md). Les tests se lancent avec `python3 -m pytest tests`.

## Versions

| Version | Date | Changement principal |
|---|---|---|
| 0.7.2 | 2026-10-11 | Correctifs : seuls les vrais titres de journal sont déplacés (plus les titres thématiques datés) ; `commit-atomic` lit les chemins depuis le dossier projet, ne committe que ses chemins et n'ajoute plus de trailer ; `rapports/` committé ; `## Détails` réécrit seulement si la borne l'exige. |
| 0.7.1 | 2026-10-11 | Correctifs : titres sans accents reconnus à la conversion ; `type_by_path` ignoré sous `subjects/`. |
| 0.7.0 | 2026-10-10 | Subject reconnu par son en-tête, où qu'il soit ; types génériques et capacités ; `/documente` en un seul circuit, sans question ; conversion sur place ; `forge migrate --dry-run` ; liens résolus par `name`. |
| 0.6.1 | 2026-10-10 | `MEMORY.md` borné aussi pour les subjects ; titres datés détectés comme journal. |
| 0.6.0 | 2026-10-09 | Prêt à l'emploi : `/forge-init` active la checklist, la règle est chargée au démarrage. |
| 0.5.0 | 2026-09-27 | Checklist post-bloc et hook Stop. |
| 0.4.0 | 2026-09-16 | `claude-forge` devient SOCLE ; dépôt public. |
| 0.3.x | 2026-09-14 | État réduit à `actif` / `archived` ; alerte `decision_echue`. |
| 0.2.x | 2026-06 → 09 | Configuration par dépôt (`.forge.yaml`), `forge init`, mémoire bornée, décisions MADR, provenance de `/skillify`. |
| 0.1.0 | 2026-05-05 | Extraction depuis claude-enterprise. |

## Auteur

Benjamin Hamon (Rubee Labs).

## Licence

**PolyForm Shield 1.0.0**, voir [LICENSE.md](LICENSE.md).

Le code source est visible et l'usage est libre, y compris commercial **en interne**. Seule interdiction : s'en servir pour proposer un produit ou un service **concurrent** de SOCLE ou des prestations de Rubee Labs bâties dessus. Ce n'est donc pas une licence open source au sens de l'OSI.
