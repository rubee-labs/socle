#!/usr/bin/env python3
"""
bench_engine.py — Bench retriever du Subject Pool.

Mesure la qualité de 3 stratégies de retrieval sur les subjects existants du
repo : cascade canonique (SUBJECTS-INDEX → MEMORY.md), grep agrégé sur un blob
concaténé, grep filesystem direct.

Le bench est strictement read-only : aucune mutation des MEMORY.md, du
frontmatter, ou de la doctrine. C'est un outil de surveillance, pas un outil
de transformation. Conformément à la décision Forge-Lab 2026-05-24 (post
analyse SamourAI) : « mesurer avant de présumer ».

Mode déterministe par défaut (~secondes, $0, reproductible). Les questions
sont auto-vérifiables — la « gold answer » est extraite directement du
frontmatter ou du `## Quick` des subjects, donc le bench ne dépend pas d'un
modèle pour évaluer la correction.

Sous-commandes :
- prepare [--limit N] [--out FILE]              Génère un corpus de questions
- run --corpus FILE [--retrievers R1,R2,R3]     Exécute les retrievers
- report --results FILE [--md|--json]           Formatte les résultats

Stdlib only (Python 3.9+). Pas d'appel LLM en mode déterministe.

Référence : analyse Forge-Lab 2026-05-19 (Voltaire — file-grep > MCP-grep >
SQL-cascade sur 558 claims atomiques). Ce bench transpose le harness au
contexte Forge (subjects gouvernés multi-producer).
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from forge_lib import get_project_dir, parse_frontmatter

# ----------------------------------------------------------------------------
# Constantes
# ----------------------------------------------------------------------------

EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude",
                "templates", "fixtures"}

# Mapping ancien cycle → nouveau (cf. forge_engine.py). Utilisé seulement pour
# normaliser le gold answer si un subject porte encore un ancien forging_state.
LEGACY_STATE_MAP = {
    "seed": "actif", "debating": "actif", "tentative": "actif",
    "stress_testing": "mature", "doctrine": "mature",
    "in_service": "mature", "under_review": "mature",
    "archived": "archived", "actif": "actif", "mature": "mature",
}


# ----------------------------------------------------------------------------
# Découverte des subjects
# ----------------------------------------------------------------------------

def find_subjects(project_dir):
    """Itère sur tous les MEMORY.md de subjects. Retourne [(path, frontmatter)]."""
    subjects = []
    for memory in project_dir.rglob("MEMORY.md"):
        if any(part in EXCLUDE_DIRS or part.startswith("_archive")
               for part in memory.parts):
            continue
        fm = parse_frontmatter(memory)
        if fm and "forging_state" in fm:
            subjects.append((memory, fm))
    return subjects


def _quick_section(memory_path):
    """Extrait le bloc `## Quick` d'un MEMORY.md (texte brut, sans le titre)."""
    try:
        content = memory_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    m = re.search(r"\n## Quick\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    return m.group(1).strip() if m else ""


# ----------------------------------------------------------------------------
# Génération de corpus
# ----------------------------------------------------------------------------

def generate_questions(subjects, limit=None):
    """Génère des questions auto-vérifiables depuis les frontmatters.

    4 patterns par subject (dans la limite des champs présents) :
    - forging_state : « Quel est l'état du subject <name> ? »
    - type          : « Quel est le type du subject <name> ? »
    - horizon       : « Quel est l'horizon du subject <name> ? »
    - linked        : « À quels subjects <name> est-il lié ? »

    Le gold answer est extrait du frontmatter — donc trivialement vérifiable
    par substring match insensible à la casse.
    """
    questions = []
    qid = 0

    for memory, fm in subjects:
        name = fm.get("name") or memory.parent.name
        slug = name.lower()

        # forging_state
        state_raw = fm.get("forging_state")
        if state_raw:
            state = LEGACY_STATE_MAP.get(str(state_raw), str(state_raw))
            qid += 1
            questions.append({
                "id": f"q{qid:03d}",
                "subject_name": name,
                "subject_path": str(memory),
                "field": "forging_state",
                "query": f"Quel est l'état (forging_state) du subject {name} ?",
                "gold": state,
            })

        # type
        type_v = fm.get("type")
        if type_v:
            qid += 1
            questions.append({
                "id": f"q{qid:03d}",
                "subject_name": name,
                "subject_path": str(memory),
                "field": "type",
                "query": f"Quel est le type du subject {name} ?",
                "gold": str(type_v),
            })

        # horizon
        horizon = fm.get("horizon")
        if horizon:
            qid += 1
            questions.append({
                "id": f"q{qid:03d}",
                "subject_name": name,
                "subject_path": str(memory),
                "field": "horizon",
                "query": f"Quel est l'horizon du subject {name} ?",
                "gold": str(horizon),
            })

        # linked_subjects (1er item)
        links = fm.get("linked_subjects") or []
        if isinstance(links, list) and links:
            first = str(links[0]).strip()
            if first:
                qid += 1
                questions.append({
                    "id": f"q{qid:03d}",
                    "subject_name": name,
                    "subject_path": str(memory),
                    "field": "linked_subjects",
                    "query": f"À quels subjects {name} est-il lié ?",
                    "gold": first,
                })

    if limit is not None and limit > 0:
        questions = questions[:limit]

    return questions


def cmd_prepare(args):
    project_dir = get_project_dir()
    subjects = find_subjects(project_dir)
    questions = generate_questions(subjects, limit=args.limit)

    corpus = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
        "subject_count": len(subjects),
        "question_count": len(questions),
        "questions": questions,
    }

    if args.out:
        Path(args.out).write_text(
            json.dumps(corpus, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"corpus écrit : {args.out} ({len(questions)} questions, "
              f"{len(subjects)} subjects)", file=sys.stderr)
    else:
        print(json.dumps(corpus, indent=2, ensure_ascii=False))

    return 0


# ----------------------------------------------------------------------------
# Retrievers déterministes
# ----------------------------------------------------------------------------

def retriever_r1_cascade(question, project_dir):
    """R1 — cascade canonique : SUBJECTS-INDEX.md → MEMORY.md du subject.

    Simule le parcours par défaut de Forge tel que décrit dans la doctrine
    `subject-pool.md` § « Lecture en cascade ». Étapes :
    1. Lire `entreprise/SUBJECTS-INDEX.md` pour trouver le path du subject.
    2. Ouvrir son MEMORY.md.
    3. Extraire la valeur du champ ciblé (frontmatter ou Quick).
    """
    name = question["subject_name"]
    field = question["field"]

    index_path = project_dir / "entreprise" / "SUBJECTS-INDEX.md"
    if not index_path.exists():
        return {"found": False, "error": "SUBJECTS-INDEX.md absent"}

    try:
        index_content = index_path.read_text(encoding="utf-8")
    except OSError as e:
        return {"found": False, "error": f"read error: {e}"}

    # Cherche une ligne `- **<name>** (...) — <path>`
    pattern = re.compile(
        rf"\*\*{re.escape(name)}\*\*[^—]*—\s*`([^`]+)`"
    )
    m = pattern.search(index_content)
    if not m:
        return {"found": False, "error": f"subject {name} absent de SUBJECTS-INDEX"}

    rel_path = m.group(1).strip().rstrip("/")
    memory_path = project_dir / rel_path / "MEMORY.md"
    if not memory_path.exists():
        return {"found": False, "error": f"MEMORY.md absent: {memory_path}"}

    fm = parse_frontmatter(memory_path)
    if not fm:
        return {"found": False, "error": "frontmatter parse failed"}

    return _extract_field_value(fm, memory_path, field)


def retriever_r2_grep_aggregated(question, project_dir, blob_cache):
    """R2 — grep agrégé : concatène tous les MEMORY.md en un blob, grep dessus.

    Simule un retrieval « MCP-style » où un serveur expose un index full-text
    plat. La précision est limitée par la résolution du paragraphe contenant
    le match.
    """
    name = question["subject_name"]
    field = question["field"]

    blob = blob_cache.get("blob")
    if blob is None:
        chunks = []
        for memory, _ in find_subjects(project_dir):
            try:
                chunks.append(f"\n\n# FILE: {memory}\n\n" + memory.read_text(encoding="utf-8"))
            except OSError:
                continue
        blob = "\n".join(chunks)
        blob_cache["blob"] = blob

    # Chercher le bloc commençant par `# FILE: ...<name>...` ou contenant `name: <name>`
    file_blocks = re.split(r"\n# FILE: ", blob)
    matching = [b for b in file_blocks if (f"name: {name}\n" in b or f"/{name}/" in b)]
    if not matching:
        return {"found": False, "error": f"aucun bloc ne matche {name}"}

    fm_text_match = re.search(r"---\n(.*?)\n---", matching[0], re.DOTALL)
    if not fm_text_match:
        return {"found": False, "error": "frontmatter introuvable dans le bloc"}

    # Reparse via le helper standard (on écrit le bloc dans un fichier temporaire mental)
    # On peut éviter ça en reusant parse_simple_yaml directement
    from forge_lib import parse_simple_yaml
    fm = parse_simple_yaml(fm_text_match.group(1))

    # Récupère le memory_path à partir du # FILE: header
    first_line = matching[0].split("\n", 1)[0].strip()
    memory_path = Path(first_line) if first_line else None

    return _extract_field_value(fm, memory_path, field)


def retriever_r3_filesystem_grep(question, project_dir):
    """R3 — grep filesystem direct : `grep -lr "name:" subjects/**/MEMORY.md`.

    Simule un retrieval Unix natif sans index préalable. La logique est :
    1. grep pour trouver le MEMORY.md qui contient `name: <name>` dans son frontmatter.
    2. Ouvrir et parser le frontmatter.
    """
    name = question["subject_name"]
    field = question["field"]

    try:
        result = subprocess.run(
            ["grep", "-l", "-r", f"^name: {name}$",
             "--include=MEMORY.md", str(project_dir)],
            capture_output=True, text=True, timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return {"found": False, "error": f"grep error: {e}"}

    paths = [Path(p) for p in result.stdout.strip().split("\n") if p.strip()]
    # Filtrer les exclusions
    paths = [p for p in paths
             if not any(part in EXCLUDE_DIRS or part.startswith("_archive")
                        for part in p.parts)]

    if not paths:
        return {"found": False, "error": f"aucun MEMORY.md avec name: {name}"}

    memory_path = paths[0]
    fm = parse_frontmatter(memory_path)
    if not fm:
        return {"found": False, "error": "frontmatter parse failed"}

    return _extract_field_value(fm, memory_path, field)


def _extract_field_value(fm, memory_path, field):
    """Extrait la valeur du champ ciblé depuis le frontmatter.

    Pour `linked_subjects`, retourne la liste sérialisée (chacun des items
    contribue au matching substring).
    """
    if field == "linked_subjects":
        v = fm.get("linked_subjects") or []
        if isinstance(v, list):
            answer = ", ".join(str(x) for x in v)
        else:
            answer = str(v)
        return {"found": True, "answer": answer, "memory_path": str(memory_path)}

    if field == "forging_state":
        raw = fm.get("forging_state")
        if raw is None:
            return {"found": False, "error": "forging_state absent"}
        answer = LEGACY_STATE_MAP.get(str(raw), str(raw))
        return {"found": True, "answer": answer, "memory_path": str(memory_path)}

    raw = fm.get(field)
    if raw is None:
        return {"found": False, "error": f"{field} absent"}
    return {"found": True, "answer": str(raw), "memory_path": str(memory_path)}


# ----------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------

def score(question, retrieval):
    """Compare la réponse retrouvée au gold answer.

    - exact : gold.lower() == answer.lower() OU gold.lower() in answer.lower()
              (pour les linked_subjects où la réponse contient plusieurs items)
    - substring : tous les tokens du gold sont présents dans la réponse
    """
    if not retrieval.get("found"):
        return {"exact": False, "substring": False}

    gold = str(question["gold"]).strip().lower()
    answer = str(retrieval.get("answer", "")).strip().lower()

    exact = (gold == answer) or (gold in answer)
    substring = all(tok in answer for tok in gold.split() if tok)

    return {"exact": exact, "substring": substring}


# ----------------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------------

def run_retrievers(corpus, retrievers, project_dir):
    """Exécute chaque retriever sur chaque question. Renvoie les résultats."""
    blob_cache = {}
    results = []

    retriever_map = {
        "R1": ("cascade", lambda q: retriever_r1_cascade(q, project_dir)),
        "R2": ("grep-aggregated", lambda q: retriever_r2_grep_aggregated(q, project_dir, blob_cache)),
        "R3": ("filesystem-grep", lambda q: retriever_r3_filesystem_grep(q, project_dir)),
    }

    for question in corpus["questions"]:
        for r_key in retrievers:
            if r_key not in retriever_map:
                continue
            r_label, r_fn = retriever_map[r_key]
            t0 = time.perf_counter()
            try:
                retrieval = r_fn(question)
            except Exception as e:
                retrieval = {"found": False, "error": f"exception: {type(e).__name__}: {e}"}
            elapsed_ms = int((time.perf_counter() - t0) * 1000)

            scoring = score(question, retrieval)
            results.append({
                "question_id": question["id"],
                "subject_name": question["subject_name"],
                "field": question["field"],
                "gold": question["gold"],
                "retriever": r_key,
                "retriever_label": r_label,
                "found": retrieval.get("found", False),
                "answer": retrieval.get("answer"),
                "error": retrieval.get("error"),
                "exact": scoring["exact"],
                "substring": scoring["substring"],
                "latency_ms": elapsed_ms,
            })

    return results


def cmd_run(args):
    project_dir = get_project_dir()
    corpus_path = Path(args.corpus)
    if not corpus_path.exists():
        print(f"corpus introuvable : {corpus_path}", file=sys.stderr)
        return 1

    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    retrievers = [r.strip().upper() for r in args.retrievers.split(",") if r.strip()]

    t0 = time.perf_counter()
    results = run_retrievers(corpus, retrievers, project_dir)
    total_ms = int((time.perf_counter() - t0) * 1000)

    output = {
        "version": 1,
        "ran_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
        "corpus_path": str(corpus_path),
        "retrievers": retrievers,
        "question_count": len(corpus["questions"]),
        "total_calls": len(results),
        "total_wallclock_ms": total_ms,
        "results": results,
    }

    if args.out:
        Path(args.out).write_text(
            json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"résultats écrits : {args.out} ({len(results)} calls, {total_ms} ms)",
              file=sys.stderr)
    else:
        print(json.dumps(output, indent=2, ensure_ascii=False))

    return 0


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

def aggregate(results):
    """Agrège les résultats par retriever : taux exact, substring, latence p50/p95."""
    per_r = {}
    for r in results:
        key = r["retriever"]
        per_r.setdefault(key, []).append(r)

    summary = {}
    for r_key, items in per_r.items():
        n = len(items)
        exact_n = sum(1 for it in items if it["exact"])
        sub_n = sum(1 for it in items if it["substring"])
        err_n = sum(1 for it in items if it.get("error"))
        latencies = sorted(it["latency_ms"] for it in items)
        p50 = latencies[n // 2] if n else 0
        p95 = latencies[min(n - 1, int(n * 0.95))] if n else 0
        summary[r_key] = {
            "n": n,
            "exact_count": exact_n,
            "exact_rate": round(exact_n / n, 3) if n else 0.0,
            "substring_count": sub_n,
            "substring_rate": round(sub_n / n, 3) if n else 0.0,
            "errors": err_n,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "latency_total_ms": sum(latencies),
            "retriever_label": items[0]["retriever_label"] if items else "",
        }
    return summary


def render_md(output_data, summary):
    lines = []
    lines.append(f"# Bench Forge — {output_data['ran_at']}")
    lines.append("")
    lines.append(f"- Project : `{output_data['project_dir']}`")
    lines.append(f"- Corpus : `{output_data['corpus_path']}`")
    lines.append(f"- Retrievers : {', '.join(output_data['retrievers'])}")
    lines.append(f"- Questions : {output_data['question_count']}")
    lines.append(f"- Total calls : {output_data['total_calls']}")
    lines.append(f"- Wall-clock : {output_data['total_wallclock_ms']} ms")
    lines.append("")
    lines.append("## Récap par retriever")
    lines.append("")
    lines.append("| Retriever | Label | Exact | Substring | Erreurs | Latence p50 | Latence p95 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r_key in sorted(summary.keys()):
        s = summary[r_key]
        lines.append(
            f"| {r_key} | {s['retriever_label']} | "
            f"{s['exact_count']}/{s['n']} ({s['exact_rate']*100:.0f}%) | "
            f"{s['substring_count']}/{s['n']} ({s['substring_rate']*100:.0f}%) | "
            f"{s['errors']} | {s['latency_p50_ms']} ms | {s['latency_p95_ms']} ms |"
        )
    lines.append("")
    lines.append("## Verdict")
    lines.append("")
    best_exact = max(summary.items(), key=lambda kv: kv[1]["exact_rate"])
    fastest = min(summary.items(), key=lambda kv: kv[1]["latency_p50_ms"])
    lines.append(f"- Meilleur exact-match : **{best_exact[0]}** ({best_exact[1]['retriever_label']}) "
                 f"— {best_exact[1]['exact_rate']*100:.0f}%")
    lines.append(f"- Plus rapide (p50) : **{fastest[0]}** ({fastest[1]['retriever_label']}) "
                 f"— {fastest[1]['latency_p50_ms']} ms")
    lines.append("")
    return "\n".join(lines)


def cmd_report(args):
    results_path = Path(args.results)
    if not results_path.exists():
        print(f"résultats introuvables : {results_path}", file=sys.stderr)
        return 1

    output_data = json.loads(results_path.read_text(encoding="utf-8"))
    summary = aggregate(output_data["results"])

    if args.format == "json":
        print(json.dumps({"summary": summary, "meta": {k: v for k, v in output_data.items()
                                                       if k != "results"}},
                         indent=2, ensure_ascii=False))
    else:
        print(render_md(output_data, summary))

    return 0


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Forge subject pool retriever bench (deterministic).")
    sub = parser.add_subparsers(dest="cmd")

    p_prep = sub.add_parser("prepare", help="Generate a corpus from existing subjects")
    p_prep.add_argument("--limit", type=int, default=None,
                        help="Cap on the number of questions")
    p_prep.add_argument("--out", default=None, help="Output JSON path")

    p_run = sub.add_parser("run", help="Execute retrievers on a corpus")
    p_run.add_argument("--corpus", required=True, help="Corpus JSON path")
    p_run.add_argument("--retrievers", default="R1,R2,R3",
                       help="Comma-separated list (R1=cascade, R2=grep-aggregated, R3=filesystem-grep)")
    p_run.add_argument("--out", default=None, help="Output JSON path")

    p_rep = sub.add_parser("report", help="Format bench results")
    p_rep.add_argument("--results", required=True, help="Results JSON path")
    p_rep.add_argument("--format", choices=("md", "json"), default="md")

    args = parser.parse_args()

    if args.cmd == "prepare":
        sys.exit(cmd_prepare(args))
    elif args.cmd == "run":
        sys.exit(cmd_run(args))
    elif args.cmd == "report":
        sys.exit(cmd_report(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
