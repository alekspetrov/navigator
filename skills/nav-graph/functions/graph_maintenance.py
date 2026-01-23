#!/usr/bin/env python3
"""
Graph Maintenance - Conflict detection, staleness pruning, health checks

Maintains knowledge graph health over time.
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, save_graph


def detect_conflicts(graph: dict) -> list:
    """Detect potentially conflicting memories."""
    conflicts = []
    memories = graph['nodes'].get('memories', {})

    # Group memories by concept
    concept_memories = {}
    for mem_id, mem_data in memories.items():
        for concept in mem_data.get('concepts', []):
            if concept not in concept_memories:
                concept_memories[concept] = []
            concept_memories[concept].append((mem_id, mem_data))

    # Check for conflicts within same concept
    for concept, mems in concept_memories.items():
        if len(mems) < 2:
            continue

        for i, (id1, mem1) in enumerate(mems):
            for id2, mem2 in mems[i + 1:]:
                # Simple heuristic: opposing patterns/pitfalls
                type1 = mem1.get('type', '')
                type2 = mem2.get('type', '')

                # Pattern vs Pitfall on same concept might conflict
                if {type1, type2} == {'pattern', 'pitfall'}:
                    summary1 = mem1.get('summary', '').lower()
                    summary2 = mem2.get('summary', '').lower()

                    # Check for opposing language
                    opposing_pairs = [
                        ('always', 'never'),
                        ('use', 'avoid'),
                        ('do', "don't"),
                        ('should', "shouldn't"),
                    ]

                    for pos, neg in opposing_pairs:
                        if (pos in summary1 and neg in summary2) or (neg in summary1 and pos in summary2):
                            conflicts.append({
                                'type': 'opposing_guidance',
                                'concept': concept,
                                'memory1': {'id': id1, 'summary': mem1.get('summary')},
                                'memory2': {'id': id2, 'summary': mem2.get('summary')},
                                'suggestion': 'Review and consolidate or mark one as superseded'
                            })
                            break

    return conflicts


def find_stale_memories(graph: dict, threshold_days: int = 90) -> list:
    """Find memories that haven't been validated recently."""
    stale = []
    cutoff = datetime.now() - timedelta(days=threshold_days)

    for mem_id, mem_data in graph['nodes'].get('memories', {}).items():
        last_validated = mem_data.get('last_validated')
        if not last_validated:
            stale.append({
                'id': mem_id,
                'summary': mem_data.get('summary'),
                'reason': 'never validated',
                'confidence': mem_data.get('confidence', 0)
            })
            continue

        try:
            validated_date = datetime.strptime(last_validated, '%Y-%m-%d')
            if validated_date < cutoff:
                days_stale = (datetime.now() - validated_date).days
                stale.append({
                    'id': mem_id,
                    'summary': mem_data.get('summary'),
                    'reason': f'not validated for {days_stale} days',
                    'confidence': mem_data.get('confidence', 0)
                })
        except ValueError:
            stale.append({
                'id': mem_id,
                'summary': mem_data.get('summary'),
                'reason': 'invalid date format',
                'confidence': mem_data.get('confidence', 0)
            })

    return sorted(stale, key=lambda x: x['confidence'])


def find_low_confidence(graph: dict, threshold: float = 0.3) -> list:
    """Find memories with low confidence (pruning candidates)."""
    low_conf = []

    for mem_id, mem_data in graph['nodes'].get('memories', {}).items():
        confidence = mem_data.get('confidence', 0)
        if confidence < threshold:
            low_conf.append({
                'id': mem_id,
                'summary': mem_data.get('summary'),
                'confidence': confidence,
                'type': mem_data.get('type')
            })

    return sorted(low_conf, key=lambda x: x['confidence'])


def apply_decay(graph: dict, decay_rate: float = 0.01) -> dict:
    """Apply confidence decay to all memories based on time since validation."""
    now = datetime.now()

    for mem_id, mem_data in graph['nodes'].get('memories', {}).items():
        last_validated = mem_data.get('last_validated')
        if not last_validated:
            continue

        try:
            validated_date = datetime.strptime(last_validated, '%Y-%m-%d')
            days_since = (now - validated_date).days
            weeks_since = days_since / 7

            # Apply decay: 1% per week
            current_conf = mem_data.get('confidence', 0.8)
            new_conf = max(0.0, current_conf - (decay_rate * weeks_since))
            mem_data['confidence'] = round(new_conf, 2)
        except ValueError:
            pass

    return graph


def prune_memories(graph: dict, threshold: float = 0.3, dry_run: bool = True) -> dict:
    """Remove memories below confidence threshold."""
    to_remove = []

    for mem_id, mem_data in graph['nodes'].get('memories', {}).items():
        if mem_data.get('confidence', 0) < threshold:
            to_remove.append(mem_id)

    result = {
        'would_remove': len(to_remove),
        'memories': to_remove
    }

    if not dry_run and to_remove:
        for mem_id in to_remove:
            del graph['nodes']['memories'][mem_id]

            # Remove from concept index
            for concept in graph.get('concept_index', {}).values():
                if mem_id in concept:
                    concept.remove(mem_id)

            # Remove edges
            graph['edges'] = [e for e in graph['edges']
                            if e['from'] != mem_id and e['to'] != mem_id]

        result['removed'] = len(to_remove)

    return result


