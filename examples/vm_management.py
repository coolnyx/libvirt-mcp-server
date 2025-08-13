#!/usr/bin/env python3
"""
Virtual machine management example for libvirt-mcp-server.

This example demonstrates more advanced VM management operations
including starting, stopping, and monitoring virtual machines.
"""

import asyncio
import json
import sys
from typing import Dict, List

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


class VMManager:
    """Virtual machine management helper class."""
    
    def __init__(self, session: ClientSession):
        self.session = session
    
    async def list_all_domains(self) -> List[Dict]:
        """List all domains and return as structured data."""
        result = await self.session.call_tool("list_domains", {"state": "all"})
        if result.content:
            return json.loads(result.content[0].text)
        return []
    
    async def get_domain_info(self, name: str) -> Dict:
        """Get detailed information about a domain."""
        result = await self.session.call_tool("domain_info", {"name": name})
        if result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def start_domain(self, name: str, force: bool = False) -> Dict:
        """Start a domain."""
        result = await self.session.call_tool("start_domain", {"name": name, "force": force})
        if result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def stop_domain(self, name: str, force: bool = False) -> Dict:
        """Stop a domain."""
        result = await self.session.call_tool("stop_domain", {"name": name, "force": force})
        if result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def reboot_domain(self, name: str, force: bool = False) -> Dict:
        """Reboot a domain."""
        result = await self.session.call_tool("reboot_domain", {"name": name, "force": force})
        if result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def get_domain_stats(self, name: str) -> Dict:
        """Get domain performance statistics."""
        result = await self.session.call_tool("domain_stats", {"name": name})
        if result.content:
            return json.loads(result.content[0].text)
        return {}
    
    async def get_domain_xml(self, name: str) -> str:
        """Get domain XML configuration."""
        result = await self.session.call_tool("get_domain_xml", {"name": name})
        if result.content:
            return result.content[0].text
        return ""


async def demonstrate_vm_management():
    """Demonstrate VM management capabilities."""
    print("🖥️  Virtual Machine Management Example")
    print("=" * 50)
    
    # Configure the MCP server connection
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        env={"LIBVIRT_URI": "qemu:///system"}  # Use test driver
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("✅ Connected to libvirt MCP server")
                
                vm_manager = VMManager(session)
                
                # Step 1: List all domains
                print("\n📋 Step 1: Listing all domains")
                domains = await vm_manager.list_all_domains()
                
                if not domains:
                    print("No domains found. This is expected with test:/// driver.")
                    print("In a real environment, you would see actual VMs here.")
                    return
                
                print(f"Found {len(domains)} domains:")
                for domain in domains:
                    print(f"  - {domain['name']} ({domain['state']})")
                
                # Step 2: Work with the first domain if available
                if domains:
                    domain_name = domains[0]['name']
                    print(f"\n🔍 Step 2: Working with domain '{domain_name}'")
                    
                    # Get detailed info
                    info = await vm_manager.get_domain_info(domain_name)
                    print(f"Domain info:")
                    print(f"  UUID: {info.get('uuid', 'N/A')}")
                    print(f"  State: {info.get('state', 'N/A')}")
                    print(f"  Memory: {info.get('memory', 0)} KB")
                    print(f"  VCPUs: {info.get('vcpus', 0)}")
                    print(f"  Autostart: {info.get('autostart', False)}")
                    
                    # Get performance stats
                    print(f"\n📊 Step 3: Getting performance statistics")
                    stats = await vm_manager.get_domain_stats(domain_name)
                    print(f"Performance stats:")
                    print(f"  CPU time: {stats.get('cpu_time', 'N/A')}")
                    print(f"  Memory actual: {stats.get('memory_actual', 'N/A')} KB")
                    print(f"  Block read bytes: {stats.get('block_rd_bytes', 'N/A')}")
                    print(f"  Network RX bytes: {stats.get('net_rx_bytes', 'N/A')}")
                    
                    # Demonstrate state management
                    current_state = info.get('state', '').lower()
                    print(f"\n⚡ Step 4: Demonstrating state management")
                    print(f"Current state: {current_state}")
                    
                    if current_state == 'shutoff':
                        print("Attempting to start domain...")
                        result = await vm_manager.start_domain(domain_name)
                        print(f"Start result: {result.get('message', 'Unknown')}")
                    elif current_state == 'running':
                        print("Domain is running. Attempting graceful shutdown...")
                        result = await vm_manager.stop_domain(domain_name)
                        print(f"Stop result: {result.get('message', 'Unknown')}")
                    
                    # Get XML configuration
                    print(f"\n📄 Step 5: Getting XML configuration")
                    xml_config = await vm_manager.get_domain_xml(domain_name)
                    if xml_config:
                        # Just show first few lines to avoid overwhelming output
                        lines = xml_config.split('\n')[:10]
                        print("XML configuration (first 10 lines):")
                        for line in lines:
                            print(f"  {line}")
                        if len(xml_config.split('\n')) > 10:
                            print("  ... (truncated)")
                    else:
                        print("No XML configuration available")
                
                print("\n✅ VM management demonstration completed!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def demonstrate_monitoring():
    """Demonstrate monitoring capabilities."""
    print("\n📊 Monitoring Example")
    print("=" * 30)
    
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        env={"LIBVIRT_URI": "qemu:///system"}
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                vm_manager = VMManager(session)
                
                # Get host information
                print("🏠 Host System Information:")
                result = await session.call_tool("host_info", {})
                if result.content:
                    host_info = json.loads(result.content[0].text)
                    print(f"  Hostname: {host_info.get('hostname', 'N/A')}")
                    print(f"  Hypervisor: {host_info.get('hypervisor_type', 'N/A')}")
                    print(f"  CPU Cores: {host_info.get('cpu_cores', 'N/A')}")
                    print(f"  Memory: {host_info.get('memory_size', 0) // 1024} MB")
                
                # List networks
                print("\n🌐 Virtual Networks:")
                result = await session.call_tool("list_networks", {})
                if result.content:
                    networks = json.loads(result.content[0].text)
                    for network in networks:
                        print(f"  - {network['name']} ({network['state']})")
                        if network.get('bridge_name'):
                            print(f"    Bridge: {network['bridge_name']}")
                
                # List storage pools
                print("\n💾 Storage Pools:")
                result = await session.call_tool("list_storage_pools", {})
                if result.content:
                    pools = json.loads(result.content[0].text)
                    for pool in pools:
                        capacity_gb = pool.get('capacity', 0) / (1024**3)
                        available_gb = pool.get('available', 0) / (1024**3)
                        print(f"  - {pool['name']} ({pool['state']})")
                        print(f"    Capacity: {capacity_gb:.1f} GB")
                        print(f"    Available: {available_gb:.1f} GB")
                
                print("\n✅ Monitoring demonstration completed!")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def main():
    """Main function."""
    await demonstrate_vm_management()
    await demonstrate_monitoring()


if __name__ == "__main__":
    asyncio.run(main())
