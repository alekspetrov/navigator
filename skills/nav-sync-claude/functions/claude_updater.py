#!/usr/bin/env python3
"""
Navigator CLAUDE.md Updater
Extracts customizations and generates updated CLAUDE.md with v3.1 template
"""

import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib import request
from urllib.error import URLError, HTTPError

def get_plugin_version() -> Optional[str]:
    """
    Get installed Navigator plugin version from plugin.json.

    Returns:
        Version string (e.g., "4.3.0") or None if not found
    """
    # Check multiple possible installation paths
    possible_paths = [
        # Marketplace cache path (versioned)
        Path.home() / '.claude' / 'plugins' / 'cache' / 'navigator-marketplace' / 'navigator',
        # Legacy marketplace paths
        Path.home() / '.claude' / 'plugins' / 'marketplaces' / 'navigator-marketplace' / '.claude-plugin' / 'plugin.json',
        Path.home() / '.config' / 'claude' / 'plugins' / 'navigator' / '.claude-plugin' / 'plugin.json',
        Path.home() / '.claude' / 'plugins' / 'navigator' / '.claude-plugin' / 'plugin.json',
    ]

    # For the cache path, need to find versioned subdirectory
    cache_base = Path.home() / '.claude' / 'plugins' / 'cache' / 'navigator-marketplace' / 'navigator'
    if cache_base.exists():
        # Find the latest version directory
        version_dirs = sorted([d for d in cache_base.iterdir() if d.is_dir()], reverse=True)
        if version_dirs:
            plugin_json = version_dirs[0] / '.claude-plugin' / 'plugin.json'
            if plugin_json.exists():
                try:
                    with open(plugin_json, 'r') as f:
                        data = json.load(f)
                        return data.get('version')
                except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                    pass

    for path in possible_paths:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    return data.get('version')
            except (json.JSONDecodeError, FileNotFoundError, PermissionError):
                continue

    return None

def fetch_template_from_github(version: Optional[str] = None) -> Optional[str]:
    """
    Fetch CLAUDE.md template from GitHub releases.

    Priority:
    1. Specified version (e.g., 'v4.3.0' or '4.3.0')
    2. Detected plugin version
    3. Returns None (caller should use bundled fallback)

    Args:
        version: Specific version to fetch (optional)

    Returns:
        Template content as string, or None if fetch fails
    """
    if not version:
        version = get_plugin_version()

    if not version:
        return None

    # Ensure version has 'v' prefix for GitHub URL
    if not version.startswith('v'):
        version = f'v{version}'

    github_url = f"https://raw.githubusercontent.com/alekspetrov/navigator/{version}/templates/CLAUDE.md"

    try:
        req = request.Request(github_url)
        req.add_header('User-Agent', 'Navigator-CLAUDE-Updater')

        with request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                content = response.read().decode('utf-8')
                return content
    except (URLError, HTTPError, TimeoutError) as e:
        # Silent fail - caller will use bundled template
        print(f"⚠️  Could not fetch template from GitHub ({version}): {e}", file=sys.stderr)
        print(f"   Falling back to bundled template", file=sys.stderr)
        return None

    return None

def get_template_path(bundled_template_dir: str, version: Optional[str] = None) -> tuple[str, bool]:
    """
    Get template path, preferring GitHub source over bundled.

    Args:
        bundled_template_dir: Path to bundled templates directory
        version: Optional specific version to fetch

    Returns:
        Tuple of (template_path_or_content, is_from_github)
    """
    # Try GitHub first
    github_template = fetch_template_from_github(version)

    if github_template:
        # Write to temporary file
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        temp_file.write(github_template)
        temp_file.close()

        detected_version = version or get_plugin_version()
        print(f"✓ Using template from GitHub ({detected_version})", file=sys.stderr)
        return (temp_file.name, True)

    # Fallback to bundled
    bundled_path = Path(bundled_template_dir) / 'CLAUDE.md'
    if bundled_path.exists():
        bundled_version = get_plugin_version() or "unknown"
        print(f"✓ Using bundled template (v{bundled_version})", file=sys.stderr)
        return (str(bundled_path), False)

    raise FileNotFoundError(f"No template found (GitHub failed, bundled not at {bundled_path})")

def extract_section(content: str, header: str, next_headers: List[str]) -> Optional[str]:
    """Extract content between header and next section header"""
    # Find header (supports ## or # with various markdown formats)
    header_pattern = r'^#{1,2}\s+' + re.escape(header) + r'.*?$'
    match = re.search(header_pattern, content, re.MULTILINE | re.IGNORECASE)

    if not match:
        return None

    start = match.end()

    # Find next header
    next_pattern = r'^#{1,2}\s+(' + '|'.join(re.escape(h) for h in next_headers) + r').*?$'
    next_match = re.search(next_pattern, content[start:], re.MULTILINE | re.IGNORECASE)

    if next_match:
        end = start + next_match.start()
    else:
        end = len(content)

    section = content[start:end].strip()
    return section if section else None

