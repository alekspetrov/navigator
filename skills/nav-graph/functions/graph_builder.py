#!/usr/bin/env python3
"""
Graph Builder - One-time construction of knowledge graph from existing docs

Scans .agent/ directory and builds initial graph from:
- tasks/ - Implementation plans
- system/ - Architecture docs
- sops/ - Standard Operating Procedures
- markers/ - Context markers
"""

import json
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional


def extract_concepts_from_text(text: str) -> list:
    """Extract potential concepts from document text."""
    # Common technical concepts to look for
    concept_patterns = [
        r'\b(auth|authentication|login|oauth|jwt)\b',
        r'\b(api|endpoint|rest|graphql)\b',
        r'\b(test|testing|unit|integration|e2e)\b',
        r'\b(database|db|migration|schema)\b',
        r'\b(component|frontend|react|vue)\b',
        r'\b(backend|server|node|express)\b',
        r'\b(deploy|deployment|ci|cd)\b',
        r'\b(token|context|efficiency)\b',
        r'\b(skill|command|plugin)\b',
        r'\b(marker|compact|session)\b',
        r'\b(profile|tom|theory[\s._-]?of[\s._-]?mind)\b',
        r'\b(loop|task[\s._-]?mode|workflow)\b',
        r'\b(simplif|clarity|code.quality)\b',
        r'\b(memory|knowledge|graph)\b',
    ]

    concepts = set()
    text_lower = text.lower()

    for pattern in concept_patterns:
        matches = re.findall(pattern, text_lower)
        concepts.update(matches)

    # Normalize concepts
    normalized = {
        'auth': 'authentication',
        'jwt': 'authentication',
        'oauth': 'authentication',
        'login': 'authentication',
        'api': 'api',
        'endpoint': 'api',
        'rest': 'api',
        'graphql': 'api',
        'test': 'testing',
        'unit': 'testing',
        'integration': 'testing',
        'e2e': 'testing',
        'database': 'database',
        'db': 'database',
        'migration': 'database',
        'schema': 'database',
        'component': 'frontend',
        'react': 'frontend',
        'vue': 'frontend',
        'backend': 'backend',
        'server': 'backend',
        'node': 'backend',
        'express': 'backend',
        'deploy': 'deployment',
        'ci': 'deployment',
        'cd': 'deployment',
        'token': 'context',
        'efficiency': 'context',
        'context': 'context',
        'skill': 'skills',
        'command': 'skills',
        'plugin': 'skills',
        'marker': 'markers',
        'compact': 'markers',
        'session': 'session',
        'profile': 'theory of mind',
        'tom': 'theory of mind',
        'theory of mind': 'theory of mind',
        'theory-of-mind': 'theory of mind',
        'theory_of_mind': 'theory of mind',
        'loop': 'workflow',
        'task mode': 'workflow',
        'task-mode': 'workflow',
        'task_mode': 'workflow',
        'workflow': 'workflow',
        'simplif': 'simplification',
        'clarity': 'simplification',
        'code.quality': 'simplification',
        'memory': 'knowledge',
        'knowledge': 'knowledge',
        'graph': 'knowledge',
    }

    return list(set(normalized.get(c, c) for c in concepts))


def extract_task_status(content: str) -> str:
    """Extract task status from content."""
    if 'Completed' in content or 'Status**: ✅' in content:
        return 'completed'
    elif 'In Progress' in content or 'Status**: 🚧' in content:
        return 'in-progress'
    elif 'Backlog' in content or 'Status**: 📋' in content:
        return 'backlog'
    elif 'Research' in content or 'Status**: 🔬' in content:
        return 'research'
    return 'unknown'


def extract_title(content: str, filename: str) -> str:
    """Extract title from markdown content."""
    # Look for first H1
    match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    # Fall back to filename
    return filename.replace('.md', '').replace('-', ' ').title()


def scan_tasks(agent_dir: Path) -> list:
    """Scan tasks directory for task documents."""
    tasks = []
    tasks_dir = agent_dir / 'tasks'

    if not tasks_dir.exists():
        return tasks

    for task_file in tasks_dir.glob('**/*.md'):
        # Skip archive by default
        if 'archive' in str(task_file):
            continue

        content = task_file.read_text()
        filename = task_file.name

        # Extract task ID
        match = re.match(r'TASK-(\d+)', filename)
        task_id = f"TASK-{match.group(1)}" if match else filename.replace('.md', '')

        tasks.append({
            'id': task_id,
            'path': str(task_file.relative_to(agent_dir.parent)),
            'title': extract_title(content, filename),
            'status': extract_task_status(content),
            'concepts': extract_concepts_from_text(content)
        })

    return tasks


