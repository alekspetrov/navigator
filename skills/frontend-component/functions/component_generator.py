#!/usr/bin/env python3
"""
Generate React component file from template with substitutions.

Replaces placeholders in template with component-specific values.
"""

import sys
import argparse
import os

def read_template(template_path: str) -> str:
    """Read template file content."""
    try:
        with open(template_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Template file not found: {template_path}")

def generate_component(name: str, props_interface: str, template_content: str, description: str = None) -> str:
    """
    Generate component code by substituting placeholders in template.

    Args:
        name: Component name (PascalCase)
        props_interface: Props interface name
        template_content: Template file content
        description: Brief component description

    Returns:
        str: Generated component code
    """
    # Convert PascalCase to kebab-case for file names
    kebab_name = ''.join(['-' + c.lower() if c.isupper() else c for c in name]).lstrip('-')

    props_interface_block = (
        f"interface {props_interface} {{\n"
        f"  children?: React.ReactNode;\n"
        f"  className?: string;\n"
        f"}}"
    )

    substitutions = {
        '${COMPONENT_NAME}': name,
        '${PROPS_INTERFACE_BLOCK}': props_interface_block,
        '${PROPS_INTERFACE}': props_interface,
        '${STYLE_IMPORT}': f"import styles from './{name}.module.css';",
        '${DESCRIPTION}': description or f"{name} component",
        '${COMPONENT_NAME_KEBAB}': kebab_name,
    }

    result = template_content
    for placeholder, value in substitutions.items():
        result = result.replace(placeholder, value)

    return result

def main():
    parser = argparse.ArgumentParser(description='Generate React component from template')
    parser.add_argument('--name', required=True, help='Component name (PascalCase)')
    parser.add_argument(
        '--type',
        default='simple',
        choices=[
            'simple', 'with-hooks', 'container',
            'nextjs-page', 'nextjs-layout', 'nextjs-client', 'nextjs-server',
        ],
        help='Component type (nextjs-* variants for App Router projects)',
    )
    parser.add_argument('--props-interface', required=True, help='Props interface name')
    parser.add_argument('--template', required=True, help='Template file path')
    parser.add_argument('--output', help='Output file path (optional, prints to stdout if not provided)')
    parser.add_argument('--description', help='Component description')

    args = parser.parse_args()

    try:
        # Read template
        template_content = read_template(args.template)

        # Generate component
        component_code = generate_component(
            args.name,
            args.props_interface,
            template_content,
            args.description
        )

        # Output
        if args.output:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(component_code)
            print(f"✅ Component generated: {args.output}")
        else:
            print(component_code)

        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
