# Installer la règle là où elle agit — design

Date : 2026-10-14. Demandeur : Benjamin. Version cible : SOCLE 0.8.0. Statut : à valider.

## Problème

Inspiration : Ramp Glass, « learn things once » (octobre 2026). Ce qu'une personne apprend à l'IA doit servir à tous, sans qu'il faille le réexpliquer.

Dans claude-enterprise (CE), `/documente` capte déjà ce que Benjamin apprend à Claude en le corrigeant. Il ne l'installe pas là où la règle doit agir. Mesures du 14/10 :

- **La capture marche.** Sur les 10 dernières corrections de Benjamin, 9 sont déjà dans le dépôt, en décision ou en discussion du projet en cours. Par exemple, l'incident du 13/10 sur nest-shipping a donné la décision R135 (`multi-entrepot/decisions/2026-10-13-incident-transport-requete-groupee.yaml`), committée dans la même minute que la note privée de Claude Code.
- **L'installation ne se fait pas.** R135 dit « une lecture de production = un seul champ racine ». Elle n'apparaît dans aucun skill, aucun module de règles, ni dans `CLAUDE.md`. Elle n'agit que par la mémoire privée de Claude Code, sur le Mac de Benjamin. Un salarié, un agent sur Cloud Run ou une autre machine n'en sait rien.
- **La Phase I de `/documente` (`scan-impacted`) devrait faire ce travail, mais elle ne le peut pas.**
  - Elle ne regarde que les dossiers *parents* du subject, et seulement les fichiers `SKILL.md`, `agent.yaml`, `brief.yaml` et `config.yaml`. Lancée sur `entreprise/projets/multi-entrepot` comme sur `entreprise/projets/pricing-dynamique`, elle ne trouve qu'un candidat : le `SKILL.md` racine de CE, qui est un gabarit vide.
  - Elle tourne rarement. Les journaux de `forge documente` comptent 37 appels pour environ 174 décisions écrites depuis mai, soit à peu près 1 sur 5.
  - Elle ne fait que proposer, et attend une validation. Les agents autonomes ne peuvent pas la donner.

## Objectif

Quand `/documente` écrit une décision, il se demande où la règle doit agir. Il **installe** la règle à cet endroit, avec un renvoi vers la décision, et l'annonce dans son récap. Il ne pose aucune question : Benjamin corrige ou supprime la ligne s'il n'est pas d'accord, et git garde tout.

Pourquoi sans validation (consigne de Benjamin du 14/10) :
- `/documente` écrit déjà sans question les décisions, les `MEMORY.md` et les rapports (invariant 0.7.0).
- Une ligne mal placée se corrige ou s'annule, ce qui est faible et réversible.
- Une validation bloquerait toutes les installations venues des agents autonomes.

Critères de réussite :

- R135 est installée là où elle agit, ou SOCLE signale qu'aucune cible du dépôt ne convient.
- Trente jours après les 20 premières installations, on sait combien de lignes sont restées telles quelles, combien ont été modifiées et combien ont été supprimées par Benjamin. Ce verdict, tiré de l'usage réel, mesure la justesse des choix de SOCLE.
- Toute installation apparaît dans le récap de `/documente` et dans le commit du bloc.
- Les autres dépôts SOCLE (civisol-ai, equipstore-direction, equipstore-hl, equipstore-ia-entreprise) se comportent exactement comme avant tant qu'ils ne déclarent pas de cibles.

Hors périmètre :

- **La mémoire privée de Claude Code** (`~/.claude/projects/…/memory/`) : ni lecture, ni écriture, ni réglage. Consigne de Benjamin du 14/10 : « Je n'ai pas envie que tu touches à la manière dont les notes privées fonctionnent ». Les deux mémoires restent redondantes, et c'est voulu.
- L'écriture de code ou de hook. SOCLE nomme la suite à faire, il ne la code pas.
- La création d'un module de règles et son branchement dans `CLAUDE.md`.
- Pistes du council du 14/10, à reprendre plus tard : taux de correction par skill, corrections transformées en tests de non-régression, consensus entre plusieurs auteurs.

## Approche retenue

Le council du 14/10 a comparé trois approches, à travers cinq avis contradictoires appuyés sur une recherche web.