def scan_sops(agent_dir: Path) -> list:
    """Scan SOPs directory for procedures."""
    sops = []
    sops_dir = agent_dir / 'sops'

    if not sops_dir.exists():
        return sops

    for sop_file in sops_dir.glob('**/*.md'):
        content = sop_file.read_text()
        filename = sop_file.name

        # Generate SOP ID
        sop_id = f"SOP-{filename.replace('.md', '').replace('-', '_')}"

        sops.append({
            'id': sop_id,
            'path': str(sop_file.relative_to(agent_dir.parent)),
            'title': extract_title(content, filename),
            'category': sop_file.parent.name,
            'concepts': extract_concepts_from_text(content)
        })

    return sops


def scan_system(agent_dir: Path) -> list:
    """Scan system directory for architecture docs."""
    system_docs = []
    system_dir = agent_dir / 'system'

    if not system_dir.exists():
        return system_docs

    for doc_file in system_dir.glob('**/*.md'):
        content = doc_file.read_text()
        filename = doc_file.name

        doc_id = filename.replace('.md', '')

        system_docs.append({
            'id': doc_id,
            'path': str(doc_file.relative_to(agent_dir.parent)),
            'title': extract_title(content, filename),
            'concepts': extract_concepts_from_text(content)
        })

    return system_docs


def scan_markers(agent_dir: Path) -> list:
    """Scan markers directory."""
    markers = []
    markers_dir = agent_dir / 'markers'
    context_markers_dir = agent_dir / '.context-markers'

    for markers_path in [markers_dir, context_markers_dir]:
        if not markers_path.exists():
            continue

        for marker_file in markers_path.glob('**/*.md'):
            content = marker_file.read_text()
            filename = marker_file.name

            marker_id = filename.replace('.md', '')

            markers.append({
                'id': marker_id,
                'path': str(marker_file.relative_to(agent_dir.parent)),
                'title': extract_title(content, filename),
                'concepts': extract_concepts_from_text(content)
            })

    return markers


def build_concept_nodes(all_concepts: set) -> dict:
    """Build concept node definitions."""
    concept_definitions = {
        'authentication': {
            'name': 'Authentication',
            'aliases': ['auth', 'login', 'OAuth', 'JWT'],
            'domain': 'backend'
        },
        'api': {
            'name': 'API',
            'aliases': ['endpoint', 'REST', 'GraphQL'],
            'domain': 'backend'
        },
        'testing': {
            'name': 'Testing',
            'aliases': ['test', 'unit', 'integration', 'e2e'],
            'domain': 'quality'
        },
        'database': {
            'name': 'Database',
            'aliases': ['db', 'migration', 'schema'],
            'domain': 'backend'
        },
        'frontend': {
            'name': 'Frontend',
            'aliases': ['component', 'React', 'Vue'],
            'domain': 'frontend'
        },
        'backend': {
            'name': 'Backend',
            'aliases': ['server', 'Node', 'Express'],
            'domain': 'backend'
        },
        'deployment': {
            'name': 'Deployment',
            'aliases': ['deploy', 'CI', 'CD'],
            'domain': 'devops'
        },
        'context': {
            'name': 'Context Management',
            'aliases': ['token', 'efficiency'],
            'domain': 'navigator'
        },
        'skills': {
            'name': 'Skills',
            'aliases': ['skill', 'command', 'plugin'],
            'domain': 'navigator'
        },
        'markers': {
            'name': 'Context Markers',
            'aliases': ['marker', 'compact'],
            'domain': 'navigator'
        },
        'session': {
            'name': 'Session',
            'aliases': ['start', 'workflow'],
            'domain': 'navigator'
        },
        'theory of mind': {
            'name': 'Theory of Mind',
            'aliases': ['tom', 'ToM', 'profile', 'bilateral'],
            'domain': 'navigator'
        },
        'workflow': {
            'name': 'Workflow',
            'aliases': ['loop', 'task mode', 'orchestration'],
            'domain': 'navigator'
        },
        'simplification': {
            'name': 'Code Simplification',
            'aliases': ['simplify', 'clarity', 'code quality'],
            'domain': 'quality'
        },
        'knowledge': {
            'name': 'Knowledge Graph',
            'aliases': ['memory', 'graph', 'learning'],
            'domain': 'navigator'
        }
    }

    concepts = {}
    for concept in all_concepts:
        if concept in concept_definitions:
            concepts[concept] = concept_definitions[concept]
        else:
            concepts[concept] = {
                'name': concept.title(),
                'aliases': [],
                'domain': 'general'
            }

    return concepts


