#!/usr/bin/env python3
"""
Debug script to check generated XML.
"""
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from libvirt_mcp_server.libvirt_client import LibvirtClient
from libvirt_mcp_server.config import Config
from libvirt_mcp_server.models import DomainCreateParams

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

# Load configuration
config = Config()
client = LibvirtClient(config)

# Generate XML
domain_xml = client.generate_domain_xml(params)
print("Generated XML:")
print(domain_xml)