---
date: 2026-06-15
type: discussion
produced_by: human_and_claude
participants: [benjamin, claude]
status: closed
resulting_decision: 2026-06-15-okf-conformance-d7-d8-d9
upstream_analyses:
  - benjamin-perso/Forge-lab/analyses/2026-06-15-okf-google-open-knowledge-format.md
---

# OKF v0.1 — positionnement Forge

## Contexte

Google Cloud Data Cloud a publié le 2026-06-12 le **Open Knowledge Format (OKF) v0.1**, une spec ouverte qui formalise le pattern « LLM wiki » en format portable et interopérable :

- Markdown + YAML frontmatter
- Directory hierarchy
- Cross-links via markdown links inline
- 1 champ obligatoire (`type`), 5 champs conventionnels (`title`, `description`, `resource`, `tags`, `timestamp`)
- Reference implementations : Enrichment Agent (Google ADK + Gemini), visualizer Cytoscape.js, 3 bundle samples BigQuery

Source signal racine : **Andrej Karpathy LLM Wiki gist**, cité explicitement par OKF — exactement le même signal qui avait nourri l'analyse Forge-Lab #1 Garry Tan (2026-05-09). Forge et OKF sont partis du même endroit, ont divergé 6 mois, et Google publie le standard.

Analyse Forge-Lab #8 a chiffré le signal : **pertinence 10** (premier de Forge-Lab), action `faire-evoluer-doctrine`.

## Tension

Trois faux conforts Forge fragilisés :

1. **« Forge est unique dans son design markdown wiki »** — démenti par OKF qui montre que le pattern est partout (Karpathy, Notion, Obsidian, Hugo, AGENTS.md). La validation par Google est rassurante, mais l'unicité est invalidée.
2. **« Forge n'a pas besoin de spec versionnée parce que c'est mon outil perso »** — démenti par la publication d'un standard ouvert avec v0.1 + conformance criteria. Si Forge se présente comme « subject pool » sans spec versionnée, c'est ad hoc face à OKF.
3. **« Le moat Forge = couplage MCPs Rubee + decisions humaines + dogfooding »** — toujours valide MAIS exige que la couche **par-dessus** OKF (cycle γ, producer typing, autolink typed, skillify) fasse maintenant tout le moat. Le pattern markdown wiki n'est plus différenciant.

## Question stratégique

Comment Forge se positionne face à OKF ? 3 options :

| Option | Description | Coût | Risque |
|---|---|---|---|
| **A** | Ignorer OKF, garder Forge ad hoc | 0 | Forge devient « pas standard », barrière d'adoption tools tiers |
| **B** | Migrer Forge vers OKF strict (abandonner cycle γ + producer typing pour matcher la spec) | 2-3 mois | Perte d'identité Forge, régression sur les couches au-dessus |
| **C** | **Forge devient superset OKF conformant** : tout subject Forge est aussi un concept OKF valide, et Forge garde ses couches additionnelles (cycle γ, producer typing, autolink, skillify) en extensions | 1 jour | Aucun — la spec OKF autorise explicitement les extensions |

## Décision

**Option C tranchée par Benjamin le 2026-06-15.**

Forge devient un **superset OKF conformant**. Concrètement :

- **D7** : étendre le frontmatter avec les 5 champs conventionnels OKF (`title`, `description`, `resource`, `tags`, `timestamp`) en optionnels. Zéro casse, rétrocompatible. ✅ Appliqué dans `subject-pool.md` § Champs du frontmatter.
- **D8** : acter Forge comme conformant OKF v0.1 dans la doctrine. ✅ Section dédiée ajoutée dans `subject-pool.md` § « Conformance Open Knowledge Format (OKF v0.1) ».
- **D9** : implémenter `forge okf-sync` qui maintient une section `## Liens` inline (markdown links) dans le body des MEMORY.md, entourée de markers HTML idempotents. ✅ Livré `bin/okf_sync_engine.py`.

## Validation empirique

Le visualizer Google Cytoscape.js (depuis le repo `GoogleCloudPlatform/knowledge-catalog`) a rendu correctement des bundles Forge :

- `services/marketing/subjects/` → 32 concepts × 20 edges
- `services/achats/subjects/` → 129 concepts × 34 edges

Sans translation côté consumer. **Preuve que Forge ↔ OKF est vraie compat fonctionnelle**, pas juste théorique.

## Déplacement du moat Forge

Le moat n'est plus le pattern subject pool (commoditisé 2026-05-21, standardisé 2026-06-15). Le moat se déplace **encore** vers les couches Forge-spécifiques au-dessus d'OKF :

1. **Cycle de vie γ** — gouvernance humaine du cycle des subjects (3 états, transitions manuelles)
2. **Producer typing** — 4 sous-dossiers `events/` `analyses/` `discussions/` `decisions/` qui distinguent `produced_by`
3. **Autolink typed** — graphe sémantique déterministe zéro-LLM
4. **`/skillify`** — compilation continue workflow → skill
5. **`/cross-modal-review`** — éval qualité 2-3 modèles
6. **`/documente`** — orchestrateur unique
7. **Couplage MCPs Rubee** — intégration native métier (achats, ads, oms, treasury, mail, slack)
8. **Dogfooding intra-CE** — la doctrine Forge est elle-même un subject auto-référentiel

Aucune de ces couches n'est requise par OKF, aucune ne casse OKF.

## Limite identifiée — veille passive

Délai détection OKF = **3 jours** (publié 12/06, analysé 15/06). Honorable au scope actuel (Benjamin lit la veille, lance `/FORGE-analyse`) mais **insuffisant si plusieurs signaux d'ampleur arrivent en parallèle** (Google + Microsoft + Anthropic le même jour).

À surveiller : faut-il un mécanisme actif de monitoring (agent SDK qui scanne GitHub topics `knowledge format`, `agent memory`, `LLM wiki`) ? Pas d'urgence — flag pour le premortem.

## Suite immédiate

- Re-sync des subjects Rubee via `forge okf-sync sync` (déjà fait pendant le bloc — 56 liens résolus sur 56)
- Publier v0.1.3 du plugin claude-forge (pour propager D7 + D8 + binaire `forge okf-sync` au cache)
- `/plugin update rubee-labs/claude-forge` côté Benjamin pour aligner l'exécution réelle
