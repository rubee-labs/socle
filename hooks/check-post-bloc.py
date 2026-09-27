#!/usr/bin/env python3
"""check-post-bloc.py — hook Stop de SOCLE : vérifie les items mécaniques de la checklist post-bloc.

Doctrine : `rules/post-bloc.md` (discussion → décision → memory → commit → push, ✅/⏭️ affichés).
Les items memory / commit / push sont vérifiés par code, pas par prose. Le hook ne synthétise
rien et ne committe rien : il lit l'état de git et des MEMORY.md et rend la main à Claude avec
une raison courte.

Pour chaque fichier modifié PENDANT la session (git status ∩ mtime ≥ début de session) :
  - non committé                                  → item commit/push manquant (bloque)
  - MEMORY.md de l'entité propriétaire (dossier ancêtre le plus proche qui contient un
    MEMORY.md) avec `derniere_maj` ≠ aujourd'hui  → item memory manquant (bloque)
  - MEMORY.md > plafond (`memory_max_kb` du frontmatter, défaut 8)
                                                  → avertissement ajouté à la raison

ACTIVATION VOLONTAIRE : le hook ne fait rien tant que le `.forge.yaml` à la racine du dépôt ne
contient pas `post_bloc: true` (ou que SOCLE_POST_BLOC=1). Un plugin installé pour l'utilisateur
se charge dans tous ses projets : sans interrupteur, il bloquerait partout.

Configuration `.forge.yaml` (toutes optionnelles) :
    post_bloc: true
    post_bloc_exclusions: ["entreprise/logs/", "data/cache/"]   # préfixes ignorés

Garde-fous :
  - `stop_hook_active` vrai → silence (pas de boucle : Claude a déjà été relancé une fois).
  - même ensemble de fichiers déjà signalé dans cette session → silence (bloque UNE fois).
  - jamais exit 2, jamais d'exception visible : toute erreur = silence.
  - exclus d'office : index du scanner (SUBJECTS-INDEX.md, SUBJECT-POOL-METRICS.md), logs,
    caches Python, .claude/settings.local.json.
  - noms de fichiers accentués lus tels quels (git status -z, core.quotepath=false).

Entrée : JSON hook Claude Code sur stdin (session_id, transcript_path, cwd, stop_hook_active).
Sortie : rien, ou `{"decision": "block", "reason": ...}`.
Journal : <git-dir>/socle/post_bloc_hook.log (SOCLE_POST_BLOC_LOG ou CE_POST_BLOC_LOG pour le déplacer).
"""

import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_MAX_KB = 8
EXCLUDED_BASENAMES = {"SUBJECTS-INDEX.md", "SUBJECT-POOL-METRICS.md"}
EXCLUDED_FILES = {".claude/settings.local.json"}
EXCLUDED_PARTS = ("__pycache__", ".git")
EXCLUDED_SUFFIXES = (".pyc", ".log")

