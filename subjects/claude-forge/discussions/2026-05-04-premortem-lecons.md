---
date: 2026-05-04
sujet: Premortem subject pool — invalidation sur prémisses fausses, leçons retenues
statut: aboutie
decision: null
---

# Discussion — Premortem invalidé, leçons retenues

## Contexte

Un premortem (méthode Klein, 8 sub-agents en parallèle) avait été lancé le 2026-05-03 sur le subject pool. Il avait produit une décision majeure d'override : "inverser la priorité Tower-Control vs subject pool — construire Tower-Control AVANT de continuer le pool".

Lors de la documentation via /documente le même jour, Benjamin a signalé que `/control-tower` existait déjà et fonctionnait. Investigation : le skill est en Phase 1 manuel, **utilisé activement** (log `control-tower-achats.jsonl` modifié 2026-05-03 11:40, 5.2 Ko de traces), et **alimente le subject pool** via /subject-create + /forge.

## 2 prémisses fausses du premortem

### Prémisse fausse 1 — "Tower-Control jamais construit"

J'avais construit le contexte des sub-agents en m'appuyant sur la décision 2026-04-29 ("Tower-Control reclassé en super-agent par dossier — Hors scope Phase 0, à brainstormer séparément après tests du subject pool"), sans réaliser qu'elle avait été **révisée le même jour soir** : `/control-tower` a été créé en Phase 1 manuel multi-service.

Vérification :
- `entreprise/skills/control-tower/SKILL.md` existe, créé 2026-04-29
- 4 sous-dossiers : `lib/`, `logs/`, `prompts/`, `services/`
- 1 service configuré : `services/achats.yaml`
- Log actif : `control-tower-achats.jsonl` (2026-05-03 11:40, 5162 octets)

### Prémisse fausse 2 — "Subjects en seed = cimetière vide"

J'avais supposé que les 13 subjects en `seed` étaient des coquilles vides créées en réflexe par Benjamin. En réalité, ils sont **pré-remplis par /control-tower avec du contexte MCP riche** :

```yaml
linked_records:
  - {type: order_id, value: 383, source: mcp_achats}
  - {type: expedition_id, value: 294, source: mcp_achats}
  - {type: order_label, value: "CADENCEMENT / TABLES 9016 - HOMFUL - 1*40'HQ - 251020"}
  - {type: order_status, value: "attente_paiement_solde"}
  - {type: order_amount, value: "14747.60 USD"}

last_event:
  date: 2026-04-16
  type: container_arrival
```

Tous les 7 supplier-orders ont leurs liens MCP, leur dernier event factuel, leur fournisseur lié. Ce ne sont pas des coquilles, ce sont des contextes attendant un forge.

## Conséquence

Les 2 conclusions stratégiques du premortem (override priorité Tower-Control + plan révisé "Tower-Control AVANT pool") sont **caduques** : le besoin est déjà adressé.

**Rollback effectué** :
- `discussions/2026-05-03-premortem-resultats.md` → supprimé
- `decisions/2026-05-03-inverser-priorite-tower-control.yaml` → supprimé
- `MEMORY.md` → restauré à son état pré-premortem (frontmatter, décisions actives, en attente, alertes)

Aucune décision active n'a été annulée. La doctrine en vigueur reste celle du 2026-04-29 + raffinements 2026-05-01.

## Causes du premortem qui restent valides (6 sur 8)

À conserver comme **veille** dans le MEMORY.md (signaux faibles à surveiller), pas comme décisions actives.

| Cause | Statut | Surveillance |
|---|---|---|
| #1 Cimetière de seeds | Recadré : seeds pré-remplis pas vides | Ratio seed/non-seed via SUBJECT-POOL-METRICS.md |
| #2 Compilation jamais déclenchée | Valide | 0 doctrine compilée à débloquer dès qu'un supplier permanent accumule 2-3 leçons |
| #3 Fatigue alerte | Valide + faux positifs knowledge-coord | "MEMORY.md vide" remonte sur subjects → fixer le scanner pour les exclure |
| #4 Bilingue chaotique | Valide pour le futur | Anticiper canon dimensions partagées avant 3ème type |
| #5 Tower-Control jamais construit | **Faux** | À jeter |
| #6 Cohabitation Labs | Valide | /CE-analyse écrit dans CE-Lab sans frontmatter étendu |
| #7 Courbe apprentissage équipe | Valide | Pas de transfert tant que pas de doctrine compilée |
| #8 Outil en quête de problème | **Faux** | À jeter |

## Vraies questions stratégiques (à brainstormer séparément si besoin)

1. **/control-tower : Phase 1 → Phase 2** (manuel → auto-apply L0/L1 + cron + Slack async). C'est la vraie question d'évolution de l'agent, pas "construire Tower-Control".
2. **Forge des 7 supplier-orders pré-remplis** : quand vas-tu les faire avancer dans le cycle γ ? Sans forge, pas de leçons remontées vers les suppliers permanents, pas de compilation.
3. **Knowledge Coordinator faux positif** : ses alertes "MEMORY.md vide" sur les 13 subjects sont structurellement fausses (les MEMORY.md de subject n'ont pas la même structure que les MEMORY.md de service). À fixer.

## Méta-leçon (pour la prochaine fois)

Le frame "ça a échoué dans 6 mois" est puissant mais ne se substitue pas à la **vérification factuelle de l'état présent**. Le SKILL premortem dit "Recherche silencieuse (max 30s) avant de demander : Conversation en cours, CLAUDE.md, MEMORY.md, dossiers discussions/decisions/ du projet concerné, fichiers explicitement référencés". Cette étape a été insuffisante : j'aurais dû :

1. Lister `entreprise/skills/control-tower/` AVANT le brainstorm (j'aurais vu qu'il existe)
2. Lire au moins 1 MEMORY.md de subject AVANT le brainstorm (j'aurais vu les `linked_records` riches)
3. Regarder la date du log `control-tower-achats.jsonl` (j'aurais vu qu'il est utilisé)

À retenir pour le SKILL premortem : enrichir la Phase 1 ("Collecte de contexte") avec une **vérification factuelle obligatoire** des prémisses centrales du plan stress-testé. Pas de premortem sur du contexte non-vérifié.

## Rapport HTML

Le rapport `entreprise/skills/premortem/cas/2026-05-03-subject-pool/premortem-report.html` reste comme trace pédagogique. Je l'annote avec un bandeau d'invalidation en tête pour signaler que les causes #5 et #8 reposent sur des prémisses fausses, et que les conclusions stratégiques (override de priorité) sont caduques.

## Décision

Aucune. Cette discussion documente l'invalidation et préserve les leçons retenues, sans produire de décision active.
