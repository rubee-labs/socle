---
name: subject-merge
description: >-
  When the user asks to merge (weld) two subjects that turn out to describe the
  same entity from different angles. Also trigger on "merge subjects",
  "souder", "fusion sujets", "consolider deux sujets". Always requires explicit
  human validation. Archives the source subjects with pointers to the new
  consolidated one.
type_anthropic: 5
visibilité: entreprise
auteur: Benjamin
date_creation: 2026-04-29
version: 1.0
tags: [subject-pool, forge, merge, weld]
effort: medium
outils_requis: []
securite_externe: false
---

# Subject Merge — Soudure de Subjects

## Objectif

Fusionner deux subjects qui décrivent la même entité avec des angles différents (ex: `supplier-simon` et `simon-pme-yiwu` qui sont en réalité le même fournisseur). Crée un nouveau subject consolidé, archive les deux sources, redirige les liens.

Voir `entreprise/config/rules/savoirs.md` § "Subject Pool" pour le modèle.

## Quand utiliser

- Quand le scanner forge a détecté un overlap fort (>70% de `linked_subjects` ou conclusions convergentes) et propose une soudure au démarrage de session
- Quand Benjamin réalise manuellement que deux subjects sont des doublons
- Quand deux subjects de domaines proches convergent (ex: après évolution stratégique)

**Quand NE PAS utiliser** :
- Sur des **instances** : on ne soude jamais 2 instances temporelles (deux commandes Simon restent 2 commandes distinctes — leurs leçons remontent vers `supplier-simon`, mais elles ne fusionnent pas entre elles)
- Sur des subjects de types incompatibles (ex: un `supplier-order` et un `marketing-campaign`)
- Si l'overlap est faible (<50% de linked_subjects communs et conclusions divergentes) — c'est probablement 2 subjects légitimement distincts

## Instructions

### Phase 1 — Identifier les 2 subjects sources

Si les chemins sont passés en argument (`/subject-merge <A> <B>`), vérifier que les 2 `MEMORY.md` existent.

Sinon, demander à Benjamin de pointer les 2 subjects.

### Phase 2 — Vérifier la compatibilité

Lire les 2 `MEMORY.md`. Vérifier :

1. **Même type ou types compatibles**. Si types différents, refuser sauf cas explicitement validé (rare). Lister les types qui peuvent éventuellement fusionner :
   - 2 instances du même type → soudure légitime si même entité
   - 2 types différents mais compatibles (`supplier` + `supplier-historical`) → soudure possible si Benjamin valide
   - Types totalement différents → refuser

2. **Overlap des linked_subjects** : calculer l'intersection. Si >70% commun → forte présomption de doublon. Si <30% → demander pourquoi merger malgré tout.

3. **Contenu suffisant** : la fusion se décide sur la substance, pas sur un état (cycle 2 états depuis 2026-09-14 : `actif` / `archived`). Refuser si l'un des deux subjects est quasi vide (0 event, 0 décision) — pas assez de matière pour justifier une soudure ; le supprimer ou le laisser vivre suffit.

### Phase 3 — Présenter le diff aux yeux de Benjamin

Afficher un tableau comparatif :

```
                    | Subject A          | Subject B          | Conflit ?
--------------------|--------------------|--------------------|----------
type                | supplier           | supplier           | non
forging_state       | actif              | archived           | oui (actif retenu si l'entité vit encore)
created_at          | 2026-01-10         | 2025-08-22         | oui (min retenu)
linked_subjects     | [...A...]          | [...B...]          | union
linked_records      | [...A...]          | [...B...]          | union
active_decisions    | [...A...]          | [...B...]          | union
stress_tests        | 2 entries          | 0 entries          | concat
events count        | 47                 | 12                 | merge
discussions count   | 3                  | 1                  | concat
decisions count     | 5                  | 0                  | concat
```

### Phase 4 — Définir les paramètres du subject consolidé

Demander à Benjamin :

1. **Nom du subject consolidé** (généralement le plus parlant des 2, ou un nouveau)
2. **Localisation** (généralement celle de A ou B selon usage principal)
3. **Stratégie de résolution des conflits** :
   - `forging_state` : `actif` si l'entité consolidée vit encore, `archived` si les deux sources étaient closes
   - `created_at` : min(A, B) (le plus ancien)
   - `archived_at`: null (le nouveau subject est actif)
4. **Quick section et Détails** : reprendre celui de A ou B, ou rédiger une nouvelle synthèse

### Phase 5 — Construire le subject consolidé

Créer le nouveau dossier `subjects/<nom-consolidé>/` avec :

