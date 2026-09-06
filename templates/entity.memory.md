---
entite: nom-entite
type: skill | skill-cas | tool | projet | service
derniere_maj: YYYY-MM-DD
maj_par: <user>  # ou "auto" quand coordinateur
# memory_max_kb: 8   # plafond du fichier (défaut 8 Ko) — surcharger seulement si la doctrine est dense
---

# État — nom-entite

## Quick
(< 100 mots : état, dernier run/événement avec pointeur `rapports/YYYY-MM-DD-<slug>.md`, prochaines étapes, risques)

## Doctrine en vigueur
- (règles et principes actifs issus des décisions — pas l'historique, l'état courant)

## Décisions actives
(≤ 10, les plus récentes en premier ; les anciennes restent dans `decisions/`)

1. **Titre décision** (date) — `decisions/YYYY-MM-DD-<slug>.yaml`
2. ...

## En attente
- (actions qui nécessitent validation ou input)

## Décisions annulées
- (règles explicitement inversées — une ligne par annulation, avec raison et date)
- ~~exemple ancienne règle~~ → remplacée par X (décision YYYY-MM-DD, raison: ...)

## Règles apprises
- (contraintes découvertes en session, pas dans les fichiers de config — gotchas durables)

<!-- Jamais de section « État » ni de journal daté ici : un run écrit rapports/YYYY-MM-DD-<slug>.md. -->
