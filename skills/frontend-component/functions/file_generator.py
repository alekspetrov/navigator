#!/usr/bin/env python3
"""
Generate test file with React Testing Library.

Creates comprehensive test suite for React components.
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

def generate_test(component_name: str, component_path: str, template_content: str) -> str:
    """
    Generate test code by substituting placeholders in template.

    Args:
        component_name: Component name (PascalCase)
        component_path: Path to component file
        template_content: Template file content

    Returns:
        str: Generated test code
    """
    # Calculate relative import path
    import_path = f'./{component_name}'

    # Basic test cases (can be expanded based on props analysis)
    test_cases = f"""
  it('renders without crashing', () => {{
    render(<{component_name} />);
  }});

  it('renders children correctly', () => {{
    render(<{component_name}>Test Content</{component_name}>);
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  }});

  it('applies custom className', () => {{
    const {{ container }} = render(<{component_name} className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  }});
""".strip()

    # Perform substitutions
    substitutions = {
        '${COMPONENT_NAME}': component_name,
        '${IMPORT_PATH}': import_path,
        '${TEST_CASES}': test_cases,
    }

    result = template_content
    for placeholder, value in substitutions.items():
        result = result.replace(placeholder, value)

    return result

def main():
    parser = argparse.ArgumentParser(description='Generate React component test file')
    parser.add_argument('--component-name', required=True, help='Component name (PascalCase)')
    parser.add_argument('--component-path', required=True, help='Path to component file')
    parser.add_argument('--template', required=True, help='Test template file path')
    parser.add_argument('--output', help='Output file path (optional, prints to stdout if not provided)')

    args = parser.parse_args()

    try:
        # Read template
        template_content = read_template(args.template)

        # Generate test
        test_code = generate_test(
            args.component_name,
            args.component_path,
            template_content
        )

        # Output
        if args.output:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(test_code)
            print(f"✅ Test file generated: {args.output}")
        else:
            print(test_code)

        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
