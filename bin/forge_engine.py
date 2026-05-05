#!/usr/bin/env python3
"""
forge_engine.py — Couche 1 du moteur /documente (re-synthese continue).

Lit un subject (MEMORY.md + sous-dossiers events/ analyses/ discussions/
decisions/), extrait les donnees structurees, calcule les stats agregees,
recalcule last_event, detecte les conditions de transition gamma. Cascade
vers les linked_subjects sur 1 niveau strict.

NE TOUCHE PAS aux fichiers — retourne un plan d'ecritures (JSON) que
/documente applique via Edit cote Claude.

Usage CLI :
  python3 forge_engine.py <subject_path> [--no-cascade]

Imprime le JSON sur stdout. Permet a Claude d'invoquer via Bash.

Cycle de vie gamma — table de transitions auto (cf. subject-pool.md) :
  seed       -> debating   : len(events) >= 1 OR len(open_discussions) >= 1
  debating   -> tentative  : len(active_decisions) >= 1  (+ bump conviction a 50)
  tentative  -> stress_testing : NON-AUTO (lance /stress-test)
  stress_testing -> doctrine   : NON-AUTO (atteint via /stress-test)
  doctrine   -> in_service     : NON-AUTO (lance /compile-doctrine)
  in_service -> under_review   : NON-AUTO (signal humain)
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

from forge_lib import (
    days_since,
    get_project_dir,
    parse_frontmatter,
    parse_value,
)

PROJECT_DIR = get_project_dir()


# -------------------------------------------------------------------- helpers


def _list_md_files(path: Path):
    """Liste les *.md d'un dossier, tries par nom (qui commence par YYYY-MM-DD)."""
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir() if p.is_file() and p.suffix == ".md")


def _list_decision_files(path: Path):
    """Liste les *.yaml et *.md d'un dossier decisions/."""
    if not path.is_dir():
        return []
    return sorted(
        p for p in path.iterdir()
        if p.is_file() and p.suffix in (".yaml", ".yml", ".md")
    )


def _read_first_content_line(file_path: Path, max_chars: int = 200) -> str:
    """Lit la 1ere ligne non-frontmatter, non-vide, non-titre d'un fichier markdown.

    Pour fournir un resume compact dans events_summary.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    # Skip frontmatter
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end > 0:
            content = content[end + 4:]
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped[:max_chars]
    return ""


def _entry_date_from_filename(filename: str) -> str | None:
    """Extrait YYYY-MM-DD du debut d'un nom de fichier."""
    match = re.match(r"(\d{4}-\d{2}-\d{2})", filename)
    return match.group(1) if match else None


def _summarize_event_file(file_path: Path) -> dict:
    """Construit l'entree events_summary pour un fichier event."""
    fm = parse_frontmatter(file_path) or {}
    date = fm.get("date") or _entry_date_from_filename(file_path.name)
    if date:
        date = str(date)[:10]
    return {
        "date": date,
        "type": fm.get("type"),
        "filename": file_path.name,
        "first_line": _read_first_content_line(file_path),
    }


def _summarize_decision_file(file_path: Path) -> dict:
    """Construit l'entree decisions_summary pour un fichier decision."""
    fm = parse_frontmatter(file_path) or {}
    date = fm.get("date") or _entry_date_from_filename(file_path.name)
    if date:
        date = str(date)[:10]
    return {
        "date": date,
        "filename": file_path.name,
        "status": fm.get("status", "active"),
        "decided_by": fm.get("decided_by"),
        "first_line": _read_first_content_line(file_path),
    }


def _summarize_discussion_file(file_path: Path) -> dict:
    """Construit l'entree discussions_summary pour un fichier discussion."""
    fm = parse_frontmatter(file_path) or {}
    date = fm.get("date") or _entry_date_from_filename(file_path.name)
    if date:
        date = str(date)[:10]
    return {
        "date": date,
        "filename": file_path.name,
        "status": fm.get("status", "open"),
        "sujet": fm.get("sujet") or fm.get("subject"),
        "first_line": _read_first_content_line(file_path),
    }


