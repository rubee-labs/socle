---
date: 2026-05-05
type: discussion
produced_by: human_and_claude
participants:
  - benjamin
  - claude
status: closed
resulting_decision: 2026-05-05-migration-claude-forge
---
# Migration Subject Pool → claude-forge plugin Claude Code

## Contexte de départ

Session ouverte sur une question apparemment simple : "comment faire fonctionner /documente dans benjamin-perso ?". La discussion a révélé que Subject Pool était physiquement enfermé dans claude-enterprise/entreprise/, alors que conceptuellement il est une couche du harnais Claude Code (la 4ème couche de mémoire structurée que Claude Code natif n'a pas).

## Cheminement

### 1. Diagnostic du couplage

Premier constat : `/documente` est une slash command dans `.claude/commands/documente.md` du projet claude-enterprise, qui pointe vers `entreprise/skills/documente/SKILL.md`, lequel invoque `entreprise/config/feedback-loop/documente_engine.py`. Pour qu'il marche dans benjamin-perso, il faut soit (a) lancer Claude depuis claude-enterprise avec un path absolu, soit (b) extraire Subject Pool en une couche partagée.

### 2. Découverte du nom mort "feedback-loop"

En cours de discussion, identification que le dossier `feedback-loop/` n'a plus de raison d'être appelé ainsi depuis le commit `16424b4c` du matin (archivage du pipeline auto-feedback). Les engines Subject Pool y sont restés orphelins de leur voisin originel. Le ménage du matin a été incomplet : 5 fichiers cassés silencieusement (refs vers `feedback-log.jsonl` archivé). Chantier 1 → suppression de ces refs orphelines.

### 3. Comparaison claude-mem vs Subject Pool

claude-mem (https://docs.claude-mem.ai) existe déjà comme produit externe. Mais axe différent : compression session-à-session (axe temporel), SQLite + Chroma. Subject Pool joue sur l'axe structurel : typage des décisions, cycle γ, cascade entre subjects liés, validation Python. Pas concurrents — complémentaires. Espace produit confirmé.

### 4. Architecture hybride retenue

3 modèles évalués : 100% global comme claude-mem, hybride global+projet, vendoré per-project. claude-mem peut se permettre 100% global parce que ses données ne sont pas projet ; Subject Pool a une contrainte différente : les `subjects/<name>/` sont du contenu projet qui doit être commité dans le repo. Décision : hybride. Code global (plugin), données per-project.

### 5. Conflit doctrinal harness

Avant le big-bang, audit memory : 4 occurrences de `feedback-loop` dans `~/.claude/projects/.../memory/`. Toutes pointent vers le pipeline mort. MAIS découverte d'un conflit majeur : memory `feedback_pas_de_jargon_harness.md` (47 jours) interdisait explicitement le mot "harness" pour désigner Claude-Enterprise. Or le plan utilise `<project>/harness/claude-forge/`. Trois options proposées (α archiver, β renommer, γ préciser portée). Benjamin tranche α : "Le mot harness est désormais compris de tous. À l'époque je n'en avais jamais entendu parler. Désormais tout le monde parle de ça." Memory archivé.

### 6. Naming et compte GitHub

claude-mem est pris. Trois alternatives proposées : `claude-forge` (métaphore alignée avec forge_engine), `subject-pool` (assumer le nom interne), `claude-doctrine`. Vote claude-forge. Compte GitHub : `rubee-labs` (org existante). Visibilité : privée d'abord (Mode 2).

### 7. Périmètre et big-bang

Q2 résolu avec une intuition supérieure de Benjamin : la méta-réflexion `entreprise/projets/subject-pool/` ne reste PAS dans claude-enterprise — elle migre dans `claude-forge/subjects/claude-forge/`. Dogfooding parfait. Q3 big-bang validé. Q4 subjects existants services/*/subjects/ INTACTES.

### 8. Réestimation des refs critiques

Mon estimation initiale "170 refs à patcher" corrigée par Benjamin : seulement 17 refs vivantes (15 SKILL.md + 1 hook + 1 rules). Les ~140 autres sont dans des artefacts datés (plans, decisions historiques, MEMORY.md) qui ne doivent JAMAIS être patchés. Règle générale : un artefact daté = un instantané, on ne le retouche pas.

### 9. Exécution big-bang (6 phases A-F)

Net : claude-forge +9929 lignes, claude-enterprise -12423/+7 lignes.

### 10. Installation plugin Claude Code

Première tentative `/plugin marketplace add rubee-labs/claude-forge` échouée : "Marketplace file not found". Découverte : Claude Code attend `.claude-plugin/marketplace.json` (catalogue), pas seulement `plugin.json` (manifest). Pattern mono-plugin : `marketplace.json` à la racine pointe vers le plugin via `"source": "./"`.

### 11. Bug post-installation v0.1.0 → fix v0.1.1

`forge scanner` retournait 0 actifs au lieu de 15. Bug critique dans `forge_lib.py:get_project_dir()` : utilisait `Path(__file__).parents[3]` qui marchait depuis `entreprise/config/feedback-loop/` mais pointe désormais vers `~/.claude/plugins/cache/rubee-labs/` une fois installé. Fix : résolution cwd-based standard. Bump 0.1.0 → 0.1.1. Validé : `15 actifs` ✅.

## Conclusion

Subject Pool est désormais un plugin Claude Code installable, autonome, distribuable. Le big-bang a démontré end-to-end : extraction propre, install marketplace plugin, cycle de release. Le repo `rubee-labs/claude-forge` est désormais un produit, pas une bibliothèque interne.
