#!/usr/bin/env python3
"""
Test script for VM creation with CDROM.
"""
import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from libvirt_mcp_server.config import Config
from libvirt_mcp_server.libvirt_client import LibvirtClient
from libvirt_mcp_server.models import DomainCreateParams


async def test_vm_creation():
    """Test creating a VM with CDROM."""
    
    # Load configuration
    config = Config()
    
    # Add domain.create to allowed operations for testing
    config.security.allowed_operations.extend([
        "domain.create",
        "domain.delete",
        "device.attach",
        "device.detach"
    ])
    
    # Initialize libvirt client
    client = LibvirtClient(config)
    
    try:
        await client.connect()
        print("✅ Connected to libvirt")
        
        # Define VM parameters
        params = DomainCreateParams(
            name="wangqing-live",
            memory=2097152,  # 2GB in KB
            vcpus=2,
            disk_size=20,  # 20GB
            disk_path="/home/wangqing/script_vm/images/wangqing-live.qcow2",
            cdrom_path="/home/wangqing/script_vm/iso/Fedora-Workstation-Live-x86_64-40-1.14.iso",
            network="default",
            boot_device="hd"
        )
        
        print("📋 VM Parameters:")
        print(f"  Name: {params.name}")
        print(f"  Memory: {params.memory // 1024} MB")
        print(f"  vCPUs: {params.vcpus}")
        print(f"  Disk Size: {params.disk_size} GB")
        print(f"  Disk Path: {params.disk_path}")
        print(f"  CDROM Path: {params.cdrom_path}")
        
        # Validate file paths first
        await client._validate_file_paths(params)
        print("✅ File paths validated")
        
        # Generate XML
        domain_xml = client.generate_domain_xml(params)
        print("✅ Domain XML generated")
        
        # Create the domain
        success = await client.create_domain(domain_xml, ephemeral=False, disk_size=params.disk_size)
        
        if success:
            print("🎉 VM created successfully!")
            
            # List domains to verify
            domains = await client.list_domains(include_inactive=True)
            for domain in domains:
                if domain.name == params.name:
                    print(f"✅ Found created domain: {domain.name} (state: {domain.state})")
                    break
        else:
            print("❌ VM creation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await client.disconnect()
        print("✅ Disconnected from libvirt")


if __name__ == "__main__":
    asyncio.run(test_vm_creation())