---
date: 2026-05-04
type: event
producer: human
event_type: supplier_acknowledgment
source: email
email_id: "2238"
message_id: "<tencent_637C558B1C417A4613E9E2ED@qq.com>"
in_reply_to_email_id: "outbound-reply-v3-fancy"
from: fancy@weifangbyron.com
subject_email: "Re: Rubee Procurement — interim contact email + status update request"
captured_by: /control-tower --achats Fancy
outbound_reply_sent: true
outbound_reply_body: "Thanks. We are waiting for the new PI and the new transport quotation for final validation."
---

# Fancy accuse réception du round-3 — nouvelle PI en cours, lead time production 25j

## Contexte

Réponse de Fancy au round-3 outbound de Benjamin (2026-05-04 12:09 CEST). Fermeture côté Fancy : pas de contre-proposition, pas de question ouverte.

## Contenu mail entrant (résumé)

1. Remercie pour l'acceptation des nouvelles payment terms (10j post-loading).
2. Va vérifier le fichier `order-398-quantity-update-2026-05-04.xlsx` et générer la nouvelle PI.
3. **Lead time production explicité** : « around 25 days after all the details confirmed ».
4. Pas de date pour la PI, pas de nouvel ETD.

## Données saillantes

- **Lead time production Weifang Byron : ~25 jours post-confirmation** (donnée nouvelle, première mention chiffrée — à propager vers supplier-weifang via /documente cascade).
- Nouvelle PI promise mais pas datée → relance proactive si pas de PI sous 5j ouvrés.
- Démarrage production conditionné à la validation de la nouvelle PI (carton design + qty déjà confirmés côté Rubee dans le round-3).

## Réponse outbound courte

Benjamin a envoyé immédiatement un mail bref (depuis son client local, threadé sur 2238) :
> Hi Fancy,
> Thanks. We are waiting for the new PI and the new transport quotation for final validation.
> Best regards, Benjamin

But : signaler à Fancy qu'on bouge la balle vers elle, pas de relance technique, pas d'engagement supplémentaire.

## Statut

- Inbound 2238 lu côté serveur (\Seen posé hors skill).
- Outbound envoyé par Benjamin 2026-05-04 (vers ~17h CEST, immédiat post-création draft).
- **Prochaine étape attendue** : nouvelle PI Fancy. Si J+5 ouvrés sans réponse → relance via /control-tower.

## Liens

- Subject parent : `supplier:weifang` (lead time à propager)
- Event amont : `2026-05-04-reply-v3-sent-fancy-quantity-list.md`
- MCP achats : order_id=398, proforma_id=bf39730e (toujours v.1, sera remplacée)
