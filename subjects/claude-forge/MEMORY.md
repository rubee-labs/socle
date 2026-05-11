---
projet: claude-forge
statut: phase-3-refonte-process-gamma-3-etats
derniere_maj: 2026-05-11
auteur: benjamin
---

# Projet : Claude-Forge — pattern subject pool + process γ

## Quick

État : actif (subject auto-référentiel du projet, pas une instance de type métier)
Statut : Phase 3 livrée — refonte process γ + 3 nouvelles primitives (P5 autolink, P3 skillify, P2 cross-modal-eval)
Liens forts : aucun (subject racine du projet)
Prochaines étapes : Vague 3 P4 (métrique retrieval BM25), migration progressive des 26 subjects existants vers les 3 nouveaux états (non urgent grâce au mapping legacy)
Risques : hint /skillify trop discret → primitive sous-utilisée (à surveiller sur 4 semaines)

## Doctrine en vigueur (2026-05-11)

Le **subject pool** est l'infrastructure de stockage et de propagation de connaissance. Il généralise le pattern CE-Lab / WM-Lab / Alter-Lab. **Le pattern d'infrastructure est intact depuis Phase 0 (avril 2026)** — seul le **process γ** (mécanisme de maturation interne d'un subject) a été refondu le 2026-05-10.

### Subject pool — infrastructure (intacte)

- **Subject** = réceptacle persistant. CE, WM, supplier-simon, order-400 sont tous des subjects.
- **Type** = patron partagé (REFERENCE.md + TEMPLATE.md). Toutes les instances d'un type héritent de sa grille d'analyse.
- **4 sous-dossiers** par subject distingués par producteur : `events/` (external), `analyses/` (claude), `discussions/` (human_and_claude), `decisions/` (human).
- **Format MEMORY.md** : Quick (<100 mots) + Détails rédigés + sous-sections custom préservées.
- **Cascade horizontale 1 niveau** via `linked_subjects` : `last_event` + Quick + stats agrégées propagés.
- **Typed graph (P5, depuis 2026-05-10)** : `typical_linked_types` enrichi en paires `{name, type}`, extraction déterministe par `bin/autolink_engine.py`, zéro LLM. Graph requêtable via `forge autolink graph-query <slug>`.
- **Nomenclature bilingue** : squelette anglais (taxonomie), contenu métier français snake_case.
- **Lecture en cascade** : niveau 1 = `SUBJECTS-INDEX.md`, niveau 2 = `MEMORY.md`, niveau 3 = fichier précis à la demande.

### Process γ — refondu (depuis 2026-05-10)

Cycle simplifié à **3 états** (`actif` / `mature` / `archived`), transitions 100% manuelles via `/documente` avec validation Benjamin. Rétrocompat 100% : anciens états (`seed`, `debating`, `tentative`, `stress_testing`, `doctrine`, `in_service`, `under_review`) mappés en lecture seule par `LEGACY_STATE_MAP`. Pas de migration forcée.

- `conviction` numérique 0..100 → **supprimée** (champ deprecated, ignoré par le moteur)
- `/compile-doctrine` → **abandonné** (théorique, jamais utilisé en pratique)
- `/stress-test` → **découplé** du cycle, optionnel à la demande
- Transitions automatiques → **aucune** (moteur ne mute jamais `forging_state`)
- Alertes scanner `doctrine_uncompiled` + `stress_test_missing` → **supprimées**

### Skills opérationnels (8 + 1 abandonné)

| Skill | Statut | Rôle |
|---|---|---|
| `/documente` | actif | Orchestrateur unique. Re-synthèse Quick + Détails, cascade horizontale, Phase F autolink, Phase H.5 validation graph, hints post-commit. |
| `/subject-create-type` | actif | Crée un type avec `typical_linked_types` enrichi `{name, type}`. |
| `/subject-create` | actif | Instancie un subject depuis un type. |
| `/subject-merge` | actif | Soude 2 subjects (validation Benjamin obligatoire). |
| `/skillify` | actif (depuis 2026-05-10) | Compile un workflow ad hoc en skill réutilisable (5 stubs). Pattern Garry Tan. Trigger humain explicite, hint dans /documente Phase J. |
| `/cross-modal-review` | actif (depuis 2026-05-10) | Évalue la qualité d'un MEMORY.md (4 axes, 2-3 modèles). À invoquer avant `actif → mature`. |
| `/stress-test` | optionnel à la demande | Challenge un subject (contradicteur, steelman, yagni). Pas de mutation d'état. Pas encore implémenté. |
| `/compile-doctrine` | **abandonné** (2026-05-10) | Théorique, 0 artefact compilé. Branche « procédurale → skill » reprise par `/skillify`. |

## Décisions actives

- **2026-04-29 — Adoption du pattern subject pool en γ pragmatique** : adoption opportuniste, pas de migration forcée. Les anciens patterns (Labs, MEMORY.md de service, discussions/decisions répartis) restent valides.
- **2026-04-29 — Intégration Forge au Health-check** : `forge_scanner.py` branché dans `~/.claude/scripts/init-healthcheck.sh`. Voir `decisions/2026-04-29-fix-integration-healthcheck.yaml`.
- **2026-05-01 — Raffinements post-Phase 0** : règle bilingue stricte, doctrine `subject-pool.md` extraite, KPIs scanner. Voir `decisions/2026-05-01-raffinements-post-phase-0.yaml`.
- **2026-05-04 — Refonte du moteur Forge : `/documente` 2.0 entry point unique** : `/forge` SKILL.md supprimé, fonctionnalité fusionnée dans `/documente`. Architecture 2 couches Python + Claude sémantique. Voir `decisions/2026-05-04-documente-2.0-entry-point-unique.yaml`.
- **2026-05-05 — Extraction Subject Pool vers plugin Claude Code `claude-forge`** : repo Git autonome `rubee-labs/claude-forge`, distribué via `/plugin marketplace add`. Voir `decisions/2026-05-05-migration-claude-forge.yaml`.
- **2026-05-07 — Doctrine MCP 100% gateway** (consigne globale, externe à claude-forge).
- **2026-05-10 — P5 Auto-link déterministe** : `typical_linked_types` enrichi `[{name, type}]`, `bin/autolink_engine.py`, intégration /documente Phase F + H.5. Voir `decisions/2026-05-10-p5-autolink-typed-graph.yaml`.
- **2026-05-10 — P3 Skillify** : 3 sous-commandes CLI (scaffold/check/audit), 8 critiques + 2 hygiène, sentinelle SKILLIFY_STUB. Skill orchestrateur `/skillify`. Voir `decisions/2026-05-10-p3-skillify-compilation-continue.yaml`.
- **2026-05-10 — P2 Cross-modal eval** : 3 sous-commandes (prepare/aggregate/write-analysis), 4 axes, 2-3 modèles Anthropic via Task tool. Skill `/cross-modal-review`. Voir `decisions/2026-05-10-p2-cross-modal-eval.yaml`.
- **2026-05-10 — Refonte process γ 8→3 états** : `actif` / `mature` / `archived`, conviction supprimée, `/compile-doctrine` abandonné, `/stress-test` découplé, transitions 100% manuelles. Voir `decisions/2026-05-10-cycle-gamma-refonte-3-etats.yaml`.
- **2026-05-11 — Hints textuels orphelinat** : `/documente` Phase J suggère `/skillify` et `/cross-modal-review` sans déclenchement auto. Tableau « Quand invoquer ces skills » dans la doctrine. Pattern Garry = trigger humain explicite, pas de détection auto qui produirait du bruit.

## Décisions annulées

(aucune)

## Détails

### Phases livrées

| Phase | Date | Livrable principal |
|---|---|---|
| Phase 0 | 2026-04-29 | 11/11 tâches : 5 skills, scanner, hook SessionStart, type `supplier-order`, doctrine `subject-pool.md`, SUBJECTS-INDEX |
| Phase 1 | 2026-05-04 | Refonte moteur : `forge_engine.py` (Python) + `/documente` 2.0 entry point unique, cascade horizontale, transitions γ auto, validation order-398 |
| Phase 2 | 2026-05-05 | Extraction plugin Claude Code (`rubee-labs/claude-forge`), 17 refs vivantes patchées, marketplace.json, binaire `forge` |
| Phase 3 | 2026-05-10/11 | P5 autolink + P3 skillify + P2 cross-modal-eval + refonte process γ + hints textuels d'orphelinat |

### Vague 1 P5 — Auto-link déterministe

`bin/autolink_engine.py` (~330 LoC stdlib) avec 3 sous-commandes : `extract` (typed edges sortants), `graph-query` (BFS limité par direction et nom de relation), `reconcile` (idempotent). Format `typical_linked_types` enrichi rétrocompatible avec l'ancien format liste plate. 17 tests verts, validation réelle sur order-398 et supplier-homful.

Intégration end-to-end ajoutée immédiatement après que Benjamin a pointé l'orphelinat initial : `/subject-create-type` Phase 2 q7 et Phase 3 génèrent le nouveau format dès la création des nouveaux types, `/documente` Phase F.1 invoque `forge autolink extract` et inclut une ligne « Liens forts » dans le Quick, nouvelle Phase H.5 valide la cohérence pré-commit (non bloquante).

### Vague 2 P3 — Skillify

`bin/skillify_engine.py` (~430 LoC) avec `scaffold` (5 stubs SKILL.md + script + tests + fixture routing + EVAL), `check` (audit 10 points dont 8 critiques + 2 hygiène), `audit` (global). Adaptation vs Garry : 3 verbes au lieu de 4 (pas de `routing-eval`, Claude Code dispatche par description du frontmatter), distinction critical/hygiène cohérente avec l'archi claude-forge (engines dans `bin/` partagé). Sentinelle `SKILLIFY_STUB` avec exclusion backticks dans `.md` pour permettre au skill `/skillify` lui-même de mentionner la sentinelle (dogfooding validé). 9 tests verts.

### Vague 2 P2 — Cross-modal eval

`bin/eval_engine.py` (~280 LoC) avec `prepare` (compose prompt + résumé sources), `aggregate` (mean/min/max + dédup issues), `write-analysis` (persiste dans `<subject>/analyses/`). 4 axes : cohérence, complétude, spécificité, citations. 3 modèles single-provider Anthropic (Opus + Sonnet + Haiku) invoqués via Task tool depuis le skill `/cross-modal-review` (pas de clé API directe — doctrine `feedback_jamais_cle_api_toujours_max_via_sdk.md`). Tolérance aux pannes (un évaluateur sur 3 peut renvoyer JSON invalide → agrégation tourne avec ≥2 valides). 6 tests verts.

### Refonte process γ

Déclenchée par la remarque pivot de Benjamin lors de la livraison Vague 2 : `/skillify` recouvre la branche « procédurale → skill auto-généré » de `/compile-doctrine` (quasi-doublon). Refonte complète validée : 8 états → 3 (actif/mature/archived), conviction numérique supprimée, transitions 100% manuelles, `/compile-doctrine` abandonné, `/stress-test` découplé du cycle. `forge_engine.py` étendu avec `LEGACY_STATE_MAP` pour mapping en lecture des anciens états. `forge_scanner.py` simplifié (alertes obsolètes supprimées, distribution sur 3 états). 5 REFERENCE.md de types annotés avec note de refonte (préserve les notes métier importantes). 32 tests cumulés Vague 1+2 passent toujours.

### Hints textuels orphelinat (2026-05-11)

Benjamin a pointé deux fois dans la session le pattern d'orphelinat (« comment skillify se lance ? », « comment autolink est appelé ? »). Résolution par hints textuels uniquement (pas de trigger auto) :

- `/documente` SKILL.md Phase J : nouvelle section « Hints post-commit (suggestions humaines, non-bloquantes) » qui suggère `/skillify` si workflow ad hoc répété détecté + `/cross-modal-review` si transition `actif → mature` envisagée
- `rules/subject-pool.md` tableau Skills enrichi (note « trigger humain explicite » sur `/skillify`, note « avant transition actif→mature » sur `/cross-modal-review`)
- Nouvelle section « Quand invoquer ces skills (triggers humains attendus) » : tableau de 6 cas d'usage → skill suggéré

Cohérent avec le pattern Garry Tan : trigger humain explicite (« skillify it »), pas de détection automatique qui produirait du bruit.

### Leçon méta (checklist a priori pour les prochaines vagues)

Pour chaque nouvelle primitive (engine + skill), avant de la considérer livrée :
- (a) **Identifier où elle est invoquée** par d'autres skills/scanners.
- (b) **Identifier comment l'utilisateur découvre** qu'il doit l'utiliser.
- (c) **Si elle reste orpheline volontairement, le dire explicitement** dans la décision technique.

Cette leçon est intégrée dans la doctrine via la section « Quand invoquer ces skills » qui force l'expression explicite des triggers humains attendus à la création de tout nouveau skill subject pool.

## En attente

- **Vague 3 P4 — métrique retrieval** : `bin/bench_engine.py` (BM25 stdlib + corpus de test, P@k / R@k / MRR / nDCG@k). Pas urgent.
- **MCP server natif OAuth 2.1** (5e primitive de l'analyse FORGE-analyse 2026-05-09) : hors scope vagues 1-3. À instruire via `/idea` si pertinence émerge.
- **Migration progressive des 26 subjects existants** vers les nouveaux états (actif/mature/archived) — pas urgent, le mapping legacy garantit la rétrocompat. Nettoyage au fil des `/documente` successifs.
- **Phase 1.5** : enrichir `forge_engine.py` avec détection de patterns émergents inter-subjects (ex: 3 retards consécutifs Simon → analysis auto). Reporté.
- **Test end-to-end `/control-tower → /documente`** sur un email réel (premier vrai cycle email automatique).
- **Backlog Phase 0.5** : enrichir scanner forge pour détecter les liens orphelins (gotcha #4).
- **Nettoyage technique mineur** : `bin/documente_engine.py:81` mentionne encore `conviction` dans `list-subjects` (lecture seule, à nettoyer un jour).

## Veille (signaux faibles à surveiller)

- **Adoption /skillify** : hint discret dans /documente Phase J — vérifier sur 4 semaines que des workflows ad hoc sont effectivement skillifiés. Si 0 skillify livré → hint trop faible, revoir.
- **Adoption /cross-modal-review** : pareil. Si aucun subject n'est passé en `mature` avec eval préalable, le hint n'est pas opérant.
- **Migration legacy** : combien de subjects ont encore un ancien `forging_state` (seed/debating/tentative/...) après 30 jours ? Si > 50%, signaler que la migration ne se fait pas naturellement.
- **Bilingue chaotique futur** : pertinent dès le 3ème type créé. Anticiper un canon de dimensions partagées.
- **Cohabitation Labs** : `/CE-analyse` écrit dans CE-Lab sans frontmatter étendu. Phase 2 (adoption opportuniste) à amorcer.
- **Courbe apprentissage équipe** : pool reste outil personnel. Pas de transfert tant que pas de doctrine compilée et utilisée.

## Alertes

(aucune)
