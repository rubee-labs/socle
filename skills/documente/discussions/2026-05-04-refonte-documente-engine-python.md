---
date: 2026-05-04
sujet: Refonte /documente vers documente_engine.py + extension legacy + Phase L0 migration
statut: aboutie
decisions_associees:
  - 2026-05-04-bascule-engine-python
  - 2026-05-04-extension-engine-au-legacy
---

## Cheminement

### 1. Question initiale (matin)

Benjamin demande : « Penses-tu qu'il serait pertinent de transformer /documente en agent avec agent-sdk ? »

Réponse : non — `/documente` est un orchestrateur dépendant du contexte conversationnel (extraction décision, propagation cascade, etc.). L'isolation Agent SDK perdrait ce contexte. Le bon candidat pour un agent SDK serait plutôt un déclencheur autonome (ex : scanner périodique qui appelle `/documente` en headless), pas le verbe `/documente` lui-même.

### 2. Identification des phases déterministes

Question reformulée par Benjamin : « Y a-t-il des actions de /documente qui pourraient être écrites en python pour éviter de brûler du token et aller plus vite ? »

Cartographie du SKILL.md v2.1 (12 phases) en 3 catégories :
- **Déjà Python** : Phase 4 (forge_engine.py)
- **Déterministe mais LLM** : Phases 0a-0e (détection), 1 (listing), 3 (frontmatter), 3.5 (cohérence), 6 (patch frontmatter), 7 (cascade mécanique), 8 (scan), 9 (commit)
- **Cognitif (LLM irréductible)** : Phase 2 (capture conversation), 3 corps (rédaction), 5 (synthèse Quick/Détails), 8 jugement (pertinence)

Identification : ~70% des tokens consommés peuvent être économisés en extrayant les phases déterministes vers un binaire CLI calqué sur `forge_engine.py`.

### 3. Plan d'extraction (13 tasks)

Création d'un plan détaillé (`plans/2026-05-04-extraction-engine-python.md`) :
- 9 commandes CLI : list-subjects, prepare, infer-type, patch-frontmatter, commit-atomic, scan-impacted, check-coherence, write-capture, cascade-last-event
- Stratégie strangler pattern (M1-M7 livrent le binaire, T13 bascule sèche)
- Pas de feature flag (validé par Benjamin)
- Tag rollback `pre-documente-engine-cutover`
- M8 hooks Claude Code écarté (cas A : seul /documente écrit dans decisions/)

### 4. Exécution TDD (~1h vs 6 jours estimés)

13 tasks exécutées en TDD strict (test rouge → implémentation → test vert → commit) :
- 1 bug détecté en cours : `forge_lib.parse_simple_yaml` transforme `parameters:` en liste vide au lieu de dict vide → contourné via helper dédié `parse_nested_dict_block` dans `documente_lib.py`
- 29 tests unittest passent
- Régression sur subjects réels (order-398, supplier-weifang) : aucune modification, idempotence OK
- Bascule sèche du SKILL.md (ligne 68-300 remplacées par workflow A-J)

### 5. Test grandeur nature et observation

Benjamin invoque `/documente` deux fois post-bascule :
- 21:01:54 sur `entreprise/skills/control-tower/` (workflow legacy, 2 min)
- 22:05:37 sur `entreprise/skills/optimisation-campagne-amazon/cas/IT/` (workflow legacy, 4 min)

Constat : aucune amélioration de perf perçue. Hypothèse confirmée via instrumentation (logger append-only dans `documente_engine.py` + hooks UserPromptSubmit/Stop) : **0 invocation Python** car les deux paths sont legacy (pas de `/subjects/` dans le chemin).

Confusion identifiée : Benjamin pensait être en subject pool car le format des fichiers produits (frontmatter YAML, MEMORY.md update) est visuellement similaire entre les deux workflows. Le vrai critère est la présence d'invocations dans `documente_engine.log`.

### 6. Décision corrective : étendre le binaire au legacy + Phase L0

Trois options évaluées :
- **A. Migration totale** : convertir tous les dossiers en subject pool. Énorme refacto.
- **B. Renommer pour clarifier** : `/documente-subject` vs `/documente-classique`. Confusion résolue mais pas le gain.
- **C. Unifier le binaire** : étendre 3 commandes génériques (`write-capture`, `scan-impacted`, `commit-atomic`) au workflow legacy.

Choix : **option C** + ajout d'une Phase L0 « Proposition de migration vers subject pool » à chaque invocation legacy (push doctrinaire vers subject pool au fil du temps).

Garde-fous Phase L0 :
- Pas de proposition sur dossiers figés (skills/tools sans cycle de vie)
- Pas de re-proposition si refus précédent (marqueur `migration_subject_pool: refused`)

## Conclusion

`/documente` v2.3 :
- **Subject pool** (paths avec `/subjects/`) : workflow Python complet, ~70% tokens en moins
- **Legacy** (autres paths) : workflow Python partiel (3 phases), ~30-40% tokens en moins, proposition migration systématique en Phase L0
- **Mesure** : logger append-only dans le binaire + hooks Claude Code permettent désormais de mesurer durée perçue / Python / LLM seul

Aucun changement d'API utilisateur (`/documente <subject-path> [--type <type>]` inchangé).

## Décisions tranchées (déjà tracées séparément)

- `2026-05-04-bascule-engine-python.yaml` : bascule sèche subject pool vers binaire (v2.2)
- `2026-05-04-extension-engine-au-legacy.yaml` : extension binaire au legacy + Phase L0 (v2.3)
