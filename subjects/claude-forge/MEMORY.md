---
projet: claude-forge
statut: phase-3-refonte-process-gamma-3-etats + vague-3-p4-livree + decouplage-CE-0.2.0 + fix-parseur-scanner-0.2.2 + memory-borne-0.2.3 + madr-decision-0.2.4 + d10-provenance-skillify-0.2.5
derniere_maj: 2026-09-14
auteur: benjamin
---

# Projet : Claude-Forge — pattern subject pool + process γ

## Quick

État : actif (subject auto-référentiel du projet, pas une instance de type métier)
Statut : Phase 3 livrée + Vague 3 P4 livrée (bench_engine 2026-05-24) + **Découplage CE livré (0.2.0, 2026-06-05)**. Le plugin est désormais distribuable : config par-repo `.forge.yaml` (loader `load_forge_config`), `forge init`, skill `/forge-init`, hook SessionStart nudge. 1er pool non-CE bootstrapé : `benjamin-perso/jean-claude-code` (subject `kite-connect`). CE strictement inchangé (zéro config).
**0.2.3 (2026-09-06)** : MEMORY.md d'entité borné — commandes `check-memory` + `patch-section`, Phase F4 v2.8 (Quick < 100 mots, ≤ 10 décisions actives, règles apprises, plafond 8 Ko, journal de runs interdit → `rapports/`), `/documente` en `effort: medium`. Bloc 3 du plan CE ; bloc 4 (migration des 3 gros MEMORY.md CE) sous relecture Benjamin.
**0.2.2 (2026-09-06)** : parseur frontmatter corrigé (dicts imbriqués `last_event` lus `[]` sur 39/39 subjects CE → 34 stagnants faux) + scanner idempotent (plus de réécriture des index à chaque SessionStart, cause de 90 % des commits « Session » CE). Bloc 1 du plan « mémoire re-synthèse bornée + hook post-bloc » ; blocs 2-4 à venir (hook Stop CE, Phase L4 bornée, migration 3 gros MEMORY.md).
**0.2.5 (2026-09-14)** : D10 provenance bidirectionnelle skill ↔ subjects — `skillify scaffold --source-subjects` écrit `source_subjects:` dans le SKILL.md généré ET met à jour `linked_skills` des subjects d'origine ; 11e check hygiène `provenance_declared`. Déclencheur : analyse Forge-Lab #9 WikiSkill (Google Research) + incident « 0 skillify » (voir Règles apprises). **/skillify est vivant** : 4 skills réels côté CE (annote 23/06, compta-facture-suspens 20/07, compta-valeur-en-transit 27/07, compta-analyse-gcp 07/08) — sursis 2026-06-15 levé sur pièces pour /skillify.
Liens forts : aucun (subject racine du projet)
Prochaines étapes : rétrofit provenance des 4 skills CE existants (optionnel), trancher le reste du sursis 2026-06-15 (/cross-modal-review adoption ?, cycle γ influence réelle ? — review du 15/07 en retard), surveillance bench Forge (re-run 3-6 mois), arbitrage backlog Forge-Lab (Obsidian lecteur ? couche d'entreprise ?)
Risques : bench v1 limité aux questions frontmatter (questions sémantiques sur Quick non couvertes — évolution v2 à instruire si signal de saturation) ; hors /skillify, adoption /cross-modal-review et valeur du cycle γ toujours non démontrées

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

### Skills opérationnels (8 + 1 outil bench + 1 abandonné)

| Skill | Statut | Rôle |
|---|---|---|
| `/documente` | actif | Orchestrateur unique. Re-synthèse Quick + Détails, cascade horizontale, Phase F autolink, Phase H.5 validation graph, hints post-commit. |
| `/subject-create-type` | actif | Crée un type avec `typical_linked_types` enrichi `{name, type}`. |
| `/subject-create` | actif | Instancie un subject depuis un type. |
| `/subject-merge` | actif | Soude 2 subjects (validation Benjamin obligatoire). |
| `/skillify` | actif (depuis 2026-05-10), **4 skills livrés côté CE** (juin-août 2026) | Compile un workflow ad hoc en skill réutilisable (5 stubs). Pattern Garry Tan. Trigger humain explicite, hint dans /documente Phase J. Depuis 0.2.5 (D10) : `--source-subjects` pose la provenance bidirectionnelle skill ↔ subjects. |
| `/cross-modal-review` | actif (depuis 2026-05-10) | Évalue la qualité d'un MEMORY.md (4 axes, 2-3 modèles). À invoquer avant `actif → mature`. |
| `/stress-test` | optionnel à la demande | Challenge un subject (contradicteur, steelman, yagni). Pas de mutation d'état. Pas encore implémenté. |
| `forge bench` | actif (depuis 2026-05-24) | Outil de surveillance retriever (prepare / run / report). 3 retrievers déterministes (R1 cascade / R2 grep-agrégé / R3 fs-grep). Mode stdlib, $0, reproductible. Pas un skill (pas de slash command) — invocable directement via le binaire. |
| `/compile-doctrine` | **abandonné** (2026-05-10) | Théorique, 0 artefact compilé. Branche « procédurale → skill » reprise par `/skillify`. |

## Décisions actives

- **2026-09-14 — D10 : provenance bidirectionnelle skill ↔ subjects (0.2.5)** : `skillify scaffold --source-subjects` écrit `source_subjects:` dans le SKILL.md généré et ajoute le skill aux `linked_skills` des subjects d'origine ; 11e check hygiène `provenance_declared`. Équivalent PURPOSE.md WikiSkill (arXiv 2608.27454, analyse Forge-Lab #9). Voir `decisions/2026-09-14-d10-provenance-bidirectionnelle-skillify.yaml`.
- **2026-09-07 — Champs MADR dans le corps des décisions (0.2.4)** : `options_considerees` + `confirmation` attendus à la racine ; `write-capture` avertit (`madr_missing`) sans refuser ; modèle `templates/decision.body.yaml`. Voir `decisions/2026-09-07-champs-madr-decision-0-2-4.yaml`.
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
- **2026-05-24 — Vague 3 P4 livrée : `bench_engine`** : outil de surveillance retriever (`forge bench prepare / run / report`), 3 retrievers déterministes (R1 cascade Forge, R2 grep agrégé, R3 grep filesystem), mode stdlib zéro coût zéro LLM. Baseline Rubee 2026-05-24 : R1 100%, R3 100% mais 450× plus lent, R2 97%. **La cascade Forge tient à 100% au scope actuel (33 subjects)** — pas de panique structurelle. Strictement read-only, aucune mutation archi. Décision déclenchée par recadrage Benjamin post-analyse Forge-Lab #6 SamourAI (2026-05-24) : « on mesure avant de présumer ». Voir `decisions/2026-05-24-p4-bench-engine-livre.yaml`.

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
| Vague 3 P4 | 2026-05-24 | `bench_engine.py` + intégration `forge bench {prepare,run,report}` + 6 tests verts + baseline Rubee 2026-05-24 (R1 100%, R2 97%, R3 100% / 450 ms p50) |

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

### Vague 3 P4 — bench_engine (2026-05-24)

Livré : `bin/bench_engine.py` (~430 LoC stdlib) avec 3 sous-commandes (`prepare`, `run`, `report`) intégrées au binaire `forge` via `forge bench`. 3 retrievers déterministes :

- **R1 cascade** : SUBJECTS-INDEX.md → MEMORY.md du subject ciblé → frontmatter parse. Pattern canonique Forge.
- **R2 grep-aggregated** : blob concaténé de tous les MEMORY.md → grep paragraphe.
- **R3 filesystem-grep** : `grep -l -r "name: X"` puis parse frontmatter.

Mode déterministe ($0, ~secondes, reproductible) — pas d'appel LLM. La gold answer est extraite directement du frontmatter, donc trivialement vérifiable par substring match.

**Baseline Rubee 2026-05-24** (33 subjects, 123 questions auto-vérifiables, 369 calls, 57 s wall-clock) :

| Retriever | Exact | Substring | Latence p50 | Latence p95 |
|---|---|---|---|---|
| R1 cascade | 100% | 100% | 0 ms | 0 ms |
| R2 grep-agrégé | 97% | 97% | 0 ms | 0 ms |
| R3 fs-grep | 100% | 100% | 450 ms | 520 ms |

Verdict : la cascade Forge tient à 100% sur le scope actuel. R3 grep est aussi précis mais 450× plus lent (subprocess fork overhead). R2 perd 3% sur des cas-bord du parseur YAML maison. Pas de raison structurelle de paniquer.

Limites assumées de la v1 :
- Questions extraites du frontmatter = trop faciles pour discriminer sur la précision.
- Pas de simulation Claude réel (mode déterministe seul).
- Latence R1 p50 = 0 ms artificielle (pas de cold-start, pas de navigation réelle).

6 tests verts (`tests/test_bench.py`). Strictement read-only — aucune mutation de l'archi Forge.

Sauvegardé : `bench/2026-05-24-rubee-baseline-{corpus,results,report}.{json,md}` comme point de référence à comparer dans 3-6 mois.

## En attente
- **MCP server natif OAuth 2.1** (5e primitive de l'analyse FORGE-analyse 2026-05-09) : hors scope vagues 1-3. À instruire via `/idea` si pertinence émerge.
- **Migration progressive des 33 subjects existants** vers les nouveaux états (actif/mature/archived) — pas urgent, le mapping legacy garantit la rétrocompat. Nettoyage au fil des `/documente` successifs.
- **Phase 1.5** : enrichir `forge_engine.py` avec détection de patterns émergents inter-subjects (ex: 3 retards consécutifs Simon → analysis auto). Reporté.
- **Test end-to-end `/control-tower → /documente`** sur un email réel (premier vrai cycle email automatique).
- **Backlog Phase 0.5** : enrichir scanner forge pour détecter les liens orphelins (gotcha #4).
- **Nettoyage technique mineur** : `bin/documente_engine.py:81` mentionne encore `conviction` dans `list-subjects` (lecture seule, à nettoyer un jour).

## Veille (signaux faibles à surveiller)

- **Re-run bench Forge dans 3-6 mois** : comparer baseline 2026-05-24 (R1 cascade 100%, 33 subjects) à un nouveau run. Si dérive significative (R1 < 90% par exemple), instruire évolution v2 du bench (questions sémantiques sur Quick, génération synthétique 100/300 subjects).
- **2 sujets flaggés post-SamourAI (2026-05-24)** à rediscuter — voir `benjamin-perso/Forge-lab/MEMORY.md` § Discussions ouvertes : (1) Obsidian comme lecteur (plugin frontmatter → wikilinks), (2) Forge n'est pas une couche d'entreprise (réouvrir D1 si scale Rubee).
- **Adoption /skillify** : ~~si 0 skillify livré → hint trop faible~~ **résolu 2026-09-14** : 4 skills réels livrés côté CE (annote, compta-facture-suspens, compta-valeur-en-transit, compta-analyse-gcp). Nouvelle veille : vérifier que les prochains skillify passent `--source-subjects` (D10) et que les `linked_skills` se peuplent.
- **Adoption /cross-modal-review** : toujours non démontrée. Si aucun subject n'est passé en `mature` avec eval préalable, le hint n'est pas opérant. Reste du sursis 2026-06-15 à trancher (avec la valeur du cycle γ).
- **Migration legacy** : combien de subjects ont encore un ancien `forging_state` (seed/debating/tentative/...) après 30 jours ? Si > 50%, signaler que la migration ne se fait pas naturellement.
- **Bilingue chaotique futur** : pertinent dès le 3ème type créé. Anticiper un canon de dimensions partagées.
- **Cohabitation Labs** : `/CE-analyse` écrit dans CE-Lab sans frontmatter étendu. Phase 2 (adoption opportuniste) à amorcer.
- **Courbe apprentissage équipe** : pool reste outil personnel. Pas de transfert tant que pas de doctrine compilée et utilisée.

## Règles apprises

- **L'usage d'une feature se vérifie dans git, jamais dans un MEMORY** (incident 2026-09-14) : ce MEMORY a affirmé « 0 skillify livré » pendant 3 mois alors que 4 skills existaient — les runs skillify ne remontaient aucune trace dans le pool (pas de provenance, `linked_skills` vides). Un MEMORY re-synthétisé ne voit que ce qu'on lui remonte. Correction structurelle : D10.

## Alertes

(aucune)
