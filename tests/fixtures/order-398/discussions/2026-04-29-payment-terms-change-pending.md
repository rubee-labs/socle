---
date: 2026-04-29
type: discussion
producer: human_and_claude
status: negotiation_closed_partial
priority: high
trigger_event:
  source: email
  email_id: "2148"
  email_message_id: "<tencent_0330910663FFF80830D6339B@qq.com>"
  from: fancy@weifangbyron.com
captured_by: /control-tower --achats
exchanges:
  - date: 2026-04-29
    direction: outbound
    event_ref: events/2026-04-29-reply-sent-fancy-pricing.md
    summary: Demande clarification +1 USD/pc et payment terms (analyse comparative PI v.1 vs v.2148)
  - date: 2026-04-30
    direction: inbound
    event_ref: events/2026-05-03-fancy-reply-pricing-justification.md
    summary: Fancy justifie +1 USD = printing complexity nouveau design + concession payment terms (10j après loading)
  - date: 2026-05-03
    direction: outbound
    event_ref: events/2026-05-03-reply-v2-sent-fancy-light-design.md
    summary: Contre-proposition simple wrap design (ancien format + nouveau logo only) + tient contrat v.1 paiement + restructure qty (CBM 30.59)
  - date: 2026-05-03
    direction: inbound
    email_id: "2232"
    email_message_id: "<tencent_229DF8626EE1AF31737E0808@qq.com>"
    summary: Fancy accepte simple wrap = prix retour ancien niveau ✓ ; refuse conditions originales paiement, maintient "10j post-loading" ; demande liste détaillée qty ; ETD 5 mai abandonné (production bloquée)
  - date: 2026-05-04
    direction: outbound
    event_ref: events/2026-05-04-reply-v3-sent-fancy-quantity-list.md
    summary: Confirmation simple wrap + acceptation 10j post-loading + envoi liste qty (xlsx, 1495 pcs / 30.22 CBM / 0 nouveau SKU) + demande nouvelle PI + nouveau ETD réaliste
outcome:
  pricing: PI v.1 unit prices preserved (Fancy abandonne le +1 USD/pc grâce au simple wrap design)
  payment_terms: compromis "balance 10 days after loading" accepté pour cette commande (vs PI v.1 = 15j avant ETA + telex release)
  quantities: restructurées selon /restock 2026-05-04 (1490 → 1495 pcs, CBM +16%, fill 91.6%)
  etd: abandonné, à redéfinir (Fancy doit envoyer nouvelle PI puis confirmer ETD réaliste)
next_step: attente nouvelle PI Fancy + nouvelle cotation transport ; relance J+3 si silence
---

# Changement unilatéral des conditions de paiement par Weifang — order-398

## Faits

Le 2026-04-28 19:33, Fancy (Weifang) annonce un changement de leurs règles internes :

> According to the new rules of our company, the balance should be paid before loading the container, replacing the original contract term of payment before arrival.

Une **PI mise à jour** est jointe : `PI BR20260303M - New Carton Printing.pdf` (référence proforma confirmée côté MCP achats).

## Conditions actuelles côté Rubee (PI INITIALE BR20260303M du 2026-03-26)

