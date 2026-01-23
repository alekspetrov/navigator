#!/usr/bin/env python3
"""
Task to Graph - Syncs task documents with knowledge graph

Extracts concepts and decisions from task documents and updates the graph.
"""

import json
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, save_graph, add_node, add_edge, add_memory


def extract_concepts_from_task(content: str) -> list:
    """Extract concepts from task document content."""
    concepts = set()

    keyword_map = {
        'auth': 'authentication',
        'login': 'authentication',
        'jwt': 'authentication',
        'oauth': 'authentication',
        'api': 'api',
        'endpoint': 'api',
        'rest': 'api',
        'graphql': 'api',
        'test': 'testing',
        'spec': 'testing',
        'unit': 'testing',
        'integration': 'testing',
        'component': 'frontend',
        'react': 'frontend',
        'vue': 'frontend',
        'database': 'database',
        'migration': 'database',
        'schema': 'database',
        'deploy': 'deployment',
        'ci': 'deployment',
        'cd': 'deployment',
        'skill': 'skills',
        'plugin': 'skills',
        'marker': 'markers',
        'compact': 'markers',
        'context': 'context',
        'token': 'context',
        'memory': 'knowledge',
        'graph': 'knowledge',
        'profile': 'tom',
        'tom': 'tom',
        'loop': 'workflow',
        'task.mode': 'workflow',
        'simplif': 'simplification',
    }

    content_lower = content.lower()
    for keyword, concept in keyword_map.items():
        if keyword in content_lower:
            concepts.add(concept)

    return list(concepts) if concepts else ['general']


def extract_status(content: str) -> str:
    """Extract task status from content."""
    if '✅ Completed' in content or 'Status**: ✅' in content:
        return 'completed'
    if '🚧 In Progress' in content or 'Status**: 🚧' in content:
        return 'in-progress'
    if '📋 Backlog' in content or 'Status**: 📋' in content:
        return 'backlog'
    if '🔬 Research' in content or 'Status**: 🔬' in content:
        return 'research'
    return 'unknown'


def extract_title(content: str, filename: str) -> str:
    """Extract title from task content."""
    match = re.search(r'^#\s+TASK-\d+:\s*(.+)$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return filename.replace('.md', '').replace('-', ' ').title()


def extract_decisions(content: str) -> list:
    """Extract technical decisions from task document."""
    decisions = []

    # Look for Technical Decisions section
    decision_match = re.search(
        r'## Technical Decisions\s*\n(.*?)(?=\n##|\Z)',
        content,
        re.DOTALL
    )

    if not decision_match:
        return decisions

    decision_section = decision_match.group(1)

    # Parse table rows (skip header)
    rows = re.findall(r'\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|', decision_section)

    for row in rows:
        decision, options, chosen, reasoning = [col.strip() for col in row]
        # Skip header row
        if decision.lower() in ['decision', '---', '-']:
            continue
        if chosen and reasoning and len(reasoning) > 5:
            decisions.append({
                'decision': decision,
                'chosen': chosen,
                'reasoning': reasoning
            })

    return decisions


def add_task_to_graph(task_path: str, graph_path: str) -> dict:
    """Add a task document to the knowledge graph."""
    task_file = Path(task_path)
    if not task_file.exists():
        return {'error': f'Task file not found: {task_path}'}

    content = task_file.read_text()

    # Extract task ID from filename
    match = re.search(r'(TASK-\d+)', task_file.name)
    task_id = match.group(1) if match else task_file.stem

    # Load graph
    graph = load_graph(graph_path)

    # Extract metadata
    title = extract_title(content, task_file.name)
    status = extract_status(content)
    concepts = extract_concepts_from_task(content)

    # Create task node
    task_data = {
        'path': str(task_file),
        'title': title,
        'status': status,
        'concepts': concepts
    }

    graph = add_node(graph, 'tasks', task_id, task_data)

    # Add implements edges for concepts
    for concept in concepts:
        graph = add_edge(graph, task_id, concept, 'implements')

    # Extract and create decision memories (for completed tasks)
    memories_created = []
    if status == 'completed':
        decisions = extract_decisions(content)
        for decision in decisions:
            summary = f"{decision['decision']}: {decision['chosen']} - {decision['reasoning']}"
            if len(summary) > 200:
                summary = summary[:197] + '...'

            memory_id = add_memory(
                graph=graph,
                memory_type='decision',
                summary=summary,
                concepts=concepts,
                confidence=0.95,
                source_task=task_id
            )
            memories_created.append(memory_id)

    # Save graph
    if save_graph(graph_path, graph):
        return {
            'task_id': task_id,
            'title': title,
            'status': status,
            'concepts': concepts,
            'memories_created': memories_created
        }

    return {'error': 'Failed to save graph'}


def sync_all_tasks(tasks_dir: str, graph_path: str) -> dict:
    """Sync all tasks from directory to graph."""
    tasks_path = Path(tasks_dir)
    results = {
        'synced': 0,
        'failed': 0,
        'tasks': []
    }

    for task_file in tasks_path.glob('TASK-*.md'):
        result = add_task_to_graph(str(task_file), graph_path)
        if 'error' in result:
            results['failed'] += 1
        else:
            results['synced'] += 1
            results['tasks'].append(result['task_id'])

    return results


def main():
    parser = argparse.ArgumentParser(description='Sync tasks with knowledge graph')
    parser.add_argument('--action', required=True,
                       choices=['add', 'sync-all'],
                       help='Action to perform')
    parser.add_argument('--task-path', help='Path to task file')
    parser.add_argument('--tasks-dir', default='.agent/tasks',
                       help='Directory containing tasks')
    parser.add_argument('--graph-path', default='.agent/knowledge/graph.json',
                       help='Path to knowledge graph')

    args = parser.parse_args()

    if args.action == 'add':
        if not args.task_path:
            print("Error: --task-path required for add", file=sys.stderr)
            sys.exit(1)

        result = add_task_to_graph(args.task_path, args.graph_path)
        if 'error' in result:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

        print(f"Added task: {result['task_id']}")
        print(f"Title: {result['title']}")
        print(f"Status: {result['status']}")
        print(f"Concepts: {', '.join(result['concepts'])}")
        if result['memories_created']:
            print(f"Decisions extracted: {len(result['memories_created'])}")

    elif args.action == 'sync-all':
        result = sync_all_tasks(args.tasks_dir, args.graph_path)
        print(f"Synced {result['synced']} tasks")
        if result['failed'] > 0:
            print(f"Failed: {result['failed']}")


if __name__ == '__main__':
    main()
