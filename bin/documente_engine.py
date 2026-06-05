#!/usr/bin/env python3
"""
documente_engine.py — Couche déterministe du skill /documente.

Frère de forge_engine.py. Extrait les phases mécaniques du skill
(infer-type, patch-frontmatter, scan, commit, etc.) pour économiser
des tokens LLM et éliminer le risque de corruption YAML.

Usage CLI :
  python3 documente_engine.py <command> [args]

Toutes les commandes retournent un JSON sur stdout au format :
  {"ok": true, "version": 1, ...}
ou
  {"ok": false, "version": 1, "error": "...", "code": "..."}

Exit code 0 toujours (sauf crash Python). Le skill teste `ok` du JSON.
"""

import argparse
import datetime as _dt
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from forge_lib import get_project_dir, load_forge_config, parse_frontmatter
from documente_lib import patch_frontmatter_file, parse_nested_dict_block

VERSION = 1

LOG_PATH = Path(__file__).resolve().parent / "documente_engine.log"


def _log_invocation(cmd, args_dict, duration_ms, ok, code=None):
    """Append-only log : 1 ligne JSON par invocation, pour mesurer perf."""
    try:
        entry = {
            "ts": _dt.datetime.now().isoformat(),
            "pid": os.getpid(),
            "cmd": cmd,
            "args": args_dict,
            "duration_ms": duration_ms,
            "ok": ok,
            "code": code,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def _ok(**payload):
    return {"ok": True, "version": VERSION, **payload}


def _err(message, code="generic_error", **extra):
    return {"ok": False, "version": VERSION, "error": message, "code": code, **extra}


def cmd_list_subjects(args):
    """Liste tous les subjects du repo (avec MEMORY.md ayant forging_state)."""
    project_dir = get_project_dir()
    subjects = []
    seen = set()
    for root in load_forge_config(project_dir)["pool_roots"]:
        if root == ".":
            # Pool plat : subjects/ directement à la racine — glob NON récursif
            # pour éviter de re-balayer (et dédoublonner) les roots nommés.
            root_dir = project_dir
            matches = root_dir.glob("subjects/*/MEMORY.md")
        else:
            root_dir = project_dir / root
            matches = root_dir.rglob("subjects/*/MEMORY.md")
        if not root_dir.is_dir():
            continue
        for memory_md in matches:
            rp = memory_md.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            fm = parse_frontmatter(memory_md)
            if not fm or "forging_state" not in fm:
                continue
            last_event = fm.get("last_event")
            last_event_date = last_event.get("date") if isinstance(last_event, dict) else None
            subjects.append({
                "path": str(memory_md.parent.relative_to(project_dir)),
                "forging_state": fm.get("forging_state"),
                "conviction": fm.get("conviction"),
                "type": fm.get("type"),
                "last_event_date": last_event_date,
            })
    return _ok(subjects=sorted(subjects, key=lambda s: s["path"]))


def _detect_service_root(p: Path, project_dir: Path):
    """Si p est sous services/<x>/ (à toute profondeur), retourne le path absolu de services/<x>/.
    Sinon None. Le service root inclut p lui-même si p == services/<x>/."""
    try:
        rel = p.relative_to(project_dir)
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "services":
        return project_dir / "services" / parts[1]
    return None


def cmd_prepare(args):
    """Phase 0a + 0b + 1 : détecte contexte, vérifie existence, retourne état.

    v2.7 : retourne aussi service_root, service_structure_exists, proposed_default_path
    pour permettre à la Phase L0.0 du skill de décider s'il faut créer la structure
    discussions/+decisions/ au niveau service.
    """
    project_dir = get_project_dir()
    raw = args.path
    p = Path(raw)
    if not p.is_absolute():
        p = project_dir / raw

    parts = p.parts
    is_subject_pool = "subjects" in parts and parts.index("subjects") < len(parts) - 1

    rel_path = str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p)

    # Détection service root + statut structure (utile en legacy comme en subject pool)
    service_root_abs = _detect_service_root(p, project_dir)
    if service_root_abs is not None:
        service_root_rel = str(service_root_abs.relative_to(project_dir))
        has_discussions = (service_root_abs / "discussions").is_dir()
        has_decisions = (service_root_abs / "decisions").is_dir()
        service_structure_exists = has_discussions and has_decisions
    else:
        service_root_rel = None
        service_structure_exists = None

    if not is_subject_pool:
        # En legacy : si le service existe mais pas la structure, proposer le service root
        # comme path par défaut (Phase L0.0 du skill).
        proposed_default_path = (
            service_root_rel
            if (service_root_abs is not None and service_structure_exists is False)
            else None
        )
        return _ok(
            is_subject_pool=False,
            subject_exists=False,
            needs_creation=False,
            recommended_workflow="legacy",
            path=rel_path,
            service_root=service_root_rel,
            service_structure_exists=service_structure_exists,
            proposed_default_path=proposed_default_path,
        )

    memory_md = p / "MEMORY.md"
    subject_exists = memory_md.is_file()
    fm = parse_frontmatter(memory_md) if subject_exists else None
    inferred_type = (fm.get("type") if fm else None)

    return _ok(
        is_subject_pool=True,
        subject_exists=subject_exists,
        path=rel_path,
        type=inferred_type,
        current_frontmatter=fm,
        needs_creation=not subject_exists,
        recommended_workflow="subject_pool",
        service_root=service_root_rel,
        service_structure_exists=service_structure_exists,
        proposed_default_path=None,
    )


