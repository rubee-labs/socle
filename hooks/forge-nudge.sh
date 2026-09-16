#!/usr/bin/env bash
# forge-nudge.sh — SessionStart hook (mode nudge) du plugin socle.
#
# Suggère `/forge-init` UNE SEULE FOIS : si un pool subjects/ existe dans le repo
# mais qu'aucun .forge.yaml n'est configuré. Ne fait que SUGGÉRER — n'écrit jamais
# de fichier, ne lance jamais forge init. Le .forge.yaml (une fois créé) est le
# marqueur « déjà configuré » → le nudge se tait pour toujours.
#
# Garanties :
#   - CE (legacy, possède entreprise/) → silencieux, jamais touché.
#   - Repo déjà configuré (un .forge.yaml quelque part) → silencieux.
#   - Repo sans pool subjects/ → silencieux.
#   - Repo multi-pool (benjamin-perso : .forge.yaml dans jean-claude-code/) →
#     silencieux, car on cherche le .forge.yaml partout sous la racine.

set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

_found() {
  # _found <find-expr...> : vrai si find renvoie au moins un résultat.
  find "$ROOT" -maxdepth 3 \
    -not -path '*/node_modules/*' -not -path '*/.git/*' \
    -not -path '*/.venv/*' -not -path '*/__pycache__/*' \
    "$@" 2>/dev/null | head -1 | grep -q .
}

# 1. Déjà configuré quelque part dans le repo ? → silence.
_found -name '.forge.yaml' && exit 0

# 2. CE / hôte legacy (possède entreprise/) → silence.
[ -d "$ROOT/entreprise" ] && exit 0

# 3. Un pool subjects/ existe-t-il (non configuré) ? → nudge.
if _found -type d -name 'subjects'; then
  echo "socle : un pool subjects/ existe ici mais n'est pas configuré — lance /forge-init pour choisir où stocker (écrit un .forge.yaml)."
fi

exit 0
