#!/usr/bin/env python3
"""
Generate backend API endpoint from template with substitutions.

Creates route handlers with authentication, validation, and error handling.
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

def generate_endpoint(
    path: str,
    method: str,
    resource: str,
    framework: str,
    template_content: str,
    auth: bool = False,
    validation: bool = False
) -> str:
    """
    Generate endpoint code by substituting placeholders in template.

    Args:
        path: API endpoint path
        method: HTTP method (GET, POST, etc.)
        resource: Resource name (PascalCase)
        framework: Backend framework (express, fastify, etc.)
        template_content: Template file content
        auth: Include authentication middleware
        validation: Include validation middleware

    Returns:
        str: Generated endpoint code
    """
    # Convert method to lowercase for handler name
    method_lower = method.lower()

    # Generate middleware chain
    middlewares = []
    if auth:
        middlewares.append('authMiddleware')
    if validation:
        validator_name = f'validate{resource}'
        middlewares.append(validator_name)

    middleware_chain = ', '.join(middlewares) if middlewares else ''
    middleware_block = f"  {middleware_chain},\n" if middlewares else ''

    resource_lower = resource.lower()
    resource_plural = resource.lower() + 's'

    substitutions = {
        '${ROUTE_PATH}': path,
        '${HTTP_METHOD}': method.upper(),
        '${HTTP_METHOD_LOWER}': method_lower,
        '${RESOURCE_NAME}': resource,
        '${RESOURCE_NAME_LOWER}': resource_lower,
        '${RESOURCE_NAME_PLURAL}': resource_plural,
        '${VALIDATION_MIDDLEWARE}': f'validate{resource}' if validation else '',
        '${AUTH_MIDDLEWARE}': 'authMiddleware' if auth else '',
        '${MIDDLEWARE_CHAIN}': middleware_chain,
        '${MIDDLEWARE_BLOCK}': middleware_block,
    }

    result = template_content
    for placeholder, value in substitutions.items():
        result = result.replace(placeholder, value)

    return result

def main():
    parser = argparse.ArgumentParser(description='Generate backend API endpoint from template')
    parser.add_argument('--path', required=True, help='API endpoint path')
    parser.add_argument('--method', required=True, choices=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'], help='HTTP method')
    parser.add_argument('--resource', required=True, help='Resource name (PascalCase)')
    parser.add_argument('--framework', default='express', choices=['express', 'fastify', 'nestjs'], help='Backend framework')
    parser.add_argument('--auth', action='store_true', help='Include authentication middleware')
    parser.add_argument('--validation', action='store_true', help='Include validation middleware')
    parser.add_argument('--template', required=True, help='Template file path')
    parser.add_argument('--output', help='Output file path (optional, prints to stdout if not provided)')

    args = parser.parse_args()

    try:
        # Read template
        template_content = read_template(args.template)

        # Generate endpoint
        endpoint_code = generate_endpoint(
            args.path,
            args.method,
            args.resource,
            args.framework,
            template_content,
            args.auth,
            args.validation
        )

        # Output
        if args.output:
            os.makedirs(os.path.dirname(args.output), exist_ok=True)
            with open(args.output, 'w') as f:
                f.write(endpoint_code)
            print(f"✅ Endpoint generated: {args.output}")
        else:
            print(endpoint_code)

        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