def cmd_infer_type(args):
    """Phase 0c : inférer le type d'un subject selon 4 stratégies."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    # Stratégie 1 : type explicite dans MEMORY.md
    memory_md = p / "MEMORY.md"
    if memory_md.is_file():
        fm = parse_frontmatter(memory_md) or {}
        if fm.get("type"):
            return _ok(
                type=fm["type"],
                strategy="from_frontmatter",
                type_exists=_type_exists(p, fm["type"]),
            )

    # Stratégie 2 : 1 seul type dans <parent>/types/
    parent = _subject_parent(p)
    if parent:
        types_dir = parent / "types"
        if types_dir.is_dir():
            existing_types = sorted(d.name for d in types_dir.iterdir() if d.is_dir())
            if len(existing_types) == 1:
                return _ok(
                    type=existing_types[0],
                    strategy="single_parent_type",
                    type_exists=True,
                )

            # Stratégie 3 : naming convention <type>-<rest>
            # Chercher le type LE PLUS LONG qui matche (sinon "supplier-order" matche aussi pour un subject "supplier-x")
            name = p.name
            best_match = None
            for t in existing_types:
                if name == t or name.startswith(t + "-"):
                    if best_match is None or len(t) > len(best_match):
                        best_match = t
            if best_match:
                return _ok(
                    type=best_match,
                    strategy="from_naming",
                    type_exists=True,
                )

            # Stratégie 4 : plusieurs candidats
            return _ok(
                type=None,
                strategy="ambiguous",
                candidates=existing_types,
                type_exists=False,
            )

    # Stratégie 5 : aucun type trouvable
    return _ok(
        type=None,
        strategy="none",
        candidates=[],
        type_exists=False,
    )


def _subject_parent(subject_path):
    """Retourne le parent qui contient subjects/ et types/. Ex: services/achats/."""
    p = subject_path.resolve() if subject_path.exists() else subject_path
    # Si le path n'existe pas, on remonte quand même via les parts
    parts = p.parts
    for i, part in enumerate(parts):
        if part == "subjects" and i > 0:
            return Path(*parts[:i])
    return None


def _type_exists(subject_path, type_name):
    parent = _subject_parent(subject_path)
    if not parent:
        return False
    return (parent / "types" / type_name).is_dir()


def cmd_patch_frontmatter(args):
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path
    memory_md = p / "MEMORY.md" if p.is_dir() else p
    if not memory_md.is_file():
        return _err(f"MEMORY.md not found at {memory_md}", code="missing_file")
    try:
        patch = json.loads(args.patch)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON patch: {e}", code="invalid_patch")
    if not isinstance(patch, dict):
        return _err("patch must be a JSON object", code="invalid_patch")
    try:
        result = patch_frontmatter_file(
            memory_md, patch,
            dry_run=args.dry_run,
            expected_hash=args.expected_hash,
        )
    except (ValueError, OSError) as e:
        return _err(str(e), code="patch_failed")
    rel_path = str(memory_md.relative_to(project_dir)) if memory_md.is_relative_to(project_dir) else str(memory_md)
    if result.get("stale_hash"):
        return _err(
            f"stale hash: expected {result['expected_hash']}, got {result['before_hash']}",
            code="stale_hash",
            path=rel_path,
            **result,
        )
    return _ok(path=rel_path, **result)


def cmd_compute_hash(args):
    """Calcule le sha256[:12] d'un MEMORY.md. À utiliser avant un patch concurrent.

    Workflow type :
      1. h=$(forge documente compute-hash path/to/subject)
      2. ... autres opérations ...
      3. forge documente patch-frontmatter path/to/subject '{"k":"v"}' --expected-hash $h

    Si quelqu'un (autre session, hook scanner, /documente concurrent) a touché
    le fichier entre 1 et 3, l'étape 3 fail avec `stale_hash` plutôt que d'écraser.
    """
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path
    memory_md = p / "MEMORY.md" if p.is_dir() else p
    if not memory_md.is_file():
        return _err(f"MEMORY.md not found at {memory_md}", code="missing_file")
    content = memory_md.read_text(encoding="utf-8")
    h = hashlib.sha256(content.encode()).hexdigest()[:12]
    rel_path = str(memory_md.relative_to(project_dir)) if memory_md.is_relative_to(project_dir) else str(memory_md)
    return _ok(path=rel_path, hash=h)


def cmd_commit_atomic(args):
    """Stage les paths, commit, et push optionnellement."""
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    if not paths:
        return _err("no paths provided", code="invalid_args")

    try:
        repo_root_out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        repo_root = repo_root_out.stdout.strip()
    except subprocess.CalledProcessError:
        return _err("not a git repository", code="not_git")

    try:
        subprocess.run(
            ["git", "-C", repo_root, "add", *paths],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        return _err(f"git add failed: {e.stderr}", code="git_add_failed")

    diff = subprocess.run(
        ["git", "-C", repo_root, "diff", "--cached", "--name-only"],
        capture_output=True, text=True, check=True,
    )
    if not diff.stdout.strip():
        return _ok(noop=True, commit_sha=None, paths=paths, repo=repo_root)

    full_message = args.message + "\n\nCo-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
    try:
        subprocess.run(
            ["git", "-C", repo_root, "commit", "-m", full_message],
            capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        return _err(f"git commit failed: {e.stderr or e.stdout}", code="git_commit_failed")

    sha = subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()

    pushed = False
    if args.push:
        try:
            subprocess.run(
                ["git", "-C", repo_root, "push"],
                capture_output=True, text=True, check=True,
            )
            pushed = True
        except subprocess.CalledProcessError as e:
            return _err(f"git push failed: {e.stderr}", code="git_push_failed", commit_sha=sha)

    return _ok(noop=False, commit_sha=sha, pushed=pushed, paths=paths, repo=repo_root)


def cmd_scan_impacted(args):
    """Scanne les fichiers exécutants potentiellement impactés.

    Remonte les parents du subject jusqu'au repo root, et liste pour chaque parent
    les fichiers qui pourraient être affectés (skills, agents, configs).
    """
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    candidates = []
    seen = set()

    KIND_BY_NAME = {
        "SKILL.md": "skill",
        "agent.yaml": "agent",
        "brief.yaml": "brief",
        "config.yaml": "config",
    }

    cursor = p.resolve() if p.exists() else p
    project_parent = project_dir.parent
    while cursor != cursor.parent:
        if cursor.is_dir():
            for entry in cursor.iterdir():
                if entry.is_file() and entry.name in KIND_BY_NAME:
                    resolved = entry.resolve()
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    rel = str(entry.relative_to(project_dir)) if entry.is_relative_to(project_dir) else str(entry)
                    candidates.append({"path": rel, "kind": KIND_BY_NAME[entry.name]})
        if cursor == project_dir or cursor == project_parent:
            break
        cursor = cursor.parent

    rel_scanned = str(p.relative_to(project_dir)) if p.is_relative_to(project_dir) else str(p)
    return _ok(candidates=candidates, scanned_from=rel_scanned)


def cmd_check_coherence(args):
    """Compare les paramètres d'une nouvelle décision aux active_decisions actuelles."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    try:
        new_params = json.loads(args.decision_yaml)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON: {e}", code="invalid_args")
    if not isinstance(new_params, dict):
        return _err("decision-yaml must be a JSON object", code="invalid_args")

    memory_md = p / "MEMORY.md"
    if not memory_md.is_file():
        return _err(f"MEMORY.md not found at {memory_md}", code="missing_file")

    fm = parse_frontmatter(memory_md) or {}
    active = fm.get("active_decisions") or []

    conflicts = []
    for slug in active:
        decision_path = p / "decisions" / f"{slug}.yaml"
        if not decision_path.is_file():
            continue
        old_params = parse_nested_dict_block(decision_path, "parameters")
        if not old_params:
            continue
        conflicting_fields = []
        for k, v in new_params.items():
            if k in old_params and old_params[k] != v:
                conflicting_fields.append({
                    "field": k,
                    "old_value": old_params[k],
                    "new_value": v,
                })
        if conflicting_fields:
            conflicts.append({
                "old_decision": slug,
                "fields": conflicting_fields,
            })

    return _ok(conflicts=conflicts, active_count=len(active))


