#!/usr/bin/env python3
"""
Graph Maintenance - Conflict detection, staleness pruning, health checks

Maintains knowledge graph health over time.
"""

import json
import sys
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, save_graph

DEFAULT_DECAY_RATE = 0.01


# ──────────────────────────────────────────────────────────────────────────────
# Integrity helpers (wp6 / TASK-47)
# ──────────────────────────────────────────────────────────────────────────────

def _all_node_ids(graph: dict) -> set:
    """Union of every node id across all node buckets (concepts included).

    A concept node is keyed by its canonical name, so an 'implements' edge that
    points task -> concept is valid only when that concept name is a node id.
    """
    ids = set()
    for nodes in graph.get('nodes', {}).values():
        ids.update(nodes.keys())
    return ids


def _edge_key(edge: dict) -> tuple:
    return (edge.get('from'), edge.get('to'), edge.get('type'))


def find_duplicate_edges(graph: dict) -> int:
    """Count edge rows that repeat an earlier (from, to, type) tuple."""
    seen = set()
    dupes = 0
    for edge in graph.get('edges', []):
        key = _edge_key(edge)
        if key in seen:
            dupes += 1
        else:
            seen.add(key)
    return dupes


def find_dangling_edges(graph: dict) -> list:
    """Return edges whose `from` or `to` is not a known node id."""
    node_ids = _all_node_ids(graph)
    return [
        e for e in graph.get('edges', [])
        if e.get('from') not in node_ids or e.get('to') not in node_ids
    ]


def find_out_of_range_confidence(graph: dict) -> list:
    """Return (id, confidence) for memories whose confidence is outside [0,1]."""
    out = []
    for mem_id, mem in graph.get('nodes', {}).get('memories', {}).items():
        c = mem.get('confidence')
        if isinstance(c, (int, float)) and (c < 0.0 or c > 1.0):
            out.append((mem_id, c))
    return out


def _normalize_confidence_value(c: float) -> float:
    """Repair an out-of-range confidence in EXISTING data.

    Values in (1, 100] are treated as mis-stored percentages (mem-026 shipped
    as 90.0, i.e. 90% -> 0.9); anything else out of range is clamped to [0,1].
    """
    if c < 0.0:
        return 0.0
    if c > 1.0:
        scaled = round(c / 100.0, 2)
        return scaled if scaled <= 1.0 else 1.0
    return c


def repair_graph(graph: dict) -> dict:
    """Idempotently repair graph integrity defects in place.

    - drop duplicate (from, to, type) edge rows (keep first occurrence)
    - drop edges referencing an absent node id (dangling)
    - normalize out-of-range memory confidences

    Returns a summary dict. Running it a second time is a no-op.
    """
    edges = graph.get('edges', [])
    before = len(edges)
    node_ids = _all_node_ids(graph)

    seen = set()
    cleaned = []
    dup_removed = 0
    dangling_removed = 0
    for edge in edges:
        if edge.get('from') not in node_ids or edge.get('to') not in node_ids:
            dangling_removed += 1
            continue
        key = _edge_key(edge)
        if key in seen:
            dup_removed += 1
            continue
        seen.add(key)
        cleaned.append(edge)
    graph['edges'] = cleaned

    conf_fixed = 0
    for mem in graph.get('nodes', {}).get('memories', {}).values():
        c = mem.get('confidence')
        if isinstance(c, (int, float)) and (c < 0.0 or c > 1.0):
            mem['confidence'] = _normalize_confidence_value(c)
            conf_fixed += 1

    return {
        'edges_before': before,
        'edges_after': len(cleaned),
        'duplicates_removed': dup_removed,
        'dangling_removed': dangling_removed,
        'confidences_normalized': conf_fixed,
    }


def _read_decay_rate(config_path: str) -> float:
    """Read knowledge_graph.confidence_decay_rate from config (default 0.01)."""
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        rate = cfg.get('knowledge_graph', {}).get('confidence_decay_rate')
        return float(rate) if rate is not None else DEFAULT_DECAY_RATE
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return DEFAULT_DECAY_RATE


def _read_staleness_days(config_path: str) -> int:
    """Read knowledge_graph.staleness_threshold_days from config (default 90)."""
    try:
        with open(config_path) as f:
            cfg = json.load(f)
        days = cfg.get('knowledge_graph', {}).get('staleness_threshold_days')
        return int(days) if days is not None else 90
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return 90


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


