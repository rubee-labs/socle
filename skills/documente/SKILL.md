---
name: documente
description: >-
  When the user asks to document a subject (decision, discussion, or session
  outcome) OR to re-synthesize a subject after new external events. Single
  orchestrator entry point for the subject pool: recognizes any folder with a MEMORY.md as a subject (type from the header,
  then .forge.yaml type_by_path, then Claude's choice), converts legacy
  MEMORY.md in place, creates missing ones silently — never asks a question, captures
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
version: 4.0
tags: [documentation, decision, discussion, memory, subject-pool, forge, orchestrator, workflow]
effort: medium
outils_requis: []
securite_externe: false
---

# Documente

## Objectif

**Orchestrateur unique du subject pool.** Combine quatre rôles dans un seul verbe utilisateur :

1. **Tout dossier qui a un MEMORY.md est un subject** (SOCLE 0.7.0, design 2026-10-10). Le type est porté par l'en-tête, jamais par le chemin. Un MEMORY.md à l'ancien format est converti sur place au premier passage (`forge documente convert`), un dossier sans MEMORY.md reçoit le sien. **Aucune question** : `/documente` tourne en fin de cycle d'agents autonomes qui ne peuvent pas répondre.
2. **Nommage et typage automatiques** : nom = dossier existant, sinon `name_pattern` du type, sinon choix de Claude ; type = en-tête, sinon `type_by_path` du `.forge.yaml`, sinon choix de Claude parmi `known_types`.
3. **Capture verticale historique** (ex-`/documente` 1.0) : extraire de la conversation une discussion ou décision tranchée, écrire les fichiers `discussions/` et `decisions/` avec frontmatters structurés.
4. **Re-synthèse continue** (ex-`/forge` archivé) : lire tous les sous-fichiers (`events/`, `analyses/`, `discussions/`, `decisions/`), régénérer `## Quick` + `## Détails` du `MEMORY.md`, propager aux `linked_subjects` sur 1 niveau, normaliser un `forging_state` legacy vers le cycle à 2 états (`actif` / `archived`, refonte 2026-09-14 — aucune transition automatique, seules les clôtures/réouvertures manuelles existent).

Le mot **« forge »** désigne le pattern subject pool et le moteur Python sous-jacent (`forge_engine.py`, `forge_lib.py`, `forge_scanner.py`). Il n'existe plus de skill `/forge` séparé — `/documente` est l'entry point unique côté utilisateur.

## Argument

`/documente [<subject-path>] [--type <type>]`

- `<subject-path>` (optionnel depuis v2.7) : chemin vers le dossier du subject (peut être inexistant — sera créé). Ex: `services/marketing/subjects/google-ads-brumeaux/`.
- `--type <type>` (optionnel) : type du subject. Utilisé par les skills appelants pour éviter l'inférence. Ex: `--type marketing-campaign`. Si omis, `/documente` infère ou demande.

**Inférence du path quand omis** : le LLM choisit seul le dossier d'après la conversation, sans question. Un fichier identifiable (skill, outil, agent) donne son dossier ; un objet métier durable donne son subject existant (`forge documente list-subjects`) ou un nouveau dossier nommé selon le `name_pattern` du type. Doublon possible : même objet → enrichir l'existant, sinon créer.

## Quand utiliser

- Après une décision prise en session (le skill capturera la décision, écrira les fichiers, puis re-synthétisera le subject)
- Après une discussion aboutie qui mérite d'être tracée
- Après que `/control-tower` (ou un autre flux) a appendé un event à un subject — invocation **automatique** ou manuelle (avec ou sans Phase C de capture, selon que la conversation contient ou non une décision)
- Quand on veut juste rafraîchir la vue d'un subject (régénérer `## Quick` + cascade vers les linked_subjects) sans rien capturer
- Quand Claude détecte un signal de décision et le propose

## Gotchas

- **0 intervention sur création d'instance** : le pas `/subject-create` est silencieux. Si tu vois un prompt sur les linked_subjects pendant un appel automatique, c'est un bug — `/subject-create` doit utiliser des valeurs par défaut quand appelé depuis `/documente`.
- **Aucune question pour nommer, typer ou classer** (0.7.0) : `prepare` donne le type ou `type_source: claude` ; dans ce cas Claude choisit dans `known_types` et le passe à `convert --type`. Jamais d'`AskUserQuestion`, jamais de marque `a_revoir`.
- **Capacités du type** : `prepare.capabilities` dit quelles phases s'appliquent. Sans `links` : pas de Phase F.1 autolink, H ni H.5. Sans `events` : pas de `last_event` à patcher en Phase G. Une phase sautée l'est en silence.
- **Une décision porte ses options écartées et sa preuve d'application (v2.9)** : clés `options_considerees` et `confirmation` à la racine du corps YAML (MADR). `write-capture` avertit sans refuser ; l'avertissement doit apparaître dans le récap.
- **Ne pas créer de décision si la discussion n'est pas aboutie** : si le statut est `en_cours` / `open`, créer uniquement la discussion. La décision viendra quand ce sera tranché.
- **Phases E-H lisent les sous-dossiers, ne les modifient pas** : seule la Phase D (`write-capture`) écrit dans `discussions/` et `decisions/`. Le reste lit puis régénère le `MEMORY.md` (frontmatter + Quick + Détails).
- **Préserver les sections custom du `## Détails`** : `### Notes libres`, `### Stress tests à prévoir`, ou toute section ajoutée à la main par Benjamin doit être conservée lors de la régénération.
- **Cascade horizontale = 1 niveau strict** : pas de récursion. Sur les linked_subjects, on régénère le `## Quick` mais **PAS** le `## Détails` (réservé à l'invocation directe sur ce subject — éviter qu'une vue partielle écrase un détail riche).
- **Aucune transition d'état automatique** (cycle 2 états depuis 2026-09-14) : le moteur ne mute jamais `forging_state`. Seules transitions possibles : `actif → archived` (clôture) et `archived → actif` (réouverture), toutes deux **manuelles avec validation utilisateur**. La seule écriture d'état sans validation est la **normalisation d'un legacy** (`seed`/`debating`/`tentative`/`mature`/… → `actif`) — sans changement sémantique, signalée dans le récap.
- **Idempotent** : 2 invocations consécutives sans nouvel input doivent produire un diff vide.
- **Commit atomique** : committer discussion + decision + memory.md (subject + cascade) ensemble dans un seul commit.
- **Propagation = proposition, pas imposition** : la Phase I (`scan-impacted` + jugement LLM) propose les modifications aux fichiers exécutants. L'utilisateur valide chaque modification.
- **Fichiers temp uniques par invocation (v2.4)** : utiliser `mktemp /tmp/documente-*-body.XXXXXX` pour les body files passés à `write-capture`. Sinon 2 `/documente` parallèles écrasent leurs body files mutuellement (race condition observée le 2026-05-04 entre `/documente skills/documente` et `/documente knowledge-coordinator`). **Attention syntaxe BSD/macOS** : les `XXXXXX` doivent être en SUFFIXE final, pas suivis d'une extension (`.md` literal écrirait XXXXXX littéralement). L'extension n'est pas requise — `write-capture` lit le contenu, pas le nom. Conserver la variable shell (`$DOC_BODY`) entre Phase C/F2 et Phase D/F3, puis `rm -f` après écriture.

## Communication en temps réel (v2.5)

**Règle : émettre une ligne de status AVANT chaque phase**, pas après. Benjamin a besoin de voir où ça en est sans attendre la fin (sinon `/documente` est une boîte noire de 30-60s).

Format strict, une seule ligne par phase :
```
▸ <code> <nom-phase>  (<info brève — état parsé, count, ou décision prise>)
```

Codes par phase (subject pool) :
- `▸ A prepare` — résultat de `prepare` (subject pool oui/non, exists oui/non)
- `▸ B convert` — type retenu et sa source (en-tête / `type_by_path` / Claude), nom, action (`converted` / `created`) — jamais de question
- `▸ C capture` — décision tranchée détectée / discussion seule / rien à capturer
- `▸ D write-capture` — fichiers écrits (`1 discussion`, `1 discussion + 1 décision`, ou `skip`)
- `▸ E forge_engine` — `current_state`, transitions appliquées, count events
- `▸ F quick+détails` — count mots Quick, sections custom préservées
- `▸ G patch-frontmatter` — patches appliqués (last_event, +decision, normalisation forging_state)
- `▸ H cascade` — count linked_subjects traités (ou « aucun »)
- `▸ I scan-impacted` — count candidats / count pertinents proposés
- `▸ J commit+push` — count fichiers, succès push


**Ne pas afficher si phase skip** (ex: pas de cascade, aucune décision capturée). Préférer un silence à un `▸ X skip` redondant.

**Récap final obligatoire** après Phase J : 1 ligne `✓ /documente terminé — <count phases> phases, <count fichiers> fichiers, <commit-sha-court>`.

## Workflow (unique depuis 0.7.0, via `forge documente`)

Toutes les phases déterministes sont déléguées au binaire `forge documente` (engine Python du plugin socle). Le LLM intervient uniquement pour : capture conversationnelle (Phase C), rédaction du contenu narratif des captures (Phase D body), synthèse Quick/Détails (Phase F), jugement de pertinence des fichiers impactés (Phase I).

Convention CLI : chaque commande retourne un JSON sur stdout au format `{"ok": true|false, "version": 1, ...}`. Le skill teste `ok` du JSON, pas l'exit code.

### Phase A — Préparer le contexte (Python)

```bash
forge documente prepare <subject-path>
```

Parser le JSON retourné :
- `needs_creation: true` ou `needs_conversion: true` → **Phase B**.
- `is_subject: true` → **Phase C**.

Garder `capabilities` pour la suite : chaque phase marquée « (capacité X) » n'est exécutée que si X y figure.

### Phase B — Création ou conversion (Python, sans question)

1. Type : `prepare.type`, sinon (`type_source: claude`) le type le plus juste parmi `prepare.known_types`, choisi par Claude d'après le contenu du dossier.
2. Nom : `prepare.default_name` pour un dossier existant ; pour un nouveau dossier, appliquer `prepare.name_pattern` (ou, à défaut, un slug kebab-case court tiré du contexte).
3. Si le type a un `TEMPLATE.md` à côté de son `REFERENCE.md` et que le dossier est neuf → `/subject-create <type> <name>` (Skill tool, silencieux). Sinon :

```bash
forge documente convert <path> --type <type> [--name <name>]
```

4. Repasser par Phase A (`is_subject: true` attendu), puis Phase C. Une conversion est committée avec le reste du bloc en Phase J.

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

**F.1 — Extraire les typed edges (Python autolink, capacité links)**

Avant de rédiger le Quick, invoquer l'engine autolink pour récupérer les relations typées sortantes du subject (extraction déterministe, zéro LLM, basée sur les `linked_subjects` du frontmatter croisés avec `typical_linked_types` du type) :

```bash
forge autolink extract <subject-path>
```

Sortie JSON `{ok, subject_name, subject_type, edges: [{name, target_slug, target_type, target_name}, ...], warnings}`. Stocker pour Phase F.2 et Phase H.5.

**F.2 — Rédiger Quick + Détails**

À partir de `forge_result.current_state`, `events_summary`, `active_decisions_summary`, et des `edges` extraits en F.1, rédiger :

- `## Quick` (<100 mots, ton synthétique factuel). Avec la capacité links, inclure une ligne **`Liens forts`** listant les typed edges, format `<relation> <target_slug>` séparés par ` ; `. Exemple :
  ```
  Liens forts : ordered_from supplier:weifang ; contains product-line:guirlande-guinguette ; shipped_via freight-forwarder:dhl
  ```
  Si aucun edge typé n'existe (subject sans `linked_subjects`), omettre la ligne. Si seulement des edges génériques (`name: linked` faute de `typical_linked_types` enrichi), les lister quand même mais Benjamin saura que la doctrine du type mérite d'être enrichie.
- `## Doctrine en vigueur` : une ligne par règle.
- `## Décisions actives` : au plus 10, chacune en pointeur vers son fichier `decisions/`.
- `## Règles apprises`.
- `## Détails` : contexte et paramètres en cours, **préserver les sous-sections custom** (`### Notes libres`, `### Stress tests à prévoir`, sections versées par une conversion), **sauf les sous-sections de journal** — titre qui commence par une date (`### 2026-08-04 — …`) ou par un mot de journal suivi d'une date (`### Décision du …`, `### Exécution du …`, `### Checkpoint du …`, `### Bilan du …`) — traitées en F.3. Un titre thématique qui contient une date (`### Vague 3 — bench (2026-05-24)`) n'est pas un journal : il est préservé.

Écrire ces sections dans le `MEMORY.md` via `forge documente patch-section` (une section par appel) (le frontmatter sera patché en Phase G séparément). Le `## Détails` n'est **réécrit en entier** que si F.3 l'exige (`over` vrai, `journal_headings` ou `journal_lines` non vide) ou si une conversion vient d'y verser du contenu ; sinon, mise à jour ciblée des seuls passages que la session change. Sans nouvel élément, aucune section n'est réécrite (règle d'idempotence, cf. Gotchas).

**F.3 — Borne du MEMORY.md (Python pour le diagnostic, LLM pour la rédaction)** — borne commune à tous les subjects (incident 2026-10-10 : un subject à 66 Ko, 25 sections `### Décision du …` recopiées dans le `## Détails`, jamais signalé):

```bash
forge documente check-memory <subject-path>
```

Afficher `▸ F.3 check-memory (<size_kb>/<max_kb> Ko, <n> titres datés, <m> lignes de journal)`. Si `over` est vrai ou si `journal_headings` / `journal_lines` est non vide :
1. Pour chaque sous-section datée dont le contenu existe déjà dans `decisions/` ou `discussions/` (même date, même objet), la **remplacer par une ligne de pointeur** (`- AAAA-MM-JJ — <objet> → decisions/<fichier>.yaml`). Aucun contenu n'est perdu : pas de validation requise.
2. Ce qui n'existe nulle part ailleurs (exécution, checkpoint, ancien Quick, tableau d'inventaire) part **tel quel** dans `rapports/AAAA-MM-JJ-<slug>.md` (Write), puis pointeur. Aucune validation : le contenu est recopié à l'identique, rien n'est perdu (0.7.0 — `/documente` tourne sans question, y compris en fin de cycle d'agents autonomes).
3. Format borné : `## Doctrine en vigueur` (1 ligne par règle), `## Décisions actives` (**≤ 10, en pointeurs**), `## Détails` (contexte, paramètres en cours, stress tests, notes libres). Plafond `memory_max_kb` (défaut 8 Ko).
4. Écrire via `forge documente patch-section <subject-path> --section "## Détails" --body-file <f>` (préserve le reste octet pour octet) ; vérifier que les balises `<!-- okf-links:start -->` / `<!-- okf-links:end -->` qui encadrent `## Liens` sont intactes après le patch. Si `over` reste vrai, l'annoncer dans le récap.

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

### Phase H — Cascade horizontale (Python pour mécanique, LLM pour Quick, capacité links)

Pour chaque entry de `forge_result.cascade` :

```bash
forge documente cascade-last-event \
  <root-subject-path> <linked-subject-path> \
  --event-ref "events/<filename> du subject <root>"
```

Puis le LLM régénère le `## Quick` du linked subject (Edit), **PAS** le `## Détails` (réservé à l'invocation directe sur ce subject).

### Phase H.5 — Validation typed graph (Python autolink, non bloquante, capacité links)

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
  --paths "<subject-path>/MEMORY.md,<subject-path>/discussions/<file>,<subject-path>/decisions/<file>,<subject-path>/rapports/<file>,<linked1>/MEMORY.md,..." \
  --message "docs: <type> — <sujet court>

- subject racine : <subject-path>
- cascade : <linked_subjects affectés>" \
  --push
```

Si la commande retourne `noop: true` (idempotent — 2ᵉ invocation sans nouvel input) → afficher « rien à re-synthétiser », pas de commit vide.

`--paths` liste **tout** ce que le bloc a écrit : `MEMORY.md` (y compris converti en Phase B), discussion, décision, fichiers `rapports/` créés en F.3, `MEMORY.md` des subjects liés. Chemins relatifs au même dossier projet que les autres commandes (`CLAUDE_FORGE_PROJECT_DIR`, sinon la racine git) ; seuls ces chemins entrent dans le commit, même si d'autres fichiers sont indexés. Le message est committé tel quel : y mettre soi-même les trailers (Co-Authored-By…).

### Hints post-commit (suggestions humaines, non-bloquantes)

À la fin de Phase J, après le commit réussi, **suggérer à Benjamin** ces deux pistes si elles s'appliquent — sans rien exécuter automatiquement :

1. **`/skillify`** — Si la session a fait émerger un **workflow ad hoc répété** que Benjamin a exécuté à la main (suite de commandes, raisonnement reproductible, séquence de validation) qui mérite d'être réifié en skill. Détecter ce pattern revient à se poser la question : *« si je devais refaire la même chose la semaine prochaine, est-ce qu'un skill me ferait gagner du temps ? »*. Si oui, suggérer : *« Considère `/skillify <pattern>` avant la prochaine session pour éviter de refaire ce raisonnement à la main »*. Pas de déclenchement auto — Benjamin décide.

2. **`/cross-modal-review`** — Si la session s'apprête à s'appuyer durablement sur la synthèse du subject (référence pour d'autres décisions, base d'un skill, doctrine), suggérer d'invoquer `/cross-modal-review` pour vérifier que le Quick + Détails tiennent la route. Pas de déclenchement auto — pure suggestion.

Ces hints sont des signaux pédagogiques — la décision reste humaine. Le pattern Garry Tan repose volontairement sur l'humain qui dit « skillify it » plutôt que sur une détection automatique (qui produirait du bruit sur des workflows non répétés ou trop vagues).

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
Question: La discussion/décision est-elle créée dans le `discussions/` ou `decisions/` du dossier du subject concerné ?
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
Question: Si subject pool, frontmatters étendus présents (type, produced_by, status, resulting_decision) ET MEMORY.md du subject re-synthétisé en Phases 5-6 (format unique : Quick, Doctrine en vigueur, Décisions actives, Règles apprises, Détails) ?
Pass: Format respecté
Fail: Format classique appliqué dans un contexte subject pool

EVAL 10 : Idempotent
Question: Une 2ᵉ invocation consécutive sans nouvel input produit-elle un diff vide ?
Pass: Aucun fichier modifié, pas de commit
Fail: Diff non-vide alors que rien n'a changé en amont

EVAL 11 : Zéro question (0.7.0)
Question: /documente a-t-il nommé, typé, converti ou créé le subject sans aucune AskUserQuestion ?
Pass: Type et nom fixés depuis prepare (en-tête, type_by_path, name_pattern) ou choisis par Claude, conversion faite et committée
Fail: Question posée à l'utilisateur, ou bloc arrêté faute de réponse

EVAL 12 : Création paresseuse instance (v2.1)
Question: Si le subject path n'existe pas mais le type oui, /subject-create a-t-il été invoqué silencieusement (0 intervention utilisateur) ?
Pass: Subject créé sans prompt sur linked_subjects, valeurs par défaut appliquées
Fail: Prompt utilisateur affiché alors que c'est un appel automatique depuis /documente
