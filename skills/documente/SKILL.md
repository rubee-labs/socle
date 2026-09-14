---
name: documente
description: >-
  When the user asks to document a subject (decision, discussion, or session
  outcome) OR to re-synthesize a subject after new external events. Single
  orchestrator entry point for the subject pool: lazy-creates the type (with
  user validation) and the instance (silent) if missing, captures
  conversation-derived discussion and decision when present, regenerates
  Quick + Détails from all sub-files, propagates to linked_subjects (1 level),
  and normalizes legacy forging_state values on write (lifecycle is 2 manual
  states actif/archived since 2026-09-14). Replaces the legacy /forge skill
  (archived). Optional
  --type argument for skills callers. Trigger on "documente", "enregistre la
  décision", "sauvegarde", "log la décision", "mets à jour le memoire",
  "re-synthétise", "compile le subject".
type_anthropic: 4
visibilite: entreprise
auteur: Benjamin
date_creation: 2026-03-31
version: 3.0
tags: [documentation, decision, discussion, memory, subject-pool, forge, orchestrator, workflow]
effort: medium
outils_requis: []
securite_externe: false
---

# Documente

## Objectif

**Orchestrateur unique du subject pool.** Combine quatre rôles dans un seul verbe utilisateur :

1. **Création paresseuse du type** (v2.1) : si le type n'existe pas, demander à l'utilisateur de le créer (workflow interactif `/subject-create-type`). C'est la seule étape qui peut requérir une validation utilisateur en amont.
2. **Création paresseuse de l'instance** (v2.1) : si le subject path n'existe pas (mais le type oui), invoquer `/subject-create` silencieusement, sans intervention utilisateur.
3. **Capture verticale historique** (ex-`/documente` 1.0) : extraire de la conversation une discussion ou décision tranchée, écrire les fichiers `discussions/` et `decisions/` avec frontmatters structurés.
4. **Re-synthèse continue** (ex-`/forge` archivé) : lire tous les sous-fichiers (`events/`, `analyses/`, `discussions/`, `decisions/`), régénérer `## Quick` + `## Détails` du `MEMORY.md`, propager aux `linked_subjects` sur 1 niveau, normaliser un `forging_state` legacy vers le cycle à 2 états (`actif` / `archived`, refonte 2026-09-14 — aucune transition automatique, seules les clôtures/réouvertures manuelles existent).

Le mot **« forge »** désigne le pattern subject pool et le moteur Python sous-jacent (`forge_engine.py`, `forge_lib.py`, `forge_scanner.py`). Il n'existe plus de skill `/forge` séparé — `/documente` est l'entry point unique côté utilisateur.

## Argument

`/documente [<subject-path>] [--type <type>]`

- `<subject-path>` (optionnel depuis v2.7) : chemin vers le dossier du subject (peut être inexistant — sera créé). Ex: `services/marketing/subjects/google-ads-brumeaux/`.
- `--type <type>` (optionnel) : type du subject. Utilisé par les skills appelants pour éviter l'inférence. Ex: `--type marketing-campaign`. Si omis, `/documente` infère ou demande.

**Inférence du path quand omis (v2.7)** : si l'utilisateur invoque `/documente` sans argument, le LLM doit inférer un path depuis le contexte de session **avant** d'appeler `forge documente prepare`. Heuristique en cascade :
1. Si la conversation porte sur un fichier identifiable (skill, MCP, tool, brief) → remonter au service propriétaire (`services/<x>/`).
2. Si la conversation porte sur un objet métier durable (commande, fournisseur, campagne) → proposer le path subject pool correspondant (`services/<x>/subjects/<name>/`).
3. Si rien d'identifiable → demander à Benjamin avec deux propositions concrètes (pas de menu vide).

Une fois le path inféré, `forge documente prepare` retourne `service_root` + `service_structure_exists` + `proposed_default_path`. La Phase F0.0 ci-dessous traite le cas où la structure folder est absente au niveau service.

## Quand utiliser

- Après une décision prise en session (le skill capturera la décision, écrira les fichiers, puis re-synthétisera le subject)
- Après une discussion aboutie qui mérite d'être tracée
- Après que `/control-tower` (ou un autre flux) a appendé un event à un subject — invocation **automatique** ou manuelle (avec ou sans Phase C de capture, selon que la conversation contient ou non une décision)
- Quand on veut juste rafraîchir la vue d'un subject (régénérer `## Quick` + cascade vers les linked_subjects) sans rien capturer
- Quand Claude détecte un signal de décision et le propose

## Gotchas

