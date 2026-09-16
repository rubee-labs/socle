---
nom: documente
type: skill
version_actuelle: "2.6"
derniere_maj: 2026-05-07
---

# MEMORY.md — Skill /documente

## Doctrine en vigueur

- **Architecture hybride Python + LLM** (depuis 2026-05-04, v2.2)
  - Phases déterministes (frontmatter, scan, commit, cohérence) → `entreprise/config/feedback-loop/documente_engine.py`
  - Phases cognitives (capture conversation, synthèse Quick/Détails, jugement pertinence) → LLM
  - Stdlib only Python (pas de pyyaml/ruamel), JSON sur stdout, exit code toujours 0

- **Workflow Subject Pool** (paths avec `/subjects/<name>/`)
  - 10 phases A-J décrites dans SKILL.md
  - 7 commandes binaire invoquées (prepare, infer-type, write-capture, patch-frontmatter, scan-impacted, cascade-last-event, commit-atomic)
  - + forge_engine.py (existant) en Phase E
  - LLM seul en Phase C (capture), F (synthèse), I-jugement
  - Gain ~70% tokens vs ancien workflow LLM-only

- **Workflow Folder** (paths sans `/subjects/`, depuis 2026-05-04 v2.3, raffiné v2.6)
  - 7 phases F0-F6 décrites dans SKILL.md
  - 3 commandes binaire invoquées (write-capture × 2, scan-impacted, commit-atomic)
  - LLM seul en F1 (identifier), F3.5 (cohérence — format markdown), F4 (MAJ MEMORY.md format markdown)
  - **Phase F0 (v2.6)** : critère POSITIF subject pool vs entité. Défaut = entité (`<entité>/decisions/`). Subject pool réservé aux objets métier durables avec cycle γ. Plus de proposition systématique de migration.
  - Gain ~30-40% tokens vs ancien workflow LLM-only

- **Bascule sèche, pas de feature flag** : tag git `pre-documente-engine-cutover` créé avant la refonte pour rollback via `git revert` ou `git reset --hard`.

- **API utilisateur inchangée** : `/documente <subject-path> [--type <type>]` — la refonte est transparente côté Benjamin.

## Décisions actives

- [2026-05-04-bascule-engine-python](decisions/2026-05-04-bascule-engine-python.yaml) — Bascule subject pool vers documente_engine.py (v2.1 → v2.2)
- [2026-05-04-extension-engine-au-legacy](decisions/2026-05-04-extension-engine-au-legacy.yaml) — Extension binaire au workflow legacy + Phase L0 migration (v2.2 → v2.3)
- [2026-05-07-phase-l0-critere-positif-defaut-entite](decisions/2026-05-07-phase-l0-critere-positif-defaut-entite.yaml) — Phase F0 reformulée en critère positif, défaut = entité (v2.5 → v2.6). Closes rubee-labs/socle#1.

## Décisions annulées

(aucune)

## Garde-fous critiques

- **Phase F0 (v2.6) — critère positif** : défaut = `<entité>/decisions/` (folder). Migration vers subject pool UNIQUEMENT si la décision concerne un objet métier durable avec cycle γ (suppliers, commandes, campagnes, décisions architecturales long-terme), itérations successives prévues. Une modification de code/comportement d'UNE entité reste dans son `decisions/`.
- **Phase F0 — pas de re-proposition si refus** : chercher marqueur `migration_subject_pool: refused` dans les `decisions/` du dossier avant de proposer.
- **Phase F4 reste LLM only** : MEMORY.md folder = sections markdown structurées (pas frontmatter étendu). `patch-frontmatter` ne s'applique pas. `patch-markdown-section` à créer si Phase F4 devient lente.
- **Phase F3.5 reste LLM only** : `check-coherence` lit le frontmatter MEMORY.md (subject pool). Folder = liste markdown.
- **Idempotence garantie** : 2 invocations consécutives sans nouvel input doivent produire un diff vide.
- **Commit atomique** : discussion + decision + memory.md (subject + cascade) ensemble dans un seul commit.

## Liens

- Plan d'extraction : [plans/2026-05-04-extraction-engine-python.md](plans/2026-05-04-extraction-engine-python.md)
- Binaire CLI : `entreprise/config/feedback-loop/documente_engine.py`
- Helpers : `entreprise/config/feedback-loop/documente_lib.py`
- Tests : `entreprise/config/feedback-loop/tests/test_documente_engine.py` (29 tests)
- Logger perf : `entreprise/config/feedback-loop/documente_engine.log` (gitignored)
- Hooks instrumentation : `.claude/settings.json` (UserPromptSubmit + Stop) + `entreprise/scripts/log-documente-hook.py`
