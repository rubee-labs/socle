#!/usr/bin/env python3
"""
skillify_engine.py — Compilation continue de workflows ad hoc en skills réutilisables.

Adapté du pattern `gbrain skillify` de Garry Tan (cf. analyse Forge-Lab
2026-05-09) — porte la primitive « workflow manuel → SKILL.md testé + scripts
+ fixtures » dans Forge. Stdlib only.

Sous-commandes :
- scaffold <name> [--description X] [--triggers X,Y] [--source-subjects P,Q]
       Crée les 5 stubs d'un nouveau skill : SKILL.md + scripts/<name>.py +
       tests/test_<name>.py + fixtures/<name>.routing.jsonl + EVAL.md.
       Sentinelle SKILLIFY_STUB sur les contenus à compléter par l'humain.
       --source-subjects (D10, 2026-09-14) : provenance bidirectionnelle —
       écrit `source_subjects: [...]` dans le frontmatter du SKILL.md généré
       ET ajoute le skill aux `linked_skills` du MEMORY.md de chaque subject
       d'origine (équivalent du PURPOSE.md WikiSkill, arXiv 2608.27454).
- check <skill-path>
       Audit 11-points sur un skill existant (présence SKILL.md, sections,
       tests, scripts, sentinelles résiduelles, description suffisante,
       provenance déclarée).
- audit [--target <dir>]
       Scanne tous les skills d'un répertoire et agrège les résultats du check.
       Par défaut : skills/ du repo courant.

Sortie JSON sur stdout. Exit 0 = ok, exit 1 = ok=false ou erreurs.
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

from forge_lib import get_project_dir, load_forge_config

STUB_SENTINEL = "SKILLIFY_STUB"

# 11 checks de l'audit `check`. 8 sont critiques (must pass pour ok=true),
# 3 sont des checks d'hygiène (HYGIENE_CHECKS) — utiles à signaler mais pas
# bloquants. Cohérent avec le fait que dans socle les engines vivent
# dans bin/ partagé, pas dans skills/<name>/scripts/.
HYGIENE_CHECKS = {"scripts_dir", "tests_dir", "provenance_declared"}

CHECK_LABELS = {
    "skill_md_exists":       "SKILL.md existe à la racine du skill",
    "frontmatter_valid":     "frontmatter contient name + description (≥30 chars)",
    "section_when_to_use":   "section 'Quand utiliser' présente",
    "section_instructions":  "section 'Instructions' / 'Workflow' / 'Phases' avec ≥1 sous-phase",
    "section_gotchas":       "section 'Gotchas' avec ≥1 entrée",
    "section_evals":         "section 'Critères d'évaluation' avec ≥1 EVAL",
    "scripts_dir":           "dossier scripts/ présent (hygiène — non bloquant)",
    "tests_dir":             "dossier tests/ présent (hygiène — non bloquant)",
    "no_residual_stubs":     f"aucun sentinel `{STUB_SENTINEL}` résiduel",
    "description_long_enough": "description du frontmatter ≥30 chars",
    "provenance_declared":   "frontmatter source_subjects non vide (provenance skill → subjects, hygiène — non bloquant)",
}


# ──────────────────────────────────────────────────────────────────────────
# scaffold
# ──────────────────────────────────────────────────────────────────────────


def _resolve_skills_root(project_dir: Path) -> Path:
    """Devine le bon répertoire `skills/` selon le repo courant.

    - Si `socle/` (le plugin lui-même), cible `skills/`.
    - Si repo client (ex: claude-enterprise), cible `entreprise/skills/` si
      ce dossier existe, sinon `skills/`.
    - Sinon fallback : `skills/` à la racine.
    """
    candidates = [
        project_dir / "entreprise" / "skills",
        project_dir / "skills",
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_dir / "skills"


def _make_skill_md(name, description, triggers, visibility="entreprise", source_subjects=None):
    triggers_block = ""
    if triggers:
        triggers_block = "\n  ".join(f"- {t.strip()}" for t in triggers if t.strip())
    desc = description or f"{STUB_SENTINEL} — décrire en ≥30 chars ce que fait le skill, ses triggers, ses limites."
    today = date.today().isoformat()
    # D10 (2026-09-14) : provenance skill → subjects. Liste vide si le skill
    # ne naît d'aucun subject — le check `provenance_declared` (hygiène) le signale.
    sources = ", ".join(source_subjects) if source_subjects else ""
    return f"""---
