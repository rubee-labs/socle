---
date: 2026-04-29
type: event
producer: human
event_type: outbound_clarification_request
source: email_sent
in_reply_to_email_id: "2148"
in_reply_to_message_id: "<tencent_0330910663FFF80830D6339B@qq.com>"
to: fancy@weifangbyron.com
cc:
  - sue@weifangbyron.com
  - zhouyuxue@weifangbyron.com
sent_by: benjamin
sent_via: client_mail_local  # draft créé par /control-tower puis envoyé manuellement par Benjamin
captured_by: /control-tower --achats (documentation post-envoi manuelle)
---

# Réponse envoyée à Fancy — clarification prix + payment terms

## Contexte

Suite à la PI 2148 du 28/04 (Fancy/Weifang) qui introduisait silencieusement deux changements substantiels par rapport à la PI initiale BR20260303M validée le 26/03 :
1. Hausse tarifaire +1.00 USD/pc sur 5 SKU/6 (+1 290 USD au total, +7.6%)
2. Changement conditions paiement (avant chargement vs 15j avant ETA + telex release)

Benjamin a envoyé une réponse pour demander clarification, en se basant sur l'analyse comparative PI v.1 ↔ PI v.2148 + scan du Vault Toma (62 emails du thread "New purchase plan in 2026").

## Synthèse de la réponse envoyée

- **Demande 1** : confirmer que les unit prices de la PI initiale (16 943 USD total) s'appliquent.
- **Demande 2** : confirmer que les payment terms originaux s'appliquent (80% balance, 15j avant ETA, telex release).
- **Si Fancy veut maintenir un changement** : justifier précisément (quel cost element, montant, pourquoi maintenant).
- **Argument réfutant la justification "New Carton Printing"** : la clause 8 (printed paper wrap) est identique dans les 2 PIs, le coût des labels (0.30 USD/roll) et la hausse matières "war" étaient déjà intégrés dans la PI v.1.
- **Signal upside** : Rubee planifie d'augmenter les quantités sur cette commande (sans détail à ce stade) — sera communiqué après résolution des 2 points.
- **Ton** : ferme, factuel, professionnel. Optimisé pour traduction IA (phrases courtes, vocabulaire commercial standard, pas d'idiomes).

## Pièces de référence

- PI initiale du 26/03 : `events/2026-04-29-attachments/PI-BR20260303M-INITIALE-2026-03-26.pdf` (extraite du Vault Toma)
- PI 2148 du 28/04 : `events/2026-04-29-attachments/PI-BR20260303M-New-Carton-Printing-2148.pdf`
- CI&PL initial : `events/2026-04-29-attachments/CI-PL-BR20260303M-INITIALE-2026-03-26.pdf`

## Statut

- Mail envoyé le 2026-04-29 par Benjamin (depuis son client mail local)
- Email entrant 2148 marqué comme lu (traité)
- Discussion `discussions/2026-04-29-payment-terms-change-pending.md` mise à jour avec statut "réponse envoyée, attente Fancy"
- **Prochaine étape** : attente réponse Fancy. Si pas de réponse sous 3-5 jours ouvrés, relance proactive via `/control-tower --achats`.

## Liens

- Subject parent : `supplier:weifang`
- MCP achats : order_id=398, expedition_id=303, proforma_id=bf39730e-936b-4abd-a4ba-627b11bf1d87
