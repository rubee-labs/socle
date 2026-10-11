#!/usr/bin/env python3
"""convert_lib.py — conversion d'un MEMORY.md au format unique (SOCLE 0.7.0).

Design 2026-10-10 §3. Fonctions pures texte → texte. Règle absolue : aucune
ligne de contenu n'est supprimée. Une section sans place dans le format unique
va dans `## Détails` sous `### <titre>`, ses titres internes descendent d'un
niveau. Le bloc okf-links est recopié tel quel, en fin de fichier.
"""

import re
import unicodedata

CANONICAL_SECTIONS = ["Quick", "Doctrine en vigueur", "Décisions actives", "Règles apprises", "Détails", "Liens"]
OKF_START = "<!-- okf-links:start -->"
_FM_RE = re.compile(r"^---\n(.*?)\n---\n?", re.DOTALL)


def _fold(title):
    """Clé d'appariement d'un titre : minuscules, sans accents (« Regles apprises » = « Règles apprises »)."""
    nfkd = unicodedata.normalize("NFKD", title.strip().lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _frontmatter(text):
    m = _FM_RE.match(text)
    if not m:
        return [], text
    return m.group(1).split("\n"), text[m.end():]


def _has_key(fm_lines, key):
    return any(re.match(rf"^{re.escape(key)}\s*:", l) for l in fm_lines)


def _split_sections(body):
    """(préambule, [(titre, lignes)]). Ignore les `## ` dans les blocs de code."""
    preamble, sections, current, in_fence = [], [], None, False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = (line[3:].strip(), [])
            sections.append(current)
            continue
        (current[1] if current else preamble).append(line)
    return preamble, sections


def _demote(lines):
    out, in_fence = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and re.match(r"^#{1,5} ", line):
            line = "#" + line
        out.append(line)
    return out


def _trim(lines):
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _header(fm_lines, *, name, type_name, today):
    fm = list(fm_lines)
    for key, value in (("name", name), ("type", type_name), ("forging_state", "actif"), ("derniere_maj", today)):
        if not _has_key(fm, key):
            fm.append(f"{key}: {value}")
    return "---\n" + "\n".join(fm) + "\n---\n"


def new_memory_text(*, name, type_name, today):
    """MEMORY.md minimal d'un nouveau subject ; /documente rédige le Quick ensuite."""
    return _header([], name=name, type_name=type_name, today=today) + f"\n# {name}\n\n## Quick\n"


def convert_memory_text(text, *, name, type_name, today):
    fm_lines, body = _frontmatter(text)
    okf_tail = ""
    idx = body.find(OKF_START)
    if idx >= 0:
        body, okf_tail = body[:idx], body[idx:]
    preamble, sections = _split_sections(body)

    canon = {_fold(c): c for c in CANONICAL_SECTIONS}
    kept = {c: [] for c in CANONICAL_SECTIONS}
    present = set()
    extras = []
    for title, lines in sections:
        key = canon.get(_fold(title))
        if key and not (key == "Liens" and okf_tail):
            present.add(key)
            kept[key].extend(_trim(lines) + [""])
        else:
            extras.extend([f"### {title}", ""] + _trim(_demote(lines)) + [""])

    out = [_header(fm_lines, name=name, type_name=type_name, today=today).rstrip("\n")]
    pre = _trim(preamble)
    if pre:
        out += [""] + pre
    for key in CANONICAL_SECTIONS:
        content = _trim(kept[key])
        if key == "Détails":
            if key in present or extras:
                details = content + ([""] if content and extras else []) + _trim(extras)
                out += ["", f"## {key}", ""] + details
        elif key == "Quick" or key in present:
            out += ["", f"## {key}"] + ([""] + content if content else [])
    text_out = "\n".join(out).rstrip("\n") + "\n"
    if okf_tail:
        text_out += "\n" + okf_tail.rstrip("\n") + "\n"
    return text_out