name: {name}
description: >-
  {desc}
visibilité: {visibility}
auteur: {STUB_SENTINEL}
date_creation: {today}
version: 0.1
tags: [{STUB_SENTINEL}]
effort: medium
outils_requis: []
securite_externe: false
source_subjects: [{sources}]
{f"triggers:\\n  {triggers_block}" if triggers_block else ""}
---

# {name}

## Objectif

{STUB_SENTINEL} — décrire l'intention en 1 paragraphe : quel problème métier ce skill résout, pour qui, quand l'invoquer.

## Quand utiliser

- {STUB_SENTINEL} — cas typique 1
- {STUB_SENTINEL} — cas typique 2

**Quand NE PAS utiliser** :

- {STUB_SENTINEL} — cas qui ressemble mais qui doit aller ailleurs

## Instructions

### Phase 1 — {STUB_SENTINEL}

{STUB_SENTINEL} — décrire ce qu'il faut faire (lecture, calcul, validation…).

### Phase 2 — {STUB_SENTINEL}

{STUB_SENTINEL} — décrire la suite.

## Exemples

### Input

> "{STUB_SENTINEL} — phrase déclencheur typique"

### Output (résumé)

```
{STUB_SENTINEL} — ce que produit le skill (fichier, message, action)
```

## Gotchas

- {STUB_SENTINEL} — piège typique à connaître

## Critères d'évaluation

- **EVAL 1** : {STUB_SENTINEL} — critère vérifiable (Pass/Fail)
"""


def _make_main_script(name):
    return f"""#!/usr/bin/env python3
\"\"\"scripts/{name}.py — script principal du skill {name}.

{STUB_SENTINEL} — remplacer par la logique réelle. Stdlib only de préférence.
\"\"\"

import argparse
import json
import sys


def main():
    parser = argparse.ArgumentParser(description="{name} — skill script")
    # {STUB_SENTINEL} — déclarer les sous-commandes ou arguments réels
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # {STUB_SENTINEL} — implémenter la logique métier
    result = {{
        "ok": False,
        "version": 1,
        "error": "{STUB_SENTINEL}: not implemented",
        "dry_run": args.dry_run,
    }}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
"""


def _make_test_file(name):
    return f"""#!/usr/bin/env python3
\"\"\"Tests unittest pour scripts/{name}.py.\"\"\"

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "{name}.py"


