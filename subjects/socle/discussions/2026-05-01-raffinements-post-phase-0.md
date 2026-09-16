---
date: 2026-05-01
sujet: Raffinements post-Phase 0 du subject pool — règle bilingue, module dédié, KPIs Tier 1
statut: aboutie
decision: 2026-05-01-raffinements-post-phase-0
---

# Discussion — Raffinements post-Phase 0

## Contexte

Suite à la livraison Phase 0 (29/04) et à son intégration dans le bloc Health-check (29/04), session de raffinements pendant l'usage initial. Benjamin commence à instancier de vrais subjects (13 créés entre les sessions : 7 supplier-orders + 6 suppliers) et plusieurs ajustements émergent naturellement.

## Cheminement

### 1. Règle bilingue (taxonomie en / contenu fr)

Benjamin remarque que le type d'exemple `supplier-order` a ses `analysis_dimensions` et `expected_events` en anglais (`cash_flow`, `lead_time`, `stock_alert`, etc.), ce qui force une traduction mentale en lecture quotidienne.

Distinction clarifiée : **squelette/taxonomie** = anglais (universel, partagé entre outils tiers, équipes), **contenu métier** = langue de l'utilisateur (français pour Rubee). Snake_case partout pour cohérence YAML.

Application :
- `analysis_dimensions: [tresorerie, delai, qualite, cout_total, risques, conformite_doctrine]`
- `expected_events: [alerte_stock, email_fournisseur_disponibilite, ...]`
- `typical_linked_types: [supplier, product-line, freight-forwarder]` (reste en anglais — taxonomie)

3 niveaux de garde-fou en place : doctrine dans `savoirs.md`, exemple corrigé dans `skills-agents.md`, règle stricte dans `/subject-create-type` SKILL.md (Gotchas + EVAL 2bis).

### 2. Module dédié subject-pool.md (option A)

Question soulevée : la doctrine du subject pool est-elle bien à sa place dans `savoirs.md` ?

Réponse : non. Le subject pool n'est pas un savoir parmi d'autres, c'est l'**infrastructure de stockage et de maturation centrale** (forge γ + compilation doctrine). Le rabaisser à une sous-section de `savoirs.md` lui fait perdre son statut.

Décision : créer `entreprise/config/rules/subject-pool.md` (~280 lignes) comme module de premier rang, lazy-chargé. Référencé dans `CLAUDE.md` au tableau des modules avec contexte de chargement explicite ("Quand on crée/utilise un subject ou un type, quand on invoque /subject-*, /forge, /stress-test, /compile-doctrine"). Le terme **"réacteur"** apparaît dans le titre du module et dans le tableau CLAUDE.md, ancrant la métaphore.

Les 2 modules d'origine (`savoirs.md`, `skills-agents.md`) gardent une référence courte vers le nouveau, pas de duplication.

### 3. KPIs Tier 1 + SUBJECT-POOL-METRICS.md

Pour observer les performances du réacteur, Benjamin demande quels KPIs mettre en place.

Analyse : un système de connaissance se mesure au **mouvement** (subjects qui mûrissent, doctrines qui se compilent), pas au stockage. Le KPI nord est le **taux de compilation** (in_service / (in_service + doctrine non compilées)) — c'est ce qui distingue le subject pool d'un PKM passif.

Décision : commencer par Tier 1 uniquement (5 KPIs essentiels), via extension de `forge_scanner.py`. Tier 2/3 plus tard si volume justifie.

Implémentation :
- Calcul Tier 1 dans `compute_metrics()` : volume actif, distribution forging_state, stagnations, compilés/30j, taux compilation
- Génération `entreprise/SUBJECT-POOL-METRICS.md` avec détail (distribution par état/type/domaine, listes des stagnants, artefacts récents)
- Ligne agrégée dans le bloc Health-check : `Forge: OK — 13 actifs, 0 stagnants, 0 compilés/30j, taux n/a`

### 4. Fix faux positifs merger candidate

Au premier vrai scan : 2 alertes "merger candidate" entre orders Simon (100% overlap). Faux positifs car toutes les commandes Simon ont par construction `[supplier-simon, product-line-guirlande-guinguette]`.

Diagnostic : la détection de doublons (merger) concerne les **doublons accidentels d'entités persistantes** (deux fichiers `supplier-simon-fr` et `supplier-simon-yiwu` qui sont en fait le même Simon), pas les instances bornées d'un type.

Fix sémantique : restreindre `merger_candidate` aux subjects `horizon: permanent`.

Validation : 13 subjects → de 2 alertes à 0. Bloc Health-check propre.

## Conclusion

Le subject pool atteint son stade de maturité cohérente : doctrine consolidée dans un module dédié, règle bilingue garantie, KPIs observables, faux positifs corrigés. Le réacteur est instrumenté et prêt à scaler avec l'usage réel.

## Décision

Voir `decisions/2026-05-01-raffinements-post-phase-0.yaml`.
