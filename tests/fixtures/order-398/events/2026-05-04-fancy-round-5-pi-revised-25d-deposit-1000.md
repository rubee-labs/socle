---
date: 2026-05-04
type: event
producer: human
event_type: supplier_revised_pi_and_counterproposal
source: email
email_id: "2249"
message_id: "<tencent_3A400BE6793EFE3646660922@qq.com>"
in_reply_to_email_id: "outbound-reply-v4-fancy"
from: fancy@weifangbyron.com
subject_email: "Re: Rubee Procurement — interim contact email + status update request"
captured_by: /control-tower --achats Fancy (round 5)
attachments_received:
  - PI BR20260303M new.pdf (118 KB — PI révisée avec correction lead time 25j)
---

# Round 5 — Fancy révise la PI (lead time 25j corrigé) + contre-propose +$1,000 deposit

## Contexte

Round 5 de la négo (suite au round-4 outbound de Benjamin envoyé 2026-05-04 ~12:30 CEST avec pushback deposit + clarif lead time).

Réponse Fancy arrivée 2026-05-04 21:34 +0800 (≈ 15:34 CEST) — réponse rapide ~3h après.

## Contenu mail entrant

### 1. Deposit — contre-proposition

Fancy refuse le top-up $338.67 :
> "USD $338.67 is too low since we will be charged $30 as handling fee. Could you kindly accept USD $1000 more as deposit this time?"

**Argument frais bancaires** : SWIFT international = $30 frais fixes → $338.67 net → $308 reçu côté Fancy = effort symbolique.

**Compromis sur la table** : +$1,000 (vs +$2,202 demandé initialement).
- Calcul : $3,388.60 + $1,000 = $4,388.60 = 23.55% du total ($18,636.35)
- Mid-point entre 20% (Rubee) et 30% (Fancy initial)

### 2. Production time — erreur reconnue

> "I am sorry that I made a mistake in the previous PI. Attachment is the PI I have revised for you"

**PI révisée vérifiée** :
- Lead time : "Production time: After all details confirmed **25 days**" ✓ corrigé
- Reste de la PI strictement identique (total $18,636.35, deposit $3,388.60 + balance $15,247.75, FOB Qingdao, qty 1495 pcs, CBM 30.25)
- **Important** : la PI papier reste à **20/80** (pas modifiée) — le +$1,000 est un complément informel hors contrat

### 3. Transport Le Havre — engagement de re-vérification

> "We will check the shipping cost again before booking and we will let you know once we get the amount."

Standard, pas de chiffres définitifs.

### 4. Question retournée — artwork carton + labels

> "could you kindly tell me when you could give me the printing design of the cartons And make a confirmation for the labels?"

**Bottleneck production identifié** : le compteur 25j ne démarre qu'à partir de "all details confirmed" = artwork carton validé. Tant que Rubee n'envoie pas l'artwork, la production reste bloquée.

## Décision Benjamin (round 5 outbound)

- **Deposit** : ACCEPTER le +$1,000 comme "goodwill complement to the deposit". PI papier reste 20/80 (cf. event suivant).
- **Lead time** : confirmé 25j ✓
- **Transport** : noté, attente confirmation finale
- **Artwork** : envoi du zip `Rouleaux_packaging.zip` avec 8 PDFs, dont 5 pour cette commande (9176, 9178, 9262, 10158, 10297). Les 3 autres (9177, 10159, 10243) sont pour usage futur, à ignorer pour ce PI.

## Données saillantes

- **Argument frais bancaires recevable** : SWIFT $30 fixes = 8.9% de friction sur $338.67. $1,000 = 3% de friction = bien plus défendable côté supplier.
- **Pattern Fancy "modifs unilatérales" tempéré** : sur le round 5, elle reconnaît son erreur (lead time 40 vs 25j) et halve sa demande deposit. Bon signal de coopération.
- **Bottleneck artwork côté Rubee** : le 25j commence à partir de la confirmation de l'artwork — donc dès que Fancy confirme réception du zip, le chrono démarre. Si confirmation aujourd'hui (4/5) → production prête ~30/05 → arrivée Le Havre fin juin/début juillet (transport maritime ~30j).
- **PI papier inchangée à 20/80** : le complément $1,000 = goodwill payment hors contrat. Pas de précédent pour modifier le ratio sur les futures commandes.

## Liens

- Subject parent : `order-398`
- Cascade : `supplier-weifang`
- PI sauvegardée localement : `/tmp/PI-BR20260303M-revised-2249.pdf` (118 KB)
- Réponse outbound : `events/2026-05-04-reply-v5-sent-fancy-deposit-1000-artwork-zip.md`
- Event amont : `events/2026-05-04-reply-v4-sent-fancy-pushback-deposit-leadtime.md`
