---
name: cross-modal-review
description: >-
  Évalue la qualité d'un MEMORY.md de subject (Quick + Détails régénérés par
  /documente) en faisant noter par 2-3 modèles distincts (Opus 4.7, Sonnet 4.6,
  Haiku 4.5) sur 4 axes : cohérence, complétude, spécificité, citations.
  Adapté du pattern "cross-modal eval" de Garry Tan (cf. analyse Forge-Lab
  2026-05-09). Trigger sur "review ce subject", "evaluate ce MEMORY",
  "cross-modal eval", "score la synthèse".
type_anthropic: 5
visibilité: entreprise
auteur: Benjamin
date_creation: 2026-05-10
version: 0.1
tags: [eval, qualité, multi-modèle, garry-tan, subject-pool]
effort: medium
outils_requis: [forge_eval_engine, Task]
securite_externe: false
---

# Cross-Modal Review — évaluation multi-modèle d'un subject

## Objectif

Quand `/documente` a régénéré le `MEMORY.md` (Quick + Détails) d'un subject, ce skill fait évaluer la qualité de cette synthèse par **plusieurs modèles indépendants** — Opus catch les erreurs de précision, Sonnet le contexte manquant, Haiku le ton générique. Les 3 scores s'agrègent en un score consolidé sur 4 axes.

C'est l'équivalent du *cross-modal eval* de Garry Tan : la mesure de qualité ne dépend pas d'un seul modèle, donc les biais de chaque modèle se compensent.

**Doctrine** : Forge n'a aujourd'hui aucune métrique de qualité de retrieval ni de re-synthèse. Sans cross-modal eval, la primitive `/documente` produit du contenu opaque dont personne ne sait s'il est bon. Ce skill est le **garde-fou de qualité** qui transforme le faux confort en signal mesurable.

## Quand utiliser