PI initiale extraite du Vault Toma : `events/2026-04-29-attachments/PI-BR20260303M-INITIALE-2026-03-26.pdf` (envoyée par Fancy à Toma le 2026-03-26 07:46 UTC, 1 jour avant le paiement de l'acompte).

- **Acompte payé** : 3 388,60 USD (**20%** explicite dans la PI v.1) le 2026-03-31 (Virement Banque POP)
- **Reste à payer** : 13 554,40 USD (80%)
- **Conditions contractuelles** : "80% balance will be paid **after departure of the goods 15 days before ETA** at the seaport of destination. And we will **telex release** for you after we receive balance."
  - ETA estimée : 2026-06-19
  - → Paiement balance prévu : **~2026-06-04** (15 jours avant ETA)
- **ETD** : 2026-05-05 (chargement container imminent)
- **Production time** : 40 jours après acompte → fin prod ~2026-05-10

## Demande Weifang

Paiement du solde de **13 554,40 USD avant le chargement** (~2026-05-05).

## Impact cash flow (chiffres corrigés après comparaison PI v.1 / PI 2148)

- **Float perdu** : ~30 jours (entre ~05/05 et ~04/06)
- **Cash supplémentaire à mobiliser** : **+1 290 USD** au titre de la hausse tarifaire silencieuse
- **Coût opportunité** : à arbitrer selon trésorerie Rubee actuelle (`mcp__treasury__get_balances` USD)
- **Mention "telex release" supprimée** dans la PI 2148 — à investiguer (impact sur libération documents BL)

## Décision Benjamin

**SKIP — pendant — Benjamin veut lire la PI complète d'abord avant de trancher** (run /control-tower --achats du 2026-04-29).

L'email 2148 reste **non-lu** dans la boîte IMAP (pas de mark_as_read). Il sera reproposé au prochain run du skill, ou Benjamin peut le traiter directement dans son client mail.

## Options identifiées (à arbitrer)

1. **Refuser** — invoquer le contrat actuel (paiement à arrivée). Risque : retard chargement + escalade.
2. **Accepter pour cette fois** + flag pour future renégociation. Préserve la relation, concède le float cash 13.5k$.
3. **Compromis 50/50** — 50% au chargement, 50% à arrivée. Neutralise partiellement.

## À investiguer avant décision

- Trésorerie Rubee disponible sous 6 jours (cf. `mcp__treasury__get_balances` USD)
- PI BR20260303M complète (montants détaillés, Incoterms confirmés, dates butoirs)
- Historique : Weifang a-t-elle déjà imposé ce genre de changement ? Toma avait-elle pris un précédent ?
- Doctrine Rubee paiement échelonné — adaptation acceptable au cas par cas ?

## Contexte historique complet (scan Vault Toma — 2026-04-29)

**Thread parent** : "New purchase plan in 2026" — 62 emails Toma↔Fancy entre 2026-01-15 et 2026-04-28.

### Chronologie du printed paper wrap (étiquettes)

| Date | Action | Détail |
|---|---|---|
| 2026-03-03 | Lisa envoie la 1ère PI test | sans label, prod 30j |
| **2026-03-12 10:39** | **Toma annonce les nouvelles étiquettes** | "we would like to add a printed paper wrap around the roll. The wrap design includes a special die-cut shape at the top around the Brumeaux brand logo. [...] Please confirm material, printing method, die-cut mold" |
| 2026-03-13 | Fancy chiffre les labels | USD $0.1/roll (Marina/Fancy reprennent, Lisa en congé) |
| 2026-03-17 | Fancy ré-évalue + invoque "war on raw materials" | USD $0.3/roll (3 sizes) + nouvelle PI envoyée + **"Because of the war, the cost of materials have risen crazily"** |
| **2026-03-25 08:29** | **Toma valide les quantités finales** | "Please send me a PI included: **new printed paper wrap around the roll full colored** + **packaging printed** (I will send you new design)" |
| **2026-03-26 07:46** | Fancy envoie la PI INITIALE BR20260303M | Total 16 943 USD — clause 8 : "New printed paper wrap around the roll full colored and packaging printed" ✓ |
| **2026-03-26 10:05** | **Toma valide** : "the PI is ok" | |
| 2026-03-31 | Acompte 3 388,60 USD payé | Engagement contractuel ferme |
| 2026-04-09→16 | Échanges design carton (Toma envoie le visuel) | finalisé par Toma 16/04 ("design for all the references") |
| 2026-04-24 | Fancy demande pour stickers master carton | sans réponse Toma (arrêt) |
| 2026-04-28 02:52 | Fancy demande pour labels distance 1mm/3mm | sans réponse Toma (arrêt) |
| 2026-04-28 19:33 | **Fancy envoie la PI v.2148 "New Carton Printing"** | Total 18 233 USD (+1 290 USD), conditions paiement avant chargement |

### Toma savait

- ✅ **Design carton printing** : annoncé par Toma elle-même le 12/03 (printed paper wrap), validé via PI v.1 du 26/03 (clause 8), envoi du visuel finalisé le 16/04
- ✅ **Labels payants** : Fancy avait chiffré $0.3/roll le 17/03 (intégré dans tarifs PI v.1)
- ✅ **Hausse matières premières** : Fancy avait invoqué "war on raw materials" le 17/03 (intégré dans tarifs PI v.1)
- ✅ **Question labels distance 1mm/3mm** : posé par Fancy 28/04 02:52, jamais répondu (Toma en arrêt depuis)
- ✅ **Question stickers master carton** : posé par Fancy 24/04 12:07, jamais répondu

### Toma ne savait PAS

- ❌ **Aucune mention** dans les 62 emails Toma↔Fancy de "new rules", "balance before loading"
- ❌ **Aucune mention** d'une seconde hausse tarifaire entre le 26/03 (PI v.1 validée) et le 28/04 (PI v.2148)
- ❌ Le payment terms change est introduit **pour la première fois** par Fancy dans son mail à Benjamin du 28/04 19:33

### Implication décisive

**Le filename "PI BR20260303M - New Carton Printing" est trompeur** :
- La clause 8 "New printed paper wrap around the roll full colored and packaging printed" figure **déjà à l'identique** dans la PI v.1 validée 26/03
- → **Il n'y a AUCUN changement de design** entre PI v.1 et PI v.2148 sur ce point
- → "New Carton Printing" du filename ne correspond à **rien de nouveau**

**La hausse de +1 USD/pc est doublement non-justifiable** :
- ❌ "Nouveau design" → déjà inclus dans PI v.1
- ❌ "Hausse matières premières" → déjà invoquée 17/03 et intégrée dans PI v.1
- ❌ Aucun nouveau coût annoncé entre 26/03 et 28/04 dans les emails Vault

**Pattern probable** : tentative opportuniste lors du changement d'interlocuteur Toma→Benjamin, avec un filename trompeur ("New Carton Printing") destiné à masquer les changements substantiels dans la PI.

## Comparaison PI initiale (MCP achats, validée 26/03) vs PI 2148 (28/04)

PDF extrait : `events/2026-04-29-attachments/PI-BR20260303M-New-Carton-Printing-2148.pdf` (109 KB).

### Tarifs (5 SKU sur 6 augmentés de +1 USD/pc)

| SKU | Désignation | Qty | Prix initial | Prix PI 2148 | Δ |
|---|---|---|---|---|---|
| 9262 | Lot Toile + Sardine 130gsm | 500 | 13.26 | **14.26** | +1.00 (+7.5%) |
| 9178 | Rouleau 1×50m 130gsm | 100 | 10.50 | **11.50** | +1.00 (+9.5%) |
| 10297 | Rouleau 2×50m 100gsm | 140 | 15.68 | **16.68** | +1.00 (+6.4%) |
| 9176 | Rouleau 1×50m 65gsm | 20 | 5.69 | **6.69** | +1.00 (+17.6%) |
| 10158 | Rouleau 1×50m 150gsm | 530 | 11.80 | **12.80** | +1.00 (+8.5%) |
| 9179 | Pack 100pcs Sardines | 200 | 3.50 | 3.50 | inchangé ✓ |
| **Total** | | | **16 943 USD** | **18 233 USD** | **+1 290 USD (+7.6%)** |

### Acompte / Solde

- Acompte reconnu : 3 388,60 USD payé le 2026-03-31 ✓
- Solde recalculé : **14 844,40 USD** (vs 13 554,40 USD initial) → +1 290 USD
- Conditions : "balance will be paid **before loading the container**" (vs "before arrival" contractuel)

### Volumes / SKU

Identiques à la PI initiale (6 SKU, mêmes quantités). ✓

### Autres clauses

- Incoterm : FOB Qingdao ✓
- Production : 40 jours après acompte (acompte 31/03 → fin prod ~10/05, vs ETD MCP 05/05 — **léger écart 5j**)
- Tolérance : ±2cm, ±5gsm, ±5% qty
- Clause 5 : "buyer can't abandon the goods" — clause ferme habituelle
- Clause 8 : "New printed paper wrap around the roll full colored and packaging printed" → c'est le nouveau design carton (validé Toma le 16/04)

### Lecture finale

Fancy a glissé **3 changements simultanés** dans la PI "New Carton Printing" :
1. ✅ **Design carton** : attendu, validé Toma 16/04
2. ❌ **Hausse tarifaire +1 USD/pc sur 5 SKU/6** : non discutée, silencieuse, +7.6% du total
3. ❌ **Changement conditions paiement** : non discutée

**Aucune justification** dans la PI ou le mail (pas de mention matière première, MOQ, devises, etc.).

**Timing** : PI envoyée le 28/04 19:33, soit ~2h après ton mail P1 de 18:32. C'est un fait accompli emballé dans un mail "Re: status update request".

## Recommandation Claude (à arbitrer)

**Stratégie de négociation à 3 niveaux** :

1. **Accepter le design carton** (clause 8 de la nouvelle PI : "New printed paper wrap around the roll full colored and packaging printed") — c'était attendu, validé Toma 16/04 dans le thread "New purchase plan in 2026".
2. **Refuser la hausse tarifaire** : la PI initiale BR20260303M v.1 du 2026-03-26 est ferme. L'acompte 20% (3 388,60 USD) a été payé le 2026-03-31 sur la base de ces tarifs (16 943 USD). Fancy ne peut pas modifier les prix unilatéralement 1 mois plus tard sans justification.
3. **Refuser le changement de termes paiement** : la PI v.1 dit "80% balance paid after departure 15 days before ETA + telex release". Pas "à arrivée" comme Fancy le présente faussement dans son mail 2148. Donc :
   - Soit on tient le contrat v.1 (recommandé)
   - Soit on accepte un compromis (paiement à BL ready, ou ETD = 05/05) en échange d'une contrepartie tangible

**Mensonge factuel à signaler** (sans agressivité) : Fancy écrit dans son mail 2148 *"replacing the original contract term of payment before arrival"* — or la PI initiale ne dit PAS "before arrival" mais "**15 days before ETA + telex release**". Présentation trompeuse à corriger.

**Argument contractuel imparable** : la PI v.1 + acompte payé constituent un **contrat ferme**. Toute modification doit faire l'objet d'un avenant explicite, pas d'une PI réémise sous prétexte de "carton printing update".

## Brouillon réponse à Fancy (v.2 renforcée — à valider avant envoi)

```
Hi Fancy,

Thanks for the follow-up. I've taken some time to compare the new PI you
sent yesterday (April 28th) with the original PI BR20260303M that Toma
confirmed on March 26th and on which we paid the 20% deposit (USD 3,388.6)
on March 31st.

I notice two changes that were not discussed and don't appear in any of
our previous exchanges with Toma:

1) Unit prices increased by USD 1.00 per piece on 5 SKUs out of 6
   (9262, 9178, 10297, 9176, 10158), raising the total from USD 16,943
   to USD 18,233 (+USD 1,290).

2) Payment terms changed from "80% balance paid after departure, 15 days
   before ETA, with telex release" (PI of March 26th, clause 3) to
   "balance paid before loading the container".

I've reviewed our full email history with Toma since January, including
your previous note from March 17th about raw material costs ("Because of
the war, the cost of materials have risen crazily") — that increase was
already reflected in the original PI of March 26th. The label fee of
USD 0.30/roll mentioned at the same time is also already integrated in
the unit prices we agreed on.

The "New Carton Printing" wording in the filename refers to the printed
paper wrap that was discussed since March 12th and is identical in both
PIs (clause 8). So there's no new design element that would justify a
price update.

Could you please:
- Restore the original unit prices of the March 26th PI, OR explain
  precisely what cost element changed between March 26th and now that
  would justify +USD 1.00/piece?
- Confirm we keep the original payment terms (15 days before ETA, with
  telex release)?

I'm happy to align on the new printed wrap design (Toma sent the final
artwork on April 16th) and move forward with production. ETD May 5th is
fine on our side.

Best regards,
Benjamin Hamon
Managing Director — Rubee
relais-toma@rubee.fr (covering for Toma during her absence)
```

**Notes pour Benjamin** :
- Ton ferme mais respectueux, factuel sans accusation directe
- Référence explicite à la chronologie connue (mail 17/03 sur "war material costs", mail 12/03 sur le wrap design) — démontre qu'on a fait nos devoirs
- Demande explicite de justification, pas un refus en bloc — laisse une porte ouverte sans concéder
- Confirmation ETD 05/05 → on n'est pas en train de bloquer la production, on demande juste à respecter le contrat v.1

## Liens

- Subject parent : `supplier:weifang`
- MCP achats reference : order_id=398, expedition_id=303, proforma_id=bf39730e-936b-4abd-a4ba-627b11bf1d87
