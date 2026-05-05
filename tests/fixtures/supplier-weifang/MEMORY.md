---
name: supplier-weifang
type: supplier
forging_state: seed
conviction: 0
horizon: unbounded
created_at: 2026-04-29
archived_at: null

linked_subjects:
  - supplier-order:order-398

linked_records:
  - {type: supplier_name, value: "WEIFANG BYRON IMPORT AND EXPORT TRADING Co., Ltd", source: mcp_achats}
  - {type: contact_email, value: "fancy@weifangbyron.com", source: mail}
  - {type: contact_email_alt, value: "sue@weifangbyron.com", source: mail}

active_decisions: []
open_discussions: []

last_event:
  date: 2026-05-04
  type: cascaded_from_order-398
  ref: "events/2026-05-04-reply-v5-sent-fancy-deposit-1000-artwork-zip.md du subject services/achats/subjects/order-398/ (round 5 — accept goodwill $1000 + delivery artwork)"

stress_tests_passed: 0
compiled_artifacts: []
---

## Quick

État : seed, conviction 0
Statut : fournisseur ROULEAUX (gamme paillage), 1 commande active (order-398, $18,636.35 PI BR20260303M révisée). **Round 5 clôturé 2026-05-04** : PI révisée avec lead time 25j ✓ corrigé, deposit "goodwill complement" +$1,000 accepté (deposit effectif 23.55%, PI papier reste 20/80), artwork zip envoyé (5 SKUs cette commande + 3 futurs). Pattern Fancy "modifs unilatérales" tempéré sur round 5 (admission erreur + halve demande deposit). Production démarre dès confirmation réception artwork → ETA Le Havre fin juin / début juillet.
Prochaines étapes :
  - virement $1,000 BPN → Citibank → Qingdao Rural Commercial Bank (SWIFT QDRCCNBQ, A/C 2330465006222811140036) cette semaine
  - attendre confirmation Fancy de réception artwork (relance J+1 si silence)
  - attendre confirmation finale transport Le Havre
  - documenter conditions courantes restantes (MOQ, paiement standard pour futures cdes)
  - clarifier statut "must_validate_cotation" sur order-398
Risques identifiés :
  - **Pattern Fancy "modifs unilatérales"** : 2 occurrences en 6 jours (mail 2148 silencieux, PI 2243 deposit 30%) — atténué sur round 5 (Fancy admet l'erreur lead time, halve sa demande). À garder en mémoire pour futures commandes.
  - Goodwill $1,000 = précédent à isoler ("for this order only") — vérifier sur la prochaine commande que Fancy reproposera 20/80 standard
  - Si Fancy traîne sur la confirmation artwork → chrono 25j ne démarre pas → ETA glissement
Stats agrégées (depuis cascade) :
  - total_orders : 1 (active : 1)
  - total_amount_usd : 18636.35 (PI BR20260303M révisée)
  - last_order_date : 2026-04-29
  - lead_time_production : **25 jours** (confirmé PI révisée 2026-05-04, démarre à "all details confirmed" = artwork validé)
  - incoterm : FOB Qingdao (confirmé)
  - deposit_ratio_official : 20% (PI papier) | deposit_effectif : 23.55% sur cette commande (goodwill +$1,000 hors contrat)
  - bank_details : Citibank N.A. New York → Qingdao Rural Commercial Bank, SWIFT QDRCCNBQ, A/C 2330465006222811140036
Liens forts :
  - supplier-order:order-398 (ROULEAUX, round 5 clôturé, attente confirmation artwork pour démarrage production 25j)

## Détails

### Identité

- Nom commercial : WEIFANG BYRON IMPORT AND EXPORT TRADING Co., Ltd
- Localisation : Weifang, Shandong, Chine
- Email principal : fancy@weifangbyron.com (49 emails reçus)
- Contact secondaire : sue@weifangbyron.com (13 emails reçus)
- Devise de facturation : USD
- Domaine email : weifangbyron.com

### Conditions courantes

- Incoterm : FOB (à confirmer)
- MOQ : à documenter
- Lead time annoncé : à documenter
- Paiement : à documenter

### Product-lines couvertes

- ROULEAUX / paillage (cf. label order-398)

### Historique de la relation

Volume relativement modéré (49+13 mails). 1 commande active (order-398).

Notes initiales :
- Order-398 (paillage WEIFANG) référencée dans memory CE (commit récent : "cde 398 paillage WEIFANG ajustement cible 17W validé") → décision restock validée
- "New purchase plan in 2026" → conversation cadrage annuel

### Notes libres

- Subject créé rétroactivement (2026-04-29)
- 2 contacts email actifs (fancy + sue) → à clarifier qui est le primary
