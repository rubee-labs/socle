---
date: 2026-04-29
sujet: Intégration de Forge au bloc Health-check unifié (correction post-Phase 0)
statut: aboutie
decision: 2026-04-29-fix-integration-healthcheck
---

# Discussion — Intégration Forge au Health-check

## Contexte

Au démarrage d'une nouvelle session après Phase 0, Benjamin remarque qu'il ne voit pas la ligne "Forge: OK" attendue. Le scanner forge tourne bien (visible dans les hook outputs séparés), mais sa sortie n'apparaît pas dans le **bloc Health-check unifié** qui agrège Git/Memory/Feedback.

Cause racine : mon installation initiale avait branché `forge_scanner.py` comme un **hook SessionStart séparé** dans `.claude/settings.json` (repo CE), alors que le bloc Health-check est produit par un script global `~/.claude/scripts/init-healthcheck.sh` (HOME, pas dans le repo CE). Les deux flux ne se croisent pas.

## Cheminement

### Investigation

1. Recherche du script qui produit "Health-check: ALERTES DÉTECTÉES" — non trouvé dans le repo CE
2. Trouvé dans `~/.claude/scripts/init-healthcheck.sh` (script global, hors repo)
3. Lecture : agrège Git + Prospection DB + Structure + Knowledge Coordinator + Feedback + Tool miss dans un tableau RESULTS, puis affiche encadré

### Solution

3 modifications coordonnées :

1. **`forge_scanner.py`** : retirer l'indentation initiale `"  "` des lignes de sortie. C'est `init-healthcheck.sh` qui ajoute `"  $r"` à chaque entrée de RESULTS.

2. **`~/.claude/scripts/init-healthcheck.sh`** : nouvelle section "Forge Scanner" entre Knowledge Coordinator et Feedback :
   ```bash
   FORGE_SCRIPT="$PROJECT_DIR/entreprise/config/feedback-loop/forge_scanner.py"
   if [ -f "$FORGE_SCRIPT" ]; then
     FORGE_OUTPUT=$(python3 "$FORGE_SCRIPT" 2>&1 || echo "Forge: erreur script")
     RESULTS+=("$FORGE_OUTPUT")
     if echo "$FORGE_OUTPUT" | grep -q "alerte(s)"; then
       HAS_ISSUE=true
     fi
   fi
   ```

3. **`.claude/settings.json` (CE)** : retirer la commande SessionStart séparée de forge_scanner.py (sinon double exécution).

### Validation

`bash ~/.claude/scripts/init-healthcheck.sh` affiche maintenant :

```
─────────────────────────────────
Health-check: ALERTES DÉTECTÉES
  Git: ...
  Prospection DB: OK (1979 leads)
  Structure: 71 erreur(s) ...
  Memory: 8 alerte(s) ...
  Forge: OK (0 subjects, 0 alerte)        ← NOUVEAU, intégré
  Feedback: 751 sessions analysées
─────────────────────────────────
```

## Conclusion (gotcha #5 ajouté)

Découverte d'un gotcha non détecté lors du test Phase 0 : tout nouveau scanner spécifique-CE qui doit apparaître dans le bloc Health-check doit être **enregistré dans `~/.claude/scripts/init-healthcheck.sh`**, pas en hook isolé dans `.claude/settings.json` du repo CE. Cette règle est à conserver pour les futures extensions du subject pool (par exemple, à terme, un scanner de doctrines obsolètes ou de stress-tests stagnants).

Le fichier `init-healthcheck.sh` étant hors repo (vit dans `~/.claude/`), sa modification n'est pas trackée par git. À noter dans la doctrine du projet.

## Décision

Voir `decisions/2026-04-29-fix-integration-healthcheck.yaml`.