- **Création paresseuse v2.1** : si le subject path n'existe pas, `/documente` le crée automatiquement (via `/subject-create`) après avoir inféré ou reçu son type. Si le type lui-même n'existe pas, `/documente` **demande validation** avant d'invoquer `/subject-create-type` (acte structurel rare). Les skills appelants (/control-tower, /optimisation-campagne-google) doivent passer l'argument `--type` pour éviter l'inférence.
- **0 intervention sur création d'instance** : le pas `/subject-create` est silencieux. Si tu vois un prompt sur les linked_subjects pendant un appel automatique, c'est un bug — `/subject-create` doit utiliser des valeurs par défaut quand appelé depuis `/documente`.
- **Identifier le bon subject (ou dossier)** : si subject pool, le chemin doit pointer vers `<...>/subjects/<name>/`. Si le `MEMORY.md` n'existe pas, Phase B (création paresseuse) gère la création. En contexte classique (sans subjects/ dans le path), stocker au plus près du sujet (cf. workflow folder ci-dessous).
- **Une décision porte ses options écartées et sa preuve d'application (v2.9)** : clés `options_considerees` et `confirmation` à la racine du corps YAML (MADR). `write-capture` avertit sans refuser ; l'avertissement doit apparaître dans le récap.
- **Ne pas créer de décision si la discussion n'est pas aboutie** : si le statut est `en_cours` / `open`, créer uniquement la discussion. La décision viendra quand ce sera tranché.
- **Phases E-H lisent les sous-dossiers, ne les modifient pas** : seule la Phase D (`write-capture`) écrit dans `discussions/` et `decisions/`. Le reste lit puis régénère le `MEMORY.md` (frontmatter + Quick + Détails).
- **Préserver les sections custom du `## Détails`** : `### Notes libres`, `### Stress tests à prévoir`, ou toute section ajoutée à la main par Benjamin doit être conservée lors de la régénération.
- **Cascade horizontale = 1 niveau strict** : pas de récursion. Sur les linked_subjects, on régénère le `## Quick` mais **PAS** le `## Détails` (réservé à l'invocation directe sur ce subject — éviter qu'une vue partielle écrase un détail riche).
- **Aucune transition d'état automatique** (cycle 2 états depuis 2026-09-14) : le moteur ne mute jamais `forging_state`. Seules transitions possibles : `actif → archived` (clôture) et `archived → actif` (réouverture), toutes deux **manuelles avec validation utilisateur**. La seule écriture d'état sans validation est la **normalisation d'un legacy** (`seed`/`debating`/`tentative`/`mature`/… → `actif`) — sans changement sémantique, signalée dans le récap.
- **Idempotent** : 2 invocations consécutives sans nouvel input doivent produire un diff vide.
- **Commit atomique** : committer discussion + decision + memory.md (subject + cascade) ensemble dans un seul commit.
- **Propagation = proposition, pas imposition** : la Phase I (`scan-impacted` + jugement LLM) propose les modifications aux fichiers exécutants. L'utilisateur valide chaque modification.
- **Critère subject pool vs entité (v2.6)** : à chaque invocation `/documente` sur un path non-subject-pool, appliquer le critère positif de Phase F0 (voir détail dans la section Phase F0). Le **défaut est l'entité** (`<entité>/decisions/`), pas le subject pool. Subject pool est réservé aux **objets métier durables avec cycle de vie** (suppliers, commandes, campagnes, décisions architecturales long-terme). Une modification de code/comportement d'UNE entité (skill, MCP, tool) reste dans son `decisions/` — pas de proposition de migration. Ne pas re-proposer si Benjamin a refusé sur ce path précédemment (marqueur `migration_subject_pool: refused` dans une décision).
- **Structure service absente (v2.7)** : si `forge documente prepare` retourne `service_structure_exists: false` avec un `service_root` identifié (ex: `services/marketing/` existe mais `services/marketing/discussions/` et `services/marketing/decisions/` n'existent pas), la Phase F0.0 propose la création de la structure au niveau service par défaut (cohérent avec `services/achats/decisions/`, `services/tech/decisions/`). Subject pool reste une alternative explicite, mais n'est PAS proposé pour les modifications de code d'entité — seulement pour objets métier durables (cf. critère Phase F0). Une seule `AskUserQuestion` suffit (pas deux comme l'incident 2026-05-11 sur marketing).
- **Folder aussi instrumenté Python (v2.3)** : depuis la bascule, les Phases F2/F3/F5/F6 du workflow folder invoquent `documente_engine.py` (`write-capture`, `scan-impacted`, `commit-atomic`). Phase F4 (MAJ MEMORY.md format markdown) reste LLM only car le format n'est pas du frontmatter mais des sections markdown.
- **Fichiers temp uniques par invocation (v2.4)** : utiliser `mktemp /tmp/documente-*-body.XXXXXX` pour les body files passés à `write-capture`. Sinon 2 `/documente` parallèles écrasent leurs body files mutuellement (race condition observée le 2026-05-04 entre `/documente skills/documente` et `/documente knowledge-coordinator`). **Attention syntaxe BSD/macOS** : les `XXXXXX` doivent être en SUFFIXE final, pas suivis d'une extension (`.md` literal écrirait XXXXXX littéralement). L'extension n'est pas requise — `write-capture` lit le contenu, pas le nom. Conserver la variable shell (`$DOC_BODY`) entre Phase C/F2 et Phase D/F3, puis `rm -f` après écriture.

## Communication en temps réel (v2.5)

**Règle : émettre une ligne de status AVANT chaque phase**, pas après. Benjamin a besoin de voir où ça en est sans attendre la fin (sinon `/documente` est une boîte noire de 30-60s).

Format strict, une seule ligne par phase :
```
▸ <code> <nom-phase>  (<info brève — état parsé, count, ou décision prise>)
```

