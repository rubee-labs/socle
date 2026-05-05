---
date: 2026-05-03
type: event
producer: human
event_type: outbound_clarification_request
source: email_sent
in_reply_to_email_id: "2191"
in_reply_to_message_id: "<tencent_633878A654B863B835FBA21D@qq.com>"
to: fancy@weifangbyron.com
cc:
  - sue@weifangbyron.com
  - zhouyuxue@weifangbyron.com
sent_by: benjamin
sent_via: client_mail_local
captured_by: /control-tower --achats (round 2 — documentation post-envoi)
attachments_sent:
  - 9176_packaging_light.pdf  # exemple de simple wrap design (joint manuellement par Benjamin)
---

# Réponse v2 envoyée à Fancy — proposition simple wrap design + restructure quantité

## Contexte

Fancy a justifié le +1 USD/pc par la complexité du nouveau design carton (die-cut autour du logo Brumeaux). Benjamin propose une contre-proposition : revenir au format simple (wrap rectangulaire) en gardant juste le nouveau logo Brumeaux. Cela doit annuler le surcoût de complexité.

Cette réponse intègre aussi les ajustements de quantité décidés en /restock le 2026-04-29 (cf. `services/achats/skills/restock/decisions/2026-04-29-cde-398-ajustement-17w.yaml`) — sans donner le détail SKU mais en mentionnant le nouveau CBM.

## Mail envoyé (3 sections)

### 1. Prices — proposal: simple wrap design

- Acceptation factuelle de l'explication Fancy (+1 USD = die-cut complexity)
- Contre-proposition : ancien format simple + nouveau logo Brumeaux only
- Description précise : no die-cut, rectangular printed wrap, same printing technique
- PJ : exemple SKU 9176 (`9176_packaging_light.pdf` — joint manuellement par Benjamin)
- Demande explicite : Fancy doit confirmer avec son carton supplier si le +1 USD/pc devient caduc avec ce design simple

### 2. Payment terms

- Reconnaissance de la concession Fancy (10 jours après loading vs avant loading)
- Refus pour cette commande spécifique (PI BR20260303M, acompte payé sur conditions v.1)
- Ouverture pour les FUTURES commandes (signal de bonne foi, on n'est pas fermé)

### 3. Quantity update

- Restructuration annoncée (some up, some down, +1 nouveau SKU)
- CBM : 26.16 → ~30.59 m³ (better fill rate du 20')
- Pas de détail SKU à ce stade
- Conditionnel : full quantity list sera envoyée APRÈS alignement prix + payment terms
- Mention nouvelle cotation transport à demander

## Choix rédactionnels

- Ton ferme mais factuel, optimisé traduction IA chinoise
- Phrases courtes, vocabulaire commercial standard, pas d'idiomes
- Numérotation 1/2/3 pour 3 sections équivalentes
- Pas de chiffrage USD précis sur la restructure (préserve la flexibilité de négo)
- Le levier CBM (+17%) est présenté comme bénéfice mutuel (meilleur cost-per-unit transport)

## Threading IMAP

Cette réponse a été créée AVEC `reply_to_id=2191` après le déploiement du fix `mcp__ce-gateway__mail__create_draft` (cf. `ce-mcp-gateway` commit `3ea55e9`, build `a7ab9c01`). Threading préservé via headers `In-Reply-To` et `References`.

## Statut

- Mail envoyé le 2026-05-03 par Benjamin (depuis son client mail local)
- Email entrant 2191 marqué comme lu (traité)
- Discussion `discussions/2026-04-29-payment-terms-change-pending.md` mise à jour avec statut "réponse v2 envoyée, attente Fancy round 3"
- **Prochaine étape** : attente réponse Fancy sur le format light + payment terms. Si pas de réponse sous 3-5 jours ouvrés, relance proactive via `/control-tower --achats`.

## Liens

- Subject parent : `supplier:weifang`
- MCP achats : order_id=398, expedition_id=303, proforma_id=bf39730e-936b-4abd-a4ba-627b11bf1d87
- Décision /restock parente : `services/achats/skills/restock/decisions/2026-04-29-cde-398-ajustement-17w.yaml`
