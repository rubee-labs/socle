---
name: order-398
type: supplier-order
forging_state: tentative
conviction: 50
horizon: bounded
created_at: 2026-04-29
archived_at: null

linked_subjects:
  - supplier:weifang

linked_records:
  - {type: order_id, value: 398, source: mcp_achats}
  - {type: expedition_id, value: 303, source: mcp_achats}
  - {type: order_label, value: "ROULEAUX - 1*20 - WEIFANG - 260325", source: mcp_achats}
  - {type: order_status, value: "must_validate_cotation", source: mcp_achats}
  - {type: order_amount, value: "16943.00 USD", source: mcp_achats}

active_decisions:
  - "2026-04-27-cible-17W-paillage-validee"  # cf. memory CE / dernier commit restock

open_discussions:
  - "2026-04-29-payment-terms-change-pending"

last_event:
  date: 2026-05-04
  type: outbound_acceptance_and_artwork_delivery
  ref: events/2026-05-04-reply-v5-sent-fancy-deposit-1000-artwork-zip.md

stress_tests_passed: 0
compiled_artifacts: []
---

## Quick

État : tentative, conviction 50
Statut : **Round 5 clôturé 2026-05-04 21:34 CST → 22:00 CEST** — Fancy a révisé la PI (lead time 25j corrigé ✓), contre-proposé +$1,000 deposit (vs $2,202 initial), reconnu son erreur. Benjamin a accepté le compromis "goodwill complement" $1,000 (deposit effectif $4,388.60 = 23.55%, PI papier reste 20/80) et envoyé le zip artwork (8 PDFs, 5 pour cette commande : 9176/9178/9262/10158/10297). **Production peut démarrer dès confirmation Fancy de réception artwork** → chrono 25j, prête ~30/05, arrivée Le Havre fin juin/début juillet. 11 events / 6 jours.
Prochaines étapes :
  - virement $1,000 à Weifang Byron (BPN → Citibank → Qingdao Rural Commercial Bank, SWIFT QDRCCNBQ, A/C 2330465006222811140036)
  - attendre confirmation Fancy de réception artwork zip (relance J+1 si silence — sans confirmation, le chrono 25j ne démarre pas)
  - attendre confirmation finale transport Le Havre
  - validation cotation transit (must_validate_cotation côté MCP achats)
  - mettre à jour MCP achats Rubee Spécific avec nouvelle PI (total $18,636.35, qty 1495)
Risques identifiés :
  - **Pattern Fancy "modifs unilatérales" tempéré** sur round 5 (Fancy reconnaît son erreur lead time + halve sa demande deposit) — relation rétablie mais pattern à garder en mémoire pour futures commandes
  - Si Fancy ne confirme pas la réception artwork → chrono 25j ne démarre pas → ETA glissement
  - Goodwill $1,000 = précédent à isoler aux yeux de Fancy ("for this order only", PI papier 20/80 inchangée)
Liens forts :
  - supplier:weifang (PI BR20260303M révisée $18,636.35, lead time 25j confirmé, deposit effectif 23.55%, artwork envoyé)

## Détails

### Contexte de la commande