Codes par phase (subject pool) :
- `▸ A prepare` — résultat de `prepare` (subject pool oui/non, exists oui/non)
- `▸ B infer-type` — stratégie d'inférence + type retenu (ou « création paresseuse demandée » si validation requise)
- `▸ C capture` — décision tranchée détectée / discussion seule / rien à capturer
- `▸ D write-capture` — fichiers écrits (`1 discussion`, `1 discussion + 1 décision`, ou `skip`)
- `▸ E forge_engine` — `current_state`, transitions appliquées, count events
- `▸ F quick+détails` — count mots Quick, sections custom préservées
- `▸ G patch-frontmatter` — patches appliqués (last_event, +decision, normalisation forging_state)
- `▸ H cascade` — count linked_subjects traités (ou « aucun »)
- `▸ I scan-impacted` — count candidats / count pertinents proposés
- `▸ J commit+push` — count fichiers, succès push

Codes folder (`F0` à `F6`) : même logique, préfixe `L`.

**Ne pas afficher si phase skip** (ex: pas de cascade, aucune décision capturée). Préférer un silence à un `▸ X skip` redondant.

**Récap final obligatoire** après Phase J : 1 ligne `✓ /documente terminé — <count phases> phases, <count fichiers> fichiers, <commit-sha-court>`.

## Workflow — Subject Pool (depuis 2026-05-04, via `forge documente`)

Toutes les phases déterministes sont déléguées au binaire `forge documente` (engine Python du plugin claude-forge). Le LLM intervient uniquement pour : capture conversationnelle (Phase C), rédaction du contenu narratif des captures (Phase D body), synthèse Quick/Détails (Phase F), jugement de pertinence des fichiers impactés (Phase I).

Convention CLI : chaque commande retourne un JSON sur stdout au format `{"ok": true|false, "version": 1, ...}`. Le skill teste `ok` du JSON, pas l'exit code.

### Phase A — Préparer le contexte (Python)

```bash
forge documente prepare <subject-path>
```

Parser le JSON retourné. Brancher selon :
- `is_subject_pool: false` → suivre le **workflow folder** ci-dessous (Phase F1+)
- `subject_exists: false` et `needs_creation: true` → enchaîner sur **Phase B** (création paresseuse)
- `subject_exists: true` → enchaîner sur **Phase C** (capture conversationnelle)

### Phase B — Création paresseuse (interactif si type absent)

```bash
forge documente infer-type <subject-path>
```

Parser le résultat :
- `strategy: from_frontmatter | single_parent_type | from_naming` + `type_exists: true` → utiliser ce type, invoquer `/subject-create <type> <name>` silencieusement (Skill tool)
- `strategy: ambiguous` → présenter les `candidates` à Benjamin, demander le choix
- `strategy: none` ou `type_exists: false` → demander confirmation **avant** d'invoquer `/subject-create-type` (interactif, acte structurel rare)

Une fois l'instance créée, repasser par Phase A pour confirmer `subject_exists: true`.

### Phase C — Capture conversation (LLM, irréductible)

Examiner la conversation récente. Trois cas :
- **Décision tranchée détectée** (Benjamin a clairement validé un choix) → préparer body discussion + body decision (rédaction LLM)
- **Discussion en cours détectée** (échange enregistré mais pas encore tranché) → préparer body discussion seul (`status: open`)
- **Rien à capturer** (invocation post-/control-tower juste pour re-synth) → skip à **Phase E**

Pour chaque body, écrire le contenu narratif dans un fichier temporaire UNIQUE par invocation (utiliser `mktemp` pour éviter race condition entre 2 `/documente` parallèles — sinon le 2ᵉ écraserait le body du 1er) :

```bash
DOC_BODY=$(mktemp /tmp/documente-discussion-body.XXXXXX)
cat > "$DOC_BODY" << 'EOF'
[Contenu narratif rédigé par le LLM : cheminement, alternatives, conclusion]
EOF
# Garder $DOC_BODY en mémoire pour Phase D, ou le passer directement
```

Si la phase produit une décision, vérifier la cohérence avec les décisions actives :

```bash
forge documente check-coherence <subject-path> \
  --decision-yaml '{"<param>": <value>, ...}'
```

