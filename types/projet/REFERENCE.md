---
type: projet
parent_type: entity
horizon: permanent
capabilities: [memory, decisions, lifecycle, events, links]
name_pattern: "{nom court du projet, kebab-case}"
---

# projet — mémoire d'un projet

Type générique livré par SOCLE (0.7.0). Un projet a un cycle complet : mémoire bornée, discussions et décisions, état, événements et liens vers d'autres subjects. Un dépôt peut surcharger ce type dans son propre `types/projet/`.
