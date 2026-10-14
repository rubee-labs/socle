# Installer la règle là où elle agit — design

Date : 2026-10-14. Demandeur : Benjamin. Version cible : SOCLE 0.8.0. Statut : à valider.

## Problème

Inspiration : Ramp Glass, « learn things once » (octobre 2026). Ce qu'une personne apprend à l'IA doit servir à tous, sans réexplication.

Dans claude-enterprise (CE), `/documente` capte déjà ce que Benjamin apprend à Claude en le corrigeant. Il ne l'installe pas là où la règle doit agir. Mesures du 14/10 :

- **La capture marche.** Sur les 10 dernières corrections de Benjamin, 9 sont déjà dans le dépôt, sous forme de décision ou de discussion du projet en cours. Exemple : l'incident du 13/10 sur nest-shipping a donné la décision R135 (`multi-entrepot/decisions/2026-10-13-incident-transport-requete-groupee.yaml`), committée dans la même minute que la note privée de Claude Code.
- **L'installation ne se fait pas.** R135 dit « une lecture de production = un seul champ racine ». Elle n'est dans aucun skill, aucun module de règles, ni dans `CLAUDE.md`. Elle n'agit que par la mémoire privée de Claude Code sur le Mac de Benjamin. Un salarié, un agent sur Cloud Run ou une autre machine n'en sait rien.
- **La Phase I de `/documente` (`scan-impacted`) devrait faire ce travail, mais elle ne le peut pas :**
  - elle ne regarde que les dossiers *parents* du subject, et seulement `SKILL.md`, `agent.yaml`, `brief.yaml` et `config.yaml`. Lancée sur `entreprise/projets/multi-entrepot` et sur `entreprise/projets/pricing-dynamique`, elle ne propose qu'un seul candidat : le `SKILL.md` racine de CE, qui est un gabarit vide ;
  - elle tourne rarement. Les journaux de `forge documente` donnent 37 appels pour environ 174 décisions écrites depuis mai, soit environ 1 sur 5.

## Objectif

Quand `/documente` écrit une décision, il se demande où la règle doit agir. Il **propose** une cible, Benjamin valide, et SOCLE **écrit** la règle à cet endroit avec un renvoi vers la décision.

Critères de réussite :

- Sur les 20 premières propositions, on connaît la part acceptée telle quelle, modifiée ou refusée. Si la majorité est acceptée telle quelle, une version suivante pourra automatiser davantage. Sinon, le choix de la cible reste humain.
- R135 est installée là où elle agit, ou bien SOCLE signale qu'aucune cible du dépôt ne convient.
- Aucune écriture dans une cible sans validation humaine.
- Les autres dépôts SOCLE (civisol-ai, equipstore-direction, equipstore-hl, equipstore-ia-entreprise) se comportent exactement comme avant tant qu'ils ne déclarent pas de cibles.
- `/documente` reste sans question (invariant 0.7.0) : la validation passe par une commande explicite, pas par une question posée en cours de route.

Hors périmètre :

- **La mémoire privée de Claude Code** (`~/.claude/projects/…/memory/`). Ni lecture, ni écriture, ni réglage. Consigne de Benjamin du 14/10 : « Je n'ai pas envie que tu touches à la manière dont les notes privées fonctionnent ». Les deux mémoires restent redondantes, et c'est voulu.
- Écrire du code ou un hook. SOCLE nomme la suite à faire, il ne la code pas.
- Créer un nouveau module de règles et le brancher dans `CLAUDE.md`.
- Les pistes du council du 14/10 à reprendre plus tard : taux de correction par skill, transformation des corrections en tests de non-régression, consensus entre plusieurs auteurs.

## Approche retenue

Trois approches ont été comparées par le council du 14/10, cinq avis contradictoires avec recherche web :

