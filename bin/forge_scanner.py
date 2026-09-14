#!/usr/bin/env python3
"""
forge_scanner.py — Scanner du Subject Pool

Scanne tous les MEMORY.md du repo qui portent un frontmatter de subject (avec
forging_state), détecte les alertes opérationnelles et régénère
entreprise/SUBJECTS-INDEX.md.

Alertes détectées (refonte 2026-05-10, cycle 3 états) :
- stagnation : forging_state == actif depuis >30j sans nouveau last_event
- merger candidat : 2 subjects horizon=permanent avec >70% overlap des
  linked_subjects et types compatibles

Alertes supprimées (cycle γ historique abandonné) :
- doctrine_uncompiled (compile-doctrine abandonné, plus de seuil de conviction)
- stress_test_missing (/stress-test découplé du cycle, optionnel à la demande)

Usage :
  python3 forge_scanner.py              # Scan + affiche alertes au format Health-check
  python3 forge_scanner.py --status     # Compteur uniquement (usage automatique hook)
  python3 forge_scanner.py --index-only # Régénère uniquement SUBJECTS-INDEX.md

Intégré au hook SessionStart en complément de knowledge-coordinator.py.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from forge_lib import (
    days_since,
    get_project_dir,
    load_forge_config,
    parse_frontmatter,
    parse_inline_dict,
    parse_inline_list,
    parse_simple_yaml,
    parse_value,
)

PROJECT_DIR = get_project_dir()
# Emplacement de sortie + groupage de domaine pilotés par la config par-repo
# (.forge.yaml à la racine du pool), avec défauts auto-détectés. CE sans config
# retombe sur `entreprise/` ; un pool plat écrit à sa racine — jamais de dossier
# `entreprise/` fantôme. Cf. load_forge_config() dans forge_lib.py.
_CONFIG = load_forge_config(PROJECT_DIR)
_OUTPUT_DIR = _CONFIG["output_dir"]
_DOMAIN_ROOTS = set(_CONFIG["domain_roots"])
INDEX_FILE = _OUTPUT_DIR / "SUBJECTS-INDEX.md"
METRICS_FILE = _OUTPUT_DIR / "SUBJECT-POOL-METRICS.md"
EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude", "templates"}

STAGNATION_DAYS = 30
MERGER_OVERLAP_THRESHOLD = 0.70

# Mapping anciens cycles (8 puis 3 etats) -> cycle a 2 etats (2026-09-14).
# Cf. forge_engine.py.
LEGACY_STATE_MAP = {
    "seed": "actif", "debating": "actif", "tentative": "actif",
    "stress_testing": "actif", "doctrine": "actif",
    "in_service": "actif", "under_review": "actif", "mature": "actif",
    "archived": "archived",
    "actif": "actif",
}


def normalize_state(raw):
    return LEGACY_STATE_MAP.get(raw, "actif")


def find_subject_memory_files():
    """Trouve tous les MEMORY.md qui portent un frontmatter de subject.

    Exclut les fixtures de test et les dossiers archivés pour éviter
    de compter des subjects fictifs ou retirés du service actif.
    """
    subjects = []
    for root, dirs, files in os.walk(PROJECT_DIR):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDE_DIRS
            and not d.startswith(".")
            and not d.startswith("_archive")
            and d != "fixtures"
        ]
        for f in files:
            if f != "MEMORY.md":
                continue
            path = Path(root) / f
            frontmatter = parse_frontmatter(path)
            if frontmatter and "forging_state" in frontmatter:
                subjects.append((path, frontmatter))
    return subjects


def detect_alerts(subjects):
    """Détecte les alertes sur tous les subjects."""
    alerts = []

    for path, fm in subjects:
        rel_path = path.relative_to(PROJECT_DIR)
        state_raw = fm.get("forging_state")
        state = normalize_state(state_raw)

        # Alerte stagnation : subject `actif` depuis >30j sans last_event
        if state == "actif":
            last_event = fm.get("last_event")
            last_date = None
            if isinstance(last_event, dict):
                last_date = last_event.get("date")
            if not last_date:
                last_date = fm.get("created_at")
            days = days_since(last_date)
            if days is not None and days > STAGNATION_DAYS:
                alerts.append({
                    "type": "stagnation",
                    "subject": str(rel_path),
                    "detail": f"actif depuis {days}j (raw={state_raw})" if state_raw and state_raw != "actif" else f"actif depuis {days}j",
                })

    # Alerte merger candidate (overlap linked_subjects)
    # NOTE : restreint aux subjects `horizon: permanent` car les instances bornées
    # d'un même type partagent par construction les mêmes linked_subjects (toutes les
    # commandes Simon → [supplier-simon, product-line-guirlande-guinguette]).
    # Le merger ne concerne que les doublons accidentels d'entités persistantes.
    for i, (path_a, fm_a) in enumerate(subjects):
        if fm_a.get("horizon") != "permanent":
            continue
        type_a = fm_a.get("type")
        links_a = set(fm_a.get("linked_subjects") or [])
        if not links_a or fm_a.get("forging_state") == "archived":
            continue
        for path_b, fm_b in subjects[i + 1:]:
            if fm_b.get("horizon") != "permanent":
                continue
            if fm_b.get("type") != type_a:
                continue
            if fm_b.get("forging_state") == "archived":
                continue
            links_b = set(fm_b.get("linked_subjects") or [])
            if not links_b:
                continue
            overlap = len(links_a & links_b) / max(len(links_a | links_b), 1)
            if overlap >= MERGER_OVERLAP_THRESHOLD:
                rel_a = path_a.relative_to(PROJECT_DIR).parent.name
                rel_b = path_b.relative_to(PROJECT_DIR).parent.name
                alerts.append({
                    "type": "merger_candidate",
                    "subject": f"{rel_a} ↔ {rel_b}",
                    "detail": f"{int(overlap * 100)}% overlap",
                })

    return alerts


def compute_metrics(subjects):
    """Calcule les KPIs Tier 1 du Subject Pool."""
    total = len(subjects)
    by_state = Counter()
    by_type = Counter()
    by_domain = Counter()

    stagnant = 0
    stagnant_subjects = []

    for path, fm in subjects:
        state_raw = fm.get("forging_state", "unknown")
        state = normalize_state(state_raw)
        by_state[state] += 1

        stype = fm.get("type", "unknown")
        by_type[stype] += 1

        # domain = premier segment du chemin relatif
        try:
            rel = path.relative_to(PROJECT_DIR)
            parts = rel.parts
            if len(parts) > 0:
                domain = parts[0]
                if len(parts) > 1 and parts[0] in _DOMAIN_ROOTS:
                    domain = "/".join(parts[:2])
                by_domain[domain] += 1
        except ValueError:
            pass

        # Stagnation : subject `actif` sans event depuis >30j
        if state == "actif":
            last_event = fm.get("last_event")
            last_date = None
            if isinstance(last_event, dict):
                last_date = last_event.get("date")
            if not last_date:
                last_date = fm.get("created_at")
            days = days_since(last_date)
            if days is not None and days > 30:
                stagnant += 1
                rel = path.relative_to(PROJECT_DIR)
                stagnant_subjects.append({
                    "name": fm.get("name") or path.parent.name,
                    "state": state,
                    "state_raw": state_raw,
                    "days": days,
                    "path": str(rel.parent),
                })

    active = total - by_state.get("archived", 0)

    return {
        "total": total,
        "active": active,
        "by_state": dict(by_state),
        "by_type": dict(by_type),
        "by_domain": dict(by_domain),
        "stagnant": stagnant,
        "stagnant_subjects": stagnant_subjects,
    }


def _strip_timestamp_line(text):
    """Retire la ligne d'horodatage pour comparer deux rendus à contenu égal."""
    return "\n".join(l for l in text.split("\n") if not l.startswith("_Régénéré automatiquement"))


