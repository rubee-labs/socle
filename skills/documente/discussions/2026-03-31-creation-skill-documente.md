---
date: 2026-03-31
sujet: Creation du skill /documente — pipeline documentation automatise
statut: aboutie
decision: null
---

# Creation du skill /documente

## Contexte

Pendant l'analyse du leak Claude Code (autoDream, extractMemories), Benjamin constate que les memory.md des agents a etat sont mis a jour par une instruction "best effort" dans le CLAUDE.md, pas par un mecanisme garanti. Le staleness tracking (verdict du council) resout le probleme en aval (detecter les perimes), mais /documente le resout en amont (s'assurer que la documentation est faite systematiquement).

## Cheminement

1. Les rules discussions/decisions etaient dispersees dans 3 fichiers (`savoirs.md`, `operations.md`, `skills-agents.md`)
2. Benjamin disait deja "documente" naturellement en fin de session
3. L'idee : formaliser ce mot en un skill qui execute le pipeline complet
4. Discussion → decision → memory.md → commit → push en une seule commande

## Decision

Skill cree dans `entreprise/skills/documente/SKILL.md` + slash command `.claude/commands/documente.md`.
Les regles existantes sont conservees (elles definissent le FORMAT, le skill execute le PIPELINE).