def run_script(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None, result.returncode


class TestSkillStub(unittest.TestCase):

    def test_runs_without_crashing(self):
        out, code = run_script("--dry-run")
        # Stub renvoie ok=False par construction. Remplacer par les vrais tests une fois implémenté.
        self.assertIsNotNone(out)
        # {STUB_SENTINEL} — remplacer par des assertions réelles


if __name__ == "__main__":
    unittest.main()
"""


def _make_routing_fixture(name, triggers):
    """Fixture JSONL — une ligne par paire {intent, expected_skill}."""
    lines = []
    if triggers:
        for t in triggers:
            t_clean = t.strip()
            if t_clean:
                lines.append(json.dumps({"intent": t_clean, "expected_skill": name}, ensure_ascii=False))
    if not lines:
        lines = [json.dumps({"intent": f"{STUB_SENTINEL} — phrase déclencheur", "expected_skill": name}, ensure_ascii=False)]
    return "\n".join(lines) + "\n"


def _make_eval_md(name):
    return f"""# EVAL — {name}

Checklist d'évaluation manuelle du skill **{name}**.

## Items vérifiés par `forge skillify check`

Voir `forge skillify check skills/{name}` pour le rapport JSON.

## Items à valider à la main

- [ ] Le skill produit un résultat reproductible sur 3 exemples concrets
- [ ] Les Gotchas couvrent les pièges réels rencontrés (pas de gotcha théorique)
- [ ] Le skill a été lancé en conditions réelles ≥1 fois et le résultat est satisfaisant
- [ ] La description du frontmatter discrimine bien le skill des skills voisins (pas d'overlap)
- [ ] {STUB_SENTINEL} — autre critère métier
"""


def _resolve_subject_memory(project_dir: Path, ref: str):
    """Résout une référence de subject (chemin de dossier ou de MEMORY.md,
    relatif au repo ou absolu) vers son MEMORY.md. Retourne (Path|None, ref_norm).

    ref_norm = chemin du dossier subject relatif au repo quand résolvable
    (c'est la forme stockée dans `source_subjects:`), sinon la ref d'origine.
    """
    ref = ref.strip().rstrip("/")
    if not ref:
        return None, ref
    candidates = [Path(ref)] if Path(ref).is_absolute() else [project_dir / ref]
    for c in candidates:
        memory = c if c.name == "MEMORY.md" else c / "MEMORY.md"
        if memory.is_file():
            subject_dir = memory.parent
            try:
                ref_norm = str(subject_dir.relative_to(project_dir))
            except ValueError:
                ref_norm = str(subject_dir)
            return memory, ref_norm
    return None, ref


def _update_subject_linked_skills(memory_path: Path, skill_name: str):
    """Ajoute `skill_name` au `linked_skills:` du frontmatter d'un MEMORY.md
    (backlink subject → skill, D10). Édition textuelle minimale — on ne
    régénère jamais le frontmatter entier (le MEMORY.md appartient à
    /documente, pas à skillify).

    Formats gérés : liste inline `linked_skills: [a, b]` (canonique), bloc
    multi-ligne `linked_skills:\\n  - a`, clé absente (insérée avant le `---`
    fermant). Retourne (updated: bool, reason: str).
    """
    try:
        text = memory_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return False, f"unreadable: {e}"

    fm_match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        return False, "no_frontmatter"
    fm_text = fm_match.group(1)

    # Cas 1 — liste inline `linked_skills: [a, b]`
    inline = re.search(r"^(linked_skills:\s*\[)([^\]]*)(\])", fm_text, re.MULTILINE)
    if inline:
        items = [s.strip() for s in inline.group(2).split(",") if s.strip()]
        if skill_name in items:
            return False, "already_present"
        items.append(skill_name)
        new_fm = fm_text[:inline.start()] + inline.group(1) + ", ".join(items) \
            + inline.group(3) + fm_text[inline.end():]
    else:
        # Cas 2 — bloc multi-ligne `linked_skills:` suivi de `  - item`
        block = re.search(r"^linked_skills:[ \t]*\n((?:[ \t]+-[^\n]*\n?)*)", fm_text, re.MULTILINE)
        if block:
            if re.search(rf"-\s*{re.escape(skill_name)}\s*$", block.group(1), re.MULTILINE):
                return False, "already_present"
            insert_at = block.end(1)
            prefix = "" if (insert_at == 0 or fm_text[insert_at - 1] == "\n") else "\n"
            new_fm = fm_text[:insert_at] + f"{prefix}  - {skill_name}\n" + fm_text[insert_at:]
        else:
            # Cas 3 — clé absente : ajout en fin de frontmatter
            new_fm = fm_text.rstrip("\n") + f"\nlinked_skills: [{skill_name}]"

    new_text = text[:fm_match.start(1)] + new_fm + text[fm_match.end(1):]
    memory_path.write_text(new_text, encoding="utf-8")
    return True, "updated"


def cmd_scaffold(name, description=None, triggers=None, target_root=None, source_subjects=None):
    """Crée les 5 stubs d'un nouveau skill."""
    project_dir = get_project_dir()
    if target_root:
        skills_root = Path(target_root).resolve()
    else:
        skills_root = _resolve_skills_root(project_dir)

    skill_dir = skills_root / name
    if skill_dir.exists():
        return {
            "ok": False,
            "error": f"skill `{name}` existe déjà à {skill_dir}",
        }

    skill_dir.mkdir(parents=True)
    (skill_dir / "scripts").mkdir()
    (skill_dir / "tests").mkdir()
    (skill_dir / "fixtures").mkdir()

    # D10 — provenance bidirectionnelle skill ↔ subjects : résolution des refs
    # AVANT génération (les refs normalisées vont dans le frontmatter), backlink
    # APRÈS création des fichiers.
    provenance = {"source_subjects": [], "backlinks_updated": [], "warnings": []}
    resolved = []  # [(memory_path|None, ref_norm)]
    for ref in (source_subjects or []):
        memory_path, ref_norm = _resolve_subject_memory(project_dir, ref)
        resolved.append((memory_path, ref_norm))
        provenance["source_subjects"].append(ref_norm)
        if memory_path is None:
            provenance["warnings"].append(f"subject introuvable (pas de MEMORY.md) : {ref}")

    triggers_list = triggers or []
    visibility = load_forge_config(project_dir)["skill_visibility"]
    (skill_dir / "SKILL.md").write_text(
        _make_skill_md(name, description, triggers_list, visibility=visibility,
                       source_subjects=provenance["source_subjects"]),
        encoding="utf-8",
    )
    (skill_dir / "scripts" / f"{name}.py").write_text(
        _make_main_script(name), encoding="utf-8"
    )
    (skill_dir / "tests" / f"test_{name}.py").write_text(
        _make_test_file(name), encoding="utf-8"
    )
    (skill_dir / "fixtures" / f"{name}.routing.jsonl").write_text(
        _make_routing_fixture(name, triggers_list), encoding="utf-8"
    )
    (skill_dir / "EVAL.md").write_text(_make_eval_md(name), encoding="utf-8")

    for memory_path, ref_norm in resolved:
        if memory_path is None:
            continue
        updated, reason = _update_subject_linked_skills(memory_path, name)
        if updated:
            provenance["backlinks_updated"].append(ref_norm)
        elif reason not in ("already_present",):
            provenance["warnings"].append(f"backlink non appliqué sur {ref_norm} : {reason}")

    return {
        "ok": True,
        "version": 1,
        "skill_name": name,
        "skill_dir": str(skill_dir),
        "provenance": provenance,
        "files_created": [
            str(skill_dir / "SKILL.md"),
            str(skill_dir / "scripts" / f"{name}.py"),
            str(skill_dir / "tests" / f"test_{name}.py"),
            str(skill_dir / "fixtures" / f"{name}.routing.jsonl"),
            str(skill_dir / "EVAL.md"),
        ],
        "stubs_remaining": True,
        "next_steps": [
            "Compléter SKILL.md (sections Quand utiliser, Instructions, Gotchas, EVAL)",
            f"Implémenter scripts/{name}.py",
            f"Écrire tests/test_{name}.py",
            f"Lancer `forge skillify check {skill_dir}`",
        ],
    }


# ──────────────────────────────────────────────────────────────────────────
# check
# ──────────────────────────────────────────────────────────────────────────


def _read_skill_md(skill_path: Path):
    """Lit SKILL.md, retourne (frontmatter_dict, body). Gère les descriptions
    multi-lignes YAML (`>-`, `|`, etc.) en accumulant les lignes indentées."""
    md = skill_path / "SKILL.md"
    if not md.exists():
        return None, None
    content = md.read_text(encoding="utf-8")
    fm = {}
    body = content
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not fm_match:
        return fm, body
    fm_text = fm_match.group(1)
    body = fm_match.group(2)

    lines = fm_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line or line.startswith(" ") or line.startswith("\t"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        k, v = line.split(":", 1)
        key = k.strip()
        value = v.strip()
        # YAML multi-line block scalars: `>-`, `>`, `|`, `|-`, `|+`, `>+`
        if value in (">", ">-", ">+", "|", "|-", "|+"):
            block_lines = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or lines[i] == ""):
                if lines[i].strip():
                    block_lines.append(lines[i].strip())
                i += 1
            joiner = " " if value.startswith(">") else "\n"
            fm[key] = joiner.join(block_lines).strip()
            continue
        fm[key] = value.strip().strip('"').strip("'")
        i += 1
    return fm, body


def _has_section(body, header_pattern):
    """Vérifie qu'une section markdown commençant par le pattern existe et a du contenu.

    Tolérant : matche `## Foo`, `### Foo bar`, `## Foo — suffix`, etc.
    """
    rx = re.compile(rf"^#+\s*{header_pattern}\b.*$", re.MULTILINE | re.IGNORECASE)
    m = rx.search(body)
    if not m:
        return False
    after = body[m.end():]
    next_section = re.search(r"^#+\s+", after, re.MULTILINE)
    chunk = after[:next_section.start()] if next_section else after
    return bool(chunk.strip())


def _strip_markdown_code_blocks(text):
    """Supprime les fenced code blocks (``` ... ```) et le code inline (`...`)
    pour permettre à la doc d'un skill de mentionner le sentinel sans le
    déclencher comme stub résiduel.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    return text


def _count_residual_stubs(skill_path: Path):
    count = 0
    locations = []
    for f in skill_path.rglob("*"):
        if not f.is_file():
            continue
        if f.suffix not in (".md", ".py", ".jsonl", ".yaml", ".yml"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if f.suffix == ".md":
            text = _strip_markdown_code_blocks(text)
        n = text.count(STUB_SENTINEL)
        if n > 0:
            count += n
            locations.append({"file": str(f.relative_to(skill_path)), "occurrences": n})
    return count, locations


def cmd_check(skill_path):
    """Audit 11-points sur un skill."""
    skill_path = Path(skill_path).resolve()
    if not skill_path.is_dir():
        return {"ok": False, "error": f"not a directory: {skill_path}"}

    checks = {k: False for k in CHECK_LABELS}
    details = {}

    fm, body = _read_skill_md(skill_path)
    if fm is not None:
        checks["skill_md_exists"] = True

        name_ok = bool(fm.get("name"))
        desc = (fm.get("description", "") or "").strip()
        desc_long_enough = len(desc) >= 30
        checks["description_long_enough"] = desc_long_enough
        checks["frontmatter_valid"] = name_ok and desc_long_enough
        details["frontmatter_name"] = fm.get("name")
        details["description_length"] = len(desc)

        checks["section_when_to_use"] = _has_section(body, r"Quand utiliser")
        # Plusieurs conventions acceptées : Instructions / Workflow / Phases /
        # ≥1 sous-section "Phase X" ou "Étape X" pour décrire le pipeline.
        checks["section_instructions"] = (
            _has_section(body, r"Instructions")
            or _has_section(body, r"Workflow")
            or _has_section(body, r"Phases?")
            or bool(re.search(r"^#+\s*(Phase|[ÉE]tape)\b", body, re.MULTILINE | re.IGNORECASE))
        )
        checks["section_gotchas"] = _has_section(body, r"Gotchas")
        checks["section_evals"] = (
            _has_section(body, r"Crit[èe]res d'?[ée]valuation")
            or _has_section(body, r"EVAL")
        )

        # D10 — provenance skill → subjects (hygiène). `source_subjects: []`
        # ou clé absente = non déclaré. Le parser stocke les listes inline
        # comme string brute → on inspecte le contenu des crochets.
        raw_src = str(fm.get("source_subjects", "") or "").strip()
        inner = raw_src[1:-1].strip() if raw_src.startswith("[") and raw_src.endswith("]") else raw_src
        checks["provenance_declared"] = bool(inner)

    checks["scripts_dir"] = (skill_path / "scripts").is_dir()
    checks["tests_dir"] = (skill_path / "tests").is_dir()

    stub_count, stub_locations = _count_residual_stubs(skill_path)
    checks["no_residual_stubs"] = stub_count == 0
    if stub_count > 0:
        details["residual_stubs"] = {
            "total": stub_count,
            "locations": stub_locations,
        }

    failed = [k for k, v in checks.items() if not v]
    failed_critical = [k for k in failed if k not in HYGIENE_CHECKS]
    failed_hygiene = [k for k in failed if k in HYGIENE_CHECKS]
    return {
        "ok": len(failed_critical) == 0,
        "version": 1,
        "skill_path": str(skill_path),
        "checks": {
            k: {"passed": v, "label": CHECK_LABELS[k], "critical": k not in HYGIENE_CHECKS}
            for k, v in checks.items()
        },
        "summary": {
            "total": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "failed_critical": failed_critical,
            "failed_hygiene": failed_hygiene,
            "failed_keys": failed,  # rétrocompat
        },
        "details": details,
    }


# ──────────────────────────────────────────────────────────────────────────
# audit
# ──────────────────────────────────────────────────────────────────────────


def cmd_audit(target_root=None, strict=False):
    """Audit global de tous les skills d'un répertoire."""
    project_dir = get_project_dir()
    if target_root:
        skills_root = Path(target_root).resolve()
    else:
        skills_root = _resolve_skills_root(project_dir)

    if not skills_root.is_dir():
        return {"ok": False, "error": f"skills root not found: {skills_root}"}

    skills = sorted(d for d in skills_root.iterdir() if d.is_dir())
    reports = []
    for skill_path in skills:
        if not (skill_path / "SKILL.md").exists():
            continue
        reports.append(cmd_check(str(skill_path)))

    total = len(reports)
    # ok = aucun fail critique. warn = uniquement des hygiène. fail = ≥1 critique.
    ok_count = sum(
        1 for r in reports
        if r.get("ok") and not r.get("summary", {}).get("failed_hygiene")
    )
    warn_count = sum(
        1 for r in reports
        if r.get("ok") and r.get("summary", {}).get("failed_hygiene")
    )
    fail_count = sum(1 for r in reports if not r.get("ok"))

    return {
        "ok": fail_count == 0 and (not strict or warn_count == 0),
        "version": 1,
        "skills_root": str(skills_root),
        "summary": {
            "total": total,
            "ok": ok_count,
            "warn": warn_count,
            "fail": fail_count,
        },
        "reports": reports,
    }


# ──────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Forge skillify engine")
    sub = parser.add_subparsers(dest="cmd")

    p_sc = sub.add_parser("scaffold", help="Crée les stubs d'un nouveau skill")
    p_sc.add_argument("name")
    p_sc.add_argument("--description", default=None)
    p_sc.add_argument("--triggers", default=None,
                      help="Triggers comma-separated (ex: 'verify webhook,check tunnel')")
    p_sc.add_argument("--target", default=None,
                      help="Override skills root (default: skills/ ou entreprise/skills/)")
    p_sc.add_argument("--source-subjects", default=None,
                      help="Subjects d'origine comma-separated (chemins de dossiers subject, "
                           "ex: 'services/finance/subjects/tresorerie'). Écrit source_subjects "
                           "dans le SKILL.md et met à jour linked_skills des subjects (D10).")

    p_ck = sub.add_parser("check", help="Audit 11-points sur un skill")
    p_ck.add_argument("skill_path")

    p_au = sub.add_parser("audit", help="Audit global du répertoire skills/")
    p_au.add_argument("--target", default=None)
    p_au.add_argument("--strict", action="store_true",
                      help="Considérer warn comme fail")

    args = parser.parse_args()

    if args.cmd == "scaffold":
        triggers = [t for t in (args.triggers or "").split(",") if t.strip()]
        sources = [s.strip() for s in (args.source_subjects or "").split(",") if s.strip()]
        result = cmd_scaffold(args.name, description=args.description,
                              triggers=triggers, target_root=args.target,
                              source_subjects=sources)
    elif args.cmd == "check":
        result = cmd_check(args.skill_path)
    elif args.cmd == "audit":
        result = cmd_audit(target_root=args.target, strict=args.strict)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