def write_if_changed(path, text):
    """Écrit `text` dans `path` seulement si le contenu (hors horodatage) change.

    Motif (2026-09-06) : le scanner tourne à chaque SessionStart et réécrivait
    les 2 index avec un nouvel horodatage → 90 % des commits « Session » du
    repo consommateur ne contenaient que ces 2 fichiers, et rafales de commits
    concurrents. Retourne True si écrit.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            old = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            old = None
        if old is not None and _strip_timestamp_line(old) == _strip_timestamp_line(text):
            return False
    path.write_text(text, encoding="utf-8")
    return True


def regenerate_metrics(m):
    """Régénère entreprise/SUBJECT-POOL-METRICS.md (refonte 2026-09-14, 2 états)."""
    state_order = ["actif", "archived"]

    lines = [
        "# SUBJECT-POOL-METRICS",
        "",
        f"_Régénéré automatiquement par forge_scanner.py — {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Santé de base",
        "",
        f"- **Volume actif** : {m['active']} subjects (sur {m['total']} total, dont {m['by_state'].get('archived', 0)} archivés)",
        f"- **Subjects en stagnation** : {m['stagnant']} (>{30}j sans event, état `actif`)",
        "",
        "## Distribution par état",
        "",
        "| État | Nombre |",
        "|---|---|",
    ]
    for state in state_order:
        count = m["by_state"].get(state, 0)
        lines.append(f"| `{state}` | {count} |")
    lines.append("")

    if m["by_type"]:
        lines.append("## Distribution par type")
        lines.append("")
        lines.append("| Type | Nombre |")
        lines.append("|---|---|")
        for stype, count in sorted(m["by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| `{stype}` | {count} |")
        lines.append("")

    if m["by_domain"]:
        lines.append("## Distribution par domaine")
        lines.append("")
        lines.append("| Domaine | Nombre |")
        lines.append("|---|---|")
        for domain, count in sorted(m["by_domain"].items(), key=lambda x: -x[1]):
            lines.append(f"| `{domain}` | {count} |")
        lines.append("")

    if m["stagnant_subjects"]:
        lines.append("## Subjects en stagnation")
        lines.append("")
        for s in sorted(m["stagnant_subjects"], key=lambda x: -x["days"]):
            lines.append(f"- **{s['name']}** ({s['state']}, {s['days']}j sans event) — `{s['path']}/`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Pour la doctrine complète : plugin `claude-forge` — `rules/subject-pool.md` (cache runtime : `~/.claude/plugins/cache/rubee-labs/claude-forge/<version>/rules/subject-pool.md`)._")

    write_if_changed(METRICS_FILE, "\n".join(lines))


def regenerate_index(subjects):
    """Régénère entreprise/SUBJECTS-INDEX.md."""
    lines = [
        "# SUBJECTS-INDEX",
        "",
        f"_Régénéré automatiquement par forge_scanner.py — {datetime.now().isoformat(timespec='seconds')}_",
        "",
        f"**{len(subjects)} subjects actifs**",
        "",
    ]

    by_state = {}
    for path, fm in subjects:
        state_raw = fm.get("forging_state", "unknown")
        state = normalize_state(state_raw)
        by_state.setdefault(state, []).append((path, fm))

    state_order = ["actif", "archived"]

    for state in state_order:
        if state not in by_state:
            continue
        items = by_state[state]
        lines.append(f"## {state} ({len(items)})")
        lines.append("")
        for path, fm in sorted(items, key=lambda x: str(x[0])):
            name = fm.get("name") or path.parent.name
            stype = fm.get("type", "?")
            rel = path.parent.relative_to(PROJECT_DIR)
            links = fm.get("linked_subjects") or []
            link_preview = ", ".join(str(l) for l in links[:3])
            if len(links) > 3:
                link_preview += f" (+{len(links) - 3})"
            lines.append(f"- **{name}** ({stype}) — `{rel}/`")
            if link_preview:
                lines.append(f"  - liens : {link_preview}")
        lines.append("")

    write_if_changed(INDEX_FILE, "\n".join(lines))


def format_alerts(alerts):
    """Format les alertes au style Health-check (sans indentation initiale, ajoutée par init-healthcheck.sh)."""
    if not alerts:
        return None
    lines = [f"Forge: {len(alerts)} alerte(s)"]
    for a in alerts[:10]:
        lines.append(f"  • {a['type']}: {a['subject']} ({a['detail']})")
    if len(alerts) > 10:
        lines.append(f"  • ... +{len(alerts) - 10} autres")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true", help="Compteur uniquement")
    parser.add_argument("--index-only", action="store_true", help="Régénère SUBJECTS-INDEX.md uniquement")
    parser.add_argument("--metrics-only", action="store_true", help="Régénère SUBJECT-POOL-METRICS.md uniquement")
    args = parser.parse_args()

    subjects = find_subject_memory_files()

    if args.index_only:
        regenerate_index(subjects)
        print(f"SUBJECTS-INDEX.md régénéré ({len(subjects)} subjects)")
        return

    if args.metrics_only:
        m = compute_metrics(subjects)
        regenerate_metrics(m)
        print(f"SUBJECT-POOL-METRICS.md régénéré ({len(subjects)} subjects)")
        return

    alerts = detect_alerts(subjects)
    metrics = compute_metrics(subjects)
    regenerate_index(subjects)
    regenerate_metrics(metrics)

    # Résumé KPIs pour la ligne Health-check (refonte 2026-09-14 : 2 états)
    by_state = metrics["by_state"]
    summary = (
        f"{by_state.get('actif', 0)} actifs, "
        f"{by_state.get('archived', 0)} archivés, "
        f"{metrics['stagnant']} stagnants"
    )

    if args.status:
        print(f"Forge: {len(alerts)} alerte(s) — {summary}")
        return

    output = format_alerts(alerts)
    if output:
        # Enrichit la 1ère ligne avec les KPIs
        lines = output.split("\n")
        lines[0] = f"{lines[0]} — {summary}"
        print("\n".join(lines))
    else:
        print(f"Forge: OK — {summary}")


if __name__ == "__main__":
    main()