- Après une re-synthèse `/documente` significative (subject central, transition γ majeure, beaucoup d'events accumulés).
- Périodiquement (mensuel ?) sur les subjects en `tentative` ou `doctrine` pour vérifier qu'ils ne dérivent pas.
- En diagnostic quand un subject « semble flou » à la lecture — l'eval donne des issues précises.
- Avant de promouvoir un subject vers `compile-doctrine` (si la conviction est élevée mais le score d'eval médiocre, ne pas compiler).

**Quand NE PAS utiliser** :

- Sur les subjects en `seed` ou `debating` (pas assez de contenu pour mesurer quoi que ce soit).
- Sur les subjects archivés (sauf audit historique).
- En boucle automatique à chaque `/documente` (coût LLM × 3) — réserver aux moments structurants.

## Workflow

### Phase 1 — Préparer le contexte (Python)

Invoquer le moteur :

```bash
forge eval prepare <subject-path>
```

Sortie JSON `{ok, eval_id, subject_name, subject_type, memory_path, sources_summary, sources, eval_axes, prompt, expected_models}`.

Le champ `prompt` contient l'instruction structurée à envoyer à chaque modèle évaluateur (4 axes, format JSON attendu en retour).

### Phase 2 — Lancer 3 évaluateurs en parallèle (Task tool)

Pour chaque modèle de `expected_models` (Opus 4.7, Sonnet 4.6, Haiku 4.5) :

- Spawn un sub-agent via le tool `Task` avec :
  - `subagent_type`: `general-purpose`
  - `model`: le modèle visé (cf. mapping ci-dessous)
  - `description`: « Cross-modal eval — <subject_name> — <model> »
  - `prompt`: le contenu de `prompt` retourné par Phase 1, complété par :
    - Le contenu du `MEMORY.md` (lecture directe)
    - Un échantillon des sources (lecture optionnelle des events/discussions/decisions selon `sources_summary`)
    - Instruction explicite : « Retourne UNIQUEMENT du JSON valide, pas de commentaire »

Mapping modèle :
- `claude-opus-4-7` → axe d'attention prioritaire : précision, factualité
- `claude-sonnet-4-6` → axe d'attention prioritaire : recall, contexte manquant
- `claude-haiku-4-5` → axe d'attention prioritaire : spécificité, ton générique

⚠️ **Doctrine Rubee** : ne JAMAIS faire `from anthropic import Anthropic` ni utiliser de clé API. Le tool `Task` invoque les sub-agents via le harness Claude Code (plan Max). Si un dispatcher différent est nécessaire (Hyperliquid, etc.), passer par `claude-agent-sdk` avec auth Claude Code.

Récupérer les 3 réponses JSON. Sauvegarder chacune dans un fichier temporaire (ex: `/tmp/eval-opus.json`, `/tmp/eval-sonnet.json`, `/tmp/eval-haiku.json`).

### Phase 3 — Agréger (Python)

```bash
forge eval aggregate \
  --results /tmp/eval-opus.json /tmp/eval-sonnet.json /tmp/eval-haiku.json
```

Sortie JSON `{ok, evaluator_count, overall_score, axes: {coherence: {score_mean, score_min, score_max, issues, suggestions}, ...}}`.

Note : si un évaluateur a planté (JSON invalide ou refus), l'agrégation tourne quand même avec les évaluateurs restants. Mais si `evaluator_count < 2`, **alerter Benjamin** — l'eval mono-modèle n'a pas l'effet recherché.

### Phase 4 — Persister l'analyse

```bash
forge eval write-analysis <subject-path> --score '<json sortie aggregate>'
```

Crée `<subject-path>/analyses/<date>-cross-modal-eval.md` avec frontmatter conforme (`type: analysis`, `produced_by: claude`, `invoked_skill: /cross-modal-review`, `evaluator_count`, `overall_score`, `scoring`).

### Phase 5 — Présenter à Benjamin

Afficher dans la conversation :

- Score global (ex: `7.3 / 10`)
- Scores par axe (ex: `coherence 8 / completeness 6 / specificity 7 / citations 8`)
- **Top 3 issues** (problèmes les plus fréquemment cités par les évaluateurs — déjà dédupliqués par l'engine)
- **Top 3 suggestions** d'amélioration
- Lien vers le fichier `analyses/<date>-cross-modal-eval.md` complet

Si `overall_score < 6`, recommander explicitement à Benjamin de re-lancer `/documente` (ou de corriger manuellement le MEMORY.md) avant que ce subject ne soit promu en doctrine.

### Phase 6 — Commit (optionnel)

L'analyse étant un fichier `analyses/<date>-cross-modal-eval.md` produit par Claude, son commit suit la doctrine subject pool (commit avec le subject parent quand il sera re-synthétisé). Pas de commit séparé sauf demande explicite.

## Exemples

### Input

> "Lance un cross-modal review sur services/achats/subjects/order-398"

### Output (résumé)

```
Cross-modal eval — order-398 (supplier-order)

Score global : 7.5 / 10

  coherence    : 8.3  (n=3, min=8, max=9)
  completeness : 6.7  (n=3, min=5, max=8)  ← faiblesse
  specificity  : 7.0  (n=3, min=6, max=8)
  citations    : 7.7  (n=3, min=7, max=9)

Top issues :
- Quick mentionne "production lancée" mais aucun event email_prod_lancee trouvé
- Détails ne couvre pas la décision 2026-04-17-acompte-30 (active)
- Phrase "risques sous contrôle" sans citation (vague)

Suggestions :
- Ajouter événement email_prod_lancee si la prod a effectivement démarré
- Citer la décision acompte-30 dans la section "Paramètres"
- Détailler les risques (douane ? change ?) ou retirer la mention vague

Analyse persistée : services/achats/subjects/order-398/analyses/2026-05-10-cross-modal-eval.md
```

## Gotchas

- **Coût LLM** : 3 modèles × ~5k tokens prompt × ~2k tokens réponse = ~21k tokens par eval. À ne pas faire en boucle automatique. Réserver aux moments structurants.
- **Modèles refusent parfois** : Haiku ou Sonnet peuvent renvoyer un texte au lieu de JSON valide (notamment si le subject est ambigu). L'engine `aggregate` gère le cas (skip les invalides) — mais si <2 évaluateurs valides, prévenir Benjamin.
- **Pas de feedback loop automatique** : l'eval signale les issues, ne corrige pas. C'est volontaire — la correction est une re-invocation `/documente` ou un edit manuel par Benjamin.
- **Cross-modal ≠ adversarial** : ce skill mesure la qualité d'une synthèse existante, il ne challenge pas la doctrine du subject. Pour challenger une décision active, utiliser `/stress-test`.
- **Score < 6 = signal d'alarme** : ne pas promouvoir un subject vers `compile-doctrine` ou `in_service` si le cross-modal eval est sous 6. La conviction γ et le score d'eval doivent monter ensemble.

## Critères d'évaluation

- **EVAL 1** : `forge eval prepare` retourne un prompt qui mentionne les 4 axes et un format JSON attendu ? (Pass / Fail)
- **EVAL 2** : Les 3 évaluateurs ont produit du JSON valide ? Si moins, l'orchestrateur a-t-il alerté Benjamin ? (Pass / Fail)
- **EVAL 3** : `forge eval aggregate` produit-il un score global cohérent avec les 4 sous-scores ? (Pass si moyenne plausible / Fail si calcul faux)
- **EVAL 4** : L'analyse écrite dans `analyses/` a-t-elle un frontmatter complet (type, produced_by, evaluator_count, overall_score, scoring par axe) ? (Pass / Fail)
- **EVAL 5** : Le skill a-t-il été lancé sur ≥1 subject réel et les issues remontées sont-elles utiles (pas génériques) ? (Pass si Benjamin valide les issues comme actionnables / Fail sinon)