- **Récupérer les notes privées de Claude Code dans le dépôt** : écartée. C'est contraire à la consigne de Benjamin, et la capture se fait déjà par la conversation.
- **Ranger chaque correction dans un subject** : écartée. Un `MEMORY.md` de subject n'est lu que quand on travaille dans son dossier, donc la règle manque au moment où elle doit servir. C'est le « défaut mortel » relevé par l'avis Contrarian.
- **Étendre la Phase I pour qu'elle installe la règle là où elle agit** : retenue. Le subject garde la trace (la décision) ; la cible porte l'effet, puisque la règle y est chargée au moment de l'action.

## 1. Les cibles, déclarées par le dépôt

Nouvelle clé facultative du `.forge.yaml` : `rule_targets`. Chaque entrée décrit un type de fichier où une règle peut agir, et la section où l'écrire.

Configuration proposée pour CE :

```yaml
rule_targets:
  - glob: "entreprise/config/rules/*.md"
    label: module de règles
    section: "## Règles apprises"
    charge: "lu par Claude quand la table de CLAUDE.md le désigne pour le contexte"
```

Deux cibles naturelles sont volontairement absentes de CE en 0.8.0.

- **`CLAUDE.md`** : il est lu à chaque session et par tout le monde, donc une ligne de trop y coûte plus cher qu'ailleurs. Une installation sans validation ne doit pas y écrire.
- **Les `SKILL.md`** (section `## Gotchas`) : la doctrine de CE (`entreprise/config/rules/sandbox-validation.md`) fait passer toute amélioration d'un skill en production par `/improve`, puis `validation/improvements/`, puis la validation de Benjamin. Une installation directe, y compris par un agent autonome, contournerait ce circuit. Ce circuit n'a pas servi depuis 90 jours (mesure du 13/10, aucun passage par `validation/`), mais le contourner est une décision de Benjamin, pas de SOCLE. Pour l'instant, une règle qui devrait vivre dans un skill est installée dans le module de règles le plus proche, ou notée `manquante` en nommant le skill.

Le mécanisme, lui, sait écrire dans un `SKILL.md`. Un autre dépôt peut déclarer ces cibles s'il le souhaite.

Aucun format n'est imposé aux cibles : tout fichier markdown qui correspond à un `glob` est une cible possible. `label` et `charge` aident Claude à choisir. Un dépôt qui utilise `.claude/rules/` le déclare de la même façon.

Deux cibles sans fichier existent toujours :

- `code` : la règle devient inutile si on répare le code ou si on pose un garde-fou. SOCLE écrit la suite à faire dans la décision et ne touche à aucun code.
- `locale` : la règle ne vaut que pour ce subject. La décision suffit.

Sans `rule_targets`, la Phase I garde son comportement actuel. C'est ce qui protège les autres dépôts.

## 2. Un déclenchement déterministe

Une phase qui tourne une fois sur cinq ne protège rien. Quand le dépôt déclare des `rule_targets` :

- `forge documente write-capture --kind decision` renvoie `install_check: true` dans son JSON, et le skill doit alors passer par la Phase I ;
- `forge documente commit-atomic` renvoie l'avertissement `installation_absente` pour toute décision du bloc qui n'a pas de bloc `installation` (voir la section 4). L'avertissement figure dans le récap.

## 3. Le choix de la cible, par Claude

Pour chaque décision du bloc, Claude procède en trois temps.

1. **Portée.** Claude classe la règle en `locale` ou `transverse`. Elle est transverse quand elle vaut hors de ce subject : un autre service, un autre outil, ou toute session qui fait la même action.
2. **Cible.** Pour une règle transverse, `forge documente list-targets` donne les fichiers candidats, chacun avec son chemin, son `label`, son `charge` et sa première ligne de description. Claude choisit l'une de ces options :
   - la cible qui sera lue au moment de l'action ;
   - `code`, si un correctif rend la règle inutile ;
   - plusieurs cibles si besoin (pour R135 : `code` et un module) ;
   - `manquante`, avec la raison, si aucune cible ne convient. C'est le signal que le dépôt n'a pas de point de chargement pour ce genre de règle.
3. **Texte.** Une à trois lignes, formulées comme une consigne d'action (« Avant de… », « Jamais… »), avec l'identifiant de la décision.

## 4. L'écriture, par le moteur

`forge documente install-rule <décision> --target <chemin|code|locale|manquante> --text-file <f>` agit selon la cible.

- **Cible fichier** :
  1. Le moteur vérifie que la cible correspond à un `glob` déclaré, et refuse sinon.
  2. Il écrit `- <texte> → <chemin de la décision>` dans la section de la cible, et crée la section si elle manque.
  3. Il ne fait rien si la cible contient déjà ce chemin de décision : l'opération est idempotente.
