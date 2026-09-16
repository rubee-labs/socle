---
name: skillify
description: >-
  Compile un workflow ad hoc — qu'on vient de faire à la main dans la conversation
  ou par tâtonnement — en un skill réutilisable et testé. Adapté du pattern
  "Skillify" de Garry Tan (cf. analyse Forge-Lab 2026-05-09). Trigger sur
  "skillifie ça", "skillify it", "transforme ça en skill", "réifie cette procédure",
  "rends ça réutilisable".
type_anthropic: 5
visibilité: entreprise
auteur: Benjamin
date_creation: 2026-05-10
version: 0.2
tags: [meta, scaffolding, compilation-continue, garry-tan]
effort: medium
outils_requis: [forge_skillify_engine]
securite_externe: false
---

# Skillify — Workflow ad hoc → SKILL.md testé

## Objectif

Quand tu viens de faire un travail à la main qui mérite d'être réifié (ex: "j'ai débuggé X via 4 commandes ; j'ai ré-fait ce raisonnement 3 fois cette semaine"), ce skill capture la procédure en un **vrai skill** (SKILL.md + script Python + tests + fixtures de routage). La compilation continue de la connaissance opérationnelle.

C'est l'équivalent du pattern Garry Tan : *« You hit a new failure. You fix it once. You say "skillify it!". Now the fix is permanent. »*

## Quand utiliser

- Tu viens de finir une procédure manuelle qui se répétera (ex: "vérifier l'archivage des emails handled offline", "scorer un fournisseur sur les 7 dimensions").
- Un workflow ad hoc revient ≥ 2 fois — c'est le signal.
- Un bug a été corrigé manuellement et tu veux qu'il ne soit plus jamais reproduit.
- Une feature manquante côté MCP, hook ou agent vient d'être identifiée et tu veux la réifier proprement.

**Quand NE PAS utiliser** :

- Pour une réflexion stratégique non procédurale → `/save` (savoir) ou `/idea` (à mûrir).
- Pour une décision architecturale → subject pool `/documente` sur un sujet de type `ce-architecture-decision`.
- Pour un workflow trop vague (« automatiser le marketing ») → trop large, le skill sera flou. Resserrer d'abord en cas concret.

## Workflow

### Phase 1 — Capturer le pattern

À partir du contexte de conversation (les derniers messages), résumer en 3 lignes :

1. **Phrase déclencheur typique** (ex: "vérifie que les emails archivés du jour ont bien été expungés").
2. **Steps déterministes** que tu (Claude) as exécutés (commandes shell, lectures, calculs) — laisser de côté le jugement et la rédaction qui resteront LLM.
3. **Critère de succès** (comment savoir que le skill a réussi).

Présenter ce résumé à Benjamin et lui demander :

- Le nom kebab-case du skill (ex: `verify-archive-expunge`).
- 2-4 phrases déclencheurs alternatives (pour la fixture routing).
- Une description ≥30 chars qui discrimine ce skill des skills voisins.
- **Le(s) subject(s) d'origine** (D10) : de quel(s) subject(s) du pool ce workflow est-il issu ? Chemins de dossiers subject (ex: `services/finance/subjects/tresorerie`). Si le workflow ne naît d'aucun subject, le dire explicitement — la provenance restera vide et le check le signalera en hygiène.

Validation explicite avant Phase 2.

### Phase 2 — Scaffold via le moteur Python

Invoquer `forge skillify scaffold` :

```bash
forge skillify scaffold <name> \
  --description "<description ≥30 chars>" \
  --triggers "<phrase déclencheur 1>,<phrase déclencheur 2>,..." \
  --source-subjects "<chemin subject 1>,<chemin subject 2>"
```

Sortie JSON `{ok, skill_dir, files_created: [...], provenance: {source_subjects, backlinks_updated, warnings}}`.

Le moteur cible `entreprise/skills/<name>/` si `entreprise/skills/` existe, sinon `skills/<name>/`. Override possible via `--target <chemin>`.

**Provenance bidirectionnelle (D10)** : `--source-subjects` écrit `source_subjects: [...]` dans le frontmatter du SKILL.md généré ET ajoute le skill aux `linked_skills` du MEMORY.md de chaque subject cité. Vérifier les `warnings` de la sortie (subject introuvable = backlink non posé). Les MEMORY.md modifiés font partie du commit de Phase 6.

### Phase 3 — Compléter les stubs (LLM)

Les 5 fichiers contiennent des sentinelles `SKILLIFY_STUB`. Compléter dans cet ordre (Edit) :

1. **`SKILL.md`** : Objectif, Quand utiliser, Workflow (Phases), Gotchas, EVAL. Pas de générique — chaque section doit refléter le cas concret capturé en Phase 1.
2. **`scripts/<name>.py`** : la logique déterministe. Stdlib only de préférence (rester aligné sur la doctrine socle). Sortie JSON sur stdout.
3. **`tests/test_<name>.py`** : ≥2 tests sur le cas nominal et 1 cas d'erreur.
4. **`fixtures/<name>.routing.jsonl`** : compléter avec les vraies phrases déclencheurs si Benjamin en a donné de nouvelles.
5. **`EVAL.md`** : adapter la checklist au cas réel (ex: "le skill produit le même résultat 3 fois sur le même input").

⚠️ **Toutes les sentinelles `SKILLIFY_STUB` doivent être supprimées** avant Phase 4. Le check les détecte et bloque.

