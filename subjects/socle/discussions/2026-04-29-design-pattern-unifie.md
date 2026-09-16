---
date: 2026-04-29
sujet: Design du pattern unifié de subjects et forge γ
statut: aboutie
decision: 2026-04-29-adoption-subject-pool
---

# Discussion — Design du pattern unifié

## Contexte

Benjamin construit Tower-Control et constate qu'il a besoin d'un pattern unifié de "piscine de sujets" pour TOUS les sujets de l'entreprise (commandes, fournisseurs, gammes, projets stratégiques, incidents, etc.), pas seulement pour les emails.

Cible long terme : niveau 3 du World Model (compilation continue interrogeable, à la "Karpathy LLM Wiki") et la promesse YC d'une "living map → executable skills file for AI" (oiya.ai, modular-context-obsidian).

## Cheminement

### Itération 1 — Cartographie de l'existant

3 patterns coexistaient sans être unifiés :
- **Pattern Lab** (CE/WM/Alter) avec analyses/discussions/decisions/INDEX/SYNTHESE/REFERENCE/IDEAS-A-APPLIQUER
- **Pattern réparti** : 104 dossiers `discussions/decisions/` proches du domaine
- **Pattern log** : Tower-Control log.jsonl

### Itération 2 — Modèle conceptuel

Initialement Claude proposait une distinction artificielle "concept (permanent) / instance (temporel)". Benjamin a recadré : **un seul type d'objet, le subject**, avec une propriété `horizon` (bounded / permanent / cyclic). CE, supplier-simon, order-400 sont tous des subjects, juste avec des cycles de vie différents.

### Itération 3 — Métaphore de la forge

Benjamin a apporté la métaphore : un savoir se forge comme du métal (brut → forme → trempe → service → ébréchée → refonte). C'est un **pipeline dialectique** (Karl Popper : conjecture & refutation).

Initialement Claude a mélangé "forge" et "bulles de savon" (agglutination, fusion). Benjamin a recadré : on garde uniquement la forge.

### Itération 4 — Architecture

Tentation initiale : créer un nouveau "data-pool" séparé (avec localisation unique, fédérée ou cohabitation). Benjamin a recadré une 2e fois : l'archi par dossier existante (`services/X/` avec mcp+tools+skills+discussions+decisions+savoirs+MEMORY.md) est excellente. Pas de nouvelle topologie. Le subject pool est juste une **discipline de frontmatter étendu** + **2 chantiers** :

1. Perfectionnement des hooks SessionStart (scanner forge)
2. La notion de forge (frontmatter + skills + compilation)

### Itération 5 — Tower-Control

Benjamin a reclassé Tower-Control comme **super-agent par dossier** (pas un tool de mail). Triggers multiples (emails, alertes, événements MCP), accès aux outils du dossier. Pattern archi C (déjà acté en mémoire). **Hors scope** Phase 0, à brainstormer séparément.

### Itération 6 — Détails du modèle

- 4 sous-dossiers distingués par **producteur** : events (external), analyses (claude seul), discussions (human_and_claude), decisions (human)
- Hiérarchie type/instance avec REFERENCE.md (grille) + TEMPLATE.md (squelette) au niveau du type
- MEMORY.md du subject = synthèse compacte (Quick <100 mots + Détails), pas un log
- Lecture en cascade : SUBJECTS-INDEX.md (toujours) → MEMORY.md du subject → fichier précis (rare)
- Nomenclature anglaise unifiée (snake_case, dates `*_at`)

## Conclusion

Position γ "vrai" recentré : aucune migration de l'existant, frontmatter étendu optionnel, scanner forge greffé sur les hooks existants, compilation doctrine → exécutable comme différenciant central.

Plan complet écrit dans `~/.claude/plans/ok-en-cr-ant-tower-glimmering-quill.md` et approuvé.

Phase 0 implémentée le même jour (29/04/2026).

## Décision

Voir `decisions/2026-04-29-adoption-subject-pool.yaml`.