def health_check(graph: dict) -> dict:
    """Run comprehensive health check on graph."""
    memories = graph['nodes'].get('memories', {})
    tasks = graph['nodes'].get('tasks', {})
    concepts = graph['nodes'].get('concepts', {})

    # Basic stats
    stats = {
        'total_nodes': sum(len(v) for v in graph['nodes'].values()),
        'total_edges': len(graph['edges']),
        'memory_count': len(memories),
        'task_count': len(tasks),
        'concept_count': len(concepts)
    }

    # Memory health
    high_conf = sum(1 for m in memories.values() if m.get('confidence', 0) >= 0.7)
    low_conf = sum(1 for m in memories.values() if m.get('confidence', 0) < 0.3)

    stats['memories_high_confidence'] = high_conf
    stats['memories_low_confidence'] = low_conf

    # Orphan detection
    indexed_nodes = set()
    for nodes in graph.get('concept_index', {}).values():
        indexed_nodes.update(nodes)

    all_node_ids = set()
    for node_type, nodes in graph['nodes'].items():
        if node_type != 'concepts':
            all_node_ids.update(nodes.keys())

    orphans = all_node_ids - indexed_nodes
    stats['orphan_nodes'] = len(orphans)

    # Issues
    issues = []
    if low_conf > 0:
        issues.append(f'{low_conf} memories below 0.3 confidence (prune candidates)')
    if len(orphans) > 10:
        issues.append(f'{len(orphans)} nodes not indexed by any concept')

    conflicts = detect_conflicts(graph)
    if conflicts:
        issues.append(f'{len(conflicts)} potential memory conflicts detected')

    stale = find_stale_memories(graph)
    if stale:
        issues.append(f'{len(stale)} stale memories (not validated in 90+ days)')

    stats['issues'] = issues
    stats['health_score'] = max(0, 100 - len(issues) * 15 - low_conf * 5)

    return stats


def main():
    parser = argparse.ArgumentParser(description='Knowledge graph maintenance')
    parser.add_argument('--action', required=True,
                       choices=['health', 'conflicts', 'stale', 'low-confidence',
                               'decay', 'prune'],
                       help='Action to perform')
    parser.add_argument('--graph-path', default='.agent/knowledge/graph.json',
                       help='Path to knowledge graph')
    parser.add_argument('--threshold', type=float, default=0.3,
                       help='Confidence threshold for pruning')
    parser.add_argument('--stale-days', type=int, default=90,
                       help='Days until memory considered stale')
    parser.add_argument('--decay-rate', type=float, default=0.01,
                       help='Decay rate per week')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be pruned without removing')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform pruning (override dry-run)')

    args = parser.parse_args()
    graph = load_graph(args.graph_path)

    if args.action == 'health':
        result = health_check(graph)
        print("Knowledge Graph Health Check")
        print("=" * 40)
        print(f"Total Nodes: {result['total_nodes']}")
        print(f"Total Edges: {result['total_edges']}")
        print(f"Memories: {result['memory_count']} ({result['memories_high_confidence']} high confidence)")
        print(f"Tasks: {result['task_count']}")
        print(f"Concepts: {result['concept_count']}")
        print(f"Orphan Nodes: {result['orphan_nodes']}")
        print(f"\nHealth Score: {result['health_score']}/100")
        if result['issues']:
            print("\nIssues:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("\nNo issues detected!")

    elif args.action == 'conflicts':
        conflicts = detect_conflicts(graph)
        if conflicts:
            print(f"Found {len(conflicts)} potential conflicts:\n")
            for c in conflicts:
                print(f"Concept: {c['concept']}")
                print(f"  Memory 1: {c['memory1']['id']} - {c['memory1']['summary']}")
                print(f"  Memory 2: {c['memory2']['id']} - {c['memory2']['summary']}")
                print(f"  Suggestion: {c['suggestion']}\n")
        else:
            print("No conflicts detected!")

    elif args.action == 'stale':
        stale = find_stale_memories(graph, args.stale_days)
        if stale:
            print(f"Found {len(stale)} stale memories:\n")
            for s in stale:
                print(f"  {s['id']}: {s['summary'][:50]}...")
                print(f"    Reason: {s['reason']}, Confidence: {s['confidence']}")
        else:
            print("No stale memories!")

    elif args.action == 'low-confidence':
        low = find_low_confidence(graph, args.threshold)
        if low:
            print(f"Found {len(low)} low-confidence memories (< {args.threshold}):\n")
            for l in low:
                print(f"  {l['id']}: {l['summary'][:50]}...")
                print(f"    Type: {l['type']}, Confidence: {l['confidence']}")
        else:
            print(f"No memories below {args.threshold} confidence!")

    elif args.action == 'decay':
        graph = apply_decay(graph, args.decay_rate)
        if save_graph(args.graph_path, graph):
            print(f"Applied decay (rate: {args.decay_rate}/week) to all memories")
        else:
            print("Failed to save graph", file=sys.stderr)
            sys.exit(1)

    elif args.action == 'prune':
        dry_run = not args.execute
        result = prune_memories(graph, args.threshold, dry_run)

        if dry_run:
            print(f"Would remove {result['would_remove']} memories below {args.threshold}:")
            for mem_id in result['memories']:
                print(f"  - {mem_id}")
            print("\nRun with --execute to actually remove them.")
        else:
            if save_graph(args.graph_path, graph):
                print(f"Pruned {result['removed']} memories below {args.threshold}")
            else:
                print("Failed to save graph", file=sys.stderr)
                sys.exit(1)


if __name__ == '__main__':
    main()