RE_DERNIERE_MAJ = re.compile(r"^derniere_maj:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.M)
RE_MAX_KB = re.compile(r"^memory_max_kb:\s*(\d+)", re.M)
RE_ACTIF = re.compile(r"^post_bloc:\s*(true|yes|oui)\s*(#.*)?$", re.M | re.I)
RE_EXCLUSIONS = re.compile(r"^post_bloc_exclusions:\s*\[(.*?)\]", re.M)


def _git(root, *args, timeout=5):
    return subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotepath=false", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _config(root):
    """(actif, exclusions) lus dans le .forge.yaml racine."""
    force = os.environ.get("SOCLE_POST_BLOC", "").strip().lower() in ("1", "true", "yes", "oui")
    try:
        texte = (root / ".forge.yaml").read_text(encoding="utf-8")
    except OSError:
        return force, ()
    exclusions = ()
    m = RE_EXCLUSIONS.search(texte)
    if m:
        exclusions = tuple(e.strip().strip("\"'") for e in m.group(1).split(",") if e.strip().strip("\"'"))
    return force or bool(RE_ACTIF.search(texte)), exclusions


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

def _log_path(root):
    custom = os.environ.get("SOCLE_POST_BLOC_LOG") or os.environ.get("CE_POST_BLOC_LOG")
    if custom:
        return Path(custom)
    try:
        git_dir = _git(root, "rev-parse", "--absolute-git-dir").stdout.strip()
    except Exception:
        git_dir = ""
    return Path(git_dir or (root / ".git")) / "socle" / "post_bloc_hook.log"


def _journal(root, entry):
    try:
        p = _log_path(root)
        p.parent.mkdir(parents=True, exist_ok=True)
        entry["ts"] = _dt.datetime.now().isoformat(timespec="seconds")
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _deja_signale(root, session, empreinte):
    try:
        p = _log_path(root)
        if not p.is_file():
            return False
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if e.get("event") == "block" and e.get("session_id") == session and e.get("empreinte") == empreinte:
                return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# Git et session
# ---------------------------------------------------------------------------

def _repo_root(payload):
    for c in (os.environ.get("CLAUDE_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if not c:
            continue
        try:
            out = _git(c, "rev-parse", "--show-toplevel", timeout=3)
        except Exception:
            continue
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    return None


def _fichiers_non_commites(root):
    """Chemins non committés, accents compris (sortie -z : séparateur NUL, aucun échappement)."""
    out = _git(root, "status", "--porcelain", "-z", "--untracked-files=all")
    if out.returncode != 0:
        return []
    jetons = out.stdout.split("\0")
    files, i = [], 0
    while i < len(jetons):
        entree = jetons[i]
        i += 1
        if len(entree) < 4:
            continue
        statut, chemin = entree[:2], entree[3:]
        if statut[0] in "RC":  # renommage / copie : le jeton suivant est l'ancien chemin
            i += 1
        files.append(chemin)
    return files


def _exclu(rel, exclusions):
    if rel in EXCLUDED_FILES or rel.rsplit("/", 1)[-1] in EXCLUDED_BASENAMES:
        return True
    if exclusions and rel.startswith(exclusions):
        return True
    if any(part in rel.split("/") for part in EXCLUDED_PARTS):
        return True
    return rel.endswith(EXCLUDED_SUFFIXES)


def _debut_session(payload):
    """Timestamp (epoch) du début de session : 1re ligne du transcript, sinon sa date de création."""
    chemin = payload.get("transcript_path")
    if not chemin or not os.path.isfile(chemin):
        return None
    try:
        with open(chemin, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    break
                ts = e.get("timestamp")
                if ts:
                    return _dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                break
    except Exception:
        pass
    try:
        st = os.stat(chemin)
        return getattr(st, "st_birthtime", st.st_ctime)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Entités et MEMORY.md
# ---------------------------------------------------------------------------

def _entite(root, rel):
    """Dossier ancêtre le plus proche contenant un MEMORY.md (relatif à root), ou None."""
    p = (root / rel).parent
    while True:
        try:
            p.relative_to(root)
        except ValueError:
            return None
        if (p / "MEMORY.md").is_file():
            return p.relative_to(root).as_posix() or "."
        if p == root:
            return None
        p = p.parent


def _analyser_memory(root, entite, aujourd_hui):
    """Retourne (derniere_maj_ok, taille_kb, max_kb, derniere_maj)."""
    md = root / entite / "MEMORY.md"
    try:
        raw = md.read_bytes()
    except OSError:
        return True, 0, DEFAULT_MAX_KB, None
    taille_kb = len(raw) / 1024
    head = raw[:4000].decode("utf-8", errors="ignore")
    m_kb = RE_MAX_KB.search(head)
    max_kb = int(m_kb.group(1)) if m_kb else DEFAULT_MAX_KB
    m_maj = RE_DERNIERE_MAJ.search(head)
    derniere_maj = m_maj.group(1) if m_maj else None
    ok = derniere_maj is None or derniere_maj == aujourd_hui
    return ok, taille_kb, max_kb, derniere_maj


# ---------------------------------------------------------------------------
# Cœur
# ---------------------------------------------------------------------------

def evaluer(payload, aujourd_hui=None):
    """Calcule la sortie du hook (dict) ou None. Pur : ne journalise pas."""
    if payload.get("stop_hook_active"):
        return None
    root = _repo_root(payload)
    if root is None:
        return None
    actif, exclusions = _config(root)
    if not actif:
        return None
    debut = _debut_session(payload)
    if debut is None:
        return None
    aujourd_hui = aujourd_hui or _dt.date.today().isoformat()

    touches = []
    for rel in _fichiers_non_commites(root):
        if _exclu(rel, exclusions):
            continue
        try:
            mtime = (root / rel).stat().st_mtime
        except OSError:
            continue
        if mtime + 1 < debut:
            continue  # modifié avant la session : pas à cette session de le committer
        touches.append(rel)
    if not touches:
        return None

    par_entite, hors_entite = {}, []
    for rel in touches:
        ent = _entite(root, rel)
        if ent is None:
            hors_entite.append(rel)
        else:
            par_entite.setdefault(ent, []).append(rel)

    blocs, avertissements = [], []
    for ent, fichiers in sorted(par_entite.items()):
        maj_ok, taille_kb, max_kb, derniere_maj = _analyser_memory(root, ent, aujourd_hui)
        details = [f"{len(fichiers)} fichier(s) non committé(s)"]
        if not maj_ok:
            details.append(f"MEMORY.md derniere_maj {derniere_maj} ≠ {aujourd_hui}")
        if taille_kb > max_kb:
            avertissements.append(f"{ent}/MEMORY.md {taille_kb:.1f} Ko > {max_kb} Ko → re-synthèse bornée via /documente {ent}")
        blocs.append(f"{ent} ({' ; '.join(details)})")
    if hors_entite:
        apercu = ", ".join(hors_entite[:3]) + (" …" if len(hors_entite) > 3 else "")
        blocs.append(f"hors entité : {len(hors_entite)} fichier(s) non committé(s) ({apercu})")

    empreinte = hashlib.sha1("\n".join(sorted(touches)).encode("utf-8")).hexdigest()[:12]
    reason = (
        "Checklist post-bloc incomplète — " + " ; ".join(blocs)
        + ". Terminer memory (/documente <path>) → commit ciblé → push, ou justifier ⏭️ en 1 ligne."
    )
    if avertissements:
        reason += " Avertissement : " + " ; ".join(avertissements) + "."
    return {"decision": "block", "reason": reason, "empreinte": empreinte, "fichiers": touches, "root": root}


def main():
    try:
        brut = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        payload = json.loads(brut) if brut and brut.strip() else {}
    except Exception:
        return
    if not isinstance(payload, dict):
        return
    try:
        resultat = evaluer(payload)
    except Exception:
        return
    if not resultat:
        return
    root = resultat["root"]
    session = payload.get("session_id")
    if _deja_signale(root, session, resultat["empreinte"]):
        return
    _journal(root, {
        "event": "block",
        "session_id": session,
        "empreinte": resultat["empreinte"],
        "fichiers": resultat["fichiers"],
        "cwd": payload.get("cwd") or "",
    })
    sys.stdout.write(json.dumps({"decision": "block", "reason": resultat["reason"]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
    sys.exit(0)
