---
projet: claude-forge
statut: phase-2-extraction-plugin-livree
derniere_maj: 2026-05-05
auteur: benjamin
---

# Projet : Subject Pool — pattern unifié de sujets et forge γ

## Doctrine en vigueur

Le **subject pool** est le pattern unifié pour tout réceptacle qui accumule des données + analyses + discussions + décisions sur un thème. Il généralise le pattern CE-Lab / WM-Lab / Alter-Lab.

- **Subject** = réceptacle persistant. CE, WM, supplier-simon, order-400 sont tous des subjects.
- **Type** = patron partagé (REFERENCE.md + TEMPLATE.md). Toutes les instances d'un type héritent de sa grille d'analyse.
- **4 sous-dossiers** par subject distingués par producteur : `events/` (external), `analyses/` (claude), `discussions/` (human_and_claude), `decisions/` (human).
- **Cycle de vie γ** : seed → debating → tentative → stress_testing → doctrine → in_service → under_review → archived.
- **Compilation en exécutable** : doctrine + conviction ≥ 80 → règle MEMORY, skill, agent SDK, monitor, injection ou negative kw.

Voir aussi :
- `entreprise/config/rules/savoirs.md` § "Subject Pool"
- `entreprise/config/rules/skills-agents.md` § "Format Subject"
- `~/.claude/plans/ok-en-cr-ant-tower-glimmering-quill.md` (plan complet)

## Décisions actives

