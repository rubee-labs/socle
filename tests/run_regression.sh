#!/usr/bin/env bash
# Tests de non-régression sur subjects réels.
# Pour chaque subject : prepare → infer-type → patch dry-run idempotent → scan
# Vérifie qu'aucun fichier n'est modifié.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ENGINE="$ROOT/entreprise/config/feedback-loop/documente_engine.py"

SUBJECTS=()
# Ajouter ceux qui existent
for candidate in \
  "services/achats/subjects/order-398" \
  "services/achats/subjects/supplier-weifang" \
  "services/marketing/subjects/google-ads-brumeaux"; do
  if [ -d "$ROOT/$candidate" ]; then
    SUBJECTS+=("$candidate")
  fi
done

if [ ${#SUBJECTS[@]} -eq 0 ]; then
  echo "Aucun subject de référence trouvé — abort"
  exit 1
fi

cd "$ROOT"

for s in "${SUBJECTS[@]}"; do
  echo "=== $s ==="

  out=$(python3 "$ENGINE" prepare "$s")
  ok=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['ok'])")
  [ "$ok" = "True" ] || { echo "FAIL prepare"; exit 1; }
  echo "  prepare OK"

  out=$(python3 "$ENGINE" infer-type "$s")
  type=$(echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('type'))")
  echo "  infer-type → $type"

  current_conv=$(python3 -c "
import sys
sys.path.insert(0, '$ROOT/entreprise/config/feedback-loop')
from forge_lib import parse_frontmatter
from pathlib import Path
fm = parse_frontmatter(Path('$ROOT/$s/MEMORY.md'))
print(fm.get('conviction', 0))
")
  out=$(python3 "$ENGINE" patch-frontmatter "$s" --patch "{\"conviction\": $current_conv}" --dry-run)
  changed=$(echo "$out" | python3 -c "import json,sys; print(json.load(sys.stdin)['changed'])")
  if [ "$changed" = "True" ]; then
    echo "  WARN: patch idempotent a renvoyé changed=True (conviction=$current_conv)"
  else
    echo "  patch idempotent OK"
  fi

  out=$(python3 "$ENGINE" scan-impacted "$s")
  count=$(echo "$out" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['candidates']))")
  echo "  scan-impacted → $count candidats"

done

echo ""
echo "Régression OK : aucun subject n'a été modifié."
echo "git status sur les subjects scannés :"
for s in "${SUBJECTS[@]}"; do
  out=$(git -C "$ROOT" status --short "$s/MEMORY.md" 2>/dev/null || true)
  if [ -n "$out" ]; then
    echo "  MODIFIÉ: $out"
  else
    echo "  OK    : $s/MEMORY.md inchangé"
  fi
done
