---
date: 2026-05-04
type: event
producer: human
event_type: supplier_pi_with_anomalies
source: email
email_id: "2243"
message_id: "<tencent_7C9EB4E65FFDC8967511C008@qq.com>"
in_reply_to_email_id: "outbound-reply-v3-fancy"
from: fancy@weifangbyron.com
subject_email: "Re: Rubee Procurement — interim contact email + status update request"
captured_by: /control-tower --achats Fancy (round 4)
attachments_received:
  - PI BR20260303M new.pdf (108 KB — nouvelle PI émise par Fancy)
---

# Round 4 — Fancy émet la nouvelle PI mais introduit 3 anomalies (deposit 30%, lead time 40j, transport $1800)

## Contexte

Round 4 de la négo (suite au round-3 outbound de Benjamin envoyé 2026-05-04 12:09 CEST).

Fancy avait promis dans le mail 2238 (acknowledgment round 3) :
- Vérifier le xlsx et émettre nouvelle PI
- Production time ~25 jours post-confirmation

Réponse arrivée le 2026-05-04 18:11 +0800 (≈ 12:11 CEST) avec la nouvelle PI **et 3 anomalies**.

## Contenu PI BR20260303M new (vérifiée)

Quantités et prix unitaires : ✓ tous conformes au round 3

| SKU | Qty | Prix unit. | Total |
|---|---:|---:|---:|
| 9262 | 500 | $13.26 | $6,630.00 |
| 9178 | 100 | $10.50 | $1,050.00 |
| 10297 | 220 | $15.68 | $3,449.60 |
| 9176 | 75 | $5.69 | $426.75 |
| 10158 | 600 | $11.80 | $7,080.00 |
| **TOTAL** | **1,495** | | **$18,636.35** |

CBM total : 30.25 m³ ✓ (vs 30.22 prévu, marge négligeable)
Weight : 12,690.75 kg
Ship Terms : FOB **Qingdao** (port confirmé)
9179 : ✓ retiré (cf. round 3)

## ⚠️ 3 anomalies détectées

### 1. Deposit — passage 20% → 30% non négocié
- PI officielle écrit : "TT deposit USD $3,388.60 + balance USD $15,247.75"
- Mail Fancy en parallèle dit : "our boss said that we need USD $2202 more to start the production again"
- Calcul : 30% de $18,636.35 = $5,591.91 - $3,388.60 (déjà payé 31/03) = $2,203.31 ≈ **$2,202** ✓
- → Boss Weifang demande **passage 20/80 → 30/70 unilatéralement**, sans avoir négocié ce point
- Notre négo round 3 : payment terms balance (10j post-loading) acceptés POUR cette commande, **deposit ratio jamais évoqué**

### 2. Production time — 25j (mail 2238) → 40j (PI 2243)
- Mail 2238 (acknowledgment round 3) : "production time around 25 days after all the details confirmed"
- PI BR20260303M new : "Production time: After receiving the deposit 40 days"
- → Allongement de **+15 jours** (60% en plus) sans explication
- Pattern récurrent côté Weifang : annonces verbales optimistes vs PI officielle plus longue

### 3. Transport jusqu'à Le Havre — estimation
- Fancy annonce : ~USD $1,800 (à confirmer avant finalisation)
- Pas de demande d'action immédiate, juste à confirmer avant booking

## Réponse outbound Benjamin (cf. event suivant)

Mail outbound 2026-05-04 (envoyé après création draft via /control-tower) avec **3 réponses fermes** :

1. **Deposit** : refus du 30%. Acceptation top-up à 20% prorata du nouveau total = $338.67 (= $3,727.27 - $3,388.60). Geste de bonne foi, pas de basculement structurel.
2. **Production time** : demande clarification 25j vs 40j (laquelle est valide ?).
3. **Transport** : noté $1,800, à confirmer avant booking.

## Logique du pushback (insight stratégique)

C'est le **2ème écart unilatéral** de Fancy :
- 1er : mail 2148 (28/04) qui introduisait silencieusement +1 USD/pc et nouvelle politique payment terms
- 2ème : PI 2243 qui demande 30% au lieu de 20%

Si Rubee accepte le 2ème sans discussion, Fancy validera qu'elle peut modifier unilatéralement les termes après acceptation → précédent dangereux pour les futures commandes. D'où la position ferme sur le deposit.

Le top-up volontaire de $338.67 = signe de bonne foi (on monte au prorata 20% de la nouvelle commande, on ne se cache pas derrière "ancienne PI"). Désamorce l'argument côté boss Weifang.

## Statut

- Mail outbound envoyé le 2026-05-04 par Benjamin (depuis client mail local)
- **Prochaines réponses attendues** :
  - Fancy clarifie deposit 20% vs 30%
  - Fancy clarifie production time 25j vs 40j
  - Fancy confirme transport Le Havre $1,800 final
- Si silence > 2 jours ouvrés : relance proactive (négo redevient bloquante avec 3 sujets ouverts)

## Liens

- Subject parent : `order-398`
- Cascade : `supplier-weifang`
- Discussion connexe : `discussions/2026-04-29-payment-terms-change-pending.md` (à mettre à jour avec round 4)
- PI sauvegardée localement : `/tmp/PI-BR20260303M-new-2243.pdf` (108 KB)
- Réponse outbound : `events/2026-05-04-reply-v4-sent-fancy-pushback-deposit-leadtime.md`