### Phase 4 — Valider via `forge skillify check`

```bash
forge skillify check <skill-dir>
```

Sortie JSON détaillée : 11 checks, dont 8 critiques (bloquants) + 3 hygiène (scripts/, tests/, source_subjects — bloquants seulement en `--strict`).

Si `ok: false` → afficher les `failed_critical` à Benjamin, demander de corriger, ré-itérer.

Si `ok: true` → Phase 5.

### Phase 5 — Tester en conditions réelles

Inviter Benjamin à invoquer le nouveau skill sur un cas réel équivalent à ce qui a déclenché Phase 1. Si le skill produit le bon résultat → succès, le réifier. Si non → retour Phase 3 pour ajuster.

### Phase 6 — Commit + push

Une fois le skill validé en conditions réelles :

- Documenter la décision dans `<repo>/decisions/` (description du pattern réifié, ce qui a déclenché la skillification).
- Commit + push selon doctrine (cf. memory `feedback_post_session_commit_doc.md`).
- Mentionner dans le commit : « skillify <name> — capture du workflow ad hoc <X> ».

## Audit global

À tout moment, `forge skillify audit` scanne tous les skills d'un répertoire :

```bash
forge skillify audit                     # défaut : skills/ ou entreprise/skills/
forge skillify audit --target <dir>      # cible spécifique
forge skillify audit --strict            # warn comptés comme fail
```

Sortie : `{ok, summary: {total, ok, warn, fail}, reports: [...]}`. Utile en CI ou en revue mensuelle pour identifier les skills qui se sont dégradés (sentinelles oubliées, sections manquantes, etc.).

## Exemples

### Input

> "Je viens de vérifier 3 fois cette semaine que les emails archivés du jour avaient bien été expungés (lire INBOX, comparer aux logs, lancer expunge si manquant). Skillifie ça."

### Output (résumé)

```
Skill créé : entreprise/skills/verify-archive-expunge/
├── SKILL.md       (description, Quand utiliser, Workflow, Gotchas, EVAL)
├── scripts/verify-archive-expunge.py   (logique déterministe : INBOX vs logs)
├── tests/test_verify-archive-expunge.py
├── fixtures/verify-archive-expunge.routing.jsonl
└── EVAL.md

forge skillify check passes ok: true
```

## Gotchas

- **Ne JAMAIS skillifier un workflow non encore exécuté à la main**. Le risque est de réifier une procédure imaginaire qui ne marchera pas en prod. Skillify capture, ne crée pas.
- **Ne pas mettre du jugement dans le script Python**. Tout ce qui demande une décision contextuelle reste dans le SKILL.md (orchestrateur LLM). Le script Python ne fait que du déterministe (lecture, parsing, calcul, validation).
- **Sentinelles `SKILLIFY_STUB` résiduelles = skill cassé**. Le check les détecte et bloque le `ok: true`. Ne pas committer un skill avec des stubs.
- **Description du frontmatter < 30 chars = skill mal discriminé**. Claude Code dispatche les skills par leur description ; trop courte = collision avec d'autres skills.
- **Un skill par cas concret**, pas un skill fourre-tout. Si tu hésites entre 2 skills, c'est qu'il y en a 2 qui se cachent — découper.
- **Provenance omise = pool aveugle**. Incident 2026-09-14 : 4 skills skillifiés (juin-août 2026) sans `source_subjects` ni backlink → le subject socle croyait `/skillify` mort (« 0 skillify livré » dans son MEMORY). Toujours passer `--source-subjects` quand le workflow vient d'un subject ; l'omission volontaire se justifie en Phase 1.
- **Doctrine Rubee** : un skill ne doit jamais embarquer une clé API Anthropic ni `from anthropic import Anthropic`. Si le skill a besoin d'invoquer Claude pour un sub-task, utiliser le Task tool ou le SDK Claude Agent (cf. `feedback_jamais_cle_api_toujours_max_via_sdk.md`).

## Critères d'évaluation

- **EVAL 1** : Le skill créé a-t-il une description ≥30 chars qui discrimine vs les skills voisins ? (Pass si `forge skillify check` retourne `description_long_enough: true` / Fail sinon)
- **EVAL 2** : Toutes les sentinelles `SKILLIFY_STUB` ont-elles été remplacées par du contenu métier réel ? (Pass si check retourne `no_residual_stubs: true` / Fail sinon)
- **EVAL 3** : Le skill a-t-il été testé en conditions réelles ≥1 fois et le résultat est-il satisfaisant ? (Pass si Benjamin a confirmé le résultat sur un cas concret post-création / Fail si scaffolding seul sans validation)
- **EVAL 4** : Le script Python (si présent) reste-t-il stdlib only et ne fait-il que du déterministe (pas de LLM call inline) ? (Pass / Fail)
- **EVAL 5** : Le skill a-t-il été décidé suite à un workflow ad hoc effectivement répété ≥2 fois (pas hypothétique) ? (Pass si Benjamin peut citer ≥2 occurrences passées / Fail si skill spéculatif)
- **EVAL 6** : La provenance est-elle posée (D10) ? (Pass si `source_subjects` non vide dans le SKILL.md ET les `linked_skills` des subjects d'origine mis à jour, OU omission explicitement justifiée en Phase 1 / Fail si oubliée)
