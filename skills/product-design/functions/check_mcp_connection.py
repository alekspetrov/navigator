#!/usr/bin/env python3
"""
Test Figma MCP connection - Quick validation script.

Tests connection to Figma Desktop MCP server and lists available tools.
"""
import asyncio
import sys

try:
    from figma_mcp_client import FigmaMCPClient, FigmaNotRunningError
except ImportError:
    print("❌ Error: figma_mcp_client not found")
    print("   Ensure you're in the correct directory: skills/product-design/functions/")
    sys.exit(1)


async def test_connection():
    """Test Figma MCP connection."""
    try:
        async with FigmaMCPClient() as client:
            # List available tools
            tools = await client.list_available_tools()

            print("✅ Successfully connected to Figma MCP server")
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool}")

            return True

    except FigmaNotRunningError as e:
        print("❌ Figma Desktop not running or MCP not enabled")
        print(f"   {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    success = await test_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