Si `conflicts` non-vide → alerter Benjamin avant de poursuivre Phase D (il décide d'archiver l'ancienne décision, de modifier la nouvelle, ou d'annuler).

### Phase D — Écrire les captures (Python)

```bash
# Discussion ($DOC_BODY = fichier temp unique créé en Phase C)
forge documente write-capture <subject-path> \
  --kind discussion --slug YYYY-MM-DD-<slug> \
  --body-file "$DOC_BODY" \
  --frontmatter '{"date": "YYYY-MM-DD", "type": "discussion", "produced_by": "human_and_claude", "participants": ["benjamin", "claude"], "status": "open|closed", "resulting_decision": "<slug-or-null>"}'

# Decision (si applicable — créer DOC_DECISION via mktemp aussi)
DOC_DECISION=$(mktemp /tmp/documente-decision-body.XXXXXX)
cat > "$DOC_DECISION" << 'EOF'
[Contenu YAML/markdown du body décision]
EOF

forge documente write-capture <subject-path> \
  --kind decision --slug YYYY-MM-DD-<slug> \
  --body-file "$DOC_DECISION" \
  --frontmatter '{"date": "YYYY-MM-DD", "type": "decision", "produced_by": "human", "decided_by": "benjamin", "parameters": {...}, "upstream_discussions": ["<slug>"], "status": "active"}'

# Cleanup post-écriture (les fichiers sont copiés dans le subject path par write-capture)
rm -f "$DOC_BODY" "$DOC_DECISION"
```

**Corps d'une décision — champs MADR (v2.9, décision CE 2026-09-07)** : structure YAML libre, mais deux clés attendues à la racine, modèle dans `templates/decision.body.yaml` :
- `options_considerees` : liste `{option, retenue: true|false, raison}` — les alternatives écartées et pourquoi (une décision sans alternative écartée n'est pas une décision, c'est un constat).
- `confirmation` : `{preuve, echeance}` — comment on saura qu'elle est appliquée (test, EVAL, hook, métrique, fichier attendu), jamais « on verra ». À l'échéance, le scanner alerte (`decision_echue`) tant que `confirmation.verdict: {date, resultat, note}` n'est pas écrit ou la décision archivée — si une alerte de ce type est visible en début de session sur le subject traité, proposer de rendre le verdict dans la même invocation.
`write-capture` retourne `madr_missing` + `warnings` si l'une manque : écriture acceptée, mais **afficher l'avertissement dans le récap** et compléter dans la même invocation si l'information est dans la conversation.

Le frontmatter est entièrement composé par Python (pas de risque de corruption YAML par le LLM). Si l'écriture échoue avec `code: exists`, c'est qu'un fichier du même slug existe déjà — choisir un autre slug ou archiver l'ancien.

### Phase E — Calcul d'état (Python, déjà existant)

```bash
forge engine <subject-path>
```

Stocker `forge_result` en mémoire. Vérifier `error` puis utiliser pour Phases F, G, H.

Le JSON contient : `current_state`, `current_conviction`, `last_event`, `stats`, `transition_proposal`, `events_summary`, `active_decisions_summary`, `open_discussions_summary`, `cascade`, `warnings`.

### Phase F — Régénérer Quick + Détails (LLM)

**F.1 — Extraire les typed edges (Python autolink)**

Avant de rédiger le Quick, invoquer l'engine autolink pour récupérer les relations typées sortantes du subject (extraction déterministe, zéro LLM, basée sur les `linked_subjects` du frontmatter croisés avec `typical_linked_types` du type) :

```bash
forge autolink extract <subject-path>
```

Sortie JSON `{ok, subject_name, subject_type, edges: [{name, target_slug, target_type, target_name}, ...], warnings}`. Stocker pour Phase F.2 et Phase H.5.

**F.2 — Rédiger Quick + Détails**

À partir de `forge_result.current_state`, `events_summary`, `active_decisions_summary`, et des `edges` extraits en F.1, rédiger :

- `## Quick` (<100 mots, ton synthétique factuel). Inclure une ligne **`Liens forts`** listant les typed edges, format `<relation> <target_slug>` séparés par ` ; `. Exemple :
  ```
  Liens forts : ordered_from supplier:weifang ; contains product-line:guirlande-guinguette ; shipped_via freight-forwarder:dhl
  ```
  Si aucun edge typé n'existe (subject sans `linked_subjects`), omettre la ligne. Si seulement des edges génériques (`name: linked` faute de `typical_linked_types` enrichi), les lister quand même mais Benjamin saura que la doctrine du type mérite d'être enrichie.
- `## Détails` (synthèse narrative, **préserver les sous-sections custom** comme `### Notes libres`, `### Stress tests à prévoir`)

Écrire ces sections dans le `MEMORY.md` via Edit (le frontmatter sera patché en Phase G séparément).

### Phase G — Patch frontmatter (Python)

Construire le patch JSON à partir de `forge_result` :

```bash
forge documente patch-frontmatter <subject-path> \
  --patch '{
    "last_event": {"date": "...", "type": "...", "ref": "..."},
    "open_discussions": ["+<slug-discussion>"],
    "active_decisions": ["+<slug-decision>", "-<slug-archived>"],
    "forging_state": "<normalisation legacy, ou clôture/réouverture validée>"
  }'
```

Conventions de patch :
- Scalaire (`"forging_state": "tentative"`) → remplace
- Dict (`"last_event": {...}`) → remplace tout le bloc
- Liste avec `+slug` / `-slug` → append/remove (préserve les autres items)

Si `current_state_was_legacy: true` dans `forge_result` :
- Inclure `"forging_state": "<current_state>"` dans le patch (normalisation en écriture, refonte 2026-09-14 — la valeur normalisée est `actif` ou `archived`, sans changement sémantique)
- Le mentionner dans le récap (`▸ G patch-frontmatter (forging_state normalisé <legacy> → <normalisé>)`)

`transition_proposal` est toujours `null` depuis 2026-05-10 (aucune transition automatique) — une clôture `actif → archived` passe par une demande explicite de l'utilisateur, jamais par le moteur.

### Phase H — Cascade horizontale (Python pour mécanique, LLM pour Quick)

Pour chaque entry de `forge_result.cascade` :

```bash
forge documente cascade-last-event \
  <root-subject-path> <linked-subject-path> \
  --event-ref "events/<filename> du subject <root>"
```

Puis le LLM régénère le `## Quick` du linked subject (Edit), **PAS** le `## Détails` (réservé à l'invocation directe sur ce subject).

### Phase H.5 — Validation typed graph (Python autolink, non bloquante)

Après cascade, ré-invoquer autolink sur le subject racine pour valider la cohérence du typed graph **après** les éventuelles modifications de `linked_subjects` :

```bash
forge autolink extract <subject-path>
```

Inspecter le champ `warnings` du JSON :

- `slug "<X>" non résolu (préfixe de type inconnu)` → un `linked_subjects` pointe vers un slug dont le type ne se déduit pas. À mentionner à Benjamin (probable typo ou type futur non encore créé).
- `type cible "<X>" absent de typical_linked_types pour type "<Y>"` → un linked_subject est valide mais sa relation n'est pas déclarée dans `typical_linked_types` du type courant. Suggérer à Benjamin d'enrichir le type.

**Affichage** : si warnings, les lister dans la conversation avec un bullet `⚠️`. **Ne pas bloquer Phase J** — c'est un signal pédagogique, pas une erreur. Si zéro warning, ne rien afficher (silence positif).

### Phase I — Scanner les exécutants impactés (Python pour scan, LLM pour jugement)

```bash
forge documente scan-impacted <subject-path>
```

Le scanner remonte les parents du subject jusqu'à la racine du repo et liste tous les `SKILL.md`, `agent.yaml`, `brief.yaml`, `config.yaml` rencontrés. Le LLM lit la liste `candidates` et juge la pertinence de chaque candidat vis-à-vis de la décision capturée. Pour chaque fichier jugé pertinent, **proposer** la modification à Benjamin (ne pas modifier sans validation).

### Phase J — Commit atomique + push (Python)

```bash
forge documente commit-atomic \
  --paths "<subject-path>/MEMORY.md,<subject-path>/discussions/<file>,<subject-path>/decisions/<file>,<linked1>/MEMORY.md,..." \
  --message "docs: <type> — <sujet court>

- subject racine : <subject-path>
- cascade : <linked_subjects affectés>" \
  --push
```

Si la commande retourne `noop: true` (idempotent — 2ᵉ invocation sans nouvel input) → afficher « rien à re-synthétiser », pas de commit vide.

### Hints post-commit (suggestions humaines, non-bloquantes)

À la fin de Phase J, après le commit réussi, **suggérer à Benjamin** ces deux pistes si elles s'appliquent — sans rien exécuter automatiquement :

1. **`/skillify`** — Si la session a fait émerger un **workflow ad hoc répété** que Benjamin a exécuté à la main (suite de commandes, raisonnement reproductible, séquence de validation) qui mérite d'être réifié en skill. Détecter ce pattern revient à se poser la question : *« si je devais refaire la même chose la semaine prochaine, est-ce qu'un skill me ferait gagner du temps ? »*. Si oui, suggérer : *« Considère `/skillify <pattern>` avant la prochaine session pour éviter de refaire ce raisonnement à la main »*. Pas de déclenchement auto — Benjamin décide.

2. **`/cross-modal-review`** — Si la session s'apprête à s'appuyer durablement sur la synthèse du subject (référence pour d'autres décisions, base d'un skill, doctrine), suggérer d'invoquer `/cross-modal-review` pour vérifier que le Quick + Détails tiennent la route. Pas de déclenchement auto — pure suggestion.

Ces hints sont des signaux pédagogiques — la décision reste humaine. Le pattern Garry Tan repose volontairement sur l'humain qui dit « skillify it » plutôt que sur une détection automatique (qui produirait du bruit sur des workflows non répétés ou trop vagues).

## Workflow — Classique (folder, hors subject pool)

Quand Phase A (`prepare`) détecte un contexte non-subject-pool (`is_subject_pool: false`), exécuter Phase F0.0 (création structure si absente) puis Phase F0 (proposition migration) puis suivre Phases F1-F6.

Depuis 2026-05-04, les phases déterministes (F2 discussion, F3 decision, F5 scan, F6 commit) sont instrumentées Python via `documente_engine.py` — mêmes commandes génériques que le workflow subject pool. Phase F4 (MAJ MEMORY.md format markdown) reste LLM only.

### Phase F0.0 — Création de structure service si absente (v2.7)

Avant tout : lire les champs `service_root`, `service_structure_exists`, `proposed_default_path` de la sortie `prepare`. Trois cas :

**Cas 1 — Pas de `service_root` identifié** (path hors `services/<x>/`, ex: `entreprise/architecture/...`) → passer directement à Phase F0.

**Cas 2 — `service_structure_exists: true`** (le service a déjà `discussions/` ET `decisions/`) → passer directement à Phase F0.

**Cas 3 — `service_structure_exists: false`** (le service `<service_root>` existe mais n'a pas la structure folder) → présenter UN choix unique à Benjamin via `AskUserQuestion` :

```
Le service <service_root> n'a pas encore de structure discussions/+decisions/.
[A] Créer <service_root>/discussions/ + <service_root>/decisions/ et y stocker (recommandé — cohérent avec services/achats/, services/tech/)
[B] Créer un subject pool (objet métier durable seulement, cf. critère F0)
```

Si **A** (défaut) : `mkdir -p <service_root>/discussions <service_root>/decisions`, puis utiliser `<service_root>` comme dossier cible pour Phases F2-F6. Sauter Phase F0 (la décision est déjà prise : on stocke en entité).

Si **B** : enchaîner sur Phase F0 standard (qui reproposera le critère et invoquera `/subject-create-type` + `/subject-create` si validé).

**Anti-pattern à éviter** : poser deux questions successives (« où stocker ? » puis « créer la structure ? »). Incident 2026-05-11 sur `services/marketing/` → 2 `AskUserQuestion` au lieu d'une. La Phase F0.0 doit aboutir en **une seule** interaction utilisateur.

### Phase F0 — Critère subject pool vs entité (v2.6)

Avant de poursuivre en folder, **classifier la décision** selon ce critère positif. Le défaut est **A (entité)** — ne proposer **B (subject pool)** que si les conditions sont clairement remplies.

**A. Stocker dans `<entité>/decisions/` (folder, défaut) si** :
- La décision **modifie le code ou le comportement d'UNE entité spécifique** (skill, MCP, tool)
- La décision est **ponctuelle** : prise → code livré → fini (pas d'états successifs ni d'itérations)
- Exemples : ajout d'un préfixe à `WRITE_PREFIXES`, fix bug HTTP timeout, refacto d'une fonction, ajout d'un paramètre optionnel, refonte d'un SKILL, création d'un nouveau skill

**B. Migrer vers subject pool si** :
- La décision concerne un **OBJET MÉTIER DURABLE** qui vit dans le temps avec des états successifs
- L'objet va vivre puis se clore (**cycle de vie** `actif → archived`, avec réouvertures possibles)
- La décision sera **révisée, complétée, contestée** plus tard — ce n'est pas une décision finale unique
- L'objet est **lié à plusieurs entités** ou n'est pas naturellement rattaché à un fichier de code
- Exemples : commande d'achat (order-398), relation fournisseur (supplier-weifang), campagne marketing (google-ads-skylantern), décision architecturale long-terme (ce-admin-v2)

**C. Doute** : demander à l'utilisateur, lui présenter A et B avec les critères ci-dessus. **Le défaut est A**, pas B.

Si choix **B** (migration explicitement justifiée par les critères ci-dessus) : invoquer `/subject-create-type <type>` (interactif) si nécessaire, puis `/subject-create <type> <name>`, puis `mv` les discussions/ et decisions/ existantes vers le nouveau path. Une fois la migration faite, repasser par Phase A pour relancer en mode subject pool.

Si choix **A** : continuer Phase F1 directement.

**Ne pas proposer B (migration) si** :
- Les critères de B ne sont **clairement pas remplis** (cas le plus fréquent : modification de code d'un skill/MCP/tool)
- Benjamin a déjà refusé la migration sur ce path dans une session précédente (vérifier les `decisions/` existantes pour un marqueur `migration_subject_pool: refused`)
- L'utilisateur a déjà précisé son intention (« je veux documenter dans le skill ») — respecter ce choix sans rappeler le menu

**Important — historique de cette doctrine** : la version v2.3 (2026-05-04) proposait la migration **systématiquement** avec un garde-fou négatif vague (« skills/tools figés »). En pratique cela biaisait toutes les décisions vers subject pool, vidant les `<entité>/decisions/` (cf. issue [rubee-labs/claude-forge#1](https://github.com/rubee-labs/claude-forge/issues/1)). La v2.6 inverse : critère **positif** sur la nature de l'objet, défaut entité.

### Phase F1 — Identifier le contexte

Déterminer le sujet, le dossier cible (cf. `entreprise/config/rules/savoirs.md` § Stockage réparti), vérifier l'existant.

### Phase F2 — Discussion (Python)

Composer le body de la discussion (LLM, narratif, sans frontmatter) dans un fichier temporaire UNIQUE par invocation (utiliser `mktemp` — sinon 2 `/documente` parallèles s'écrasent) :

```bash
DOC_BODY=$(mktemp /tmp/documente-discussion-body.XXXXXX)
cat > "$DOC_BODY" << 'EOF'
[Contenu narratif rédigé par le LLM : cheminement, alternatives, conclusion]
EOF
```

Puis écrire le fichier via le binaire :

```bash
forge documente write-capture <dossier> \
  --kind discussion --slug YYYY-MM-DD-sujet-court \
  --body-file "$DOC_BODY" \
  --frontmatter '{"date": "YYYY-MM-DD", "sujet": "Description courte", "statut": "en_cours|aboutie", "decision": "YYYY-MM-DD-sujet-court"}'
```

Le frontmatter folder a un format différent du subject pool (`sujet`, `statut`, `decision` au lieu de `type`, `produced_by`, `status`, `resulting_decision`) — c'est passé en JSON donc géré nativement.

### Phase F3 — Décision (si aboutie, Python)

Si la discussion est aboutie, composer le body décision dans un fichier temp unique puis invoquer write-capture :

```bash
DOC_DECISION=$(mktemp /tmp/documente-decision-body.XXXXXX)
cat > "$DOC_DECISION" << 'EOF'
[Contenu YAML/markdown du body décision]
EOF

forge documente write-capture <dossier> \
  --kind decision --slug YYYY-MM-DD-sujet-court \
  --body-file "$DOC_DECISION" \
  --frontmatter '{"date": "YYYY-MM-DD", "sujet": "...", "parameters": {...}, "affects": [...]}'

# Cleanup
rm -f "$DOC_BODY" "$DOC_DECISION"
```

Mêmes champs MADR `options_considerees` + `confirmation` qu'en Phase D (modèle `templates/decision.body.yaml`) ; afficher `warnings` de `write-capture` si présents.

Mettre à jour la discussion existante via Edit pour passer `statut: aboutie` + lien (Phase F4 inchangée).

### Phase F3.5 — Vérification de cohérence (LLM, hors binaire)

Le binaire `check-coherence` ne s'applique pas au folder (il lit le frontmatter du MEMORY.md format subject pool). En folder, le LLM lit la section "Décisions actives" du MEMORY.md (markdown) et compare manuellement avec la nouvelle décision. Si conflit, alerter Benjamin avant Phase F3.

### Phase F4 — Re-synthèse bornée du MEMORY.md (Python pour le diagnostic et l'écriture, LLM pour la rédaction)

Décision CE 2026-09-06 : le MEMORY.md d'une entité est une **synthèse bornée**, jamais un journal en append. Incident de référence : `services/finance/tools/factures/MEMORY.md` passé de 33 Ko à 187 Ko en 7 semaines (318 lignes de journal de runs), non relu avant un niveau 2 → 4 doublons publiés (2026-08-06).

**F4.1 — Diagnostic (Python)**

```bash
forge documente check-memory <dossier>
```

JSON : `size_kb`, `max_kb` (frontmatter `memory_max_kb`, défaut 8), `over`, `derniere_maj`, `derniere_maj_today`, `sections`, `journal_lines` (lignes datées `- YYYY-MM-DD …` par section : signature d'un journal), `decisions_actives`, `has_quick`. Afficher `▸ F4 check-memory (<size_kb>/<max_kb> Ko, <n> lignes de journal)`.

**F4.2 — Rédiger les sections bornées (LLM)** — à partir du MEMORY.md actuel, de la discussion/décision écrites en F2/F3 et, si `journal_lines` non vide, des lignes de journal à évacuer :

| Section | Contenu | Borne |
|---|---|---|
| `## Quick` | état, dernier run/événement (date + pointeur `rapports/…`), prochaines étapes, risques | < 100 mots |
| `## Doctrine en vigueur` | règles actives, état courant, pas l'historique ; intégrer la nouvelle décision si elle change une règle | 1 ligne par règle |
| `## Décisions actives` | les plus récentes, une ligne chacune avec pointeur `decisions/<fichier>.yaml` ; les plus anciennes sortent de la liste mais restent dans `decisions/` | ≤ 10 |
| `## Décisions annulées` | règle inversée + raison + date (si F3.5 a trouvé une contradiction) | 1 ligne par annulation |
| `## Règles apprises` | contraintes découvertes en session (gotchas durables), extraites notamment du journal évacué | 1 ligne par règle |

Interdits : section `## État` ou tout journal daté dans le MEMORY ; un run écrit `<entité>/rapports/YYYY-MM-DD-<slug>.md`. Si `journal_lines` non vide, proposer à l'utilisateur de déplacer ces lignes en un fichier `rapports/<date-min>-au-<date-max>-journal.md` (Write) puis remplacer la section par son Quick — **validation explicite** avant de retirer du contenu (relecture humaine, `/cross-modal-review` recommandé sur les fichiers > 30 Ko).

**F4.3 — Écrire (Python, une commande par section)**

```bash
DOC_SECTION=$(mktemp /tmp/documente-section.XXXXXX)
cat > "$DOC_SECTION" << 'EOF'
[corps de la section]
EOF
forge documente patch-section <dossier> --section "## Quick" --body-file "$DOC_SECTION" --touch-derniere-maj
rm -f "$DOC_SECTION"
```

`patch-section` remplace uniquement le corps de la section visée (ou la crée en fin de fichier), conserve le reste octet pour octet, met `derniere_maj` à aujourd'hui avec `--touch-derniere-maj`, refuse si `--expected-hash` (de `compute-hash`) ne correspond plus (`stale_hash`). Retourne `size_kb_after` / `over` : si `over` reste vrai après re-synthèse, l'annoncer dans le récap (le hook Stop de CE le rappellera au prochain bloc). Ne pas patcher une section dont le contenu n'a pas changé (idempotence : 2 invocations sans nouvel input = diff vide).

Le format MEMORY.md folder reste du markdown structuré (pas de frontmatter étendu) : `patch-frontmatter` ne s'applique pas, seul `derniere_maj` est géré via `--touch-derniere-maj`.

### Phase F5 — Propagation (Python pour scan, LLM pour jugement)

```bash
forge documente scan-impacted <dossier>
```

Le scanner remonte les parents et liste tous les `SKILL.md`, `agent.yaml`, `brief.yaml`, `config.yaml`. Le LLM juge la pertinence de chaque candidat et propose les modifications à Benjamin (ne pas modifier sans validation).

### Phase F6 — Commit + push (Python)

```bash
forge documente commit-atomic \
  --paths "<dossier>/discussions/<file>,<dossier>/decisions/<file>,<dossier>/MEMORY.md" \
  --message "docs: <type> — <sujet court>" \
  --push
```

Types de message : `discussion`, `decision`, `decision + memory`. Si `noop: true` retourné → afficher « rien à committer ».

## Exemples

### Exemple 1 — Re-synthèse pure (post-/control-tower)

Input :
```
/documente services/achats/subjects/order-398/
```

(Aucune décision dans la conversation préalable — un event a déjà été ajouté par /control-tower.)

Output (résumé) :
```
✓ forge_engine.py invoqué — 6 events, 1 discussion ouverte, 1 décision active (frontmatter)
✓ forging_state normalisé : seed → actif (legacy, refonte 2026-09-14)
✓ ## Quick régénéré (8 lignes, état actif, négo Weifang en cours, payment terms 10j accepté)
✓ ## Détails régénéré (sections custom préservées : ### Notes libres)
✓ Cascade : supplier-weifang
  - last_event ← cascaded_from_order-398 (events/2026-05-04-reply-v3-sent-fancy-quantity-list.md)
  - ## Quick régénéré (1 commande active 16943 USD, négo en cours)
  - ## Détails inchangé
✓ Hint : /stress-test invocable à la demande si tu doutes de la conclusion
Commit : docs: re-synthèse — order-398 + cascade weifang
Push : OK
```

### Exemple 2 — Capture décision puis re-synthèse

Input :
```
[après échange où Benjamin a tranché : "on accepte les payment terms 10j post-loading proposés par Weifang"]
/documente services/achats/subjects/order-398/
```

Output (résumé) :
```
Phase C — Décision détectée :
  Sujet : payment terms 10j post-loading acceptés (Weifang, order-398)
  Confirmer ? [oui]
✓ discussions/2026-05-04-payment-terms-acceptes.md créé (status: closed)
✓ decisions/2026-05-04-payment-terms-acceptes.yaml créé (status: active)
✓ forge_engine.py invoqué
✓ active_decisions ← +"2026-05-04-payment-terms-acceptes" dans MEMORY.md
✓ ## Quick + ## Détails régénérés
✓ Cascade : supplier-weifang
✓ Phase I — Propagation : aucun exécutant impacté
Commit : docs: décision + memory — payment terms order-398
Push : OK
```

## Critères d'évaluation

EVAL 1 : Bon dossier
Question: La discussion/décision est-elle créée dans le bon `subjects/<name>/discussions|decisions/` (subject pool) ou au plus près du sujet (folder) ?
Pass: Fichier au bon endroit
Fail: Au mauvais endroit ou absent

EVAL 2 : Décision si aboutie
Question: La décision a-t-elle été créée si la discussion est aboutie ?
Pass: decisions/*.yaml présent avec paramètres exacts, `options_considerees` et `confirmation` à la racine
Fail: Discussion aboutie mais pas de décision

EVAL 3 : Couche 1 invoquée (subject pool)
Question: forge_engine.py a-t-il été appelé et son JSON parsé sans erreur ?
Pass: Bash invocation + parsing OK
Fail: Saut direct de Phase D à Phase J sans appeler le moteur

EVAL 4 : Verticale complète (subject pool)
Question: Le ## Quick reflète-t-il l'état réel (events, décisions, discussions actuels) et pas une snapshot figée ?
Pass: Quick mentionne le dernier event + l'état post-transition
Fail: Quick reste sur "État: seed, conviction 0" alors que le subject a évolué

EVAL 5 : Horizontale 1 niveau (subject pool)
Question: Tous les linked_subjects résolus voient-ils leur last_event + ## Quick MAJ ?
Pass: Cascade complète sur 1 niveau, pas de récursion plus loin
Fail: Linked_subjects non touchés OU cascade récursive multi-niveau

EVAL 6 : Pas de transition d'état non validée (subject pool)
Question: le forging_state n'a-t-il changé que par normalisation legacy (→ actif/archived, signalée au récap) ou par clôture/réouverture explicitement validée par l'utilisateur ?
Pass: Comportement strict respecté
Fail: forging_state muté sans validation (hors normalisation legacy), ou normalisation silencieuse non signalée

EVAL 7 : Propagation proposée
Question: Les fichiers exécutants impactés ont-ils été identifiés et la modification proposée ?
Pass: Au moins un fichier identifié et modification proposée (ou aucun impacté documenté)
Fail: Décision impacte un exécutant évident mais aucune propagation proposée

EVAL 8 : Commit et push
Question: Le commit et push ont-ils été effectués (sauf si idempotent → diff vide) ?
Pass: Commit avec message descriptif + push réussi
Fail: Fichiers non committés

EVAL 9 : Subject Pool format
Question: Si subject pool, frontmatters étendus présents (type, produced_by, status, resulting_decision) ET MEMORY.md du subject re-synthétisé en Phases 5-6 (pas un MEMORY.md de service) ?
Pass: Format respecté
Fail: Format classique appliqué dans un contexte subject pool

EVAL 10 : Idempotent
Question: Une 2ᵉ invocation consécutive sans nouvel input produit-elle un diff vide ?
Pass: Aucun fichier modifié, pas de commit
Fail: Diff non-vide alors que rien n'a changé en amont

EVAL 11 : Création paresseuse type (v2.1)
Question: Si le type n'existe pas, /documente a-t-il demandé validation avant d'invoquer /subject-create-type ?
Pass: Question explicite affichée à Benjamin avec 3 options (créer / type existant / annuler)
Fail: Type créé silencieusement, ou /documente plante au lieu de gérer la création paresseuse

EVAL 12 : Création paresseuse instance (v2.1)
Question: Si le subject path n'existe pas mais le type oui, /subject-create a-t-il été invoqué silencieusement (0 intervention utilisateur) ?
Pass: Subject créé sans prompt sur linked_subjects, valeurs par défaut appliquées
Fail: Prompt utilisateur affiché alors que c'est un appel automatique depuis /documente

EVAL 13 : Création de structure service (v2.7)
Question: Si le service cible existe sans discussions/+decisions/, Phase F0.0 a-t-elle posé UNE seule question (A créer structure / B subject pool) avant d'agir ?
Pass: 1 AskUserQuestion, choix A → mkdir des deux dossiers + stockage au niveau service ; choix B → enchaînement Phase F0 normale
Fail: Aucun prompt (création silencieuse), OU 2 prompts successifs (incident 2026-05-11), OU bascule subject pool par défaut alors que la décision concerne du code d'entité
