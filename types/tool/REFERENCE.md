---
type: tool
parent_type: entity
horizon: permanent
capabilities: [memory, decisions, lifecycle]
name_pattern: "{nom du dossier de l'outil}"
---

# tool — mémoire d'un outil

Type générique livré par SOCLE (0.7.0). Un outil garde une mémoire bornée, ses discussions et ses décisions, et un état `actif` / `archived`. Pas d'événements externes ni de liens typés. Un dépôt peut surcharger ce type dans son propre `types/tool/`.
