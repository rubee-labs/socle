#!/usr/bin/env bash
# Smoke test : invoque chaque commande de documente_engine.py et vérifie
# que la sortie est un JSON valide avec champs ok et version.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
ENGINE="$ROOT/entreprise/config/feedback-loop/documente_engine.py"

assert_json() {
  local name="$1"
  local output="$2"
  if ! echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'ok' in d and 'version' in d, 'missing keys'" 2>/dev/null; then
    echo "FAIL $name : sortie non-JSON ou champs manquants"
    echo "  output: $output"
    exit 1
  fi
  echo "OK   $name"
}

assert_json "list-subjects" "$(python3 "$ENGINE" list-subjects 2>&1)"
assert_json "prepare(/tmp)" "$(python3 "$ENGINE" prepare /tmp 2>&1)"
assert_json "infer-type(/tmp)" "$(python3 "$ENGINE" infer-type /tmp 2>&1)"
assert_json "patch-frontmatter(/tmp)" "$(python3 "$ENGINE" patch-frontmatter /tmp --patch '{}' 2>&1)"
assert_json "commit-atomic" "$(python3 "$ENGINE" commit-atomic --paths /tmp --message x 2>&1)"
assert_json "scan-impacted(/tmp)" "$(python3 "$ENGINE" scan-impacted /tmp 2>&1)"
assert_json "check-coherence(/tmp)" "$(python3 "$ENGINE" check-coherence /tmp --decision-yaml '{}' 2>&1)"

echo ""
echo "Smoke OK : toutes les commandes retournent un JSON parsable."
