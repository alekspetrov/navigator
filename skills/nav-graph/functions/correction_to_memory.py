#!/usr/bin/env python3
"""
Correction to Memory - Converts profile corrections to graph memories

Integrates nav-profile corrections with the knowledge graph by creating
pitfall/pattern memories from repeated corrections.
"""

import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Import from sibling module
sys.path.insert(0, str(Path(__file__).parent))
from graph_manager import load_graph, save_graph, add_memory


def load_profile(profile_path: str) -> dict:
    """Load user profile from file."""
    path = Path(profile_path)
    if path.exists():
        with open(path, 'r') as f:
            return json.load(f)
    return {}


def extract_concepts_from_correction(correction: dict) -> list:
    """Extract concepts from a correction based on context and pattern."""
    concepts = set()

    # Keywords to concept mapping
    keyword_map = {
        'auth': 'authentication',
        'login': 'authentication',
        'jwt': 'authentication',
        'oauth': 'authentication',
        'api': 'api',
        'endpoint': 'api',
        'rest': 'api',
        'test': 'testing',
        'spec': 'testing',
        'component': 'frontend',
        'react': 'frontend',
        'database': 'database',
        'migration': 'database',
        'schema': 'database',
        'deploy': 'deployment',
        'ci': 'deployment',
        'style': 'code-style',
        'naming': 'code-style',
        'format': 'code-style',
    }

    # Check context and pattern for keywords
    text = f"{correction.get('context', '')} {correction.get('pattern', '')}".lower()

    for keyword, concept in keyword_map.items():
        if keyword in text:
            concepts.add(concept)

    # Default to 'general' if no concepts found
    if not concepts:
        concepts.add('general')

    return list(concepts)


def determine_memory_type(correction: dict) -> str:
    """Determine if correction should be a pitfall, pattern, or learning."""
    pattern_text = correction.get('pattern', '').lower()

    pitfall_words = ['avoid', "don't", 'never', 'watch out', 'careful', 'breaks', 'fails']
    if any(word in pattern_text for word in pitfall_words):
        return 'pitfall'

    pattern_words = ['always', 'use', 'prefer', 'should', 'must']
    if any(word in pattern_text for word in pattern_words):
        return 'pattern'

    return 'learning'


def correction_to_memory(correction: dict, graph_path: str) -> Optional[str]:
    """Convert a single correction to a graph memory."""
    graph = load_graph(graph_path)

    # Extract info from correction
    pattern = correction.get('pattern', '')
    if not pattern:
        pattern = correction.get('corrected_to', 'Unknown correction')

    concepts = extract_concepts_from_correction(correction)
    memory_type = determine_memory_type(correction)

    # Determine confidence based on correction confidence
    confidence_map = {'high': 0.9, 'medium': 0.8, 'low': 0.7}
    confidence = confidence_map.get(correction.get('confidence', 'medium'), 0.8)

    # Create memory
    memory_id = add_memory(
        graph=graph,
        memory_type=memory_type,
        summary=pattern,
        concepts=concepts,
        confidence=confidence,
        source_task=None  # Corrections don't have source tasks
    )

    if save_graph(graph_path, graph):
        return memory_id
    return None


def sync_corrections_to_graph(profile_path: str, graph_path: str,
                               last_synced_count: int = 0) -> dict:
    """Sync new corrections from profile to graph as memories."""
    profile = load_profile(profile_path)
    corrections = profile.get('corrections', [])

    # Only process corrections after last_synced_count
    new_corrections = corrections[last_synced_count:]

    results = {
        'synced': 0,
        'failed': 0,
        'memory_ids': [],
        'new_count': len(corrections)
    }

    for correction in new_corrections:
        memory_id = correction_to_memory(correction, graph_path)
        if memory_id:
            results['synced'] += 1
            results['memory_ids'].append(memory_id)
        else:
            results['failed'] += 1

    return results


def check_for_new_corrections(profile_path: str, graph_path: str) -> dict:
    """Check if there are new corrections to sync."""
    profile = load_profile(profile_path)
    graph = load_graph(graph_path)

    correction_count = len(profile.get('corrections', []))

    # Check how many corrections we've already synced
    # We track this by counting memories with no source_task (correction-based)
    synced_count = sum(
        1 for m in graph['nodes'].get('memories', {}).values()
        if 'learned-from' not in str(graph.get('edges', []))
    )

    return {
        'profile_corrections': correction_count,
        'synced_memories': synced_count,
        'pending': max(0, correction_count - synced_count)
    }


def main():
    parser = argparse.ArgumentParser(
        description='Convert profile corrections to graph memories'
    )
    parser.add_argument('--action', required=True,
                       choices=['sync', 'check', 'convert-one'],
                       help='Action to perform')
    parser.add_argument('--profile-path', default='.agent/.user-profile.json',
                       help='Path to user profile')
    parser.add_argument('--graph-path', default='.agent/knowledge/graph.json',
                       help='Path to knowledge graph')
    parser.add_argument('--correction-json', help='JSON of correction to convert')
    parser.add_argument('--last-synced', type=int, default=0,
                       help='Count of already synced corrections')

    args = parser.parse_args()

    if args.action == 'check':
        result = check_for_new_corrections(args.profile_path, args.graph_path)
        print(f"Profile corrections: {result['profile_corrections']}")
        print(f"Synced to graph: {result['synced_memories']}")
        print(f"Pending sync: {result['pending']}")

    elif args.action == 'sync':
        result = sync_corrections_to_graph(
            args.profile_path,
            args.graph_path,
            args.last_synced
        )
        print(f"Synced {result['synced']} corrections to graph")
        if result['failed'] > 0:
            print(f"Failed: {result['failed']}")
        if result['memory_ids']:
            print(f"Created memories: {', '.join(result['memory_ids'])}")

    elif args.action == 'convert-one':
        if not args.correction_json:
            print("Error: --correction-json required", file=sys.stderr)
            sys.exit(1)

        correction = json.loads(args.correction_json)
        memory_id = correction_to_memory(correction, args.graph_path)

        if memory_id:
            print(f"Created memory: {memory_id}")
        else:
            print("Failed to create memory", file=sys.stderr)
            sys.exit(1)


if __name__ == '__main__':
    main()
