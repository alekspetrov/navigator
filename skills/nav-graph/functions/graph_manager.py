#!/usr/bin/env python3
"""
Graph Manager - CRUD operations for Project Knowledge Graph

Manages .agent/knowledge/graph.json for unified knowledge retrieval.
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def load_graph(graph_path: str) -> dict:
    """Load graph from file, return empty structure if missing or corrupt."""
    path = Path(graph_path)
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Corrupt graph file — fall back to an empty graph rather than
            # crashing every session-start hook / nav-graph query that loads it.
            print(f"Warning: {graph_path} is not valid JSON; using empty graph",
                  file=sys.stderr)
            return create_empty_graph()
    return create_empty_graph()


def save_graph(graph_path: str, graph: dict) -> bool:
    """Save graph to file."""
    try:
        path = Path(graph_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Update metadata
        graph["last_updated"] = datetime.now(timezone.utc).isoformat()
        graph["stats"] = calculate_stats(graph)

        with open(path, 'w') as f:
            json.dump(graph, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving graph: {e}", file=sys.stderr)
        return False


def create_empty_graph() -> dict:
    """Create a new empty graph structure."""
    return {
        "version": "1.0.0",
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total_nodes": 0,
            "total_edges": 0,
            "memory_count": 0
        },
        "nodes": {
            "tasks": {},
            "system": {},
            "sops": {},
            "markers": {},
            "concepts": {},
            "memories": {},
            "files": {}
        },
        "edges": [],
        "concept_index": {}
    }


def calculate_stats(graph: dict) -> dict:
    """Calculate graph statistics."""
    nodes = graph.get("nodes", {})
    total_nodes = sum(len(v) for v in nodes.values())
    total_edges = len(graph.get("edges", []))
    memory_count = len(nodes.get("memories", {}))

    return {
        "total_nodes": total_nodes,
        "total_edges": total_edges,
        "memory_count": memory_count
    }


def add_node(graph: dict, node_type: str, node_id: str, data: dict) -> dict:
    """Add a node to the graph."""
    if node_type not in graph["nodes"]:
        graph["nodes"][node_type] = {}

    graph["nodes"][node_type][node_id] = data

    # Update concept index if node has concepts
    concepts = data.get("concepts", [])
    for concept in concepts:
        if concept not in graph["concept_index"]:
            graph["concept_index"][concept] = []
        if node_id not in graph["concept_index"][concept]:
            graph["concept_index"][concept].append(node_id)

    return graph


def remove_node(graph: dict, node_type: str, node_id: str) -> dict:
    """Remove a node from the graph."""
    if node_type in graph["nodes"] and node_id in graph["nodes"][node_type]:
        # Get concepts before deletion
        concepts = graph["nodes"][node_type][node_id].get("concepts", [])

        # Remove from nodes
        del graph["nodes"][node_type][node_id]

        # Remove from concept index
        for concept in concepts:
            if concept in graph["concept_index"]:
                graph["concept_index"][concept] = [
                    n for n in graph["concept_index"][concept] if n != node_id
                ]
                # Clean up empty concept entries
                if not graph["concept_index"][concept]:
                    del graph["concept_index"][concept]

        # Remove edges involving this node
        graph["edges"] = [
            e for e in graph["edges"]
            if e["from"] != node_id and e["to"] != node_id
        ]

    return graph


def add_edge(graph: dict, from_id: str, to_id: str,
             edge_type: str, weight: float = 1.0) -> dict:
    """Add an edge to the graph."""
    edge = {
        "from": from_id,
        "to": to_id,
        "type": edge_type
    }
    if weight != 1.0:
        edge["weight"] = weight

    # Check for duplicates
    for existing in graph["edges"]:
        if (existing["from"] == from_id and
            existing["to"] == to_id and
            existing["type"] == edge_type):
            return graph  # Edge already exists

    graph["edges"].append(edge)
    return graph


def _clamp_confidence(confidence: float) -> float:
    """Coerce a confidence to the valid [0.0, 1.0] range.

    Memory confidence is a probability-like score. Callers passing values
    outside [0,1] (e.g. a percentage like 90) are clamped rather than allowed
    to poison the graph — mem-026 shipped at 90.0 and rendered as "9000%".
    Out-of-range repair of *existing* data uses a percentage heuristic; this
    input guard simply clamps.
    """
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return 0.8
    if c < 0.0:
        return 0.0
    if c > 1.0:
        print(f"warning: confidence {c} out of range [0,1]; clamping to 1.0",
              file=sys.stderr)
        return 1.0
    return c


def resolve_concept_alias(graph: dict, query: str) -> str:
    """Resolve a query term to canonical concept name via aliases."""
    query_lower = query.lower()

    # Direct match in concept_index
    if query_lower in graph.get("concept_index", {}):
        return query_lower

    # Check if query matches any concept's aliases
    for concept_name, concept_data in graph["nodes"].get("concepts", {}).items():
        # Check concept name
        if concept_name.lower() == query_lower:
            return concept_name
        # Check aliases
        aliases = concept_data.get("aliases", [])
        for alias in aliases:
            if alias.lower() == query_lower:
                return concept_name

    # Common abbreviation mappings as fallback
    abbreviations = {
        "auth": "authentication",
        "authn": "authentication",
        "authz": "authorization",
        "db": "database",
        "fe": "frontend",
        "be": "backend",
        "api": "api",
        "ui": "frontend",
        "tom": "theory of mind",
        "profile": "theory of mind",
        "docs": "documentation",
        "task-mode": "workflow",
        "task_mode": "workflow",
        "loop": "workflow",
        "loop-mode": "workflow",
        "iteration": "workflow",
        "perf": "performance",
        "latency": "performance",
        "sec": "security",
        "vuln": "security",
        "config": "configuration",
        "env": "configuration",
        # Execution-layer aliases (v6.4.0)
        "execution": "skills",
        "implementation": "skills",
        "code-generation": "skills",
        "code-writing": "skills",
        "autonomous": "workflow",
        "autonomous-completion": "workflow",
        "autonomous-mode": "workflow",
        "finish-protocol": "workflow",
        "verify": "testing",
        "verification": "testing",
        "workflow-orchestration": "workflow",
        "orchestration": "workflow",
    }
    if query_lower in abbreviations:
        canonical = abbreviations[query_lower]
        if canonical in graph.get("concept_index", {}):
            return canonical

    return query_lower


def query_by_concept(graph: dict, concept: str) -> dict:
    """Query all nodes related to a concept."""
    # Resolve aliases first
    resolved_concept = resolve_concept_alias(graph, concept)

    # Map node types to result categories
    type_to_category = {
        "tasks": "tasks",
        "memories": "memories",
        "sops": "sops",
        "system": "system",
        "files": "files",
        "markers": "markers",
        "concepts": "concepts",
    }

    results = {
        "concept": concept,  # Show original query
        "resolved_to": resolved_concept if resolved_concept != concept.lower() else None,
        "tasks": [],
        "memories": [],
        "sops": [],
        "system": [],
        "files": [],
        "markers": [],
        "concepts": [],
    }

    # Query using resolved concept
    if resolved_concept in graph.get("concept_index", {}):
        node_ids = graph["concept_index"][resolved_concept]
        for node_id in node_ids:
            for node_type, nodes in graph["nodes"].items():
                if node_id not in nodes:
                    continue
                category = type_to_category.get(node_type)
                if not category:
                    continue
                node_data = nodes[node_id].copy()
                node_data["id"] = node_id
                results[category].append(node_data)

    # Also check concept node itself for additional aliases
    if resolved_concept in graph["nodes"].get("concepts", {}):
        concept_node = graph["nodes"]["concepts"][resolved_concept]
        results["concept_details"] = concept_node

    return results


def query_related(graph: dict, node_id: str, max_depth: int = 2) -> list:
    """Find nodes related to a given node via edges."""
    related = set()
    to_explore = [(node_id, 0)]
    explored = set()

    while to_explore:
        current_id, depth = to_explore.pop(0)
        if current_id in explored or depth > max_depth:
            continue
        explored.add(current_id)

        # Find edges involving this node
        for edge in graph["edges"]:
            if edge["from"] == current_id:
                related.add(edge["to"])
                if depth < max_depth:
                    to_explore.append((edge["to"], depth + 1))
            elif edge["to"] == current_id:
                related.add(edge["from"])
                if depth < max_depth:
                    to_explore.append((edge["from"], depth + 1))

    # Remove the starting node
    related.discard(node_id)
    return list(related)


def _next_memory_id(memories: dict, base_dir: str = ".agent/knowledge") -> str:
    """Generate the next memory ID by scanning both graph nodes AND on-disk files.

    Uses max(existing numeric suffix) + 1 across the union of graph IDs and
    on-disk `memories/**/mem-*.md` files. The disk scan prevents overwriting
    memory files that exist on disk but aren't yet registered in the graph
    (e.g., when a file was authored manually or the graph drifted out of sync
    via a partial reconciliation).
    """
    from pathlib import Path

    max_n = 0

    def _consume(stem: str) -> None:
        nonlocal max_n
        if stem.startswith("mem-"):
            try:
                n = int(stem[4:])
            except ValueError:
                return
            if n > max_n:
                max_n = n

    for mid in memories:
        _consume(mid)

    mem_root = Path(base_dir) / "memories"
    if mem_root.is_dir():
        for f in mem_root.glob("**/mem-*.md"):
            _consume(f.stem)

    return f"mem-{max_n + 1:03d}"


def add_memory(graph: dict, memory_type: str, summary: str,
               concepts: list, confidence: float = 0.8,
               source_task: Optional[str] = None,
               base_dir: str = ".agent/knowledge",
               create_file: bool = True,
               memory_id: Optional[str] = None) -> str:
    """Add a memory node to the graph.

    Also creates the backing markdown file at
    `{base_dir}/memories/{memory_type}s/{id}.md` by default, so the `path`
    field in the graph node always resolves to a real file. Pass
    `create_file=False` to skip file creation (e.g. when ingesting into a
    transient/test graph that isn't on disk).

    If `memory_id` is provided, that ID is used directly (after collision
    check against the graph). If omitted, the next free ID is computed via
    `_next_memory_id` which scans both graph nodes and on-disk files.
    """
    confidence = _clamp_confidence(confidence)
    memories = graph["nodes"].get("memories", {})
    if memory_id is None:
        memory_id = _next_memory_id(memories, base_dir)
    elif memory_id in memories:
        raise ValueError(
            f"Memory ID {memory_id} already exists in graph. "
            f"Use a different --node-id or omit it to auto-assign."
        )

    # Determine path (relative; resolves to {base_dir}/{path})
    path = f"memories/{memory_type}s/{memory_id}.md"

    memory_data = {
        "type": memory_type,
        "summary": summary,
        "path": path,
        "confidence": confidence,
        "concepts": concepts,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "last_validated": datetime.now(timezone.utc).strftime("%Y-%m-%d")
    }

    graph = add_node(graph, "memories", memory_id, memory_data)

    if create_file:
        try:
            # Lazy import to avoid a hard dependency cycle at module load
            from memory_writer import create_memory_file
            create_memory_file(
                memory_id=memory_id,
                memory_type=memory_type,
                title=summary[:80],
                summary=summary,
                confidence=int(round(confidence * 100)),
                concepts=concepts or [],
                base_dir=base_dir,
            )
        except Exception as e:
            # Non-fatal: the graph node is still valid even if file creation
            # fails. Surface a warning so callers can investigate.
            print(
                f"warning: add_memory created {memory_id} node but failed to "
                f"write backing file ({e})",
                file=sys.stderr,
            )

    # Add edge from source task if provided
    if source_task:
        graph = add_edge(graph, memory_id, source_task, "learned-from")

    return memory_id


def update_confidence(graph: dict, memory_id: str,
                      boost: bool = False, decay_days: int = 0) -> float:
    """Update memory confidence with decay/boost."""
    if memory_id not in graph["nodes"].get("memories", {}):
        return 0.0

    memory = graph["nodes"]["memories"][memory_id]
    # Defensive: clamp any pre-existing out-of-range value before math so a
    # poisoned node (e.g. 90.0) cannot propagate through decay/boost.
    confidence = _clamp_confidence(memory.get("confidence", 0.8))

    # Apply decay (1% per week = ~0.14% per day)
    if decay_days > 0:
        decay_rate = 0.01 / 7  # 1% per week
        confidence -= decay_rate * decay_days

    # Apply boost (5% per use), capped at the [0,1] ceiling. No fixed-0.8
    # anchor — that broke for memories that had decayed or been elevated.
    if boost:
        confidence = min(confidence + 0.05, 1.0)

    # Clamp to valid range
    confidence = max(0.0, min(1.0, confidence))

    memory["confidence"] = round(confidence, 2)
    memory["last_validated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return memory["confidence"]


def _format_task(task: dict) -> str:
    """Format a single task for display."""
    status = task.get("status", "unknown")
    title = task.get("title", task.get("id", "Unknown"))
    return f"  - {task.get('id', 'Unknown')}: {title} ({status})"


def _format_memory(memory: dict) -> str:
    """Format a single memory for display."""
    mem_type = memory.get("type", "unknown").upper()
    summary = memory.get("summary", "No summary")
    confidence = int(memory.get("confidence", 0) * 100)
    return f"  - {mem_type}: \"{summary}\" ({confidence}%)"


def _format_sop(sop: dict) -> str:
    """Format a single SOP for display."""
    title = sop.get("title", sop.get("id", "Unknown"))
    return f"  - {title}"


def _format_file(file_node: dict) -> str:
    """Format a single file for display."""
    return f"  - {file_node.get('path', file_node.get('id', 'Unknown'))}"


def _format_marker(marker: dict) -> str:
    """Format a single context marker for display."""
    return f"  - {marker.get('title', marker.get('id', 'Unknown'))}"


def _format_concept(concept: dict) -> str:
    """Format a single concept node for display."""
    return f"  - {concept.get('name', concept.get('id', 'Unknown'))}"


def format_query_results(results: dict) -> str:
    """Format query results for display."""
    concept = results.get("concept", "Unknown")
    resolved = results.get("resolved_to")

    if resolved:
        output = [f"Knowledge Graph: \"{concept}\" → \"{resolved}\"", ""]
    else:
        output = [f"Knowledge Graph: \"{concept}\"", ""]

    tasks = results.get("tasks", [])
    memories = results.get("memories", [])
    sops = results.get("sops", [])
    files = results.get("files", [])
    markers = results.get("markers", [])
    concepts = results.get("concepts", [])

    if tasks:
        output.append(f"TASKS ({len(tasks)})")
        output.extend(_format_task(t) for t in tasks[:5])

    if memories:
        sorted_memories = sorted(memories, key=lambda x: x.get("confidence", 0), reverse=True)
        output.append(f"\nMEMORIES ({len(memories)})")
        output.extend(_format_memory(m) for m in sorted_memories[:5])

    if sops:
        output.append(f"\nSOPs ({len(sops)})")
        output.extend(_format_sop(s) for s in sops[:3])

    if files:
        output.append(f"\nFILES ({len(files)})")
        output.extend(_format_file(f) for f in files[:5])

    if markers:
        output.append(f"\nMARKERS ({len(markers)})")
        output.extend(_format_marker(m) for m in markers[:5])

    if concepts:
        output.append(f"\nCONCEPTS ({len(concepts)})")
        output.extend(_format_concept(c) for c in concepts[:5])

    if any([tasks, memories, sops, files, markers, concepts]):
        output.append("\nLoad details: \"Read TASK-XX\" or \"Show [concept] memories\"")
    else:
        output.append("No results found for this concept.")

    return "\n".join(output)


def main():
    parser = argparse.ArgumentParser(description='Manage Navigator knowledge graph')
    parser.add_argument('--action', required=True,
                       choices=['query', 'add-node', 'add-memory', 'add-edge',
                               'remove-node', 'stats', 'init', 'related'],
                       help='Action to perform')
    parser.add_argument('--graph-path', default='.agent/knowledge/graph.json',
                       help='Path to graph file')
    parser.add_argument('--concept', help='Concept to query')
    parser.add_argument('--node-type', help='Type of node (tasks, memories, etc.)')
    parser.add_argument('--node-id', help='ID of node')
    parser.add_argument('--node-data', help='JSON string of node data')
    parser.add_argument('--memory-type', choices=['pattern', 'pitfall', 'decision', 'learning'],
                       help='Type of memory')
    parser.add_argument('--summary', help='Memory summary')
    parser.add_argument('--concepts', help='Comma-separated list of concepts')
    parser.add_argument('--confidence', type=float, default=0.8, help='Memory confidence')
    parser.add_argument('--source-task', help='Source task for memory')
    parser.add_argument('--from-id', help='Edge source node')
    parser.add_argument('--to-id', help='Edge target node')
    parser.add_argument('--edge-type', help='Edge type')
    parser.add_argument('--max-depth', type=int, default=2, help='Max traversal depth')

    args = parser.parse_args()

    if args.action == 'init':
        graph = create_empty_graph()
        if save_graph(args.graph_path, graph):
            print(f"Initialized empty graph at {args.graph_path}")
        else:
            sys.exit(1)

    elif args.action == 'stats':
        graph = load_graph(args.graph_path)
        stats = calculate_stats(graph)
        print(f"Knowledge Graph Statistics")
        print(f"==========================")
        print(f"Total Nodes: {stats['total_nodes']}")
        print(f"Total Edges: {stats['total_edges']}")
        print(f"Memories: {stats['memory_count']}")
        print(f"Last Updated: {graph.get('last_updated', 'Unknown')}")

    elif args.action == 'query':
        if not args.concept:
            print("Error: --concept required for query", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        results = query_by_concept(graph, args.concept.lower())
        print(format_query_results(results))

    elif args.action == 'related':
        if not args.node_id:
            print("Error: --node-id required for related query", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        related = query_related(graph, args.node_id, args.max_depth)
        print(f"Nodes related to {args.node_id}:")
        for node_id in related:
            print(f"  - {node_id}")

    elif args.action == 'add-node':
        if not all([args.node_type, args.node_id, args.node_data]):
            print("Error: --node-type, --node-id, and --node-data required", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        data = json.loads(args.node_data)
        graph = add_node(graph, args.node_type, args.node_id, data)

        if save_graph(args.graph_path, graph):
            print(f"Added {args.node_type}/{args.node_id}")
        else:
            sys.exit(1)

    elif args.action == 'add-memory':
        if not all([args.memory_type, args.summary, args.concepts]):
            print("Error: --memory-type, --summary, and --concepts required", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        concepts = [c.strip().lower() for c in args.concepts.split(',')]
        try:
            memory_id = add_memory(
                graph, args.memory_type, args.summary, concepts,
                args.confidence, args.source_task,
                memory_id=args.node_id,
            )
        except (ValueError, FileExistsError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if save_graph(args.graph_path, graph):
            print(f"Added memory: {memory_id}")
            print(f"Type: {args.memory_type}")
            print(f"Summary: {args.summary}")
            print(f"Concepts: {', '.join(concepts)}")
        else:
            sys.exit(1)

    elif args.action == 'add-edge':
        if not all([args.from_id, args.to_id, args.edge_type]):
            print("Error: --from-id, --to-id, and --edge-type required", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        graph = add_edge(graph, args.from_id, args.to_id, args.edge_type)

        if save_graph(args.graph_path, graph):
            print(f"Added edge: {args.from_id} --[{args.edge_type}]--> {args.to_id}")
        else:
            sys.exit(1)

    elif args.action == 'remove-node':
        if not all([args.node_type, args.node_id]):
            print("Error: --node-type and --node-id required", file=sys.stderr)
            sys.exit(1)

        graph = load_graph(args.graph_path)
        graph = remove_node(graph, args.node_type, args.node_id)

        if save_graph(args.graph_path, graph):
            print(f"Removed {args.node_type}/{args.node_id}")
        else:
            sys.exit(1)


if __name__ == '__main__':
    main()
