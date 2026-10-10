# Subject reconnu par son en-tête, plus par son chemin — design

Date : 2026-10-10. Demandeur : Benjamin. Version cible : SOCLE 0.7.0.

## Problème

Aujourd'hui, `/documente` décide « subject ou pas » à partir du chemin : un dossier est un subject seulement s'il vit sous `subjects/`. Sinon, la phase F0 juge décision par décision s'il faut créer un subject, et ce jugement n'est jamais réévalué. Résultat dans claude-enterprise : 42 subjects pour 88 MEMORY.md hors `subjects/`, dont des projets longs jamais migrés. Ces 88 mémoires suivent un autre format et passent par un autre circuit de `/documente` : le dossier-entité (workflow folder).

Le critère « entité ou objet métier durable » date de la reprise de l'ancien système, qui ne connaissait pas les subjects. Il n'a plus de raison d'être.

## Objectif

- Tout dossier qui a un MEMORY.md est un subject, une fois converti au format unique. Pendant la transition, un MEMORY.md non converti n'est pas encore compté (section 4).
- Son type est porté par l'en-tête du MEMORY.md, jamais par le chemin.
- `/documente` n'a qu'un circuit. Il tourne sans aucune question, parce que les agents autonomes le lancent à la fin de chaque cycle et ne peuvent pas répondre.

Critères de réussite :

- La phase F0 et le workflow folder disparaissent de `skills/documente/SKILL.md`.
- Aucun `AskUserQuestion` n'est posé par `/documente` pour nommer, typer ou classer.
- Un MEMORY.md converti garde tout son contenu.
- Les 4 autres dépôts SOCLE (civisol-ai, equipstore-direction, equipstore-hl, equipstore-ia-entreprise) continuent de marcher sans changer leur `.forge.yaml`.

Hors périmètre : déplacer des dossiers, et faire une migration en masse.

## Approche retenue

Approche 3 parmi les trois présentées : tout devient subject sur place. Les deux autres approches ont été écartées.

- Déplacer les 88 dossiers sous `subjects/` : trop de chemins cassés (skills, outils, imports, liens).
- Garder deux circuits en élargissant seulement F0 : la décision par chemin et le double format restent.

## 1. Nommage, entièrement automatique

Le champ `name` de l'en-tête est fixé sans validation humaine.

1. **Dossier existant** : `name` est le nom du dossier.
2. **Nouveau subject avec un identifiant métier** : le nom suit le modèle déclaré dans le `REFERENCE.md` du type, par exemple `order-{n°}`, `supplier-{nom}`, `{régie}-{compte}`, ou le nom du skill ou de l'outil.
3. **Nouveau subject sans identifiant métier** : Claude choisit seul un slug court en kebab-case, d'après le contexte de la conversation.
4. **Doublon possible** : Claude juge seul. Si c'est le même objet, il enrichit le subject existant ; sinon, il en crée un nouveau.

Pas de question, pas de marque `a_revoir`, pas de commande de renommage.

## 2. Types

Inventaire de CE au 10/10 : 46 des 88 mémoires déclarent déjà un type (13 `tool`, 11 `skill`, 10 `service`, 9 `projet`, 3 `skill-cas`) ; 42 n'en ont pas.

### Attribution du type, la première source qui répond gagne

1. Le `type:` de l'en-tête.
2. La table emplacement → type du `.forge.yaml` du dépôt, clé `type_by_path`, qui est facultative. La configuration de CE :

   ```yaml
   type_by_path:
     - pattern: "*/skills/*/cas/*"
       type: skill-cas
     - pattern: "*/skills/*"
       type: skill
     - pattern: "*/tools/*"
       type: tool
     - pattern: "*/agents/*"
       type: agent
     - pattern: "entreprise/projets/*"
       type: projet
     - pattern: "services/*"
       type: service
   ```

   Les motifs sont lus dans l'ordre et le premier qui correspond l'emporte. Ce qui est sous `*/subjects/*` garde le type déjà présent dans son en-tête.
