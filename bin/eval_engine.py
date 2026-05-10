#!/usr/bin/env python3
"""
eval_engine.py — Cross-modal eval pour subjects (préparation + agrégation).

Adapté du pattern "cross-modal eval" de Garry Tan (cf. analyse Forge-Lab
2026-05-09) : chaque output significatif d'un subject (Quick + Détails après
re-synthèse /documente) est passé par 2-3 modèles distincts qui se notent
mutuellement sur 4 axes : coherence, completeness, specificity, citations.

Ce module ne fait PAS d'appel LLM directement. Il :
1. `prepare <subject-path>` — lit MEMORY.md + sources, compose un prompt
   structuré + résumé des sources. Sortie JSON utilisée par le skill markdown
   qui dispatche les sub-tasks (Task tool ou SDK Claude Agent imbriqué).
2. `aggregate --results <file>...` — prend N résultats JSON et les agrège
   en un score consolidé (mean/min/max + issues dédupliquées).
3. `write-analysis <subject-path> --score <json>` — écrit le résultat dans
   `<subject-path>/analyses/<date>-cross-modal-eval.md` (produced_by: claude).

Stdlib only. Sortie JSON. Doctrine Rubee : pas d'`import anthropic` ni de
clé API — le skill markdown invoque les modèles via Task tool ou SDK
Claude Agent (plan Max).
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

from forge_lib import get_project_dir, parse_frontmatter

EVAL_AXES = {
    "coherence": {
        "label": "Cohérence Quick ↔ Détails ↔ events/decisions",
        "question": (
            "Le Quick reflète-t-il fidèlement les Détails ? Les Détails sont-ils "
            "cohérents avec les events les plus récents et les décisions actives ? "
            "Repérer toute contradiction interne (ex: Quick parle de retard alors "
            "que les events récents indiquent dans les délais)."
        ),
    },
    "completeness": {
        "label": "Complétude vs sources",
        "question": (
            "La synthèse couvre-t-elle (a) toutes les décisions actives, (b) tous "
            "les events des 30 derniers jours, (c) les discussions ouvertes ? "
            "Citer ce qui manque dans les `issues` si applicable."
        ),
    },
    "specificity": {
        "label": "Spécificité métier (vs généralités)",
        "question": (
            "La synthèse est-elle ancrée dans des faits Rubee concrets (noms, "
            "dates, montants, identifiants MCP) ou tombe-t-elle dans des phrases "
            "génériques (« le projet avance », « risques sous contrôle ») ? "
            "Les phrases génériques sont des points de fuite — flagger."
        ),
    },
    "citations": {
        "label": "Citations vers events / discussions / decisions",
        "question": (
            "Chaque assertion forte de la synthèse (un fait, une décision, un risque) "
            "renvoie-t-elle à un fichier identifiable dans events/, discussions/ ou "
            "decisions/ ? Les assertions sans backlink sont fragiles."
        ),
    },
}


def _read_memory(subject_path: Path):
    p = subject_path if subject_path.is_file() else subject_path / "MEMORY.md"
    if not p.exists():
        return None, None
    content = p.read_text(encoding="utf-8")
    fm = parse_frontmatter(p) or {}
    return content, fm


def _scan_sources(subject_dir: Path):
    """Liste les fichiers events/, discussions/, decisions/, analyses/ du subject."""
    sources = {"events": [], "discussions": [], "decisions": [], "analyses": []}
    for kind in sources:
        d = subject_dir / kind
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix in (".md", ".yaml", ".yml"):
                sources[kind].append({
                    "name": f.name,
                    "path": str(f.relative_to(subject_dir)),
                    "size_bytes": f.stat().st_size,
                })
    return sources


def cmd_prepare(subject_path):
    """Compose le contexte d'évaluation pour qu'un skill markdown invoque les modèles."""
    subject_path = Path(subject_path).resolve()
    if subject_path.is_file():
        subject_dir = subject_path.parent
        memory_path = subject_path
    else:
        subject_dir = subject_path
        memory_path = subject_path / "MEMORY.md"

    if not memory_path.exists():
        return {"ok": False, "error": f"no MEMORY.md at {subject_path}"}

    memory_content = memory_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(memory_path) or {}
    sources = _scan_sources(subject_dir)

    eval_id = f"{date.today().isoformat()}-cross-modal-eval"

    prompt = (
        "Tu es un évaluateur cross-modal pour un subject pool Forge. Le subject "
        f"`{fm.get('name', subject_dir.name)}` (type `{fm.get('type', 'unknown')}`) "
        "contient un MEMORY.md (Quick + Détails régénérés par /documente) et des "
        "sources brutes (events, discussions, decisions, analyses).\n\n"
        "Ta tâche : noter le MEMORY.md sur 4 axes (0..10) en t'appuyant sur les "
        "sources pour vérification. Pour chaque axe, retourner :\n"
        "- score (int 0-10)\n"
        "- issues (list[str]) : phrases problématiques précises (citer)\n"
        "- suggestions (list[str]) : ce qu'il faudrait ajouter / corriger\n\n"
        "Retourne UNIQUEMENT du JSON valide, format :\n"
        "```\n"
        '{"coherence": {"score": int, "issues": [...], "suggestions": [...]},\n'
        ' "completeness": {...}, "specificity": {...}, "citations": {...}}\n'
        "```\n\n"
        "Axes à évaluer :\n"
    )
    for axis, meta in EVAL_AXES.items():
        prompt += f"\n## {axis} — {meta['label']}\n{meta['question']}\n"

    return {
        "ok": True,
        "version": 1,
        "eval_id": eval_id,
        "subject_name": fm.get("name", subject_dir.name),
        "subject_type": fm.get("type", "unknown"),
        "subject_dir": str(subject_dir),
        "memory_path": str(memory_path),
        "memory_content_chars": len(memory_content),
        "sources_summary": {kind: len(items) for kind, items in sources.items()},
        "sources": sources,
        "eval_axes": list(EVAL_AXES.keys()),
        "prompt": prompt,
        "expected_models": [
            "claude-opus-4-7",      # précision
            "claude-sonnet-4-6",    # recall
            "claude-haiku-4-5",     # rapidité, perspective tierce
        ],
    }


def cmd_aggregate(result_files):
    """Agrège N résultats JSON (un par modèle évaluateur) en un score consolidé."""
    results = []
    for f in result_files:
        p = Path(f)
        if not p.exists():
            return {"ok": False, "error": f"result file not found: {f}"}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"invalid JSON in {f}: {e}"}
        results.append({"source": str(p), "data": data})

    if not results:
        return {"ok": False, "error": "no results provided"}

    aggregated = {}
    for axis in EVAL_AXES:
        scores = []
        all_issues = []
        all_suggestions = []
        for r in results:
            ax = r["data"].get(axis)
            if not isinstance(ax, dict):
                continue
            s = ax.get("score")
            if isinstance(s, (int, float)):
                scores.append(int(s))
            for issue in ax.get("issues", []) or []:
                if issue and issue not in all_issues:
                    all_issues.append(issue)
            for sug in ax.get("suggestions", []) or []:
                if sug and sug not in all_suggestions:
                    all_suggestions.append(sug)
        aggregated[axis] = {
            "score_mean": round(sum(scores) / len(scores), 1) if scores else None,
            "score_min": min(scores) if scores else None,
            "score_max": max(scores) if scores else None,
            "score_count": len(scores),
            "issues": all_issues,
            "suggestions": all_suggestions,
        }

    overall_scores = [
        aggregated[axis]["score_mean"]
        for axis in EVAL_AXES
        if aggregated[axis]["score_mean"] is not None
    ]
    overall = round(sum(overall_scores) / len(overall_scores), 1) if overall_scores else None

    return {
        "ok": True,
        "version": 1,
        "evaluator_count": len(results),
        "overall_score": overall,
        "axes": aggregated,
    }


def cmd_write_analysis(subject_path, score_json):
    """Écrit le résultat dans <subject>/analyses/<date>-cross-modal-eval.md."""
    subject_path = Path(subject_path).resolve()
    subject_dir = subject_path if subject_path.is_dir() else subject_path.parent
    if not (subject_dir / "MEMORY.md").exists():
        return {"ok": False, "error": f"no MEMORY.md at {subject_dir}"}

    try:
        score = json.loads(score_json)
    except json.JSONDecodeError as e:
        return {"ok": False, "error": f"invalid score JSON: {e}"}

    analyses_dir = subject_dir / "analyses"
    analyses_dir.mkdir(exist_ok=True)
    out = analyses_dir / f"{date.today().isoformat()}-cross-modal-eval.md"

    overall = score.get("overall_score")
    axes = score.get("axes", {})
    evaluator_count = score.get("evaluator_count", 0)

    body = [
        "---",
        f"date: {date.today().isoformat()}",
        "type: analysis",
        "produced_by: claude",
        "invoked_skill: /cross-modal-review",
        f"evaluator_count: {evaluator_count}",
        f"overall_score: {overall if overall is not None else 'null'}",
        "scoring:",
    ]
    for axis in EVAL_AXES:
        ax = axes.get(axis, {})
        body.append(f"  {axis}: {ax.get('score_mean', 'null')}")
    body.append("---")
    body.append("")
    body.append("# Cross-modal eval")
    body.append("")
    body.append(f"**Score global** : {overall if overall is not None else 'n/a'} / 10 "
                f"(moyenne des moyennes axes, {evaluator_count} évaluateur·s)")
    body.append("")
    for axis in EVAL_AXES:
        ax = axes.get(axis, {})
        meta = EVAL_AXES[axis]
        body.append(f"## {axis} — {meta['label']}")
        body.append("")
        s_mean = ax.get("score_mean")
        s_min = ax.get("score_min")
        s_max = ax.get("score_max")
        s_count = ax.get("score_count", 0)
        body.append(f"**Score** : {s_mean if s_mean is not None else 'n/a'} / 10 "
                    f"(min={s_min}, max={s_max}, n={s_count})")
        body.append("")
        issues = ax.get("issues", [])
        if issues:
            body.append("**Issues identifiées** :")
            for iss in issues:
                body.append(f"- {iss}")
            body.append("")
        suggestions = ax.get("suggestions", [])
        if suggestions:
            body.append("**Suggestions** :")
            for sug in suggestions:
                body.append(f"- {sug}")
            body.append("")

    out.write_text("\n".join(body) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "version": 1,
        "analysis_path": str(out),
        "overall_score": overall,
    }


def main():
    parser = argparse.ArgumentParser(description="Forge cross-modal eval engine")
    sub = parser.add_subparsers(dest="cmd")

    p_pr = sub.add_parser("prepare", help="Prépare le contexte d'éval (prompt + sources)")
    p_pr.add_argument("subject_path")

    p_ag = sub.add_parser("aggregate", help="Agrège N résultats d'éval JSON")
    p_ag.add_argument("--results", nargs="+", required=True,
                      help="Fichiers JSON de résultat (un par modèle)")

    p_wr = sub.add_parser("write-analysis", help="Écrit le résultat agrégé dans analyses/")
    p_wr.add_argument("subject_path")
    p_wr.add_argument("--score", required=True, help="Score JSON (sortie de aggregate)")

    args = parser.parse_args()

    if args.cmd == "prepare":
        result = cmd_prepare(args.subject_path)
    elif args.cmd == "aggregate":
        result = cmd_aggregate(args.results)
    elif args.cmd == "write-analysis":
        result = cmd_write_analysis(args.subject_path, args.score)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
