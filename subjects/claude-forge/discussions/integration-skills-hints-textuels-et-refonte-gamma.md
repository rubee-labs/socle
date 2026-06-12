---
date: 2026-05-11
type: discussion
produced_by: human_and_claude
participants:
  - benjamin
  - claude
status: closed
resulting_decisions:
  - 2026-05-10-p5-autolink-typed-graph.yaml
  - 2026-05-10-p3-skillify-compilation-continue.yaml
  - 2026-05-10-p2-cross-modal-eval.yaml
  - 2026-05-10-cycle-gamma-refonte-3-etats.yaml
---
## Contexte

Session du 10-11 mai 2026 sur le repo plugin claude-forge. Démarrée par la création du skill `/FORGE-analyse` (modèle adversarial cf. `/CE-analyse` mais ciblé sur la doctrine subject pool / cycle γ / compilation Forge), puis premier passage sur le manifeste « Meta-Meta-Prompting » de Garry Tan (CEO Y Combinator, 9 mai 2026) qui propose la triade `Fat Skills + Fat Data + Thin Harness` avec 5 primitives manquantes côté Forge : auto-link déterministe, hybrid search mesurée, skillify, cross-modal eval, MCP server.

## Décisions livrées dans la session (cf. decisions/)

1. **2026-05-10 — P5 Auto-link déterministe** (`2026-05-10-p5-autolink-typed-graph.yaml`) : option enrichir `typical_linked_types` retenue + intégration end-to-end via `/subject-create-type` (génère le nouveau format), `/documente` Phase F (extract + ligne « Liens forts » dans Quick) et nouvelle Phase H.5 (validation pré-commit non bloquante). 17 tests verts.
2. **2026-05-10 — P3 Skillify** (`2026-05-10-p3-skillify-compilation-continue.yaml`) : 3 sous-commandes CLI (`scaffold`, `check`, `audit`), 8 critiques + 2 hygiène, sentinelle `SKILLIFY_STUB`. 9 tests verts. Skill orchestrateur `/skillify` livré avec 6 phases.
3. **2026-05-10 — P2 Cross-modal eval** (`2026-05-10-p2-cross-modal-eval.yaml`) : 3 sous-commandes (`prepare`, `aggregate`, `write-analysis`), 4 axes (cohérence, complétude, spécificité, citations), 2-3 modèles Anthropic via Task tool (pas de clé API). 6 tests verts.
4. **2026-05-10 — Refonte process γ** (`2026-05-10-cycle-gamma-refonte-3-etats.yaml`) : 8 états → 3 états (actif/mature/archived), conviction numérique supprimée, transitions 100% manuelles, `/compile-doctrine` abandonné, `/stress-test` découplé du cycle. Rétrocompat 100% via `LEGACY_STATE_MAP`.

## Discussion structurante de la session — orphelinat des nouveaux skills

Benjamin a pointé deux fois le même piège pendant la session :

- **Première occurrence (après P5)** : « comment autolink est-il appelé par /documente ? » → réponse honnête : il était orphelin, livraison incomplète. Comblé par intégration Phase F + Phase H.5 dans `/documente` SKILL.md + format enrichi généré dès `/subject-create-type`.
- **Deuxième occurrence (après P3+P2)** : « comment skillify se lance-t-il ? » → même piège, skillify et cross-modal-review livrés mais orphelins (aucun trigger, aucune mention dans les autres skills).

Tentative de réponse via 3 options de scope (hints textuels, hints + alerte scanner, détection workflow répété). Benjamin a bifurqué sur une remarque pivot : `/skillify` est en réalité l'équivalent de la branche « procédurale → skill auto-généré » de `/compile-doctrine`. Quasi-doublon partiel.

**Détour refonte process γ** : la résolution du doublon /skillify ↔ /compile-doctrine a entraîné une refonte plus large du cycle de vie. /compile-doctrine était théorique (0 artefact compilé en 5 jours d'existence Phase 1), le cycle γ à 8 états était sur-segmenté, la conviction numérique 0..100 était arbitraire. Refonte complète validée : 3 états (actif/mature/archived), transitions manuelles, conviction supprimée. /stress-test découplé.

**Retour au sujet initial** : « subject-pool existe toujours, on a juste changé le process γ ». Distinction importante que la formulation initiale n'avait pas claire. Le subject pool comme infrastructure de stockage est intact ; seul le mécanisme de maturation interne (process γ) a été simplifié.

**Retour à la question d'origine** : la refonte n'a pas comblé l'orphelinat — elle a clarifié le rôle de /skillify (porte la branche compile procédurale) mais aucun trigger automatique n'a été branché. 4 options proposées :

- Hints textuels uniquement
- Hints + alerte scanner
- Détection événementielle workflow répété
- Orphelins volontaires (pattern Garry pur)

## Décision (capturée dans le commit 79332e2)

**Option retenue : hints textuels uniquement.** Cohérent avec le pattern Garry Tan où le trigger humain explicite (« skillify it ») évite le bruit qu'une détection automatique produirait sur des workflows non répétés ou trop vagues.

Implémentation :

- `/documente` SKILL.md Phase J post-commit : nouvelle section « Hints post-commit (suggestions humaines, non-bloquantes) » qui suggère `/skillify` si workflow ad hoc répété + `/cross-modal-review` si transition `actif → mature` envisagée
- `rules/subject-pool.md` § Skills : note « trigger humain explicite » sur `/skillify` + note « à invoquer typiquement avant transition `actif → mature` » sur `/cross-modal-review`
- Nouvelle mini-section « Quand invoquer ces skills (triggers humains attendus) » dans la doctrine : tableau de 6 cas d'usage → skill suggéré

Pas d'alerte scanner auto, pas de hook session-end. La décision reste humaine.

## Leçon méta (pour le subject claude-forge lui-même)

Le pattern qui s'est répété 2× dans cette session (livrer une primitive → constater l'orphelinat parce que Benjamin pose la question d'intégration → combler) doit devenir un **checklist a priori** pour les prochaines vagues :

> *Pour chaque nouvelle primitive (engine + skill), avant de la considérer livrée, identifier : (a) où est-elle invoquée par d'autres skills/scanners, (b) comment l'utilisateur découvre qu'il doit l'utiliser, (c) si elle reste orpheline volontairement, le dire explicitement dans la décision technique.*

Cette leçon est intégrée dans la doctrine via la section « Quand invoquer ces skills » qui force l'expression explicite des triggers humains attendus à la création de tout nouveau skill subject pool.

## Suite

- **Vague 3 P4** (métrique retrieval, BM25 stdlib + corpus de test) — pas urgent, à attaquer quand Benjamin sera prêt
- **MCP server** (5e primitive identifiée dans l'analyse FORGE-analyse) — hors scope, instruire via `/idea` si pertinence émerge
- **Migration progressive des 26 subjects existants** vers les nouveaux états (actif/mature/archived) au fil des `/documente` successifs — pas urgent grâce au mapping legacy
- **Hint applicable rétroactivement** : si lors d'une session future Claude détecte qu'un workflow ad hoc a été exécuté manuellement, mentionner `/skillify` sans l'exécuter

## Liens

- Subject auto-référentiel : `/Users/bhamon/git/claude-forge/subjects/claude-forge/`
- Analyse déclencheuse : `benjamin-perso/Forge-lab/analyses/2026-05-09-meta-meta-prompting-garry-tan.md`
- Schéma post-refonte : `benjamin-perso/Forge-lab/analyses/2026-05-10-schema-forge-apres-refonte-cycle.html`
- 4 décisions YAML actives : `subjects/claude-forge/decisions/2026-05-10-*.yaml`