- **Récupérer les notes privées de Claude Code dans le dépôt** : écartée. Contrainte de Benjamin, et la capture est déjà faite par la conversation.
- **Ranger chaque correction dans un subject** : écartée. Un `MEMORY.md` de subject n'est lu que quand on travaille dans son dossier, donc la règle manque au moment où elle doit servir. C'était le « défaut mortel » relevé par l'avis Contrarian.
- **Étendre la Phase I pour qu'elle installe la règle là où elle agit** : retenue. Le subject garde la trace (la décision), la cible porte l'effet (la règle chargée au moment de l'action).

## 1. Les cibles, déclarées par le dépôt

Nouvelle clé facultative du `.forge.yaml` : `rule_targets`. Chaque entrée décrit un type de fichier où une règle peut agir, et la section où l'écrire.

Configuration proposée pour CE :

```yaml
rule_targets:
  - glob: "entreprise/config/rules/*.md"
    label: module de règles
    section: "## Règles apprises"
    charge: "lu par Claude quand la table de CLAUDE.md le désigne pour le contexte"
  - glob: "**/skills/*/SKILL.md"
    label: skill
    section: "## Gotchas"
    charge: "lu quand le skill est invoqué"
  - glob: "CLAUDE.md"
    label: instructions du dépôt
    section: "## Règles apprises"
    charge: "lu à chaque session"
```

Les cibles n'ont pas de format imposé. Tout fichier markdown qui correspond à un `glob` est une cible possible ; `label` et `charge` servent à Claude pour choisir. Un dépôt qui utilise `.claude/rules/` le déclare de la même façon.

Deux cibles sans fichier existent toujours :

- `code` : la règle disparaît si on répare le code ou si on pose un garde-fou. SOCLE écrit la suite à faire dans la décision et ne touche à aucun code.
- `locale` : la règle ne vaut que pour ce subject. La décision suffit, rien n'est installé.

Sans `rule_targets`, la Phase I garde son comportement actuel. C'est ce qui protège les autres dépôts.

## 2. Le déclenchement, déterministe

Une phase qui tourne une fois sur cinq ne protège rien. Quand le dépôt a des `rule_targets` :

- `forge documente write-capture --kind decision` renvoie `install_check: true` dans son JSON, et le skill doit alors passer par la Phase I ;
- `forge documente commit-atomic` renvoie l'avertissement `installation_absente` pour toute décision du bloc qui n'a pas de bloc `installation` (section 4). L'avertissement apparaît dans le récap.

## 3. La proposition (Claude)

Pour chaque décision du bloc :

1. **Portée.** Claude classe la règle en `locale` ou `transverse`. Elle est transverse quand elle vaut hors de ce subject : un autre service, un autre outil, toute session qui fait la même action.
2. **Cible.** Si la règle est transverse, `forge documente list-targets` donne les fichiers candidats. Pour chacun, le moteur fournit le chemin, le `label`, le `charge` et la première ligne de description. Claude choisit la cible qui sera lue au moment de l'action, ou `code` si un correctif rend la règle inutile, ou plusieurs cibles si besoin (R135 : `code` et un module). Si aucune cible ne convient, il l'écrit (`cible: manquante`, avec la raison) : c'est un signal que le dépôt n'a pas de point de chargement pour ce genre de règle.
3. **Texte.** Une à trois lignes, formulées comme une consigne d'action (« Avant de… », « Jamais… »), avec l'identifiant de la décision.

`forge documente propose-install <décision> --target <chemin|code|locale|manquante> --text-file <f>` ajoute le bloc `installation` à la fin du fichier de décision. Le reste du fichier reste intact, octet pour octet.

## 4. La trace dans la décision

```yaml
installation:
  - cible: entreprise/config/rules/<module>.md
    statut: proposee          # proposee | installee | refusee
    texte: >
      Lecture de production sur un service nest : un seul champ racine par requête,
      les requêtes l'une après l'autre (R135).
    propose_le: 2026-10-14
  - cible: code
    statut: proposee
    suite: Porter le correctif du pool de connexions (modules/mysql) dans nest-stock et nest-oms.
    propose_le: 2026-10-14
```

Statuts, selon la cible :

| Cible | Statut écrit par `propose-install` | Après la réponse de Benjamin |
|---|---|---|
| fichier | `proposee` | `installee` (ligne écrite) ou `refusee` |
| `code` | `proposee` | `acceptee` (la suite est retenue, rien n'est écrit) ou `refusee` |
| `locale`, `manquante` | `notee` | aucune validation, mais la ligne figure au récap pour pouvoir être contestée |

À la validation, le moteur ajoute la date (`installee_le` ou `acceptee_le`) et `verdict: tel_quel | modifie`. Un refus ajoute une `raison`. Ces verdicts servent de mesure (section 7). Classer une règle en `locale` à tort est le risque silencieux de ce design. C'est pour ça que les `notee` restent visibles au récap.

## 5. Validation et écriture (humain, puis moteur)

- **Pendant `/documente`** : aucune question. Le récap liste les propositions, par exemple « 2 règles à installer : R135 → module X, R135 → code ». Benjamin y répond s'il le souhaite.
- **Validation** : quand Benjamin dit « installe », éventuellement en corrigeant le texte, Claude lance `forge documente install-rule <décision> [--texte-file <f>]`. Le moteur :
  1. vérifie que la cible correspond à un `glob` déclaré, et refuse sinon ;
  2. écrit la ligne dans la section de la cible, en créant la section si elle manque : `- <texte> → <chemin de la décision>` ;
  3. ne fait rien si la cible contient déjà ce chemin de décision (idempotent) ;
  4. passe le statut à `installee`, avec la date et le verdict. Pour une cible `code`, la même commande n'écrit rien dans le dépôt et passe le statut à `acceptee`.
- **Refus** : `forge documente reject-install <décision> --cible <c> --raison "<r>"`.
- **Agents autonomes** : leur `/documente` laisse les propositions en `proposee`. Elles attendent une session humaine.
- Le commit du bloc inclut la décision et la cible modifiée (`commit-atomic --paths`).

Une suite `code` acceptée reste dans la décision. Elle est suivie par le mécanisme MADR existant (`confirmation.preuve` et `echeance`, puis alerte `decision_echue`).

## 6. Alerte du scanner

Nouvelle alerte `installation_en_attente` : une proposition en `proposee` depuis plus de 7 jours. Elle s'affiche au health-check de début de session, comme `decision_echue`. Le scanner n'écrit rien de plus. Les fichiers régénérés continuent de passer par `write_if_changed`.

## 7. Mesure

`forge documente install-stats` lit les blocs `installation` du dépôt et compte, par type de cible : en attente (`proposee`), validées telles quelles, validées après modification, refusées, notées (`locale`, `manquante`). C'est une commande à la demande : aucun fichier n'est écrit et aucun commit n'est généré. Le critère de réussite se lit sur les 20 premières propositions.

## 8. Rattrapage

Le stock à rattraper est dans le dépôt : ce sont les décisions déjà écrites, et non les notes privées. `/documente <subject> --installer` rejoue les sections 3 à 5 sur les décisions actives d'un subject qui n'ont pas de bloc `installation`. Il se fait subject par subject, à la demande, avec le même circuit propose → valide → écrit. Les corrections antérieures à mai 2026, qui n'existent qu'en note privée, restent hors périmètre.

## 9. Fichiers touchés

- `bin/documente_engine.py` : sous-commandes `list-targets`, `propose-install`, `install-rule`, `reject-install`, `install-stats` ; `install_check` dans `write-capture` ; avertissement `installation_absente` dans `commit-atomic`.
- `bin/forge_lib.py` : lecture et validation de `rule_targets` dans `load_forge_config`.
- `bin/forge_scanner.py` : alerte `installation_en_attente`.
- `skills/documente/SKILL.md` : Phase I réécrite (portée, cible, proposition), récap, option `--installer`, nouvel EVAL.
- `templates/decision.body.yaml` : bloc `installation` en commentaire.
- `README.md`, `VERSION` (0.8.0).
- Tests : `tests/test_install_rule.py`. Il couvre :
  - l'ajout en fin de décision sans altérer le reste ;
  - l'écriture dans la section, avec création si elle est absente ;
  - le refus d'une cible hors `glob` ;
  - l'idempotence ;
  - le refus sans rien écrire ;
  - un dépôt sans `rule_targets` identique à avant ;
  - les comptes de `install-stats`.

## 10. Premier cas réel : R135

Après la livraison, lancer `/documente entreprise/projets/multi-entrepot --installer` dans CE. La proposition attendue comprend :
- la cible `code`, pour le correctif du pool de connexions dans nest-stock et nest-oms, encore « non planifié » selon la décision ;
- une cible texte, ou `manquante` si aucun module actuel ne couvre les lectures de production.

La réponse de Benjamin est le premier point de mesure.

## Constat annexe, côté CE et non SOCLE

Le `SKILL.md` à la racine de claude-enterprise est un gabarit vide (« A brief description of what this skill does », commit du 26/04). C'est le seul candidat que la Phase I actuelle trouve pour les projets. Il est à supprimer dans CE, hors de ce chantier.