3. Sinon, Claude choisit le type parmi ceux déclarés dans le dépôt et l'écrit dans l'en-tête.

Le type écrit dans l'en-tête n'est plus jamais recalculé.

### Capacités déclarées par type

Chaque type déclare ses capacités dans son `REFERENCE.md`, champ `capabilities` :

| Capacité | Rôle |
|---|---|
| `memory` | MEMORY.md borné (format unique, section 3) |
| `decisions` | fichiers `discussions/` et `decisions/` |
| `lifecycle` | `forging_state` (`actif`, `archived`) |
| `events` | `last_event`, alertes de stagnation |
| `links` | `linked_subjects`, propagation sur 1 niveau |

- `skill`, `skill-cas`, `tool`, `agent` et `service` ont `memory`, `decisions` et `lifecycle`.
- `projet` et les 6 types métier existants (`supplier`, `supplier-order`, `freight-forwarder`, `marketing-campaign`, `backlog-tech`, `ce-architecture-decision`) ont les cinq capacités.

Les cinq nouveaux types (`skill`, `skill-cas`, `tool`, `agent`, `service`) et `projet` sont livrés comme types génériques du plugin, dans un nouveau dossier `types/<type>/REFERENCE.md` à la racine de SOCLE, chacun avec un `REFERENCE.md` minimal. Un dépôt peut les surcharger dans son propre `types/`.

Un type inconnu, sans `REFERENCE.md`, reçoit `memory`, `decisions` et `lifecycle`, et une alerte du scanner le signale.

## 3. Format unique et circuit unique

### Format du MEMORY.md

En-tête :

- `name`, `type` et `forging_state` : obligatoires ;
- `derniere_maj` ;
- `memory_max_kb` : facultatif, 8 par défaut ;
- `linked_subjects` : seulement si le type a `links` ;
- `last_event` : seulement si le type a `events`.

Corps, au niveau `##` pour que `check-memory` compte chaque section :

1. `## Quick` : moins de 100 mots.
2. `## Doctrine en vigueur` : une ligne par règle.
3. `## Décisions actives` : au plus 10, chacune en pointeur vers son fichier.
4. `## Règles apprises`.
5. `## Détails` : facultatif, borné, sans sous-sections datées.
6. `## Liens` : seulement si le type a `links`, entre les balises `okf-links`.

Fichiers de discussion et de décision : l'en-tête des subjects devient le seul format écrit (`type`, `status`, `resulting_decision`, etc.). Les fichiers existants ne sont pas réécrits, et les lecteurs acceptent les deux formats.

### Circuit de `/documente`

`forge documente prepare` reconnaît un subject par son en-tête. À défaut, il applique `type_by_path` puis le choix de Claude. Il rend les capacités du type. Ensuite, `/documente` déroule toujours la même suite d'étapes :

1. capturer la discussion et la décision ;
2. les écrire (`write-capture`) ;
3. calculer l'état du cycle de vie ;
4. propager vers les subjects liés, seulement avec `links` ;
5. réécrire les sections (`patch-section`) ;
6. contrôler la borne (F.3 : `check-memory`, recopies remplacées par des pointeurs) ;
7. mettre à jour l'en-tête (`patch-frontmatter`) ;
8. committer (`commit-atomic`).

Une étape dont la capacité est absente est sautée, sans erreur. La phase F0, sa sous-phase F0.0 et tout le workflow folder sont supprimés du SKILL.md.

### Migration au fil de l'eau

- La première fois que `/documente` touche un MEMORY.md à l'ancien format, sans `forging_state`, il le convertit dans le même commit :
  - il complète l'en-tête (`name`, `type`, `forging_state: actif`) ;
  - il range le contenu dans les sections du format unique ;
  - il ne supprime rien : un contenu sans section d'accueil va dans `## Détails`, puis la borne F.3 s'applique.
- `forge migrate --dry-run` liste les MEMORY.md restant à convertir, avec le type que chacun recevrait. Elle n'écrit rien. Il n'y a pas de mode d'écriture en masse.

