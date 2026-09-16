---
date: 2026-05-04
type: discussion
produced_by: human_and_claude
participants: [benjamin, claude]
sujet: Refonte du moteur Forge — gap détecté entre /forge codé et /forge imaginé
status: closed
resulting_decision: 2026-05-04-documente-2.0-entry-point-unique
---

# Refonte du moteur Forge — gap structurel détecté et corrigé

## Contexte

Point sur le workflow subject pool en début de session. Benjamin demande "comment faire un point avant que tout claude enterprise soit corrompu par des procédures mal codées" : il a l'impression que :

1. `/documente` ne lance pas le workflow subject-pool en fin de discussion
2. `/forge` ne tourne pas automatiquement au lancement d'une nouvelle session

Investigation immédiate (lecture des SKILL.md de `/forge`, `/documente`, `/control-tower`, du hook SessionStart, et de `forge_scanner.py`).

## Premier constat : pas de procédure mal codée

Tout fonctionnait conformément à la doctrine :
- `forge_scanner.py` tourne bien en SessionStart (via `~/.claude/scripts/init-healthcheck.sh`), génère SUBJECTS-INDEX + METRICS, émet alertes
- `/forge` est un skill manuel par design (Phase 4 demande validation utilisateur)
- `/documente` est un skill manuel, pas auto-déclenché
- 13 subjects actifs, 0 stagnation, pas d'alertes parasites

Mais le système est **sous-utilisé** : aucun subject n'a été promu au-delà de `seed` depuis sa création. Le scanner détecte mais ne forge pas (par design : la forge est un acte humain validé).

## Deuxième constat : gap conceptuel majeur

En creusant, Benjamin clarifie qu'il avait une vision **différente** de `/forge` :

> "Je ne comprends pas /forge. Pour moi /forge était une sorte de concaténation du savoir fait progressivement à partir de l'enchaînement d'intrants (ici des emails). Pour moi ça se faisait automatiquement après chaque nouvel email."

Deux visions de `/forge` se confrontent :

| Vision Benjamin (intuitive) | Vision codée (machine à états) |
|---|---|
| Métaphore : forgeron qui martèle continûment | Métaphore : machine à états |
| Auto-déclenché à chaque event/discussion/décision | Manuel, validation à chaque transition |
| Régénère `## Quick` + `## Détails` du MEMORY.md | Change `forging_state` dans le frontmatter |
| Propage vers les `linked_subjects` (cascade horizontale) | Aucune cascade |
| Détecte transitions γ et les applique en transparent | Demande validation pour chaque transition |

La vision Benjamin = un **moteur de re-compilation continue**. La vision codée = un **opérateur de transition d'état**. Ce n'est pas la même chose.

## Concept clé manquant : compilation horizontale

Benjamin formalise la distinction critique :

- **Compilation verticale** = historique d'un même sujet dans le temps (ex-`/decision`, `/documente`). Bien implémenté.
- **Compilation horizontale** = liens entre sujets différents (order-398 ↔ supplier-weifang ↔ product-line). Annoncé dans le frontmatter (`linked_subjects`) mais **inerte** : aucune propagation effective.

Sans compilation horizontale active, le `## Quick` d'order-398 reste figé à "État: seed, conviction 0" alors que 5 events accumulés. Et `supplier-weifang` ne sait rien des évolutions de ses commandes filles.

C'est exactement la dimension qui devait justifier l'existence du subject pool (vs `/decision` historique). Benjamin synthétise : "j'avais l'impression que notre réflexion avait été efficace, mais je me rends compte que j'ai loupé des concepts".

## Clarifications via AskUserQuestion (4 questions)

1. **Verbe "/forge"** → re-synthèse continue (vision Benjamin) ; la transition d'état devient un mécanisme interne, pas un skill séparé.
2. **Auto-déclenchement** → transparent (résultat affiché, pas de prompt).
3. **Profondeur cascade** → 1 niveau (rapidité prioritaire pour appel fréquent).
4. **Re-synthèse cascade contient** : stats agrégées + référence dans last_event + Quick narratif régénéré + détection de patterns émergents.

