---
type: agent
parent_type: entity
horizon: permanent
capabilities: [memory, decisions, lifecycle]
name_pattern: "{nom de l'agent}"
---

# agent — mémoire d'un agent

Type générique livré par SOCLE (0.7.0). Un agent garde une mémoire bornée, ses discussions et ses décisions, et un état `actif` / `archived`. Pas d'événements externes ni de liens typés. Un dépôt peut surcharger ce type dans son propre `types/agent/`.