Commande ROULEAUX paillage chez Weifang (1*20', 17k$ USD). Cible 17W de paillage validée 2026-04-27 (cf. memory CE / commit `853a45a1 docs(restock)`). Cotation Sparx reçue (expédition #303), statut MCP achats : `must_validate_cotation`.

Round 3 de négociation conclu le 2026-05-04 avec Fancy (Weifang) sur 7 events compactés en 6 jours (2026-04-29 → 2026-05-04) :

1. **Stickers master carton** (2026-04-29) : Fancy demande des stickers comme pour Brumeaux → forwarded.
2. **Réponse v1 pricing** (2026-04-29) : Benjamin demande clarification +1 USD/pc et payment terms suite à PI v.2148 qui changeait silencieusement les conditions.
3. **Distance ligne rouge labels** (2026-04-29) : problème côté imprimeur sur la distance < 1mm → résolution simple (espacer).
4. **Justification pricing Fancy** (2026-05-03) : +1 USD = complexité die-cut nouveau design carton ; concession sur payment terms (10j post-loading).
5. **Contre-proposition v2** (2026-05-03) : Benjamin propose simple wrap design (ancien format + nouveau logo only) → maintien prix PI v.1 + restructuration qty (CBM 30.59).
6. **Confirmation v3 outbound** (2026-05-04) : Benjamin confirme simple wrap, accepte payment 10j post-loading pour cette commande, envoie liste qty détaillée (xlsx, 1495 pcs / CBM 30.22 / fill 91.6%), demande nouveau ETD.
7. **Acknowledgment Fancy + lead time 25j** (2026-05-04 09:26 CEST) : Fancy accepte tous les termes, s'engage à générer la nouvelle PI, révèle pour la première fois un lead time production explicite : ≈ 25 jours post-confirmation détails. Pas de date pour la PI. Benjamin envoie réponse courte d'attente ("waiting for new PI and transport quotation for final validation").

8. **Round 4 inbound — PI BR20260303M new + 3 anomalies** (2026-05-04 12:11 CEST) : Fancy émet la nouvelle PI ($18,636.35 / 1495 pcs / CBM 30.25 ✓ chiffres conformes round 3). MAIS 3 anomalies introduites :
   - **Deposit** : PI dit $3,388.60 (déjà payé) mais boss Weifang demande +$2,202 verbalement → passage 20% → 30% unilatéral, non négocié.
   - **Production time** : 40 jours dans la PI vs 25 jours promis dans le mail 2238 (allongement +60% sans explication).
   - **Transport Le Havre** : ~$1,800 estimé, à confirmer avant booking.

9. **Round 4 outbound — pushback Benjamin** (2026-05-04 ~12:30 CEST) : refus du 30% deposit ("not part of our agreement"), top-up volontaire 20% prorata accepté ($338.67), demande clarif Fancy sur lead time 25 vs 40j, accusé transport. Position ferme + constructive — geste de bonne foi sur le top-up désamorce, mais ligne anti-précédent claire ("we will not move to 30%").

10. **Round 5 inbound — Fancy révise PI + contre-propose** (2026-05-04 15:34 CEST) : Fancy refuse le $338.67 ("too low, $30 handling fee"), contre-propose **+$1,000** (au lieu de $2,202). Reconnaît son erreur sur le lead time : envoie **PI révisée corrigée à 25 jours** ✓. Sur transport : "we will check before booking". Demande l'artwork carton + labels pour démarrer la production.

11. **Round 5 outbound — accept goodwill + delivery artwork** (2026-05-04 ~16:00 CEST) : Benjamin accepte le +$1,000 comme "goodwill complement" (PI papier reste 20/80 officiel — le complément est hors contrat). Envoi du zip `Rouleaux_packaging.zip` (~6.5 MB, 8 PDFs) avec liste explicite des **5 SKUs** pour cette commande (9176/9178/9262/10158/10297) et **3 SKUs** à ignorer (9177/10159/10243, futurs). Mention "Production time can start counting from this confirmation" → chrono 25j démarre à la confirmation Fancy.

### Paramètres confirmés (post-négo v3)

- **Fournisseur** : Weifang (supplier:weifang), contact fancy@weifangbyron.com
- **Produit principal** : rouleaux paillage, simple wrap design (logo Brumeaux nouveau, format carton ancien)
- **Quantité** : 1495 pcs (cible 17W stock — PI v.3 attendue)
- **Volume** : CBM 30.22, fill conteneur 20' = 91.6% (≥90% ✓ doctrine Rubee)
- **Prix FOB** : 17k$ USD (PI v.1 préservé, pas de +1 USD/pc)
- **Transport** : 1*20' (conteneur 20 pieds)
- **Acompte** : 30/70 standard (à confirmer dans nouvelle PI)
- **Payment terms** : compromis "balance 10j post-loading" pour cette commande (vs PI v.1 = 15j avant ETA + telex release)
- **ETD** : ~30/05 production prête (chrono 25j démarre à confirmation Fancy de l'artwork) → arrivée Le Havre fin juin / début juillet (transport maritime ~30j)
- **Lead time production Weifang** : **25 jours** confirmés via PI révisée 2026-05-04 (mail 2249, point 2). Démarre à "all details confirmed" = réception artwork carton.
- **PI finale** : BR20260303M révisée (mail 2249). Total $18,636.35. Deposit officiel PI = $3,388.60 (20%, déjà payé). **Goodwill complement $1,000 accepté** par Benjamin (en plus du deposit officiel) → deposit effectif $4,388.60 (23.55%). PI papier reste 20/80 — le complément est hors contrat.
- **Discussion** : `2026-04-29-payment-terms-change-pending` (status: round-5-clos — capture chronologie complète des 11 events, à clôturer définitivement après confirmation Fancy de réception artwork)

### Stress tests à prévoir

- [ ] Cash flow compatible avec l'échéancier
- [ ] Container 20' rempli ≥90% (cf. doctrine Rubee)
- [ ] Cible 17W validée et pas de surstock attendu

### Notes libres

- Subject créé rétroactivement (2026-04-29)
- Décision restock du 2026-04-27 référencée dans le commit `853a45a1 docs(restock): cde 398 (paillage WEIFANG) — ajustement cible 17W validé`
- À retrouver le fichier décision dans `entreprise/tools/restock/decisions/` éventuellement, et le linker dans `active_decisions`