def infer_edges(tasks: list, sops: list, system_docs: list) -> list:
    """Infer edges between nodes based on relationships."""
    edges = []

    # SOPs often relate to tasks that created them
    for sop in sops:
        for task in tasks:
            # Check for overlapping concepts
            common = set(sop['concepts']) & set(task['concepts'])
            if len(common) >= 2:
                edges.append({
                    'from': sop['id'],
                    'to': task['id'],
                    'type': 'relates-to',
                    'weight': min(len(common) * 0.2, 1.0)
                })

    # System docs relate to tasks
    for doc in system_docs:
        for task in tasks:
            common = set(doc['concepts']) & set(task['concepts'])
            if len(common) >= 2:
                edges.append({
                    'from': doc['id'],
                    'to': task['id'],
                    'type': 'relates-to',
                    'weight': min(len(common) * 0.2, 1.0)
                })

    # Tasks implement concepts
    for task in tasks:
        for concept in task['concepts']:
            edges.append({
                'from': task['id'],
                'to': concept,
                'type': 'implements'
            })

    return edges


def build_graph(agent_dir: str) -> dict:
    """Build complete knowledge graph from .agent/ directory."""
    agent_path = Path(agent_dir)

    if not agent_path.exists():
        print(f"Error: {agent_dir} does not exist", file=sys.stderr)
        sys.exit(1)

    # Scan all sources
    tasks = scan_tasks(agent_path)
    sops = scan_sops(agent_path)
    system_docs = scan_system(agent_path)
    markers = scan_markers(agent_path)

    # Collect all concepts
    all_concepts = set()
    for items in [tasks, sops, system_docs, markers]:
        for item in items:
            all_concepts.update(item.get('concepts', []))

    # Build graph structure
    graph = {
        "version": "1.0.0",
        "last_updated": datetime.now().isoformat() + "Z",
        "stats": {},
        "nodes": {
            "tasks": {t['id']: t for t in tasks},
            "system": {d['id']: d for d in system_docs},
            "sops": {s['id']: s for s in sops},
            "markers": {m['id']: m for m in markers},
            "concepts": build_concept_nodes(all_concepts),
            "memories": {},
            "files": {}
        },
        "edges": infer_edges(tasks, sops, system_docs),
        "concept_index": {}
    }

    # Build concept index
    for node_type, nodes in graph["nodes"].items():
        if node_type == "concepts":
            continue
        for node_id, node_data in nodes.items():
            for concept in node_data.get('concepts', []):
                if concept not in graph["concept_index"]:
                    graph["concept_index"][concept] = []
                graph["concept_index"][concept].append(node_id)

    # Calculate stats
    graph["stats"] = {
        "total_nodes": sum(len(v) for v in graph["nodes"].values()),
        "total_edges": len(graph["edges"]),
        "memory_count": len(graph["nodes"]["memories"]),
        "task_count": len(tasks),
        "sop_count": len(sops),
        "concept_count": len(all_concepts)
    }

    return graph


def main():
    parser = argparse.ArgumentParser(
        description='Build knowledge graph from existing documentation'
    )
    parser.add_argument('--agent-dir', default='.agent',
                       help='Path to .agent directory')
    parser.add_argument('--output', default='.agent/knowledge/graph.json',
                       help='Output path for graph.json')
    parser.add_argument('--dry-run', action='store_true',
                       help='Print stats without writing')

    args = parser.parse_args()

    print(f"Scanning {args.agent_dir}...")
    graph = build_graph(args.agent_dir)

    stats = graph["stats"]
    print(f"\nGraph Statistics:")
    print(f"  Tasks: {stats.get('task_count', 0)}")
    print(f"  SOPs: {stats.get('sop_count', 0)}")
    print(f"  Concepts: {stats.get('concept_count', 0)}")
    print(f"  Total Nodes: {stats['total_nodes']}")
    print(f"  Total Edges: {stats['total_edges']}")

    if args.dry_run:
        print("\n(Dry run - no file written)")
        return

    # Write graph
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(graph, f, indent=2)

    print(f"\nGraph written to {args.output}")


if __name__ == '__main__':
    main()
