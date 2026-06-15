#!/usr/bin/env python3
"""
graph_engine.py — Renderer du graphe Forge en HTML interactif (vis.js).

Équivalent natif Forge du Graph view Obsidian, sans dépendre d'Obsidian. Produit
un fichier HTML self-contained (vis.js inline via CDN) qui affiche :

- les subjects comme nœuds (couleur par `type`, forme par `forging_state`)
- les `linked_subjects` typés comme arêtes (label = nom de la relation extraite
  via `autolink_engine`)
- des filtres par état (actif / mature / archived) et par type
- au hover : tooltip avec nom, type, état, last_event, chemin
- au click : ouvre le MEMORY.md correspondant dans VS Code via URL `vscode://`

Sous-commandes :
- render [--out FILE] [--no-open]   Génère le HTML, l'ouvre dans Chrome par défaut
- stats                              Compte nœuds et arêtes (debug rapide)

Stdlib only. Réutilise `forge_lib`, `autolink_engine`. Pas d'appel LLM.

Motivation : Forge respecte la doctrine « memory at the edge » (les MEMORY.md
sont co-localisés avec le code qu'ils décrivent). Cette co-localisation rend
Obsidian inutilisable comme lecteur (cf. retour Benjamin 2026-05-26). Un
renderer HTML natif dédié au pattern Forge contourne le problème — pas besoin
d'extraire la mémoire dans un vault dédié juste pour la visualiser.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

_VIS_NETWORK_JS = (Path(__file__).parent / "_assets" / "vis-network.min.js").read_text(encoding="utf-8")

from forge_lib import (
    days_since,
    get_project_dir,
    parse_frontmatter,
    parse_subject_slug,
)
from autolink_engine import _build_full_graph, _load_type_index

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

EXCLUDE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".claude",
                "templates", "fixtures"}

LEGACY_STATE_MAP = {
    "seed": "actif", "debating": "actif", "tentative": "actif",
    "stress_testing": "mature", "doctrine": "mature",
    "in_service": "mature", "under_review": "mature",
    "archived": "archived", "actif": "actif", "mature": "mature",
}

# Shape per cycle γ state. vis.js shapes: dot, square, triangle, diamond, star,
# cross, hexagon, circle, ellipse, box.
SHAPE_BY_STATE = {
    "actif": "dot",
    "mature": "diamond",
    "archived": "triangle",
}


def _color_for_type(type_name):
    """Couleur stable dérivée du hash du nom de type. Pas d'ordre fixe — chaque
    type a sa couleur propre, persistante entre runs."""
    if not type_name:
        return "#9a9a9a"
    h = hashlib.md5(type_name.encode()).hexdigest()
    # Use HSL with low-medium saturation, mid lightness — pleasant pastel-ish.
    hue = int(h[:4], 16) % 360
    return f"hsl({hue}, 55%, 55%)"


# ----------------------------------------------------------------------------
# Subject discovery (reuse pattern from forge_scanner / bench_engine)
# ----------------------------------------------------------------------------

def _normalize_state(raw):
    return LEGACY_STATE_MAP.get(str(raw or ""), "actif")


def _find_subject_memories(project_dir):
    """Itère sur tous les MEMORY.md de subjects avec frontmatter parsé."""
    for memory in project_dir.rglob("MEMORY.md"):
        if any(part in EXCLUDE_DIRS or part.startswith("_archive")
               for part in memory.parts):
            continue
        fm = parse_frontmatter(memory)
        if not fm or "forging_state" not in fm:
            continue
        yield memory, fm


def build_graph_data(project_dir):
    """Construit la structure nœuds + arêtes prête à sérialiser en JSON.

    Returns: dict {nodes, edges, types, states, stats, generated_at}.
    """
    nodes = []
    edges = []
    types_seen = set()
    states_seen = set()

    # 1. Collect nodes from MEMORY.md frontmatters.
    slug_to_path = {}
    for memory, fm in _find_subject_memories(project_dir):
        name = str(fm.get("name") or memory.parent.name)
        subject_type = str(fm.get("type") or "")
        state = _normalize_state(fm.get("forging_state"))
        slug = f"{subject_type}:{name}" if subject_type else name
        slug_to_path[slug] = str(memory)

        types_seen.add(subject_type or "(no type)")
        states_seen.add(state)

        last_event = fm.get("last_event")
        last_event_str = ""
        if isinstance(last_event, dict):
            last_event_str = (
                f"{last_event.get('date', '')} — "
                f"{last_event.get('type', '')}"
            ).strip(" —")

        horizon = str(fm.get("horizon") or "")
        archived_at = fm.get("archived_at")

        # Compose tooltip HTML (vis.js renders title HTML if title is HTMLElement;
        # plain text fallback works fine and is safer).
        rel_path = (
            str(memory.relative_to(project_dir))
            if memory.is_relative_to(project_dir) else str(memory)
        )
        title_lines = [
            f"{slug}",
            f"État : {state}",
        ]
        if horizon:
            title_lines.append(f"Horizon : {horizon}")
        if last_event_str:
            title_lines.append(f"Last event : {last_event_str}")
        if archived_at:
            title_lines.append(f"Archivé : {archived_at}")
        title_lines.append(f"Path : {rel_path}")

        nodes.append({
            "id": slug,
            "label": name,
            "group": subject_type or "(no type)",
            "title": "\n".join(title_lines),
            "shape": SHAPE_BY_STATE.get(state, "dot"),
            "color": _color_for_type(subject_type),
            "state": state,
            "type": subject_type or "(no type)",
            "memory_path": str(memory),
            "rel_path": rel_path,
        })

    # 2. Collect edges from autolink (typed graph).
    by_slug, _incoming, known_types = _build_full_graph(project_dir)
    edge_id = 0
    for source_slug, info in by_slug.items():
        for edge in info["edges_out"]:
            # Strip inline YAML comments and double-space separators that some
            # subjects use after the linked_subjects entry (eg.
            # "supplier:weifang  # via expedition #299").
            raw = edge["target_slug"]
            cleaned = raw.split("#", 1)[0].strip()
            if "  " in cleaned:
                cleaned = cleaned.split("  ", 1)[0].strip()

            target = parse_subject_slug(cleaned, known_types=known_types)
            if target["type"] and target["name"]:
                target_canonical = f"{target['type']}:{target['name']}"
            else:
                target_canonical = cleaned
            edge_id += 1
            edges.append({
                "id": f"e{edge_id}",
                "from": source_slug,
                "to": target_canonical,
                "label": edge["name"] if edge["name"] != "linked" else "",
                "arrows": "to",
            })

    # 3. Build an alias map for node ids so edges that reference a subject by
    #    its short name (without the type-prefix) still resolve. Forge subjects
    #    have inconsistent naming in the repo: some files use `name:
    #    supplier-weifang` (slug = `supplier:supplier-weifang`), while some
    #    linked_subjects reference them as `supplier:weifang`.
    node_id_set = {n["id"] for n in nodes}
    alias_map = {}
    for n in nodes:
        canonical = n["id"]
        type_name = n["type"]
        if not type_name or type_name == "(no type)":
            continue
        label = n["label"]
        prefix = f"{type_name}-"
        # Variant 1: label starts with "type-" -> register "type:label_without_prefix"
        if label.startswith(prefix):
            short = label[len(prefix):]
            alt = f"{type_name}:{short}"
            if alt != canonical and alt not in node_id_set:
                alias_map[alt] = canonical
        # Variant 2: label does NOT start with "type-" -> register "type:type-label"
        else:
            alt = f"{type_name}:{prefix}{label}"
            if alt != canonical and alt not in node_id_set:
                alias_map[alt] = canonical

    # Remap edge endpoints through the alias map. Drop edges whose endpoints
    # cannot be resolved at all (likely typos / archived subjects).
    resolved_edges = []
    dropped = 0
    for e in edges:
        src = e["from"] if e["from"] in node_id_set else alias_map.get(e["from"])
        dst = e["to"] if e["to"] in node_id_set else alias_map.get(e["to"])
        if not src or not dst:
            dropped += 1
            continue
        e["from"] = src
        e["to"] = dst
        resolved_edges.append(e)
    edges = resolved_edges

    return {
        "nodes": nodes,
        "edges": edges,
        "types": sorted(types_seen),
        "states": sorted(states_seen),
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "type_count": len(types_seen),
        },
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project_dir": str(project_dir),
    }


# ----------------------------------------------------------------------------
# HTML template
# ----------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Forge graph — __PROJECT__</title>
<script>__VIS_NETWORK_JS__</script>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  body { display: flex; }
  aside { width: 260px; min-width: 260px; background: #1a0f0a; color: #f5e6d0; padding: 18px 16px; overflow-y: auto; }
  aside h1 { font-size: 16px; margin: 0 0 4px; font-weight: 600; }
  aside .meta { font-size: 11px; opacity: 0.65; margin-bottom: 18px; }
  aside h2 { font-size: 12px; text-transform: uppercase; letter-spacing: 0.8px; color: #f5b46c; margin: 18px 0 6px; }
  aside label { display: flex; align-items: center; font-size: 13px; padding: 4px 0; cursor: pointer; user-select: none; }
  aside label input { margin-right: 8px; }
  aside .swatch { width: 12px; height: 12px; border-radius: 2px; margin-right: 8px; display: inline-block; }
  aside .stat { font-size: 12px; opacity: 0.8; margin: 4px 0; }
  aside button { background: #3d1f0d; color: #f5e6d0; border: 1px solid #5a3818; border-radius: 4px; padding: 6px 10px; font-size: 12px; cursor: pointer; margin-top: 8px; width: 100%; }
  aside button:hover { background: #5a3818; }
  aside .info { font-size: 11px; opacity: 0.6; line-height: 1.4; margin-top: 16px; }
  #graph { flex: 1; height: 100vh; background: #faf8f5; }
</style>
</head>
<body>

<aside>
  <h1>Forge graph</h1>
  <div class="meta">Généré le __GENERATED_AT__</div>
  <div class="stat">Subjects : <span id="stat-nodes">0</span></div>
  <div class="stat">Liens : <span id="stat-edges">0</span></div>

  <h2>États (γ)</h2>
  <div id="state-filters"></div>

  <h2>Types</h2>
  <div id="type-filters"></div>

  <button id="reset-view">Réinitialiser la vue</button>

  <div class="info">
    Survol = détails. Clic sur un nœud = ouvre le MEMORY.md dans VS Code.
    Drag = déplacer un nœud. Molette = zoom.
  </div>
</aside>

<div id="graph"></div>

<script>
  const RAW = __DATA__;

  // Active sets MUST be declared before vis.DataView (its constructor calls
  // the filter callbacks immediately to compute initial state).
  const activeStates = new Set(RAW.states);
  const activeTypes = new Set(RAW.types);

  const nodes = new vis.DataSet(RAW.nodes);
  const edges = new vis.DataSet(RAW.edges);

  function filterNode(n) {
    return activeStates.has(n.state) && activeTypes.has(n.type);
  }
  function filterEdge(e) {
    const fromNode = nodes.get(e.from);
    const toNode = nodes.get(e.to);
    if (!fromNode || !toNode) return false;
    return filterNode(fromNode) && filterNode(toNode);
  }

  const nodesView = new vis.DataView(nodes, { filter: filterNode });
  const edgesView = new vis.DataView(edges, { filter: filterEdge });

  const container = document.getElementById("graph");
  const data = { nodes: nodesView, edges: edgesView };
  const options = {
    physics: { stabilization: { iterations: 200 }, barnesHut: { gravitationalConstant: -3000, springLength: 140 } },
    nodes: {
      borderWidth: 1.5,
      font: { color: "#1f1610", size: 12, face: "-apple-system, BlinkMacSystemFont, sans-serif" },
      size: 16,
    },
    edges: {
      color: { color: "#8a7860", opacity: 0.55 },
      font: { color: "#5a3818", size: 9, background: "rgba(250, 248, 245, 0.6)", strokeWidth: 0 },
      smooth: { enabled: true, type: "dynamic", roundness: 0.25 },
      arrows: { to: { enabled: true, scaleFactor: 0.6 } },
    },
    interaction: { hover: true, tooltipDelay: 120, zoomView: true, dragView: true },
  };
  const network = new vis.Network(container, data, options);

  // ---- Filters UI ----
  function buildStateFilters() {
    const root = document.getElementById("state-filters");
    RAW.states.forEach(state => {
      const label = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {
        if (cb.checked) activeStates.add(state); else activeStates.delete(state);
        nodesView.refresh();
        edgesView.refresh();
        updateCounts();
      });
      label.appendChild(cb);
      label.appendChild(document.createTextNode(state));
      root.appendChild(label);
    });
  }
  function buildTypeFilters() {
    const root = document.getElementById("type-filters");
    const colorByType = {};
    RAW.nodes.forEach(n => { colorByType[n.type] = n.color; });
    RAW.types.forEach(type => {
      const label = document.createElement("label");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = true;
      cb.addEventListener("change", () => {
        if (cb.checked) activeTypes.add(type); else activeTypes.delete(type);
        nodesView.refresh();
        edgesView.refresh();
        updateCounts();
      });
      const swatch = document.createElement("span");
      swatch.className = "swatch";
      swatch.style.background = colorByType[type] || "#9a9a9a";
      label.appendChild(cb);
      label.appendChild(swatch);
      label.appendChild(document.createTextNode(type));
      root.appendChild(label);
    });
  }
  function updateCounts() {
    document.getElementById("stat-nodes").textContent = nodesView.length;
    document.getElementById("stat-edges").textContent = edgesView.length;
  }
  document.getElementById("reset-view").addEventListener("click", () => {
    network.fit({ animation: { duration: 400, easingFunction: "easeInOutQuad" } });
  });

  // ---- Click -> open MEMORY.md in VS Code ----
  network.on("click", params => {
    if (params.nodes.length === 0) return;
    const nodeId = params.nodes[0];
    const node = nodes.get(nodeId);
    if (node && node.memory_path) {
      // vscode:// URL scheme. Requires VS Code's URL handler to be registered (default on macOS).
      window.location.href = "vscode://file" + node.memory_path;
    }
  });

  // ---- Init ----
  buildStateFilters();
  buildTypeFilters();
  updateCounts();
</script>

</body>
</html>
"""


