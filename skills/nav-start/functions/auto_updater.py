#!/usr/bin/env python3
"""
Navigator Auto-Updater

Automatically updates Navigator plugin on session start if:
1. auto_update.enabled is true in .nav-config.json
2. A newer version is available
3. Last check was more than check_interval_hours ago

Usage:
    python auto_updater.py [--config-path PATH]

Returns JSON:
    {"status": "updated|up-to-date|failed|disabled|skipped", ...}
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from urllib import request


# --- Version Detection (from nav-upgrade/version_detector.py) ---

def get_current_version() -> Optional[str]:
    """Get currently installed Navigator version from plugin list."""
    try:
        result = subprocess.run(
            ['claude', 'plugin', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )

        for line in result.stdout.split('\n'):
            if 'navigator' in line.lower():
                match = re.search(r'v?(\d+\.\d+\.\d+)', line)
                if match:
                    return match.group(1)
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return None


def get_latest_version_from_github() -> Dict:
    """Get latest Navigator version from GitHub releases API."""
    try:
        url = 'https://api.github.com/repos/alekspetrov/navigator/releases/latest'
        req = request.Request(url)
        req.add_header('User-Agent', 'Navigator-Auto-Updater')

        with request.urlopen(req, timeout=10) as response:
            data = json.load(response)
            tag_name = data.get('tag_name', '')
            version = tag_name.lstrip('v')
            return {
                'version': version,
                'release_url': data.get('html_url', ''),
                'release_date': data.get('published_at', '').split('T')[0]
            }
    except Exception as e:
        return {'version': None, 'error': str(e)}


def compare_versions(current: str, latest: str) -> int:
    """
    Compare semantic versions.
    Returns: -1 if current < latest, 0 if equal, 1 if current > latest
    """
    try:
        current_parts = [int(x) for x in current.split('.')]
        latest_parts = [int(x) for x in latest.split('.')]

        while len(current_parts) < len(latest_parts):
            current_parts.append(0)
        while len(latest_parts) < len(current_parts):
            latest_parts.append(0)

        for c, l in zip(current_parts, latest_parts):
            if c < l:
                return -1
            elif c > l:
                return 1
        return 0
    except (ValueError, AttributeError):
        return 0


# --- Plugin Update (from nav-upgrade/plugin_updater.py) ---

def update_plugin_via_claude() -> Dict:
    """Execute plugin update command."""
    try:
        result = subprocess.run(
            ['claude', 'plugin', 'update', 'navigator'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr,
            'method': 'update'
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Update timed out (60s)', 'method': 'update'}
    except FileNotFoundError:
        return {'success': False, 'error': 'claude command not found', 'method': 'update'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'method': 'update'}


def reinstall_plugin() -> Dict:
    """Fallback: uninstall and reinstall Navigator."""
    try:
        # Uninstall
        uninstall_result = subprocess.run(
            ['claude', 'plugin', 'uninstall', 'navigator'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if uninstall_result.returncode != 0:
            return {
                'success': False,
                'error': f'Uninstall failed: {uninstall_result.stderr}',
                'method': 'reinstall'
            }

        time.sleep(2)

        # Add from marketplace
        add_result = subprocess.run(
            ['claude', 'plugin', 'marketplace', 'add', 'alekspetrov/navigator'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if add_result.returncode != 0:
            return {
                'success': False,
                'error': f'Marketplace add failed: {add_result.stderr}',
                'method': 'reinstall'
            }

        time.sleep(2)

        # Install
        install_result = subprocess.run(
            ['claude', 'plugin', 'install', 'navigator'],
            capture_output=True,
            text=True,
            timeout=60
        )
        return {
            'success': install_result.returncode == 0,
            'output': install_result.stdout,
            'error': install_result.stderr if install_result.returncode != 0 else None,
            'method': 'reinstall'
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Reinstall timed out', 'method': 'reinstall'}
    except Exception as e:
        return {'success': False, 'error': str(e), 'method': 'reinstall'}


# --- Version Drift Detection ---

def detect_version_drift(config_path: str = '.agent/.nav-config.json') -> Dict:
    """
    Detect if plugin version differs from project config version.

    Returns:
        Dict with drift status:
        - has_drift: bool
        - plugin_version: str
        - project_version: str
        - message: str
    """
    plugin_version = get_current_version()
    if not plugin_version:
        return {
            'has_drift': False,
            'message': 'Could not detect plugin version'
        }

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            project_version = config.get('version', '')
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            'has_drift': False,
            'message': 'Could not read project config'
        }

    if not project_version:
        return {
            'has_drift': True,
            'plugin_version': plugin_version,
            'project_version': 'unknown',
            'message': f'Project config missing version. Plugin is v{plugin_version}.'
        }

    if compare_versions(project_version, plugin_version) < 0:
        return {
            'has_drift': True,
            'plugin_version': plugin_version,
            'project_version': project_version,
            'message': f'Project config (v{project_version}) behind plugin (v{plugin_version}). Run "update my CLAUDE.md" to sync.'
        }

    return {
        'has_drift': False,
        'plugin_version': plugin_version,
        'project_version': project_version,
        'message': 'Versions in sync'
    }


def sync_project_config(config_path: str, new_version: str) -> Dict:
    """
    Update project .nav-config.json with new version and any missing config sections.

    Returns:
        Dict with sync status
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'success': False, 'error': 'Could not read config'}

    old_version = config.get('version', 'unknown')
    changes = []

    # Update version
    config['version'] = new_version
    changes.append(f'version: {old_version} → {new_version}')

    # Add missing config sections based on version
    # v5.0.0+: tom_features
    if 'tom_features' not in config:
        config['tom_features'] = {
            'verification_checkpoints': True,
            'confirmation_threshold': 'high-stakes',
            'profile_enabled': True,
            'diagnose_enabled': True,
            'belief_anchors': False
        }
        changes.append('added: tom_features')

    # v5.1.0+: loop_mode
    if 'loop_mode' not in config:
        config['loop_mode'] = {
            'enabled': False,
            'max_iterations': 5,
            'stagnation_threshold': 3,
            'exit_requires_explicit_signal': True
        }
        changes.append('added: loop_mode')

    # v5.4.0+: simplification
    if 'simplification' not in config:
        config['simplification'] = {
            'enabled': True,
            'trigger': 'post-implementation',
            'scope': 'modified'
        }
        changes.append('added: simplification')

    # v5.5.0+: auto_update (ensure it exists)
    if 'auto_update' not in config:
        config['auto_update'] = {
            'enabled': True,
            'check_interval_hours': 1
        }
        changes.append('added: auto_update')

    # v5.6.0+: task_mode
    if 'task_mode' not in config:
        config['task_mode'] = {
            'enabled': True,
            'auto_detect': True,
            'defer_to_skills': True,
            'complexity_threshold': 0.5,
            'show_phase_indicator': True
        }
        changes.append('added: task_mode')

    # Save updated config
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
            f.write('\n')
        return {
            'success': True,
            'changes': changes,
            'message': f'Config synced: {", ".join(changes)}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# --- Auto-Update Logic ---

def load_config(config_path: str = '.agent/.nav-config.json') -> Dict:
    """Load Navigator configuration."""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(config: Dict, config_path: str = '.agent/.nav-config.json'):
    """Save Navigator configuration."""
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass  # Non-critical, just skip


def should_check_update(config: Dict) -> bool:
    """
    Determine if we should check for updates based on interval.
    Returns True if last check was more than check_interval_hours ago.
    """
    auto_update = config.get('auto_update', {})
    if not auto_update.get('enabled', False):
        return False

    interval_hours = auto_update.get('check_interval_hours', 1)
    last_check_str = auto_update.get('last_check')

    if not last_check_str:
        return True

    try:
        last_check = datetime.fromisoformat(last_check_str)
        next_check = last_check + timedelta(hours=interval_hours)
        return datetime.now() > next_check
    except (ValueError, TypeError):
        return True


def auto_update(config_path: str = '.agent/.nav-config.json') -> Dict:
    """
    Main auto-update logic.

    Returns:
        Dict with status and details:
        - status: 'updated' | 'up-to-date' | 'failed' | 'disabled' | 'skipped'
        - current_version: str
        - latest_version: str (if checked)
        - message: str
    """
    config = load_config(config_path)
    auto_update_config = config.get('auto_update', {})

    # Check if auto-update is enabled
    if not auto_update_config.get('enabled', False):
        return {
            'status': 'disabled',
            'message': 'Auto-update disabled in config'
        }

    # Check if we should check (based on interval)
    if not should_check_update(config):
        return {
            'status': 'skipped',
            'message': 'Checked recently, skipping'
        }

    # Get current version
    current_version = get_current_version()
    if not current_version:
        return {
            'status': 'failed',
            'message': 'Could not detect current Navigator version',
            'current_version': None
        }

    # Get latest version from GitHub
    latest_info = get_latest_version_from_github()
    latest_version = latest_info.get('version')

    if not latest_version:
        # Update last check time even on failure (to avoid hammering)
        auto_update_config['last_check'] = datetime.now().isoformat()
        config['auto_update'] = auto_update_config
        save_config(config, config_path)

        return {
            'status': 'failed',
            'message': f"Could not check latest version: {latest_info.get('error', 'unknown')}",
            'current_version': current_version
        }

    # Compare versions
    comparison = compare_versions(current_version, latest_version)

    if comparison >= 0:
        # Up to date or ahead
        auto_update_config['last_check'] = datetime.now().isoformat()
        config['auto_update'] = auto_update_config
        save_config(config, config_path)

        return {
            'status': 'up-to-date',
            'message': f'Already on latest version',
            'current_version': current_version,
            'latest_version': latest_version
        }

    # Update available - attempt update
    update_result = update_plugin_via_claude()

    if not update_result['success']:
        # Try reinstall as fallback
        update_result = reinstall_plugin()

    # Update last check time
    auto_update_config['last_check'] = datetime.now().isoformat()
    config['auto_update'] = auto_update_config
    save_config(config, config_path)

    if update_result['success']:
        # Sync project config with new version
        sync_result = sync_project_config(config_path, latest_version)

        return {
            'status': 'updated',
            'message': f'Auto-updated to v{latest_version}',
            'current_version': current_version,
            'new_version': latest_version,
            'method': update_result.get('method', 'update'),
            'requires_restart': True,
            'restart_reason': 'Claude Code caches skill paths at session start. Restart to load new skills.',
            'project_synced': sync_result.get('success', False),
            'sync_changes': sync_result.get('changes', [])
        }
    else:
        return {
            'status': 'failed',
            'message': f"Auto-update failed: {update_result.get('error', 'unknown')}",
            'current_version': current_version,
            'latest_version': latest_version,
            'update_available': True
        }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description='Navigator Auto-Updater')
    parser.add_argument(
        '--config-path',
        default='.agent/.nav-config.json',
        help='Path to Navigator config file'
    )
    parser.add_argument(
        '--check-drift',
        action='store_true',
        help='Only check for version drift, do not update'
    )
    args = parser.parse_args()

    # Check drift mode
    if args.check_drift:
        result = detect_version_drift(args.config_path)
        print(json.dumps(result, indent=2))
        sys.exit(0 if not result.get('has_drift') else 1)

    # Normal auto-update mode
    result = auto_update(args.config_path)

    # Output as JSON
    print(json.dumps(result, indent=2))

    # Exit codes:
    # 0 = updated or up-to-date
    # 1 = failed
    # 2 = disabled or skipped
    if result['status'] in ('updated', 'up-to-date'):
        sys.exit(0)
    elif result['status'] == 'failed':
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == '__main__':
    main()