## 4. Découverte, liens, autres dépôts

### Découverte

Une seule fonction, `find_subjects(project_dir)`, dans `forge_lib.py`. Elle parcourt le dépôt et retient tout MEMORY.md dont l'en-tête porte `forging_state`. Elle exclut `.git`, les dossiers cachés, `fixtures`, `_archive*` et `node_modules`.

Elle remplace :

- `forge_scanner.find_subject_memory_files` ;
- `documente_engine.cmd_list_subjects`, qui ne cherchait que `subjects/*/MEMORY.md` ;
- la recherche de `autolink_engine`, qui ne cherchait que `subjects/*/MEMORY.md` ;
- `forge_engine._candidate_subject_roots`, utilisée par `resolve_link`.

`pool_roots` reste lu pour la compatibilité, mais ne limite plus la découverte.

Un MEMORY.md non converti n'est pas un subject : il n'apparaît ni dans l'index ni dans les alertes avant sa conversion. Cela évite une vague d'alertes « MEMORY vide » au passage en 0.7.0.

### Liens

`resolve_link` cherche, dans l'ordre :

1. un subject dont l'en-tête porte `name:` égal au lien (ou à `<name>` pour un lien `<type>:<name>`, avec vérification du type) ;
2. un subject dont le dossier porte ce nom.

S'il trouve deux subjects homonymes, il ne résout pas le lien et rend une alerte. Les liens existants restent valides.

### Index

`SUBJECTS-INDEX.md` est regroupé par type. Pour CE, il passe d'environ 42 entrées à environ 130 au fil des conversions.

### Autres dépôts SOCLE

| Dépôt | Subjects | Autres MEMORY |
|---|---|---|
| equipstore-direction | 1 | 5 |
| equipstore-ia-entreprise | 0 | 5 |
| equipstore-hl | 0 | 1 |
| civisol-ai | 0 | 8 |

`type_by_path` est facultatif. Sans lui, le type vient de l'en-tête ou du choix de Claude. Aucun `.forge.yaml` n'a besoin de changer.

### Ce qui ne change pas

Le hook Stop post-bloc : il raisonne déjà sur « dossier ancêtre le plus proche qui a un MEMORY.md ».

## 5. Tests (dépôt socle)

- `find_subjects` :
  - un subject hors `subjects/` est trouvé ;
  - un MEMORY.md sans `forging_state` est ignoré ;
  - `fixtures` et `_archive*` sont exclus.
- Attribution du type : un cas par source (en-tête, `type_by_path`, choix par défaut), ordre des motifs respecté, type d'en-tête jamais recalculé.
- Capacités : un type sans `links` saute la propagation, et un type inconnu reçoit les trois capacités par défaut avec une alerte.
- `resolve_link` : résolution par `name` hors `subjects/`, homonymes refusés, liens `<type>:<name>` existants toujours résolus.
- Conversion : sur un MEMORY.md à l'ancien format, chaque ligne de contenu d'origine se retrouve après passage, et l'en-tête est complété.
- `forge migrate --dry-run` : aucune écriture, et liste cohérente avec `find_subjects`.
- Non-régression : la suite actuelle passe, notamment `test_check_post_bloc.py` et `test_memory_commands.py`.
- Essai réel avant publication : `forge migrate --dry-run` sur claude-enterprise et sur equipstore-direction, sortie relue par Benjamin.

## Livraison

- SOCLE 0.7.0 : `plugin.json`, `marketplace.json`, `VERSION` et changelog du README.
- `rules/subject-pool.md` : le critère « entité ou objet métier » est remplacé par la section 2 de ce document.
- Côté CE : ajout de `type_by_path` dans `.forge.yaml` ; dans le `CLAUDE.md` global de Benjamin (`~/.claude/CLAUDE.md`) et dans `entreprise/config/rules/operations.md`, le paragraphe « délégation à `/documente` si subject pool » devient « toujours `/documente` ».