def apply_decay(graph: dict, decay_rate: Optional[float] = None,
                config_path: str = '.agent/.nav-config.json',
                today: Optional[object] = None) -> dict:
    """Idempotently decay memory confidence by time since the last decay.

    EXPERIMENTAL / manual-only: this is NOT wired to any hook. Decaying on every
    session start would mutate a git-tracked file each session (fights
    knowledge_graph.git_tracked=true), so decay runs only via an explicit
    `--action decay` invocation.

    Idempotency: decay accrues from each memory's `last_decayed` anchor (falling
    back to `last_validated`), and the anchor is advanced to `today` after each
    run. Running twice on the same calendar day is therefore a no-op. The rate
    defaults to knowledge_graph.confidence_decay_rate from config.
    """
    if decay_rate is None:
        decay_rate = _read_decay_rate(config_path)
    if today is None:
        today = datetime.now(timezone.utc).date()
    today_str = today.isoformat()

    for mem_data in graph['nodes'].get('memories', {}).values():
        anchor = mem_data.get('last_decayed') or mem_data.get('last_validated')
        if not anchor:
            continue
        try:
            anchor_date = datetime.strptime(anchor, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            continue

        days_since = (today - anchor_date).days
        mem_data['last_decayed'] = today_str
        if days_since <= 0:
            continue  # already decayed today (or future-dated) — no-op

        weeks_since = days_since / 7
        current_conf = mem_data.get('confidence', 0.8)
        mem_data['confidence'] = round(max(0.0, current_conf - (decay_rate * weeks_since)), 2)

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

            # Remove from concept index, dropping now-empty concept keys
            # (mirror remove_node — leftover empty keys are graph cruft).
            empty_concepts = []
            for concept, members in graph.get('concept_index', {}).items():
                if mem_id in members:
                    members.remove(mem_id)
                    if not members:
                        empty_concepts.append(concept)
            for concept in empty_concepts:
                del graph['concept_index'][concept]

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

    # Integrity defects — the wp6 health gate (these must read 0 post-repair).
    dup_edges = find_duplicate_edges(graph)
    dangling = find_dangling_edges(graph)
    oor_conf = find_out_of_range_confidence(graph)
    stats['duplicate_edges'] = dup_edges
    stats['dangling_edges'] = len(dangling)
    stats['confidence_out_of_range'] = len(oor_conf)

    # Issues (score-affecting): integrity defects + low-confidence volume.
    issues = []
    if dup_edges:
        issues.append(f'{dup_edges} duplicate edges')
    if dangling:
        issues.append(f'{len(dangling)} dangling edges (reference missing nodes)')
    if oor_conf:
        issues.append(f'{len(oor_conf)} memories with confidence outside [0,1]')
    if low_conf > 0:
        issues.append(f'{low_conf} memories below 0.3 confidence (prune candidates)')
    if len(orphans) > 10:
        issues.append(f'{len(orphans)} nodes not indexed by any concept')

    # Advisory (NOT score-affecting): the conflict heuristic is high-false-
    # positive and staleness is expected on an actively-curated graph.
    advisory = []
    conflicts = detect_conflicts(graph)
    if conflicts:
        advisory.append(f'{len(conflicts)} potential memory conflicts (heuristic, advisory)')
    stale = find_stale_memories(graph)
    if stale:
        advisory.append(f'{len(stale)} stale memories (not validated in 90+ days)')

    stats['issues'] = issues
    stats['advisory'] = advisory
    stats['health_score'] = max(0, 100 - len(issues) * 15 - low_conf * 5)

    return stats


def main():
    parser = argparse.ArgumentParser(description='Knowledge graph maintenance')
    parser.add_argument('--action', required=True,
                       choices=['health', 'conflicts', 'stale', 'low-confidence',
                               'decay', 'prune', 'repair'],
                       help='Action to perform')
    parser.add_argument('--graph-path', default='.agent/knowledge/graph.json',
                       help='Path to knowledge graph')
    parser.add_argument('--threshold', type=float, default=0.3,
                       help='Confidence threshold for pruning')
    parser.add_argument('--stale-days', type=int, default=None,
                       help='Days until memory considered stale (default: knowledge_graph.staleness_threshold_days)')
    parser.add_argument('--decay-rate', type=float, default=None,
                       help='Decay rate per week (default: knowledge_graph.confidence_decay_rate)')
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
        print(f"Duplicate Edges: {result['duplicate_edges']}")
        print(f"Dangling Edges: {result['dangling_edges']}")
        print(f"Confidence Out-of-Range: {result['confidence_out_of_range']}")
        print(f"\nHealth Score: {result['health_score']}/100")
        if result['issues']:
            print("\nIssues:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("\nNo integrity issues detected!")
        if result.get('advisory'):
            print("\nAdvisory (not scored):")
            for note in result['advisory']:
                print(f"  - {note}")

    elif args.action == 'repair':
        summary = repair_graph(graph)
        if save_graph(args.graph_path, graph):
            print("Knowledge Graph Repair")
            print("=" * 40)
            print(f"Edges: {summary['edges_before']} -> {summary['edges_after']}")
            print(f"  Duplicates removed: {summary['duplicates_removed']}")
            print(f"  Dangling removed:   {summary['dangling_removed']}")
            print(f"Confidences normalized: {summary['confidences_normalized']}")
        else:
            print("Failed to save graph", file=sys.stderr)
            sys.exit(1)

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
        stale_days = (args.stale_days if args.stale_days is not None
                      else _read_staleness_days('.agent/.nav-config.json'))
        stale = find_stale_memories(graph, stale_days)
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
        effective_rate = (args.decay_rate if args.decay_rate is not None
                          else _read_decay_rate('.agent/.nav-config.json'))
        graph = apply_decay(graph, effective_rate)
        if save_graph(args.graph_path, graph):
            print(f"Applied decay (rate: {effective_rate}/week, idempotent per day)")
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
