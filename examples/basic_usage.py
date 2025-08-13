#!/usr/bin/env python3
"""
Basic usage example for libvirt-mcp-server.

This example demonstrates how to connect to the libvirt MCP server
and perform basic virtual machine management operations.
"""

import asyncio
import sys
from typing import Dict, List

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    """Main example function."""
    print("🚀 Libvirt MCP Server - Basic Usage Example")
    print("=" * 50)
    
    # Configure the MCP server connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        # You can also specify environment variables if needed
        env={"LIBVIRT_URI": "qemu:///system"}  # Use test driver for demo
    )
    
    try:
        # Connect to the MCP server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to libvirt MCP server")
                
                # List available tools
                print("\n📋 Available tools:")
                tools = await session.list_tools()
                for tool in tools.tools:
                    print(f"  - {tool.name}: {tool.description}")
                
                # Example 1: List all domains
                print("\n🖥️  Example 1: Listing all domains")
                result = await session.call_tool("list_domains", {"state": "all"})
                domains = result.content[0].text if result.content else "No content"
                print(f"Domains found: {domains}")
                
                # Example 2: Get host information
                print("\n🏠 Example 2: Getting host information")
                result = await session.call_tool("host_info", {})
                host_info = result.content[0].text if result.content else "No content"
                print(f"Host info: {host_info}")
                
                # Example 3: List networks
                print("\n🌐 Example 3: Listing virtual networks")
                result = await session.call_tool("list_networks", {})
                networks = result.content[0].text if result.content else "No content"
                print(f"Networks: {networks}")
                
                # Example 4: List storage pools
                print("\n💾 Example 4: Listing storage pools")
                result = await session.call_tool("list_storage_pools", {})
                storage = result.content[0].text if result.content else "No content"
                print(f"Storage pools: {storage}")
                
                # Example 5: Try to get info for a specific domain (might not exist)
                print("\n🔍 Example 5: Getting domain info (may fail if domain doesn't exist)")
                try:
                    result = await session.call_tool("domain_info", {"name": "test-vm"})
                    domain_info = result.content[0].text if result.content else "No content"
                    print(f"Domain info: {domain_info}")
                except Exception as e:
                    print(f"Expected error (domain may not exist): {e}")
                
                print("\n✅ All examples completed successfully!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
