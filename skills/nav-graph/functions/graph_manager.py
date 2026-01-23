#!/usr/bin/env python3
"""
Graph Manager - CRUD operations for Project Knowledge Graph

Manages .agent/knowledge/graph.json for unified knowledge retrieval.
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_graph(graph_path: str) -> dict:
    """Load graph from file, return empty structure if not exists."""
    path = Path(graph_path)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return create_empty_graph()


def save_graph(graph_path: str, graph: dict) -> bool:
    """Save graph to file."""
    try:
        path = Path(graph_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Update metadata
        graph["last_updated"] = datetime.now().isoformat() + "Z"
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
        "last_updated": datetime.now().isoformat() + "Z",
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
        "files": "files"
    }

    results = {
        "concept": concept,  # Show original query
        "resolved_to": resolved_concept if resolved_concept != concept.lower() else None,
        "tasks": [],
        "memories": [],
        "sops": [],
        "system": [],
        "files": []
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


def add_memory(graph: dict, memory_type: str, summary: str,
               concepts: list, confidence: float = 0.8,
               source_task: Optional[str] = None) -> str:
    """Add a memory node to the graph."""
    # Generate memory ID
    memory_count = len(graph["nodes"].get("memories", {})) + 1
    memory_id = f"mem-{memory_count:03d}"

    # Determine path
    path = f"memories/{memory_type}s/{memory_id}.md"

    memory_data = {
        "type": memory_type,
        "summary": summary,
        "path": path,
        "confidence": confidence,
        "concepts": concepts,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "last_validated": datetime.now().strftime("%Y-%m-%d")
    }

    graph = add_node(graph, "memories", memory_id, memory_data)

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
    confidence = memory.get("confidence", 0.8)

    # Apply decay (1% per week = ~0.14% per day)
    if decay_days > 0:
        decay_rate = 0.01 / 7  # 1% per week
        confidence -= decay_rate * decay_days

    # Apply boost (5% per use, max +25%)
    if boost:
        boost_amount = 0.05
        max_boost = 0.25
        current_boost = confidence - 0.8  # Assuming base 0.8
        if current_boost < max_boost:
            confidence = min(confidence + boost_amount, 0.8 + max_boost)

    # Clamp to valid range
    confidence = max(0.0, min(1.0, confidence))

    memory["confidence"] = round(confidence, 2)
    memory["last_validated"] = datetime.now().strftime("%Y-%m-%d")

    return confidence


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

    if any([tasks, memories, sops, files]):
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
        memory_id = add_memory(
            graph, args.memory_type, args.summary, concepts,
            args.confidence, args.source_task
        )

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