- **2026-04-29 — Adoption du pattern subject pool en γ pragmatique** : les anciens patterns (Labs, MEMORY.md de service, discussions/decisions répartis) restent valides. Adoption opportuniste, pas de migration forcée.
- **2026-04-29 — Tower-Control reclassé en super-agent par dossier** : pas un tool de mail. Hors scope Phase 0. À brainstormer séparément après tests du subject pool.
- **2026-04-29 (soir) — Reprise sous `/control-tower --achats` (skill manuel multi-service)** : décision révisée le même jour. Le skill privé `Tower-Control-Achats` (2026-04-28) est archivé ; un skill enterprise `/control-tower` est créé dans `entreprise/skills/control-tower/` avec config par service (`services/<service>.yaml`) et **intégration au subject pool** (matching + `/subject-create` + `/forge` + mise en perspective avec contenu de l'instance). Phase 1 = manuel (Benjamin lance), validation explicite sur **chaque** écriture. Phase 2 = auto-apply L0/L1 + cron + Slack async. Phase 3 = migration archi C si volume justifie. Voir `entreprise/skills/control-tower/SKILL.md` et `~/.claude/plans/merry-nibbling-lamport.md`.
- **2026-04-29 — Corrections post-test** : 2 gotchas critiques corrigés (forge bump conviction à 50 lors de tentative, compile-doctrine gère MEMORY.md inexistant). 2 gotchas mineurs reportés. Voir `decisions/2026-04-29-corrections-gotchas.yaml`.
- **2026-04-29 — Intégration Forge au Health-check** : forge_scanner.py branché dans `~/.claude/scripts/init-healthcheck.sh` (hors repo) au lieu d'un hook SessionStart séparé. La ligne "Forge: ..." apparaît maintenant dans le bloc Health-check unifié entre Memory et Feedback. Règle apprise (gotcha #5) : tout futur scanner spécifique-CE qui doit s'afficher dans le bloc unifié doit être enregistré dans init-healthcheck.sh, pas en hook isolé. Voir `decisions/2026-04-29-fix-integration-healthcheck.yaml`.
- **2026-05-01 — Raffinements post-Phase 0 (4 décisions consolidées)** : (1) règle bilingue stricte (squelette anglais, contenu métier français) appliquée à supplier-order et garante dans `/subject-create-type`. (2) module dédié `entreprise/config/rules/subject-pool.md` (~280 lignes) comme "réacteur" de premier rang, sortie de `savoirs.md`. (3) KPIs Tier 1 ajoutés au scanner forge + génération `entreprise/SUBJECT-POOL-METRICS.md`. (4) fix sémantique : merger_candidate restreint aux subjects `horizon: permanent` (évite faux positifs sur instances bornées). Voir `decisions/2026-05-01-raffinements-post-phase-0.yaml`.
- **2026-05-04 — Premortem invalidé sur prémisses fausses, leçons retenues** : le premortem du 2026-05-03 a été basé sur 2 prémisses fausses (Tower-Control "jamais construit" alors qu'il est en Phase 1 manuel actif, et "subjects en seed = cimetière vide" alors qu'ils contiennent des linked_records riches du MCP achats). Les causes #5 et #8 du premortem sont à rejeter. 6 causes restent valides comme veille (cimetière recadré, compilation jamais déclenchée, fatigue alerte avec faux positifs knowledge-coordinator, bilingue chaotique futur, cohabitation Labs, courbe apprentissage équipe). Aucun override de décision active. Voir `discussions/2026-05-04-premortem-lecons.md`.
- **2026-05-04 — Refonte du moteur Forge : `/documente` 2.0 entry point unique** : gap structurel détecté en début de session — `/forge` était codé comme un opérateur de transition d'état pure, alors que la vision Benjamin était un **moteur de re-compilation continue** (verticale + horizontale). Plan envoyé à Ultraplan, qui a choisi une approche radicale : `/forge` SKILL.md **supprimé**, fonctionnalité fusionnée dans `/documente` 2.0. Architecture en 2 couches : `forge_engine.py` (Python déterministe, <500ms) + `/documente` (Claude sémantique, régénère Quick + Détails + cascade horizontale 1 niveau). Auto-déclenchement transparent par `/control-tower` après chaque event. Transitions auto limitées à `seed→debating` et `debating→tentative`. Validation end-to-end sur order-398 OK (chaînage seed→tentative, cascade vers supplier-weifang). Voir `discussions/2026-05-04-refonte-moteur-forge.md` + `decisions/2026-05-04-documente-2.0-entry-point-unique.yaml`.
- **2026-05-05 — Extraction Subject Pool vers plugin Claude Code `claude-forge`** : Subject Pool reconnu comme 4ème couche de mémoire de Claude Code (après contexte session, auto-memory, CLAUDE.md), pas spécifique Rubee. Extraction big-bang depuis `claude-enterprise/entreprise/config/feedback-loop/` vers son propre repo Git autonome `rubee-labs/claude-forge` (privé GitHub). Distribué comme plugin Claude Code via `/plugin marketplace add`. Architecture hybride : code global (engines + skills + binaire `forge` dans PATH), données per-project (`<project>/subjects/<name>/`). Méta-réflexion (ce subject lui-même) migrée dans `claude-forge/subjects/claude-forge/` — dogfooding. Bug `get_project_dir()` corrigé en v0.1.1 (résolution cwd-based standard). Validé : `forge scanner` 15 actifs depuis claude-enterprise. Voir `discussions/2026-05-05-migration-claude-forge.md` + `decisions/2026-05-05-migration-claude-forge.yaml`.

## Décisions annulées

(aucune pour l'instant)

## Phase 0 livrée (2026-04-29)

11/11 tâches Phase 0 complétées :

- ✅ Documentation conventions (`savoirs.md` + `skills-agents.md` étendus)
- ✅ Type d'exemple `supplier-order` (REFERENCE.md + TEMPLATE.md)
- ✅ ~~6 skills~~ → 5 skills (depuis 2026-05-04, `/forge` supprimé) : `/subject-create-type`, `/subject-create`, `/documente` (ex-/forge), `/stress-test`, `/subject-merge`, `/compile-doctrine`
- ✅ Scanner forge (`entreprise/config/feedback-loop/forge_scanner.py`)
- ✅ Hook SessionStart intégré (.claude/settings.json)
- ✅ `/documente` étendu pour le frontmatter subject pool (puis refondu en 2.0 le 2026-05-04 — entry point unique du moteur forge)
- ✅ `entreprise/SUBJECTS-INDEX.md` régénéré au démarrage de session

## Phase 2 livrée (2026-05-05) — extraction plugin Claude Code

Migration du moteur Subject Pool depuis claude-enterprise vers son propre repo plugin Claude Code.

- ✅ Repo Git autonome `rubee-labs/claude-forge` (privé) avec marketplace.json + plugin.json
- ✅ Engines Python (5 fichiers) + 4 skills (documente, subject-create*, subject-merge) + slash command + rules + templates + tests migrés
- ✅ Binaire CLI `forge` (dispatcher documente/engine/scanner) auto-installé dans PATH par Claude Code
- ✅ 17 refs vivantes patchées (`python3 entreprise/config/feedback-loop/<engine>.py` → `forge documente|engine`)
- ✅ Hook `~/.claude/scripts/init-healthcheck.sh` invoque `forge` (PATH) avec fallback clone local
- ✅ Hook `entreprise/scripts/log-documente-hook.py` log dans `entreprise/logs/documente_hook.log`
- ✅ Méta-réflexion migrée vers `claude-forge/subjects/claude-forge/` (dogfooding)
- ✅ Symlink local `claude-enterprise/harness/claude-forge` (gitignored)
- ✅ Fix v0.1.1 : `get_project_dir()` cwd-based au lieu de `Path(__file__).parents[3]`
- ✅ Validé end-to-end : `/plugin marketplace add rubee-labs/claude-forge` + `/plugin install claude-forge@rubee-labs` + `/reload-plugins` + `forge scanner` retourne `15 actifs` ✅

Net : claude-forge +9929 lignes (commits `06ba19a` → `73317dc`), claude-enterprise -12423/+7 lignes (commit `dca6fd02`).

## Phase 1 livrée (2026-05-04) — moteur de re-synthèse opérationnel

Refonte complète du moteur forge suite au gap "compilation horizontale absente" détecté en début de session 2026-05-04.

- ✅ Architecture 2 couches : `forge_engine.py` (Python déterministe) + `/documente` (Claude sémantique)
- ✅ `forge_lib.py` extrait des helpers communs (parse_frontmatter, days_since, etc.)
- ✅ `/documente` 1.0 → 2.0 (Phases 1-9, entry point unique)
- ✅ `/forge` SKILL.md supprimé (fusion dans /documente)
- ✅ `/control-tower` Phase 5 : invoque /documente après chaque event
- ✅ Cascade horizontale 1 niveau implémentée (last_event + Quick + stats agrégées sur les linked_subjects)
- ✅ Transitions γ auto (`seed→debating`, `debating→tentative`) avec chaînage limité à 2 itérations
- ✅ Résolution heuristique tolérante des linked_subjects (formats hétérogènes acceptés)
- ✅ Validation end-to-end sur order-398 (chaînage seed→tentative, cascade supplier-weifang OK)
- ✅ Doctrine `subject-pool.md` mise à jour + section "Compilation horizontale"

PR Ultraplan : commit `6e189bc4` (15 fichiers, +1129 / -479).

## En attente

- ~~Test end-to-end~~ ✅ effectué le 2026-04-29 (cf. rapport)
- ~~Phase 1 : premier subject réel~~ ✅ livré 2026-05-04 (refonte moteur forge + validation order-398)
- Phase 1.5 : enrichir `forge_engine.py` avec détection de patterns émergents inter-subjects (ex: 3 retards consécutifs Simon → analysis auto). Émettre alertes scanner SessionStart.
- Phase 2 : adoption opportuniste sur l'existant — invoquer `/documente` sur les autres subjects pour les sortir de `seed`.
- Phase 3 (long terme, optionnel) : wrapper CE-Lab / WM-Lab / Alter-Lab.
- Test end-to-end `/control-tower → /documente` sur un email réel (premier vrai cycle email automatique).
- Test `/stress-test` sur order-398 (transition tentative→stress_testing manuelle).
- ~~Brainstorm Tower-Control / super-agents par dossier (archi C)~~ → repris en `/control-tower --achats` Phase 1 le 2026-04-29 (skill manuel actif). Migration archi C reportée Phase 3.
- Backlog Phase 0.5 : enrichir scanner forge pour détecter les liens orphelins (gotcha #4).

## Veille (issues du premortem 2026-05-03, prémisses fausses sur #5/#8)

6 causes à surveiller comme signaux faibles, sans en faire des décisions actives :

- **Cimetière de seeds** (recadré) : les 13 subjects pré-remplis par /control-tower contiennent du contexte MCP riche, mais ne forgent pas. Surveiller le ratio seed/non-seed via SUBJECT-POOL-METRICS.md.
- **Compilation jamais déclenchée** : 0 doctrine compilée à ce jour. À débloquer dès qu'un supplier permanent aura accumulé 2-3 leçons remontées.
- **Fatigue alerte (avec faux positifs knowledge-coordinator)** : "MEMORY.md vide" remonte sur les 13 subjects parce que knowledge-coordinator était écrit pour les MEMORY.md de service. À fixer pour exclure les subjects.
- **Bilingue chaotique futur** : pertinent dès le 3ème type créé. Anticiper un canon de dimensions partagées.
- **Cohabitation Labs jamais résolue** : /CE-analyse écrit dans CE-Lab sans frontmatter étendu. Phase 2 (adoption opportuniste) à amorcer.
- **Courbe apprentissage équipe** : pool reste outil personnel. Pas de transfert tant que pas de doctrine compilée et utilisée.

## Alertes

(aucune pour l'instant — les "alertes premortem" précédentes ont été retirées car basées sur prémisses fausses)