- **`code`, `locale`, `manquante`** : rien n'est écrit hors de la décision.
- **Dans tous les cas**, un bloc `installation` est ajouté à la fin du fichier de décision. Le reste du fichier reste intact, octet pour octet :

```yaml
installation:
  - cible: entreprise/config/rules/<module>.md
    statut: installee
    texte: >
      Lecture de production sur un service nest : un seul champ racine par requête,
      les requêtes l'une après l'autre (R135).
    le: 2026-10-14
  - cible: code
    statut: a_faire
    suite: Porter le correctif du pool de connexions (modules/mysql) dans nest-stock et nest-oms.
    le: 2026-10-14
```

Statuts : `installee` pour une cible fichier, `a_faire` pour `code`, `notee` pour `locale` et `manquante`. Une suite `a_faire` est suivie par le mécanisme MADR existant : `confirmation.preuve` et `echeance`, puis l'alerte `decision_echue`.

Les fichiers cibles modifiés entrent dans le commit du bloc (`commit-atomic --paths`). Les agents autonomes installent comme une session humaine.

## 5. Le récap et la correction

Le récap de `/documente` liste chaque installation sur une ligne, par exemple :

```
▸ I installation  R135 → entreprise/config/rules/<module>.md ; R135 → code (à faire)
```

Les règles classées `locale` y figurent aussi. Classer à tort une règle transverse en `locale` est le risque silencieux de ce design, et c'est en la voyant passer que Benjamin peut le contester.

Pour corriger, Benjamin modifie ou supprime la ligne dans la cible, à la main ou en le demandant à Claude. Il n'y a pas de commande dédiée : la mesure (section 6) lit l'état réel des fichiers.

## 6. La mesure

`forge documente install-stats` relit chaque bloc `installation` et compare le texte installé à ce que contient la cible aujourd'hui, en se repérant au chemin de la décision. Chaque ligne tombe dans l'une de ces catégories :
- présente telle quelle ;
- présente mais modifiée ;
- absente (supprimée par Benjamin) ;
- `a_faire` ;
- `notee`.

C'est une commande à la demande. Elle n'écrit aucun fichier et ne génère aucun commit. Le critère de réussite se lit 30 jours après les 20 premières installations : si la majorité est restée telle quelle, le choix de SOCLE est fiable. Sinon, on corrige les consignes de la Phase I ou la liste des cibles.

## 7. Le rattrapage

Le stock à rattraper est dans le dépôt : ce sont les décisions déjà écrites, pas les notes privées. `/documente <subject> --installer` rejoue les sections 3 et 4 sur les décisions actives d'un subject qui n'ont pas de bloc `installation`. Il s'exécute subject par subject, à la demande. Les corrections antérieures à mai 2026, qui n'existent qu'en note privée, restent hors périmètre.

## 8. Fichiers touchés

- `bin/documente_engine.py` : sous-commandes `list-targets`, `install-rule` et `install-stats` ; `install_check` dans `write-capture` ; avertissement `installation_absente` dans `commit-atomic`.
- `bin/forge_lib.py` : lecture et validation de `rule_targets` dans `load_forge_config`.
- `skills/documente/SKILL.md` : Phase I réécrite (portée, cible, installation, sans question), ligne de récap, option `--installer`, nouvel EVAL.
- `templates/decision.body.yaml` : bloc `installation`, en commentaire.
- `README.md` et `VERSION` (0.8.0).
- Tests : `tests/test_install_rule.py`. Ils couvrent :
  - l'ajout en fin de décision sans altérer le reste ;
  - l'écriture dans la section, et sa création si elle est absente ;
  - le refus d'une cible hors `glob` ;
  - l'idempotence ;
  - les cibles sans fichier ;
  - un dépôt sans `rule_targets`, qui doit rester identique ;
  - les cinq catégories de `install-stats`, sur des cibles modifiées ou supprimées.

## 9. Premier cas réel : R135

Après la livraison, lancer dans CE `/documente entreprise/projets/multi-entrepot --installer`. On attend deux installations :
- `code`, pour le correctif du pool de connexions dans nest-stock et nest-oms, qui reste « non planifié » selon la décision ;
- un module de règles, ou `manquante` si aucun module actuel ne couvre les lectures de production.

## Constat annexe, côté CE et non SOCLE

Le `SKILL.md` à la racine de claude-enterprise est un gabarit vide (« A brief description of what this skill does », commit du 26/04). C'est le seul candidat que la Phase I actuelle trouve pour les projets. Il est à supprimer dans CE, hors de ce chantier.
