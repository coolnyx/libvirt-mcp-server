"""
Data models for libvirt-mcp-server.

This module defines Pydantic models for representing libvirt resources
and MCP tool inputs/outputs with proper validation and serialization.
"""

from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field


class DomainState(str, Enum):
    """Virtual machine domain states."""
    
    NOSTATE = "nostate"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    SHUTDOWN = "shutdown"
    SHUTOFF = "shutoff"
    CRASHED = "crashed"
    PMSUSPENDED = "pmsuspended"


class NetworkState(str, Enum):
    """Virtual network states."""
    
    INACTIVE = "inactive"
    ACTIVE = "active"


class StoragePoolState(str, Enum):
    """Storage pool states."""
    
    INACTIVE = "inactive"
    BUILDING = "building"
    RUNNING = "running"
    DEGRADED = "degraded"
    INACCESSIBLE = "inaccessible"


class DomainInfo(BaseModel):
    """Virtual machine domain information."""
    
    name: str = Field(description="Domain name")
    uuid: str = Field(description="Domain UUID")
    id: Optional[int] = Field(description="Domain ID (None if inactive)")
    state: DomainState = Field(description="Current domain state")
    max_memory: int = Field(description="Maximum memory in KB")
    memory: int = Field(description="Current memory in KB")
    vcpus: int = Field(description="Number of virtual CPUs")
    cpu_time: Optional[int] = Field(description="CPU time used in nanoseconds")
    autostart: bool = Field(description="Whether domain starts automatically")
    persistent: bool = Field(description="Whether domain is persistent")


class DomainStats(BaseModel):
    """Virtual machine performance statistics."""
    
    name: str = Field(description="Domain name")
    state: DomainState = Field(description="Current domain state")
    cpu_time: Optional[int] = Field(description="Total CPU time in nanoseconds")
    cpu_user_time: Optional[int] = Field(description="User CPU time in nanoseconds")
    cpu_system_time: Optional[int] = Field(description="System CPU time in nanoseconds")
    memory_actual: Optional[int] = Field(description="Actual memory in KB")
    memory_unused: Optional[int] = Field(description="Unused memory in KB")
    memory_available: Optional[int] = Field(description="Available memory in KB")
    memory_usable: Optional[int] = Field(description="Usable memory in KB")
    block_rd_bytes: Optional[int] = Field(description="Block device read bytes")
    block_wr_bytes: Optional[int] = Field(description="Block device write bytes")
    block_rd_reqs: Optional[int] = Field(description="Block device read requests")
    block_wr_reqs: Optional[int] = Field(description="Block device write requests")
    net_rx_bytes: Optional[int] = Field(description="Network received bytes")
    net_tx_bytes: Optional[int] = Field(description="Network transmitted bytes")
    net_rx_pkts: Optional[int] = Field(description="Network received packets")
    net_tx_pkts: Optional[int] = Field(description="Network transmitted packets")


class HostInfo(BaseModel):
    """Host system information."""
    
    hostname: str = Field(description="Host hostname")
    uri: str = Field(description="Libvirt connection URI")
    hypervisor_type: str = Field(description="Hypervisor type")
    hypervisor_version: int = Field(description="Hypervisor version")
    libvirt_version: int = Field(description="Libvirt version")
    cpu_model: str = Field(description="CPU model")
    cpu_arch: str = Field(description="CPU architecture")
    cpu_cores: int = Field(description="Number of CPU cores")
    cpu_threads: int = Field(description="Number of CPU threads")
    cpu_sockets: int = Field(description="Number of CPU sockets")
    cpu_mhz: int = Field(description="CPU frequency in MHz")
    memory_size: int = Field(description="Total memory in KB")
    memory_free: Optional[int] = Field(description="Free memory in KB")
    numa_nodes: int = Field(description="Number of NUMA nodes")


class NetworkInfo(BaseModel):
    """Virtual network information."""
    
    name: str = Field(description="Network name")
    uuid: str = Field(description="Network UUID")
    state: NetworkState = Field(description="Network state")
    bridge_name: Optional[str] = Field(description="Bridge device name")
    autostart: bool = Field(description="Whether network starts automatically")
    persistent: bool = Field(description="Whether network is persistent")


class StoragePoolInfo(BaseModel):
    """Storage pool information."""
    
    name: str = Field(description="Storage pool name")
    uuid: str = Field(description="Storage pool UUID")
    state: StoragePoolState = Field(description="Storage pool state")
    capacity: int = Field(description="Total capacity in bytes")
    allocation: int = Field(description="Allocated space in bytes")
    available: int = Field(description="Available space in bytes")
    autostart: bool = Field(description="Whether pool starts automatically")
    persistent: bool = Field(description="Whether pool is persistent")


class DomainCreateParams(BaseModel):
    """Parameters for creating a new domain."""
    
    name: str = Field(description="Domain name")
    memory: int = Field(description="Memory size in KB", ge=1024)
    vcpus: int = Field(description="Number of virtual CPUs", ge=1, le=128)
    disk_size: Optional[int] = Field(description="Disk size in GB", ge=1, default=None)
    disk_path: Optional[str] = Field(description="Path to disk image", default=None)
    cdrom_path: Optional[str] = Field(description="Path to CDROM/ISO image", default=None)
    network: Optional[str] = Field(description="Network name", default="default")
    os_type: str = Field(description="OS type", default="hvm")
    arch: str = Field(description="Architecture", default="x86_64")
    boot_device: str = Field(description="Boot device", default="hd")
    xml: Optional[str] = Field(description="Custom XML configuration", default=None)


class OperationResult(BaseModel):
    """Result of an operation."""
    
    success: bool = Field(description="Whether operation succeeded")
    message: str = Field(description="Result message")
    details: Optional[Dict] = Field(description="Additional details")


class DomainListParams(BaseModel):
    """Parameters for listing domains."""
    
    state: str = Field(
        description="Domain state filter",
        default="all",
        pattern="^(all|running|stopped|active|inactive)$"
    )
    include_inactive: bool = Field(description="Include inactive domains", default=True)


class DomainActionParams(BaseModel):
    """Parameters for domain actions (start, stop, reboot)."""
    
    name: str = Field(description="Domain name")
    force: bool = Field(description="Force the action", default=False)


class DomainStatsParams(BaseModel):
    """Parameters for getting domain statistics."""
    
    name: str = Field(description="Domain name")
    flags: List[str] = Field(
        description="Statistics flags",
        default_factory=lambda: ["state", "cpu-total", "balloon", "vcpu", "interface", "block"]
    )


class DeviceAttachParams(BaseModel):
    """Parameters for attaching devices to domains."""
    
    domain_name: str = Field(description="Domain name")
    device_xml: str = Field(description="Device XML configuration")
    flags: List[str] = Field(description="Attach flags", default_factory=list)


class DomainConfigUpdateParams(BaseModel):
    """Parameters for updating domain configuration."""
    
    domain_name: str = Field(description="Domain name")
    xml: str = Field(description="New XML configuration")
    flags: List[str] = Field(description="Update flags", default_factory=list)


class DomainDeleteParams(BaseModel):
    """Parameters for deleting a domain."""
    
    name: str = Field(description="Domain name")
    remove_storage: bool = Field(description="Remove associated storage", default=False)
    force: bool = Field(description="Force delete even if running", default=False)


class DeviceOperationParams(BaseModel):
    """Parameters for device attach/detach operations."""
    
    domain_name: str = Field(description="Domain name")
    device_xml: str = Field(description="Device XML configuration")
    live: bool = Field(description="Apply to live domain", default=True)
    persistent: bool = Field(description="Apply to persistent configuration", default=True)