- **MEMORY.md** : frontmatter unifié (selon stratégie Phase 4) + Quick rédigée + Détails rédigés
- **INDEX.md** : stub
- **events/** : copier les events de A et B (préservant noms de fichiers et dates ; en cas de conflit de slug, ajouter suffixe `-a` ou `-b`)
- **analyses/** : idem
- **discussions/** : idem (concat, pas dédupliquer — l'historique est précieux)
- **decisions/** : idem

Le frontmatter du nouveau subject doit avoir :

```yaml
merged_from:
  - {path: <A path>, archived_at: <YYYY-MM-DD>}
  - {path: <B path>, archived_at: <YYYY-MM-DD>}
```

(Pour traçabilité complète. Permet d'auditer la soudure et éventuellement de revenir en arrière si besoin.)

### Phase 6 — Archiver les 2 sources

Modifier `MEMORY.md` de A et B :

- `forging_state: archived`
- `archived_at: <YYYY-MM-DD>`
- Ajouter dans Quick : `⚠ MERGED into <nouveau-chemin>. Cf. MEMORY.md là-bas pour la suite.`
- Ajouter dans frontmatter : `merged_into: <nouveau-chemin>`

Les fichiers events/discussions/decisions des 2 sources **restent en place** (ne pas supprimer — les fichiers d'historique sont au nouveau subject mais les originaux restent comme témoins archivés).

### Phase 7 — Rediriger les liens entrants

Pour chaque subject pointant vers A ou B (recherche par grep dans `linked_subjects`), mettre à jour le lien vers le nouveau subject.

```bash
grep -r -l "linked_subjects:.*<A-name>" /Users/bhamon/Documents/1\ -\ Boulot/Dev/Git/claude-enterprise --include="MEMORY.md"
```

Pour chaque résultat, remplacer `<A-name>` par `<nouveau-nom>` dans `linked_subjects` (en utilisant Edit). Idem pour `<B-name>`.

### Phase 8 — Confirmer et synthétiser

Afficher à Benjamin :

```
✅ Soudure effectuée :
  - Nouveau subject : <chemin-absolu>
  - Sources archivées : <chemin-A>, <chemin-B>
  - Liens redirigés dans : <N subjects>

Frontmatter du nouveau subject :
  - forging_state: <actif ou archived>
  - merged_from: 2 sources
  - linked_subjects: <count> liens
  - events: <count> events
  - discussions: <count>
  - decisions: <count>

Suite suggérée :
  - Vérifier la Quick section et la rédiger si nécessaire
  - Optionnel : /stress-test pour valider la doctrine consolidée
```

## Exemples

### Input

> `/subject-merge services/achats/subjects/supplier-simon services/achats/subjects/simon-pme-yiwu`

### Output (résumé)

```
Soudure validée par Benjamin.

Nouveau subject : services/achats/subjects/supplier-simon/  (nom retenu)

Détails :
  - forging_state: actif (relation fournisseur toujours vivante)
  - created_at: 2025-08-22 (min)
  - linked_subjects: 8 (union sans doublon)
  - merged_from: [supplier-simon, simon-pme-yiwu]
  - events: 59 (47 + 12)
  - discussions: 4 (3 + 1)
  - decisions: 5

Sources archivées :
  - simon-pme-yiwu (forging_state: archived, merged_into: supplier-simon)
  - [l'ancien supplier-simon n'existe plus séparément, il est devenu le nouveau]

Liens redirigés dans 12 subjects (commandes Simon, gammes liées, etc.)
```

## Gotchas

- **TOUJOURS validation Benjamin avant écriture**. Aucune soudure automatique. Le scanner forge propose, Benjamin décide.
- **Même nom de fichier nouveau dossier que l'ancien** : si le subject consolidé garde le nom de A, et que A existait déjà à ce chemin... STOP. Il faut soit renommer le subject consolidé, soit créer dans un nouveau dossier puis archiver l'ancien proprement.
- **Ne pas dédupliquer les events/discussions/decisions**. L'historique complet est précieux. Si un même fait est référencé dans A et B, on garde les deux fichiers (avec suffixe -a / -b si conflit de slug).
- **Lien `merged_from` est crucial**. Sans lui, on ne peut pas auditer la soudure. Toujours le préserver.
- **Si overlap < 50%** : refuser la soudure et expliquer. Ce sont probablement 2 subjects distincts qui partagent quelques liens. Suggérer plutôt d'ajouter `linked_subjects` croisés.
- **Pas de soudure d'instances temporelles**. order-400 + order-401 ne se mergent JAMAIS. Leurs leçons remontent vers supplier-simon mais elles restent 2 instances distinctes. Refuser.

## Critères d'évaluation

- **EVAL 1** : Les 2 subjects sources sont-ils du même type (ou types compatibles validés) ? (Pass / Fail)
- **EVAL 2** : Validation Benjamin a-t-elle été obtenue avant écriture ? (Pass / Fail)
- **EVAL 3** : Le frontmatter `merged_from` du nouveau subject contient-il les 2 sources avec leurs chemins et dates d'archivage ? (Pass / Fail)
- **EVAL 4** : Les 2 sources ont-elles bien `forging_state: archived` ET `merged_into: <nouveau>` ? (Pass / Fail)
- **EVAL 5** : Tous les linked_subjects entrants pointant vers A ou B ont-ils été redirigés vers le nouveau ? (Pass si grep retourne 0 / Fail sinon)
- **EVAL 6** : Tous les fichiers events/discussions/decisions ont-ils été préservés (pas supprimés) ? (Pass / Fail)