def cmd_write_capture(args):
    """Écrit un fichier discussion (.md) ou decision (.yaml) avec frontmatter composé côté Python."""
    project_dir = get_project_dir()
    p = Path(args.path)
    if not p.is_absolute():
        p = project_dir / args.path

    try:
        fm = json.loads(args.frontmatter)
    except json.JSONDecodeError as e:
        return _err(f"invalid JSON frontmatter: {e}", code="invalid_args")
    if not isinstance(fm, dict):
        return _err("frontmatter must be a JSON object", code="invalid_args")

    body_file = Path(args.body_file)
    if not body_file.is_file():
        return _err(f"body file not found: {body_file}", code="missing_file")
    body = body_file.read_text(encoding="utf-8")

    if args.kind == "discussion":
        target_dir = p / "discussions"
        ext = ".md"
    else:
        target_dir = p / "decisions"
        ext = ".yaml"
    target_dir.mkdir(parents=True, exist_ok=True)

    target = target_dir / f"{args.slug}{ext}"
    if target.exists():
        return _err(f"file already exists: {target}", code="exists")

    fm_lines = ["---"]
    for k, v in fm.items():
        if isinstance(v, dict):
            fm_lines.append(f"{k}:")
            for subk, subv in v.items():
                fm_lines.append(f"  {subk}: {_yaml_scalar(subv)}")
        elif isinstance(v, list):
            if not v:
                fm_lines.append(f"{k}: []")
            else:
                fm_lines.append(f"{k}:")
                for item in v:
                    fm_lines.append(f"  - {_yaml_scalar(item)}")
        else:
            fm_lines.append(f"{k}: {_yaml_scalar(v)}")
    fm_lines.append("---")
    fm_lines.append("")

    content = "\n".join(fm_lines) + body
    if not content.endswith("\n"):
        content += "\n"

    target.write_text(content, encoding="utf-8")
    rel = str(target.relative_to(project_dir)) if target.is_relative_to(project_dir) else str(target)
    return _ok(written=rel)