def extract_customizations(claude_md_path: str) -> Dict:
    """Extract project-specific customizations from CLAUDE.md"""

    with open(claude_md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    customizations = {
        "project_name": "",
        "description": "",
        "tech_stack": [],
        "code_standards": [],
        "forbidden_actions": [],
        "pm_tool": "none",
        "custom_sections": {}
    }

    # Extract project name (first # header)
    title_match = re.search(r'^#\s+(.+?)\s*-\s*Claude Code Configuration', content, re.MULTILINE)
    if title_match:
        customizations["project_name"] = title_match.group(1).strip()

    # Extract description from Context section
    context = extract_section(content, "Context", [
        "Navigator Quick Start", "Quick Start", "Project-Specific", "Code Standards",
        "Forbidden Actions", "Documentation", "Project Management"
    ])

    if context:
        # Extract brief description (text before tech stack, excluding brackets)
        lines = context.split('\n')
        desc_lines = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('**Tech Stack') and not line.startswith('['):
                desc_lines.append(line)
            if line.startswith('**Tech Stack'):
                break
        if desc_lines:
            customizations["description"] = ' '.join(desc_lines)

        # Extract tech stack
        tech_match = re.search(r'\*\*Tech Stack\*\*:\s*(.+?)(?:\n|$)', context)
        if tech_match:
            tech_text = tech_match.group(1).strip()
            # Remove brackets and split by comma
            tech_text = re.sub(r'\[|\]', '', tech_text)
            customizations["tech_stack"] = [t.strip() for t in tech_text.split(',')]

    # Extract code standards
    standards_section = extract_section(content, "Project-Specific Code Standards", [
        "Forbidden", "Documentation", "Project Management", "Configuration",
        "Commit Guidelines", "Success Metrics"
    ])

    if not standards_section:
        standards_section = extract_section(content, "Code Standards", [
            "Forbidden", "Documentation", "Project Management", "Configuration"
        ])

    if standards_section:
        # Extract custom rules (lines that aren't in default template)
        default_rules = [
            "KISS, DRY, SOLID",
            "TypeScript",
            "Strict mode",
            "Line Length",
            "Max 100",
            "Testing",
            "Framework-Specific",
            "General Standards",
            "Architecture"
        ]

        lines = standards_section.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines, headers, and default rules
            if not line or line.startswith('#') or line.startswith('**'):
                continue
            # Check if it's a custom rule
            is_default = any(rule in line for rule in default_rules)
            if not is_default:
                if line.startswith('-') or line.startswith('*'):
                    customizations["code_standards"].append(line.lstrip('-*').strip())
                elif ':' in line:  # Format like "Custom rule: Always use hooks"
                    customizations["code_standards"].append(line)

    # Extract forbidden actions
    forbidden_section = extract_section(content, "Forbidden Actions", [
        "Documentation", "Project Management", "Configuration",
        "Commit Guidelines", "Success Metrics"
    ])

    if forbidden_section:
        # Extract custom forbidden actions (not in default template)
        default_forbidden = [
            "NEVER wait for explicit commit",
            "NEVER leave tickets open",
            "NEVER skip documentation",
            "NEVER load all `.agent/`",
            "NEVER load all .agent",
            "NEVER skip reading DEVELOPMENT-README",
            "No Claude Code mentions",
            "No package.json modifications",
            "Never commit secrets",
            "Don't delete tests",
            "NEVER skip tests"
        ]

        lines = forbidden_section.split('\n')
        for line in lines:
            line = line.strip()
            # Skip empty lines and headers
            if not line or line.startswith('#') or line.startswith('**'):
                continue
            if line.startswith('❌') or line.startswith('-'):
                action = line.lstrip('❌- ').strip()
                # Check if it's truly custom
                is_default = any(df in action for df in default_forbidden)
                if action and not is_default:
                    # Remove any leading emoji that might remain
                    action = action.lstrip('❌ ')
                    customizations["forbidden_actions"].append(action)

    # Extract PM tool configuration
    pm_section = extract_section(content, "Project Management", [
        "Configuration", "Commit Guidelines", "Success Metrics"
    ])

    if pm_section:
        # Look for configured tool
        tool_match = re.search(r'\*\*Configured Tool\*\*:\s*(\w+)', pm_section, re.IGNORECASE)
        if tool_match:
            tool = tool_match.group(1).lower()
            if tool in ['linear', 'github', 'jira', 'gitlab']:
                customizations["pm_tool"] = tool

    # Extract custom sections (not in standard template)
    standard_sections = [
        "Context", "Navigator", "Quick Start", "Code Standards",
        "Project-Specific Code Standards", "Forbidden Actions",
        "Documentation Structure", "Project Management",
        "Configuration", "Commit Guidelines", "Success Metrics"
    ]

    # Find all ## headers
    headers = re.findall(r'^##\s+(.+?)$', content, re.MULTILINE)
    for header in headers:
        if header.strip() not in standard_sections:
            section_content = extract_section(content, header, standard_sections + headers)
            if section_content:
                customizations["custom_sections"][header.strip()] = section_content

    return customizations

def generate_updated_claude_md(customizations: Dict, template_path: str, output_path: str):
    """Generate updated CLAUDE.md using v3.1 template and customizations"""

    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # Replace project name
    if customizations["project_name"]:
        template = template.replace('[Project Name]', customizations["project_name"])

    # Replace description
    if customizations["description"]:
        template = template.replace(
            '[Brief project description - explain what this project does]',
            customizations["description"]
        )

    # Replace tech stack
    if customizations["tech_stack"]:
        tech_stack = ', '.join(customizations["tech_stack"])
        template = template.replace(
            '[List your technologies, e.g., Next.js, TypeScript, PostgreSQL]',
            tech_stack
        )

    # Append custom code standards
    if customizations["code_standards"]:
        standards_marker = "[Add project-specific violations here]"
        if standards_marker in template:
            custom_standards = "\n\n### Additional Project Standards\n\n"
            for standard in customizations["code_standards"]:
                custom_standards += f"- {standard}\n"
            template = template.replace(standards_marker, custom_standards + "\n" + standards_marker)

    # Append custom forbidden actions
    if customizations["forbidden_actions"]:
        forbidden_marker = "[Add project-specific violations here]"
        if forbidden_marker in template:
            custom_forbidden = "\n### Additional Forbidden Actions\n\n"
            for action in customizations["forbidden_actions"]:
                custom_forbidden += f"- ❌ {action}\n"
            # Find the marker and append after it
            template = template.replace(forbidden_marker, custom_forbidden)

    # Update PM tool
    if customizations["pm_tool"] != "none":
        template = template.replace(
            '**Configured Tool**: [Linear / GitHub Issues / Jira / GitLab / None]',
            f'**Configured Tool**: {customizations["pm_tool"].title()}'
        )
        # Update config JSON
        template = template.replace(
            '"project_management": "none"',
            f'"project_management": "{customizations["pm_tool"]}"'
        )

    # Append custom sections at the end
    if customizations["custom_sections"]:
        template += "\n\n---\n\n## Custom Project Sections\n\n"
        for section_name, section_content in customizations["custom_sections"].items():
            template += f"### {section_name}\n\n{section_content}\n\n"

    # Write updated file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(template)

def main():
    if len(sys.argv) < 3:
        print("Usage:", file=sys.stderr)
        print("  Extract: python3 claude_updater.py extract CLAUDE.md > customizations.json", file=sys.stderr)
        print("  Generate: python3 claude_updater.py generate --customizations file.json --template template.md --output CLAUDE.md", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "extract":
        claude_md_path = sys.argv[2]

        if not Path(claude_md_path).exists():
            print(f"Error: File not found: {claude_md_path}", file=sys.stderr)
            sys.exit(1)

        try:
            customizations = extract_customizations(claude_md_path)
            print(json.dumps(customizations, indent=2))
        except Exception as e:
            print(f"Error extracting customizations: {e}", file=sys.stderr)
            sys.exit(2)

    elif command == "generate":
        # Parse arguments
        args = {
            'customizations': None,
            'template': None,
            'output': None
        }

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == '--customizations' and i + 1 < len(sys.argv):
                args['customizations'] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--template' and i + 1 < len(sys.argv):
                args['template'] = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == '--output' and i + 1 < len(sys.argv):
                args['output'] = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        if not all(args.values()):
            print("Error: Missing required arguments", file=sys.stderr)
            print("Required: --customizations, --template, --output", file=sys.stderr)
            sys.exit(1)

        try:
            with open(args['customizations'], 'r') as f:
                customizations = json.load(f)

            # Use get_template_path for GitHub fetch with bundled fallback
            # If --template is a directory, treat it as bundled_template_dir
            # Otherwise, use it directly as a file path
            template_arg = args['template']

            if Path(template_arg).is_dir():
                # Directory provided - use get_template_path for smart fetching
                template_path, is_github = get_template_path(template_arg)
            elif Path(template_arg).is_file():
                # File provided directly - use as-is (backward compatibility)
                template_path = template_arg
                is_github = False
            else:
                # Try parent directory for get_template_path
                template_dir = str(Path(template_arg).parent)
                template_path, is_github = get_template_path(template_dir)

            generate_updated_claude_md(customizations, template_path, args['output'])
            print(f"✓ Generated {args['output']}", file=sys.stderr)

            # Cleanup temp file if from GitHub
            if is_github and Path(template_path).exists():
                Path(template_path).unlink()

        except Exception as e:
            print(f"Error generating CLAUDE.md: {e}", file=sys.stderr)
            sys.exit(2)

    else:
        print(f"Error: Unknown command: {command}", file=sys.stderr)
        print("Valid commands: extract, generate", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
