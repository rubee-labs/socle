#!/usr/bin/env python3
"""
forge_scanner.py — Scanner du Subject Pool (forge γ)

Scanne tous les MEMORY.md du repo qui portent un frontmatter de subject (avec
forging_state), détecte les alertes du cycle de vie γ et régénère
entreprise/SUBJECTS-INDEX.md.

Alertes détectées :
- stagnation : forging_state in {seed, debating, tentative} depuis >30j sans
  nouveau last_event
- doctrine non compilée : forging_state == doctrine && conviction >= 80 &&
  compiled_artifacts vide
- stress test manquant : forging_state == tentative && conviction >= 60 sans
  stress_tests passé
- merger candidat : 2 subjects avec >70% overlap des linked_subjects et types
  compatibles

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
    parse_frontmatter,
    parse_inline_dict,
    parse_inline_list,
    parse_simple_yaml,
    parse_value,
)

PROJECT_DIR = get_project_dir()
INDEX_FILE = PROJECT_DIR / "entreprise" / "SUBJECTS-INDEX.md"
METRICS_FILE = PROJECT_DIR / "entreprise" / "SUBJECT-POOL-METRICS.md"
EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude", "templates"}

STAGNATION_DAYS = 30
DOCTRINE_CONVICTION_THRESHOLD = 80
TENTATIVE_CONVICTION_THRESHOLD = 60
MERGER_OVERLAP_THRESHOLD = 0.70


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
        forging_state = fm.get("forging_state")
        conviction = fm.get("conviction", 0) or 0
        compiled_artifacts = fm.get("compiled_artifacts") or []
        stress_tests_passed = fm.get("stress_tests_passed", 0) or 0

        # Alerte stagnation
        if forging_state in ("seed", "debating", "tentative"):
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
                    "detail": f"{forging_state} depuis {days}j",
                })

        # Alerte doctrine non compilée
        if forging_state == "doctrine" and conviction >= DOCTRINE_CONVICTION_THRESHOLD:
            if not compiled_artifacts:
                alerts.append({
                    "type": "doctrine_uncompiled",
                    "subject": str(rel_path),
                    "detail": f"conviction {conviction}, aucun artefact compilé",
                })

        # Alerte stress test manquant
        if forging_state == "tentative" and conviction >= TENTATIVE_CONVICTION_THRESHOLD:
            if stress_tests_passed == 0:
                alerts.append({
                    "type": "stress_test_missing",
                    "subject": str(rel_path),
                    "detail": f"conviction {conviction} sans stress test",
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
    compiled_30d = 0
    compiled_artifacts_recent = []
    doctrines_uncompiled = 0

    for path, fm in subjects:
        state = fm.get("forging_state", "unknown")
        by_state[state] += 1

        stype = fm.get("type", "unknown")
        by_type[stype] += 1

        # domain = premier segment du chemin relatif
        try:
            rel = path.relative_to(PROJECT_DIR)
            parts = rel.parts
            if len(parts) > 0:
                domain = parts[0]
                if len(parts) > 1 and parts[0] in ("services", "humains", "entreprise"):
                    domain = "/".join(parts[:2])
                by_domain[domain] += 1
        except ValueError:
            pass

        # Stagnation
        if state in ("seed", "debating", "tentative"):
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
                    "days": days,
                    "path": str(rel.parent),
                })

        # Artefacts compilés sur 30 jours
        artifacts = fm.get("compiled_artifacts") or []
        for a in artifacts:
            if isinstance(a, dict):
                compiled_at = a.get("compiled_at")
                days = days_since(compiled_at)
                if days is not None and days <= 30:
                    compiled_30d += 1
                    compiled_artifacts_recent.append({
                        "subject": fm.get("name") or path.parent.name,
                        "type": a.get("type", "?"),
                        "compiled_at": compiled_at,
                        "artifact": a.get("artifact", "?"),
                    })

        # Doctrines non compilées
        conviction = fm.get("conviction", 0) or 0
        if state == "doctrine" and conviction >= 80 and not artifacts:
            doctrines_uncompiled += 1

    active = total - by_state.get("archived", 0)
    in_service = by_state.get("in_service", 0)
    doctrine_state = by_state.get("doctrine", 0)
    denom_compilation = in_service + doctrine_state
    compilation_rate = (in_service / denom_compilation * 100) if denom_compilation > 0 else None

    return {
        "total": total,
        "active": active,
        "by_state": dict(by_state),
        "by_type": dict(by_type),
        "by_domain": dict(by_domain),
        "stagnant": stagnant,
        "stagnant_subjects": stagnant_subjects,
        "compiled_30d": compiled_30d,
        "compiled_artifacts_recent": compiled_artifacts_recent,
        "compilation_rate": compilation_rate,
        "doctrines_uncompiled": doctrines_uncompiled,
    }


def regenerate_metrics(m):
    """Régénère entreprise/SUBJECT-POOL-METRICS.md (Tier 1)."""
    state_order = [
        "seed", "debating", "tentative", "stress_testing",
        "doctrine", "in_service", "under_review", "archived",
    ]

    rate_str = f"{m['compilation_rate']:.0f}%" if m["compilation_rate"] is not None else "n/a"

    lines = [
        "# SUBJECT-POOL-METRICS",
        "",
        f"_Régénéré automatiquement par forge_scanner.py — {datetime.now().isoformat(timespec='seconds')}_",
        "",
        "## Tier 1 — Santé de base",
        "",
        f"- **Volume actif** : {m['active']} subjects (sur {m['total']} total, dont {m['by_state'].get('archived', 0)} archivés)",
        f"- **Subjects en stagnation** : {m['stagnant']} (>{30}j sans event en seed/debating/tentative)",
        f"- **Artefacts compilés (30j)** : {m['compiled_30d']}",
        f"- **Taux de compilation** : {rate_str}  _(in_service / (in_service + doctrine non compilées))_",
        f"- **Doctrines non compilées** : {m['doctrines_uncompiled']}",
        "",
        "## Distribution par état",
        "",
        "| État | Nombre |",
        "|---|---|",
    ]
    for state in state_order:
        count = m["by_state"].get(state, 0)
        if count or state in ("seed", "debating", "tentative", "doctrine", "in_service"):
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

    if m["compiled_artifacts_recent"]:
        lines.append("## Artefacts compilés (30 derniers jours)")
        lines.append("")
        for a in sorted(m["compiled_artifacts_recent"], key=lambda x: x["compiled_at"] or "", reverse=True):
            lines.append(f"- {a['compiled_at']} — **{a['subject']}** : {a['type']} → `{a['artifact']}`")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("_Pour la doctrine complète : `entreprise/config/rules/subject-pool.md`_")

    METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    METRICS_FILE.write_text("\n".join(lines), encoding="utf-8")


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
        state = fm.get("forging_state", "unknown")
        by_state.setdefault(state, []).append((path, fm))

    state_order = [
        "seed", "debating", "tentative", "stress_testing",
        "doctrine", "in_service", "under_review", "archived",
    ]

    for state in state_order:
        if state not in by_state:
            continue
        items = by_state[state]
        lines.append(f"## {state} ({len(items)})")
        lines.append("")
        for path, fm in sorted(items, key=lambda x: str(x[0])):
            name = fm.get("name") or path.parent.name
            stype = fm.get("type", "?")
            conv = fm.get("conviction", 0) or 0
            rel = path.parent.relative_to(PROJECT_DIR)
            links = fm.get("linked_subjects") or []
            link_preview = ", ".join(str(l) for l in links[:3])
            if len(links) > 3:
                link_preview += f" (+{len(links) - 3})"
            lines.append(f"- **{name}** ({stype}, conv {conv}) — `{rel}/`")
            if link_preview:
                lines.append(f"  - liens : {link_preview}")
        lines.append("")

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text("\n".join(lines), encoding="utf-8")


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

    # Résumé KPIs Tier 1 pour la ligne Health-check
    rate_str = f"{metrics['compilation_rate']:.0f}%" if metrics["compilation_rate"] is not None else "n/a"
    summary = f"{metrics['active']} actifs, {metrics['stagnant']} stagnants, {metrics['compiled_30d']} compilés/30j, taux {rate_str}"

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