def _yaml_scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if any(c in s for c in [":", "#"]) and not (s.startswith('"') and s.endswith('"')):
        return f'"{s}"'
    return s


def cmd_cascade_last_event(args):
    """Met à jour le frontmatter `last_event` d'un linked subject."""
    project_dir = get_project_dir()
    root = Path(args.root_path)
    linked = Path(args.linked_path)
    if not root.is_absolute():
        root = project_dir / args.root_path
    if not linked.is_absolute():
        linked = project_dir / args.linked_path

    linked_memory = linked / "MEMORY.md"
    if not linked_memory.is_file():
        return _err(f"linked MEMORY.md not found at {linked_memory}", code="missing_file")

    today = _dt.date.today().isoformat()
    new_event = {
        "date": today,
        "type": f"cascaded_from_{root.name}",
        "ref": args.event_ref,
    }
    patch = {"last_event": new_event}
    try:
        result = patch_frontmatter_file(linked_memory, patch, dry_run=False)
    except (ValueError, OSError) as e:
        return _err(str(e), code="patch_failed")
    rel = str(linked.relative_to(project_dir)) if linked.is_relative_to(project_dir) else str(linked)
    return _ok(linked_path=rel, **result)


def main():
    parser = argparse.ArgumentParser(prog="documente_engine.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-subjects")

    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("path")

    p_infer = sub.add_parser("infer-type")
    p_infer.add_argument("path")

    p_patch = sub.add_parser("patch-frontmatter")
    p_patch.add_argument("path")
    p_patch.add_argument("--patch", required=True, help="JSON patch object")
    p_patch.add_argument("--dry-run", action="store_true")
    p_patch.add_argument(
        "--expected-hash",
        default=None,
        help="Expected sha256[:12] of the current file content. If provided "
             "and the actual hash differs, the patch is refused (stale_hash). "
             "Pattern adopté depuis Optimike Obsidian MCP `expectedHash` "
             "(analyse Forge-Lab #7 2026-05-26). À utiliser pour éviter les "
             "overwrites stale en présence de sessions concurrentes.",
    )

    p_hash = sub.add_parser("compute-hash",
                            help="Calcule le sha256[:12] d'un MEMORY.md pour un "
                                 "workflow patch ultérieur avec --expected-hash")
    p_hash.add_argument("path")

    p_commit = sub.add_parser("commit-atomic")
    p_commit.add_argument("--paths", required=True, help="comma-separated paths")
    p_commit.add_argument("--message", required=True)
    p_commit.add_argument("--push", action="store_true")

    p_scan = sub.add_parser("scan-impacted")
    p_scan.add_argument("path")

    p_check = sub.add_parser("check-coherence")
    p_check.add_argument("path")
    p_check.add_argument("--decision-yaml", required=True, help="JSON of new decision parameters")

    p_write = sub.add_parser("write-capture")
    p_write.add_argument("path")
    p_write.add_argument("--kind", required=True, choices=["discussion", "decision"])
    p_write.add_argument("--slug", required=True)
    p_write.add_argument("--body-file", required=True, help="path to file containing body markdown/yaml")
    p_write.add_argument("--frontmatter", required=True, help="JSON object of frontmatter fields")

    p_cascade = sub.add_parser("cascade-last-event")
    p_cascade.add_argument("root_path")
    p_cascade.add_argument("linked_path")
    p_cascade.add_argument("--event-ref", required=True)

    args = parser.parse_args()

    handlers = {
        "list-subjects": cmd_list_subjects,
        "prepare": cmd_prepare,
        "infer-type": cmd_infer_type,
        "patch-frontmatter": cmd_patch_frontmatter,
        "compute-hash": cmd_compute_hash,
        "commit-atomic": cmd_commit_atomic,
        "scan-impacted": cmd_scan_impacted,
        "check-coherence": cmd_check_coherence,
        "write-capture": cmd_write_capture,
        "cascade-last-event": cmd_cascade_last_event,
    }

    t_start = time.perf_counter()
    result = handlers[args.cmd](args)
    duration_ms = int((time.perf_counter() - t_start) * 1000)
    args_summary = {k: (str(v)[:80] if not isinstance(v, bool) else v)
                    for k, v in vars(args).items() if k != "cmd" and v is not None}
    _log_invocation(
        cmd=args.cmd,
        args_dict=args_summary,
        duration_ms=duration_ms,
        ok=result.get("ok", False),
        code=result.get("code"),
    )
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    sys.exit(0)


if __name__ == "__main__":
    main()
