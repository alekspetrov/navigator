#!/usr/bin/env python3
"""
Preference Extractor - Extract preferences and corrections from user input

Parses natural language to identify preference updates and correction patterns.
"""

import json
import sys
import argparse
import re
from typing import Optional, Dict, Tuple


# Preference mappings: user phrases -> (category, field, value)
PREFERENCE_PATTERNS = {
    # Communication - Verbosity
    r'\b(concise|brief|short)\b': ('communication', 'verbosity', 'concise'),
    r'\b(detailed|thorough|verbose)\b': ('communication', 'verbosity', 'detailed'),
    r'\bbalanced\b': ('communication', 'verbosity', 'balanced'),

    # Communication - Confirmation threshold
    r'\balways confirm\b': ('communication', 'confirmation_threshold', 'always'),
    r'\b(skip confirmations?|no confirmations?)\b': ('communication', 'confirmation_threshold', 'never'),
    r'\bhigh.?stakes?\s*(only)?\b': ('communication', 'confirmation_threshold', 'high-stakes'),

    # Communication - Explanation style
    r'\bshow\s*examples?\b': ('communication', 'explanation_style', 'examples'),
    r'\btheory\s*(first|based)?\b': ('communication', 'explanation_style', 'theory'),
    r'\bboth\s*(examples?\s*(and|&)\s*theory|theory\s*(and|&)\s*examples?)\b': ('communication', 'explanation_style', 'both'),

    # Technical - Code style
    r'\bfunctional\s*(style|programming)?\b': ('technical', 'code_style', 'functional'),
    r'\b(oop|object.?oriented)\s*(style|programming)?\b': ('technical', 'code_style', 'oop'),
    r'\bmixed\s*(style)?\b': ('technical', 'code_style', 'mixed'),

    # Technical - Testing
    r'\btdd\b': ('technical', 'testing_preference', 'tdd'),
    r'\bbdd\b': ('technical', 'testing_preference', 'bdd'),
    r'\bmanual\s*test(ing)?\b': ('technical', 'testing_preference', 'manual'),

    # Workflow - Autonomous commits
    r'\bautonomous\s*commits?\b': ('workflow', 'autonomous_commits', True),
    r'\bask\s*before\s*commit(ting)?\b': ('workflow', 'autonomous_commits', False),
    r'\bno\s*auto\s*commit\b': ('workflow', 'autonomous_commits', False),

    # Workflow - Markers
    r'\bmarkers?\s*before\s*risky\b': ('workflow', 'marker_before_risky', True),
    r'\b(no|skip)\s*markers?\b': ('workflow', 'marker_before_risky', False),
}

# Framework patterns
FRAMEWORK_PATTERNS = {
    r'\breact\b': 'react',
    r'\bvue\b': 'vue',
    r'\bangular\b': 'angular',
    r'\bsvelte\b': 'svelte',
    r'\bnext\.?js\b': 'nextjs',
    r'\bexpress\b': 'express',
    r'\bfastify\b': 'fastify',
    r'\bnest\.?js\b': 'nestjs',
    r'\bdjango\b': 'django',
    r'\bflask\b': 'flask',
    r'\bfastapi\b': 'fastapi',
}

# Correction patterns
CORRECTION_SIGNALS = [
    r'\bno,?\s*i\s*meant\b',
    r'\bactually,?\s*(i\s*)?(prefer|want)\b',
    r'\bnot\s+(\w+),?\s*(use|prefer)\s+(\w+)\b',
    r'\balways\s+do\b',
    r'\bnever\s+do\b',
    r'\bi\s*like\s*when\s*you\b',
    r'\bstop\s+doing\b',
    r'\bdon\'?t\s+(do|use|make)\b',
    r'\bshould\s*be\b',
    r'\bshould\s*have\s*been\b',
]


def extract_preference(text: str) -> Optional[Dict]:
    """Extract preference from user text."""
    text_lower = text.lower()

    for pattern, (category, field, value) in PREFERENCE_PATTERNS.items():
        if re.search(pattern, text_lower):
            return {
                'category': category,
                'field': field,
                'value': value,
                'confidence': 'high'
            }

    return None


def extract_framework_preference(text: str) -> Optional[Dict]:
    """Extract framework preference from user text."""
    text_lower = text.lower()

    # Check if this is a preference statement
    is_preference = any(
        word in text_lower
        for word in ['prefer', 'like', 'use', 'want', 'love', 'favorite']
    )

    if not is_preference:
        return None

    frameworks = []
    for pattern, framework in FRAMEWORK_PATTERNS.items():
        if re.search(pattern, text_lower):
            frameworks.append(framework)

    if frameworks:
        return {
            'category': 'technical',
            'field': 'preferred_frameworks',
            'value': frameworks,
            'action': 'append',  # Append to existing list
            'confidence': 'medium'
        }

    return None


def detect_correction(text: str) -> Optional[Dict]:
    """Detect if text contains a correction pattern."""
    text_lower = text.lower()

    for signal in CORRECTION_SIGNALS:
        match = re.search(signal, text_lower)
        if match:
            return {
                'is_correction': True,
                'signal': match.group(),
                'original_text': text,
                'confidence': 'high' if 'should' in text_lower or 'meant' in text_lower else 'medium'
            }

    return None


def extract_correction_pattern(text: str) -> Optional[Dict]:
    """Extract the correction pattern from user text."""
    detection = detect_correction(text)

    if not detection:
        return None

    # Try to extract "not X, use Y" pattern
    not_use_match = re.search(
        r'not\s+["\']?(\w+)["\']?,?\s*(use|prefer)\s+["\']?(\w+)["\']?',
        text.lower()
    )
    if not_use_match:
        return {
            'context': 'naming convention',
            'original': not_use_match.group(1),
            'corrected_to': not_use_match.group(3),
            'pattern': f"Use {not_use_match.group(3)} instead of {not_use_match.group(1)}",
            'confidence': detection['confidence']
        }

    # Try to extract "should be X" pattern
    should_be_match = re.search(
        r'should\s*(have\s*)?be(en)?\s+["\']?([^"\']+)["\']?',
        text.lower()
    )
    if should_be_match:
        return {
            'context': 'correction',
            'original': 'previous output',
            'corrected_to': should_be_match.group(3).strip(),
            'pattern': f"Should be: {should_be_match.group(3).strip()}",
            'confidence': detection['confidence']
        }

    # Generic correction
    return {
        'context': 'general correction',
        'original': 'previous output',
        'corrected_to': text[:100],  # Truncate
        'pattern': 'User correction (review manually)',
        'confidence': 'low'
    }


def main():
    parser = argparse.ArgumentParser(description='Extract preferences from user input')
    parser.add_argument('--text', required=True, help='User input text to analyze')
    parser.add_argument('--mode', default='all',
                       choices=['preference', 'framework', 'correction', 'all'],
                       help='What to extract')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    results = {
        'preference': None,
        'framework': None,
        'correction': None
    }

    if args.mode in ['preference', 'all']:
        results['preference'] = extract_preference(args.text)

    if args.mode in ['framework', 'all']:
        results['framework'] = extract_framework_preference(args.text)

    if args.mode in ['correction', 'all']:
        results['correction'] = extract_correction_pattern(args.text)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for key, value in results.items():
            if value:
                print(f"{key.upper()}: {json.dumps(value)}")

    # Exit with appropriate code
    if any(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)  # Nothing extracted


if __name__ == '__main__':
    main()