## Architecture conçue (plan initial)

Couche 1 — `forge_engine.py` (Python, déterministe) : extraction events, stats agrégées, last_event, détection transition γ, cascade list. <500ms.

Couche 2 — `/forge` SKILL.md refondu (Claude, sémantique) : régénère `## Quick` + `## Détails`, applique transitions γ auto, affiche diff transparent.

Auto-déclenchement par `/control-tower` (Phase 5 après chaque event) et `/documente` (Phase 4 après décision).

Plan envoyé à Ultraplan (cloud) pour raffinement architectural avant implémentation.

## Décision Ultraplan (plus radicale que le plan initial)

Ultraplan a choisi une approche **différente et plus propre** :

- **Pas de skill `/forge` séparé** : `/forge` SKILL.md **supprimé**.
- `/documente` 2.0 devient l'**entry point unique** : capture conversation (si applicable) + re-synthèse (si subject pool) + cascade horizontale + transitions auto + diff + commit + push.
- Le mot "forge" reste pour le moteur Python (`forge_engine.py`, `forge_lib.py`, `forge_scanner.py`) mais sort du vocabulaire utilisateur.

Avantage majeur : **un seul verbe utilisateur ("documenter") = un seul point d'entrée**. Plus de "je documente ou je forge ?" — tu documentes, et la re-synthèse + cascade + maturation γ se font dans la foulée.

PR mergée : commit `6e189bc4` (15 fichiers, +1129 / -479).

## Validation end-to-end (post-merge)

Tests exécutés sur order-398 (subject réel, 6 events, négo Fancy/Weifang) :

1. ✅ `forge_engine.py` : JSON valide, transition `seed→debating` détectée, cascade vers `supplier-weifang` résolue (heuristique `supplier:weifang` → `supplier-weifang/`), stats agrégées calculées (`total_orders: 1, total_amount_usd: 16943.0`).
2. ✅ `/documente services/achats/subjects/order-398/` : pipeline 9 phases exécuté. Chaînage `seed→debating→tentative` (≥1 active_decision dans frontmatter), conviction bumped à 50, `## Quick` reflète l'état réel (vs figé "seed, conviction 0"), `## Détails` régénéré en préservant les sections custom (`### Stress tests à prévoir`, `### Notes libres`).
3. ✅ Cascade vers `supplier-weifang` : `last_event.type: cascaded_from_order-398`, `## Quick` enrichi avec stats agrégées, `## Détails` non touché (règle cascade respectée).
4. ✅ Transition `tentative→stress_testing` proposée mais `auto: false` (hint affiché, pas appliquée — garde-fou Ultraplan respecté).
5. ✅ `forge_scanner.py` : pas de régression (`Forge: OK — 13 actifs`).

## Méta-leçon

Le pattern "verbe trop large, fonctionnalités confondues" est piégeux. "Forge" évoquait à la fois :
- Le **process global** (re-compilation continue) — vision Benjamin
- Une **étape de transition** (machine à états) — vision codée

Quand on construit du vocabulaire interne, **un mot = une responsabilité**. Si le mot couvre plusieurs niveaux d'abstraction, on finit par coder le niveau le plus simple (transition) et oublier le niveau le plus important (compilation continue). Ultraplan a remédié à ça en **réservant "forge" au moteur interne** (Python) et en faisant porter la responsabilité utilisateur par `/documente` (verbe métier clair).

## Conséquences sur la doctrine projet

1. La décision Phase 0 du 2026-04-29 listait "6 skills : /subject-create-type, /subject-create, /forge, /stress-test, /subject-merge, /compile-doctrine". À ramener à 5 skills (suppression de /forge).
2. La décision /control-tower du 2026-04-29 mentionnait "/forge" comme étape du workflow d'intégration au subject pool. À actualiser : `/control-tower` Phase 5 invoque désormais `/documente`, pas `/forge`.
3. Le projet sort de "phase-0-validee" pour entrer en **"phase-1-moteur-resynthese-operationnel"** : la Phase 0 livrait l'infrastructure ; Phase 1 livre le moteur vivant.