def render_html(graph_data):
    project_label = Path(graph_data["project_dir"]).name
    html = _HTML_TEMPLATE
    html = html.replace("__PROJECT__", project_label)
    html = html.replace("__GENERATED_AT__", graph_data["generated_at"])
    # vis-network.min.js inlined as a single self-contained file (no CDN call,
    # no corporate proxy issue, no mixed-content blocking).
    html = html.replace("__VIS_NETWORK_JS__", _VIS_NETWORK_JS)
    # Embed JSON. ensure_ascii=False keeps accents readable; double-quotes safe in <script>.
    html = html.replace(
        "__DATA__",
        json.dumps(graph_data, ensure_ascii=False),
    )
    return html


# ----------------------------------------------------------------------------
# Commands
# ----------------------------------------------------------------------------

def cmd_render(args):
    project_dir = get_project_dir()

    # Rafraîchit les liens inline OKF (`## Liens`) avant le render — « on ouvre
    # un viewer » est le moment naturel pour resynchroniser les liens (décision
    # 2026-06-15 : okf-sync à la demande, hors chemin critique de /documente).
    # Désactivable via --no-sync pour un render rapide.
    okf_sync_summary = None
    if not args.no_sync:
        try:
            from okf_sync_engine import sync_all
            okf_sync_summary = sync_all(project_dir, dry_run=False)
        except Exception as e:
            okf_sync_summary = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    graph_data = build_graph_data(project_dir)
    html = render_html(graph_data)

    out_path = Path(args.out) if args.out else (project_dir / "_forge-graph.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    rel = str(out_path.relative_to(project_dir)) if out_path.is_relative_to(project_dir) else str(out_path)
    print(json.dumps({
        "ok": True,
        "out": rel,
        "absolute_path": str(out_path),
        "node_count": graph_data["stats"]["node_count"],
        "edge_count": graph_data["stats"]["edge_count"],
        "type_count": graph_data["stats"]["type_count"],
        "okf_sync": okf_sync_summary,
    }, indent=2, ensure_ascii=False))

    if not args.no_open:
        try:
            subprocess.run(
                ["open", "-a", "Google Chrome", str(out_path)],
                check=False,
            )
        except OSError:
            webbrowser.open(out_path.as_uri())

    return 0


def cmd_stats(args):
    project_dir = get_project_dir()
    graph_data = build_graph_data(project_dir)
    nodes_by_state = {}
    nodes_by_type = {}
    for n in graph_data["nodes"]:
        nodes_by_state[n["state"]] = nodes_by_state.get(n["state"], 0) + 1
        nodes_by_type[n["type"]] = nodes_by_type.get(n["type"], 0) + 1
    print(json.dumps({
        "ok": True,
        "node_count": graph_data["stats"]["node_count"],
        "edge_count": graph_data["stats"]["edge_count"],
        "nodes_by_state": nodes_by_state,
        "nodes_by_type": nodes_by_type,
        "generated_at": graph_data["generated_at"],
    }, indent=2, ensure_ascii=False))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Forge subject pool graph renderer (interactive vis.js HTML).")
    sub = parser.add_subparsers(dest="cmd")

    p_render = sub.add_parser("render", help="Generate interactive HTML graph")
    p_render.add_argument(
        "--out",
        default=None,
        help="Output HTML path. Default: <project>/_forge-graph.html",
    )
    p_render.add_argument(
        "--no-open",
        action="store_true",
        help="Do not auto-open the result in Chrome",
    )
    p_render.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip the OKF inline-links refresh before rendering (faster, but "
             "the `## Liens` sections may be stale for external OKF consumers)",
    )

    sub.add_parser("stats", help="Print node/edge counts (debug)")

    args = parser.parse_args()
    if args.cmd == "render":
        sys.exit(cmd_render(args))
    elif args.cmd == "stats":
        sys.exit(cmd_stats(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