def _parse_amount_to_usd(value) -> float | None:
    """Parse un montant tolerant : '16943.00 USD' -> 16943.0. None si non parseable."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    match = re.search(r"-?\d+(?:[.,]\d+)?", value)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def _parse_inline_record(value):
    """Parse une entree linked_records de la forme '{type: foo, value: bar, source: baz}'.

    parse_simple_yaml retourne ces lignes comme strings ; on les desaccouple ici
    de facon tolerante (sans full YAML).
    """
    if isinstance(value, dict):
        # Deja parse (ou wrapper {"_inline": "..."} de parse_inline_dict)
        if "_inline" in value and len(value) == 1:
            return _parse_inline_record(value["_inline"])
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    inner = s[1:-1]
    result = {}
    # Split tolerant : on respecte les guillemets
    parts = []
    depth = 0
    quote = None
    buf = []
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
            buf.append(ch)
            continue
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf))

    for part in parts:
        if ":" not in part:
            continue
        k, _, v = part.partition(":")
        result[k.strip()] = parse_value(v.strip())
    return result or None


def _normalize_linked_records(linked_records):
    """Applique _parse_inline_record a chaque entree, ignore les non-parseable."""
    if not linked_records:
        return []
    normalized = []
    for rec in linked_records:
        parsed = _parse_inline_record(rec)
        if parsed is not None:
            normalized.append(parsed)
    return normalized


# ------------------------------------------------------ resolution des liens


def _candidate_subject_roots() -> list[Path]:
    """Liste les racines ou chercher des subjects/."""
    roots = []
    for top in ("services", "entreprise", "humains"):
        top_path = PROJECT_DIR / top
        if not top_path.is_dir():
            continue
        # services/<X>/subjects/, entreprise/subjects/, humains/<nom>/subjects/
        if (top_path / "subjects").is_dir():
            roots.append(top_path / "subjects")
        for child in top_path.iterdir():
            if not child.is_dir() or child.name.startswith("."):
                continue
            sub = child / "subjects"
            if sub.is_dir():
                roots.append(sub)
    return roots


def resolve_link(link: str, current_subject_path: Path) -> Path | None:
    """Resout un linked_subject vers le path absolu de son MEMORY.md.

    Heuristique, premiere qui matche gagne :
      1. slug exact -> <base>/<slug>/MEMORY.md
      2. <type>:<name> -> <base>/<type>-<name>/MEMORY.md
      3. <type>:<name> -> <base>/<name>/MEMORY.md (verif type: dans frontmatter)
      4. grep "^name: <name>" dans tous les MEMORY.md des roots
      5. None
    """
    if not isinstance(link, str) or not link.strip():
        return None
    link = link.strip()

    # 1. Chercher d'abord dans le meme parent que le subject courant (mode rapide)
    same_parent = current_subject_path.parent
    candidate = same_parent / link / "MEMORY.md"
    if candidate.is_file():
        return candidate

    # 2. Format <type>:<name>
    if ":" in link:
        type_part, _, name_part = link.partition(":")
        type_part = type_part.strip()
        name_part = name_part.strip()
        candidate = same_parent / f"{type_part}-{name_part}" / "MEMORY.md"
        if candidate.is_file():
            return candidate
        candidate = same_parent / name_part / "MEMORY.md"
        if candidate.is_file():
            fm = parse_frontmatter(candidate) or {}
            if fm.get("type") == type_part:
                return candidate

    # 3. Chercher dans toutes les racines connues
    roots = _candidate_subject_roots()
    for root in roots:
        # 3a. slug direct
        candidate = root / link / "MEMORY.md"
        if candidate.is_file():
            return candidate
        # 3b. <type>-<name>
        if ":" in link:
            type_part, _, name_part = link.partition(":")
            candidate = root / f"{type_part.strip()}-{name_part.strip()}" / "MEMORY.md"
            if candidate.is_file():
                return candidate
            candidate = root / name_part.strip() / "MEMORY.md"
            if candidate.is_file():
                fm = parse_frontmatter(candidate) or {}
                if fm.get("type") == type_part.strip():
                    return candidate

    # 4. grep par name dans tous les MEMORY.md des roots
    target_name = link.partition(":")[2].strip() if ":" in link else link
    for root in roots:
        if not root.is_dir():
            continue
        for memory in root.glob("*/MEMORY.md"):
            fm = parse_frontmatter(memory) or {}
            if fm.get("name") == target_name:
                return memory

    return None


# ------------------------------------------------------- detection transition


def detect_transition(
    forging_state: str,
    events_count: int,
    open_discussions_count: int,
    active_decisions_count: int,
    current_conviction: int,
) -> dict | None:
    """Retourne le dict transition_proposal selon la table Cycle de vie gamma.

    Couche 1 ne propose QUE la transition immediate a partir de l'etat actuel.
    La couche 2 (Claude) chaine seed->debating->tentative en re-invoquant
    forge_engine.py apres application.
    """
    if forging_state == "seed":
        if events_count >= 1 or open_discussions_count >= 1:
            return {
                "from": "seed",
                "to": "debating",
                "auto": True,
                "conviction_bump": None,
                "hint": None,
            }
        return None
    if forging_state == "debating":
        if active_decisions_count >= 1:
            bump = 50 if current_conviction < 50 else None
            return {
                "from": "debating",
                "to": "tentative",
                "auto": True,
                "conviction_bump": bump,
                "hint": None,
            }
        return None
    if forging_state == "tentative":
        return {
            "from": "tentative",
            "to": "stress_testing",
            "auto": False,
            "conviction_bump": None,
            "hint": "lance /stress-test pour confronter cette opinion",
        }
    if forging_state == "stress_testing":
        return {
            "from": "stress_testing",
            "to": "doctrine",
            "auto": False,
            "conviction_bump": None,
            "hint": "atteint via /stress-test (conviction >= 60 + survived: true)",
        }
    if forging_state == "doctrine":
        return {
            "from": "doctrine",
            "to": "in_service",
            "auto": False,
            "conviction_bump": None,
            "hint": "lance /compile-doctrine pour produire l'artefact executable",
        }
    if forging_state == "in_service":
        return {
            "from": "in_service",
            "to": "under_review",
            "auto": False,
            "conviction_bump": None,
            "hint": "manuel : declencher si contre-signal detecte",
        }
    return None


# -------------------------------------------------------- stats par type


def _light_read_subject(memory_path: Path) -> dict:
    """Lecture minimale d'un MEMORY.md : frontmatter uniquement, pas de cascade,
    pas de scan des sous-dossiers. Pour supplier stats sans recursion."""
    fm = parse_frontmatter(memory_path) or {}
    return {
        "name": fm.get("name"),
        "type": fm.get("type"),
        "current_state": fm.get("forging_state"),
        "current_conviction": fm.get("conviction"),
        "horizon": fm.get("horizon"),
        "created_at": str(fm.get("created_at"))[:10] if fm.get("created_at") else None,
        "linked_records": _normalize_linked_records(fm.get("linked_records") or []),
    }


def _supplier_stats_from_links(subject_path: Path, fm: dict) -> dict:
    """Calcule les stats supplier en lisant directement les linked_subjects
    du frontmatter, sans recursion. Utilisable en cascade=False mode."""
    linked = fm.get("linked_subjects") or []
    if not isinstance(linked, list):
        linked = []
    supplier_orders = []
    for link in linked:
        if not isinstance(link, str) or not link.strip():
            continue
        # Filtrer aux supplier-orders
        if link.startswith("supplier-order:") or link.startswith("supplier-order-"):
            target = resolve_link(link, subject_path)
            if target is None:
                continue
            light = _light_read_subject(target)
            if light.get("type") == "supplier-order":
                supplier_orders.append(light)
    active = [c for c in supplier_orders if c.get("current_state") not in ("archived",)]
    amounts = []
    last_order_dates = []
    for c in supplier_orders:
        for rec in c.get("linked_records") or []:
            if isinstance(rec, dict) and rec.get("type") == "order_amount":
                amount = _parse_amount_to_usd(rec.get("value"))
                if amount is not None:
                    amounts.append(amount)
        if c.get("created_at"):
            last_order_dates.append(c["created_at"])
    return {
        "total_orders": len(supplier_orders),
        "active_orders": len(active),
        "total_amount_usd": sum(amounts) if amounts else 0.0,
        "last_order_date": max(last_order_dates) if last_order_dates else None,
    }


def aggregate_stats(
    subject_path: Path,
    fm: dict,
    subject_type: str | None,
    events_summary: list,
    discussions_summary: list,
    decisions_summary: list,
    last_event: dict | None,
) -> dict:
    """Calcule les stats agregees specifiques au type. Phase 0 : support
    minimal pour supplier-order, supplier ; generique pour le reste."""
    stats = {
        "events_count": len(events_summary),
        "discussions_count": len(discussions_summary),
        "decisions_count": len(decisions_summary),
        "last_event_at": last_event.get("date") if last_event else None,
        "days_since_last_event": days_since(last_event.get("date") if last_event else None),
    }

    if subject_type == "supplier":
        stats.update(_supplier_stats_from_links(subject_path, fm))

    return stats


# ----------------------------------------------------- moteur principal


def forge_subject(subject_path: Path, cascade: bool = True) -> dict:
    """Re-synthetise un subject (couche 1 deterministe).

    NE TOUCHE PAS aux fichiers. Retourne un dict serialisable JSON.
    """
    warnings: list[str] = []
    subject_path = subject_path.resolve()
    memory_path = subject_path / "MEMORY.md"
    if not memory_path.is_file():
        return {
            "error": f"MEMORY.md not found at {memory_path}",
            "subject_path": str(subject_path),
        }

    fm = parse_frontmatter(memory_path) or {}

    # Sous-fichiers
    events = [_summarize_event_file(p) for p in _list_md_files(subject_path / "events")]
    events.sort(key=lambda e: (e["date"] or "", e["filename"]), reverse=True)

    discussions = [
        _summarize_discussion_file(p)
        for p in _list_md_files(subject_path / "discussions")
    ]
    open_discussions = [d for d in discussions if d["status"] == "open"]

    decisions = [
        _summarize_decision_file(p)
        for p in _list_decision_files(subject_path / "decisions")
    ]
    active_decisions = [d for d in decisions if d["status"] == "active"]

    # last_event recalcule
    last_event = None
    if events:
        first = events[0]
        last_event = {
            "date": first["date"],
            "type": first["type"],
            "ref": f"events/{first['filename']}",
        }
    elif fm.get("last_event"):
        # Preserver l'existant si pas de fichier event
        existing = fm["last_event"]
        if isinstance(existing, dict):
            last_event = {
                "date": str(existing.get("date"))[:10] if existing.get("date") else None,
                "type": existing.get("type"),
                "ref": existing.get("ref"),
            }

    # Cascade horizontale (1 niveau strict)
    cascade_results: list = []
    if cascade:
        linked_subjects = fm.get("linked_subjects") or []
        if not isinstance(linked_subjects, list):
            linked_subjects = []
        for link in linked_subjects:
            if not isinstance(link, str) or not link.strip():
                continue
            link_memory = resolve_link(link, subject_path)
            if link_memory is None:
                warnings.append(f"linked_subject non resolu : {link!r}")
                continue
            link_subject_path = link_memory.parent
            sub_result = forge_subject(link_subject_path, cascade=False)
            if "error" in sub_result:
                warnings.append(
                    f"forge_subject failed on link {link!r} : {sub_result['error']}"
                )
                continue
            sub_result["link_raw"] = link
            cascade_results.append(sub_result)

    # Stats agregees
    stats = aggregate_stats(
        subject_path=subject_path,
        fm=fm,
        subject_type=fm.get("type"),
        events_summary=events,
        discussions_summary=discussions,
        decisions_summary=decisions,
        last_event=last_event,
    )

    # Detection transition gamma
    # On compte les active_decisions et open_discussions a la fois depuis le
    # frontmatter (qui peut referencer des fichiers externes) et depuis les
    # sous-dossiers (decisions/, discussions/). On prend le max pour ne pas
    # rater une transition quand la doctrine est trackee uniquement dans le
    # frontmatter.
    fm_active_decisions = fm.get("active_decisions") or []
    fm_open_discussions = fm.get("open_discussions") or []
    if not isinstance(fm_active_decisions, list):
        fm_active_decisions = []
    if not isinstance(fm_open_discussions, list):
        fm_open_discussions = []
    active_decisions_count = max(len(active_decisions), len(fm_active_decisions))
    open_discussions_count = max(len(open_discussions), len(fm_open_discussions))

    forging_state = fm.get("forging_state") or "seed"
    current_conviction = fm.get("conviction") or 0
    if not isinstance(current_conviction, int):
        try:
            current_conviction = int(current_conviction)
        except (TypeError, ValueError):
            current_conviction = 0
    transition = detect_transition(
        forging_state=forging_state,
        events_count=len(events),
        open_discussions_count=open_discussions_count,
        active_decisions_count=active_decisions_count,
        current_conviction=current_conviction,
    )

    return {
        "subject_path": str(subject_path.relative_to(PROJECT_DIR)) if subject_path.is_relative_to(PROJECT_DIR) else str(subject_path),
        "memory_path": str(memory_path.relative_to(PROJECT_DIR)) if memory_path.is_relative_to(PROJECT_DIR) else str(memory_path),
        "name": fm.get("name") or subject_path.name,
        "type": fm.get("type"),
        "current_state": forging_state,
        "current_conviction": current_conviction,
        "horizon": fm.get("horizon"),
        "created_at": str(fm.get("created_at"))[:10] if fm.get("created_at") else None,
        "linked_records": _normalize_linked_records(fm.get("linked_records") or []),
        "frontmatter_active_decisions": fm_active_decisions,
        "frontmatter_open_discussions": fm_open_discussions,
        "frontmatter_linked_subjects": fm.get("linked_subjects") or [],
        "stats": stats,
        "last_event": last_event,
        "transition_proposal": transition,
        "events_summary": events,
        "active_decisions_summary": active_decisions,
        "open_discussions_summary": open_discussions,
        "all_decisions_summary": decisions,
        "all_discussions_summary": discussions,
        "cascade": cascade_results,
        "warnings": warnings,
    }


# ------------------------------------------------------------ CLI


def main():
    parser = argparse.ArgumentParser(description="Couche 1 du moteur /documente.")
    parser.add_argument("subject_path", help="Chemin vers le dossier du subject (contient MEMORY.md)")
    parser.add_argument("--no-cascade", action="store_true", help="Desactive la cascade vers les linked_subjects")
    args = parser.parse_args()

    subject_path = Path(args.subject_path)
    if not subject_path.is_absolute():
        subject_path = (Path.cwd() / subject_path).resolve()

    result = forge_subject(subject_path, cascade=not args.no_cascade)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    if "error" in result:
        sys.exit(1)


if __name__ == "__main__":
    main()
