# Checklist post-bloc

Un **bloc** se termine quand quelque chose a abouti : une décision prise, un document produit, un skill
ou un outil créé ou corrigé, une analyse conclue. Pas après chaque question.

## Les cinq items, dans l'ordre, sans demander

1. **discussion** : `discussions/YYYY-MM-DD-<sujet>.md` de l'entité si l'échange a été une vraie
   analyse ou un débat ; sinon ⏭️ avec la raison.
2. **décision** : `decisions/YYYY-MM-DD-<sujet>.yaml` si une règle, un paramètre ou un choix durable
   a été arrêté ; sinon ⏭️ avec la raison.
3. **memory** : `/documente <chemin de l'entité>` — re-synthèse **bornée** du `MEMORY.md` (Quick < 100 mots,
   doctrine, ≤ 10 décisions actives avec pointeurs, règles apprises, plafond 8 Ko). Jamais d'ajout à la
   main, jamais de journal de runs dans un MEMORY.md. **Obligatoire.**
4. **commit** : ajout ciblé des fichiers du bloc, message qui dit ce qui a changé. **Obligatoire.**
5. **push** : envoi sur le dépôt partagé, par la commande de synchronisation du dépôt quand il en a une.
   **Obligatoire.**

Si le bloc touche un **subject** (`subjects/<slug>/`), `/documente` écrit lui-même discussion, décision et
MEMORY.md : les items 1 à 3 se font en une commande.

## Affichage en fin de réponse

Preuve d'application, pas décoration :

```
✅ discussion   (ou ⏭️ raison en 1 ligne)
✅ décision     (ou ⏭️ raison en 1 ligne)
✅ memory
✅ commit       <hash-court>
✅ push
```

Sauter un item exige une justification visible. Pas de checklist = bloc incomplet, même si le travail a marché.

## Vérification par code

Le hook Stop `hooks/check-post-bloc.py` (activé par `post_bloc: true` dans le `.forge.yaml` racine,
écrit par défaut par `/forge-init`) vérifie
les items memory, commit et push : un fichier modifié pendant la session et non committé, ou le MEMORY.md
de son entité (dossier ancêtre le plus proche qui en contient un) dont `derniere_maj` n'est pas du jour,
bloque la fin de réponse **une seule fois**, avec la raison. Réponse attendue : finir la checklist, ou
justifier ⏭️ en une ligne (par exemple un fichier qui appartient à une autre session). Un MEMORY.md au-dessus
de son plafond ajoute un avertissement : re-synthèse attendue au prochain `/documente`.

## Activation

`/forge-init` écrit `post_bloc: true` dans le `.forge.yaml` : un dépôt qui adopte SOCLE a la checklist d'office.
Le hook SessionStart du plugin charge alors cette règle à chaque démarrage, `/clear` ou compaction ; rien à
recopier dans le `CLAUDE.md`. Un dépôt sans `.forge.yaml` n'est jamais concerné. Pour couper la checklist
dans un dépôt : `post_bloc: false`.
