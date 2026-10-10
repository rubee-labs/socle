---
type: skill-cas
parent_type: entity
horizon: permanent
capabilities: [memory, decisions, lifecycle]
name_pattern: "{nom du cas}"
---

# skill-cas — mémoire d'un cas d'usage d'un skill

Type générique livré par SOCLE (0.7.0). Un cas d'usage garde une mémoire bornée, ses discussions et ses décisions, et un état `actif` / `archived`. Pas d'événements externes ni de liens typés. Un dépôt peut surcharger ce type dans son propre `types/skill-cas/`.
