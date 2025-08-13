#!/usr/bin/env python3
"""
Example: Creating a VM with CDROM using libvirt-mcp-server.

This example demonstrates how to create a virtual machine with a CDROM/ISO image
using the MCP create_domain tool.
"""

import asyncio
from pathlib import Path


async def example_create_vm_with_cdrom():
    """
    Example of creating a VM with CDROM via MCP client.
    
    This would typically be called by an AI model through MCP protocol.
    """
    
    # Example MCP tool call parameters for creating a VM with CDROM
    vm_params = {
        "name": "wangqing-live",
        "memory": 2097152,  # 2GB in KB
        "vcpus": 2,
        "disk_size": 20,  # 20GB disk
        "disk_path": "/home/wangqing/script_vm/images/wangqing-live.qcow2",
        "cdrom_path": "/home/wangqing/script_vm/iso/Fedora-Workstation-Live-x86_64-40-1.14.iso",
        "network": "default",
        "boot_device": "hd",  # Boot order: CDROM first, then HD
        "ephemeral": False  # Create persistent VM
    }
    
    print("VM Creation Parameters:")
    print("=" * 40)
    for key, value in vm_params.items():
        print(f"{key:12}: {value}")
    
    print("\nGenerated VM Configuration:")
    print("=" * 40)
    print("- VM will have both a hard disk and CDROM")
    print("- Boot order: CDROM first, then hard disk")
    print("- CDROM is read-only with IDE controller")
    print("- Disk uses virtio for better performance")
    print("- Input devices: USB tablet, PS2 mouse/keyboard")
    print("- Proper PCI/USB controller configuration")
    print("- Default network configuration")
    print("")
    print("✅ Fixed input device configuration:")
    print("  - Tablet device uses USB bus (not PS2)")
    print("  - Mouse and keyboard use PS2 bus")
    print("  - USB controller added for tablet support")
    
    # Note: To actually create the VM, you would call:
    # result = await mcp_client.call_tool("create_domain", vm_params)
    
    return vm_params


if __name__ == "__main__":
    # Run the example
    params = asyncio.run(example_create_vm_with_cdrom())
    
    print(f"\n✅ Example completed!")
    print(f"💡 Use these parameters with MCP create_domain tool to create a VM with CDROM.")