"""
Libvirt client wrapper for secure and controlled access to libvirt functionality.

This module provides a safe abstraction layer over the libvirt Python bindings
with proper error handling, connection management, and security controls.
"""

import asyncio
import contextlib
from typing import Dict, List, Optional, Union
import xml.etree.ElementTree as ET

import libvirt
from libvirt import libvirtError

from .config import Config
from .exceptions import (
    LibvirtConnectionError,
    LibvirtOperationError,
    LibvirtPermissionError,
    LibvirtResourceNotFoundError,
)
from .logging import get_logger, log_async_performance, LogContext
from .models import (
    DomainInfo,
    DomainState,
    DomainStats,
    HostInfo,
    NetworkInfo,
    NetworkState,
    StoragePoolInfo,
    StoragePoolState,
)


logger = get_logger(__name__)


class LibvirtClient:
    """
    Secure libvirt client with controlled access and proper error handling.
    
    This client provides safe access to libvirt functionality with:
    - Connection pooling and management
    - Operation validation and security checks
    - Comprehensive error handling
    - Audit logging
    """

    def __init__(self, config: Config):
        """Initialize libvirt client with configuration."""
        self.config = config
        self._connection: Optional[libvirt.virConnect] = None
        self._lock = asyncio.Lock()
        
        # Set up libvirt error handler to prevent default stderr output
        libvirt.registerErrorHandler(self._libvirt_error_handler, None)
    
    def _libvirt_error_handler(self, ctx, err):
        """Custom libvirt error handler."""
        # Log the error but don't print to stderr
        logger.debug(f"Libvirt error: {err}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
    
    async def connect(self) -> None:
        """Establish connection to libvirt."""
        async with self._lock:
            if self._connection is not None:
                return
            
            try:
                if self.config.libvirt.readonly:
                    self._connection = libvirt.openReadOnly(self.config.libvirt.uri)
                else:
                    self._connection = libvirt.open(self.config.libvirt.uri)
                
                logger.info(f"Connected to libvirt: {self.config.libvirt.uri}")
                
            except libvirtError as e:
                logger.error(f"Failed to connect to libvirt: {e}")
                raise LibvirtConnectionError(f"Failed to connect to libvirt: {e}")
    
    async def disconnect(self) -> None:
        """Close connection to libvirt."""
        async with self._lock:
            if self._connection is not None:
                try:
                    self._connection.close()
                    logger.info("Disconnected from libvirt")
                except libvirtError as e:
                    logger.warning(f"Error closing libvirt connection: {e}")
                finally:
                    self._connection = None
    
    def _ensure_connected(self) -> libvirt.virConnect:
        """Ensure we have an active connection."""
        if self._connection is None:
            raise LibvirtConnectionError("Not connected to libvirt")
        
        try:
            # Test connection by checking if it's alive
            self._connection.getVersion()
            return self._connection
        except libvirtError:
            # Connection is dead, need to reconnect
            self._connection = None
            raise LibvirtConnectionError("Libvirt connection lost")
    
    def _check_operation_allowed(self, operation: str) -> None:
        """Check if operation is allowed by security configuration."""
        if operation not in self.config.security.allowed_operations:
            raise LibvirtPermissionError(f"Operation not allowed: {operation}")
    
    def _domain_state_to_enum(self, state: int) -> DomainState:
        """Convert libvirt domain state to our enum."""
        state_map = {
            libvirt.VIR_DOMAIN_NOSTATE: DomainState.NOSTATE,
            libvirt.VIR_DOMAIN_RUNNING: DomainState.RUNNING,
            libvirt.VIR_DOMAIN_BLOCKED: DomainState.BLOCKED,
            libvirt.VIR_DOMAIN_PAUSED: DomainState.PAUSED,
            libvirt.VIR_DOMAIN_SHUTDOWN: DomainState.SHUTDOWN,
            libvirt.VIR_DOMAIN_SHUTOFF: DomainState.SHUTOFF,
            libvirt.VIR_DOMAIN_CRASHED: DomainState.CRASHED,
            libvirt.VIR_DOMAIN_PMSUSPENDED: DomainState.PMSUSPENDED,
        }
        return state_map.get(state, DomainState.NOSTATE)
    
    async def list_domains(self, include_inactive: bool = True) -> List[DomainInfo]:
        """List all domains."""
        self._check_operation_allowed("domain.list")
        conn = self._ensure_connected()
        
        try:
            domains = []
            
            # Get active domains
            for domain_id in conn.listDomainsID():
                try:
                    domain = conn.lookupByID(domain_id)
                    domains.append(self._get_domain_info(domain))
                except libvirtError as e:
                    logger.warning(f"Failed to get domain info for ID {domain_id}: {e}")
            
            # Get inactive domains if requested
            if include_inactive:
                for domain_name in conn.listDefinedDomains():
                    try:
                        domain = conn.lookupByName(domain_name)
                        domains.append(self._get_domain_info(domain))
                    except libvirtError as e:
                        logger.warning(f"Failed to get domain info for {domain_name}: {e}")
            
            logger.info(f"Listed {len(domains)} domains")
            return domains
            
        except libvirtError as e:
            logger.error(f"Failed to list domains: {e}")
            raise LibvirtOperationError(f"Failed to list domains: {e}")
    
    def _get_domain_info(self, domain) -> DomainInfo:
        """Get domain information from libvirt domain object."""
        try:
            state, max_mem, memory, vcpus, cpu_time = domain.info()
            
            return DomainInfo(
                name=domain.name(),
                uuid=domain.UUIDString(),
                id=domain.ID() if state == libvirt.VIR_DOMAIN_RUNNING else None,
                state=self._domain_state_to_enum(state),
                max_memory=max_mem,
                memory=memory,
                vcpus=vcpus,
                cpu_time=cpu_time,
                autostart=bool(domain.autostart()),
                persistent=bool(domain.isPersistent()),
            )
        except libvirtError as e:
            raise LibvirtOperationError(f"Failed to get domain info: {e}")
    
    async def get_domain_info(self, domain_name: str) -> DomainInfo:
        """Get information about a specific domain."""
        self._check_operation_allowed("domain.info")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            result = self._get_domain_info(domain)
            logger.info(f"Retrieved info for domain: {domain_name}")
            return result
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to get domain info for {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to get domain info: {e}")
    
    async def start_domain(self, domain_name: str, force: bool = False) -> bool:
        """Start a domain."""
        self._check_operation_allowed("domain.start")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            # Check if already running
            state, _ = domain.state()
            if state == libvirt.VIR_DOMAIN_RUNNING:
                logger.info(f"Domain {domain_name} is already running")
                return True
            
            flags = 0
            if force:
                flags |= libvirt.VIR_DOMAIN_START_FORCE_BOOT
            
            domain.createWithFlags(flags)
            logger.info(f"Started domain: {domain_name}")
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to start domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to start domain: {e}")
    
    async def stop_domain(self, domain_name: str, force: bool = False) -> bool:
        """Stop a domain."""
        self._check_operation_allowed("domain.stop")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            # Check if already stopped
            state, _ = domain.state()
            if state == libvirt.VIR_DOMAIN_SHUTOFF:
                logger.info(f"Domain {domain_name} is already stopped")
                return True
            
            if force:
                domain.destroy()
                logger.info(f"Forcefully stopped domain: {domain_name}")
            else:
                domain.shutdown()
                logger.info(f"Gracefully stopping domain: {domain_name}")
            
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to stop domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to stop domain: {e}")
    
    async def reboot_domain(self, domain_name: str, force: bool = False) -> bool:
        """Reboot a domain."""
        self._check_operation_allowed("domain.reboot")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            flags = 0
            if force:
                flags |= libvirt.VIR_DOMAIN_REBOOT_ACPI_POWER_BTN
            
            domain.reboot(flags)
            logger.info(f"Rebooted domain: {domain_name}")
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to reboot domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to reboot domain: {e}")
    
    async def get_domain_stats(self, domain_name: str) -> DomainStats:
        """Get domain performance statistics."""
        self._check_operation_allowed("domain.stats")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            state, _ = domain.state()
            
            stats = DomainStats(
                name=domain_name,
                state=self._domain_state_to_enum(state),
            )
            
            # Only get detailed stats for running domains
            if state == libvirt.VIR_DOMAIN_RUNNING:
                try:
                    # Get CPU stats
                    cpu_stats = domain.getCPUStats(True)
                    if cpu_stats:
                        stats.cpu_time = cpu_stats[0].get('cpu_time')
                        stats.cpu_user_time = cpu_stats[0].get('user_time')
                        stats.cpu_system_time = cpu_stats[0].get('system_time')
                    
                    # Get memory stats
                    mem_stats = domain.memoryStats()
                    stats.memory_actual = mem_stats.get('actual')
                    stats.memory_unused = mem_stats.get('unused')
                    stats.memory_available = mem_stats.get('available')
                    stats.memory_usable = mem_stats.get('usable')
                    
                    # Get block device stats
                    try:
                        xml_desc = domain.XMLDesc()
                        root = ET.fromstring(xml_desc)
                        
                        total_rd_bytes = 0
                        total_wr_bytes = 0
                        total_rd_reqs = 0
                        total_wr_reqs = 0
                        
                        for disk in root.findall('.//disk[@device="disk"]'):
                            target = disk.find('target')
                            if target is not None:
                                dev = target.get('dev')
                                if dev:
                                    block_stats = domain.blockStats(dev)
                                    total_rd_bytes += block_stats[1]
                                    total_wr_bytes += block_stats[3]
                                    total_rd_reqs += block_stats[0]
                                    total_wr_reqs += block_stats[2]
                        
                        stats.block_rd_bytes = total_rd_bytes
                        stats.block_wr_bytes = total_wr_bytes
                        stats.block_rd_reqs = total_rd_reqs
                        stats.block_wr_reqs = total_wr_reqs
                        
                    except (libvirtError, ET.ParseError):
                        pass  # Block stats not available
                    
                    # Get network interface stats
                    try:
                        xml_desc = domain.XMLDesc()
                        root = ET.fromstring(xml_desc)
                        
                        total_rx_bytes = 0
                        total_tx_bytes = 0
                        total_rx_pkts = 0
                        total_tx_pkts = 0
                        
                        for interface in root.findall('.//interface'):
                            target = interface.find('target')
                            if target is not None:
                                dev = target.get('dev')
                                if dev:
                                    net_stats = domain.interfaceStats(dev)
                                    total_rx_bytes += net_stats[0]
                                    total_tx_bytes += net_stats[4]
                                    total_rx_pkts += net_stats[1]
                                    total_tx_pkts += net_stats[5]
                        
                        stats.net_rx_bytes = total_rx_bytes
                        stats.net_tx_bytes = total_tx_bytes
                        stats.net_rx_pkts = total_rx_pkts
                        stats.net_tx_pkts = total_tx_pkts
                        
                    except (libvirtError, ET.ParseError):
                        pass  # Network stats not available
                
                except libvirtError:
                    pass  # Some stats not available
            
            logger.info(f"Retrieved stats for domain: {domain_name}")
            return stats
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to get domain stats for {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to get domain stats: {e}")
    
    async def get_host_info(self) -> HostInfo:
        """Get host system information."""
        self._check_operation_allowed("host.info")
        conn = self._ensure_connected()
        
        try:
            info = conn.getInfo()
            
            return HostInfo(
                hostname=conn.getHostname(),
                uri=conn.getURI(),
                hypervisor_type=conn.getType(),
                hypervisor_version=conn.getVersion(),
                libvirt_version=conn.getLibVersion(),
                cpu_model=info[0],
                cpu_arch=info[0],
                cpu_cores=info[6],
                cpu_threads=info[2],
                cpu_sockets=info[5],
                cpu_mhz=info[3],
                memory_size=info[1] * 1024,  # Convert MB to KB
                memory_free=conn.getFreeMemory() // 1024,  # Convert bytes to KB
                numa_nodes=info[4],
            )
            
        except libvirtError as e:
            logger.error(f"Failed to get host info: {e}")
            raise LibvirtOperationError(f"Failed to get host info: {e}")
    
    async def list_networks(self) -> List[NetworkInfo]:
        """List all networks."""
        self._check_operation_allowed("network.list")
        conn = self._ensure_connected()
        
        try:
            networks = []
            
            # Get active networks
            for net_name in conn.listNetworks():
                try:
                    network = conn.networkLookupByName(net_name)
                    networks.append(self._get_network_info(network))
                except libvirtError as e:
                    logger.warning(f"Failed to get network info for {net_name}: {e}")
            
            # Get inactive networks
            for net_name in conn.listDefinedNetworks():
                try:
                    network = conn.networkLookupByName(net_name)
                    networks.append(self._get_network_info(network))
                except libvirtError as e:
                    logger.warning(f"Failed to get network info for {net_name}: {e}")
            
            logger.info(f"Listed {len(networks)} networks")
            return networks
            
        except libvirtError as e:
            logger.error(f"Failed to list networks: {e}")
            raise LibvirtOperationError(f"Failed to list networks: {e}")
    
    def _get_network_info(self, network) -> NetworkInfo:
        """Get network information from libvirt network object."""
        try:
            bridge_name = None
            try:
                bridge_name = network.bridgeName()
            except libvirtError:
                pass  # Bridge name not available
            
            return NetworkInfo(
                name=network.name(),
                uuid=network.UUIDString(),
                state=NetworkState.ACTIVE if network.isActive() else NetworkState.INACTIVE,
                bridge_name=bridge_name,
                autostart=bool(network.autostart()),
                persistent=bool(network.isPersistent()),
            )
        except libvirtError as e:
            raise LibvirtOperationError(f"Failed to get network info: {e}")
    
    async def list_storage_pools(self) -> List[StoragePoolInfo]:
        """List all storage pools."""
        self._check_operation_allowed("storage.list")
        conn = self._ensure_connected()
        
        try:
            pools = []
            
            # Get active pools
            for pool_name in conn.listStoragePools():
                try:
                    pool = conn.storagePoolLookupByName(pool_name)
                    pools.append(self._get_storage_pool_info(pool))
                except libvirtError as e:
                    logger.warning(f"Failed to get storage pool info for {pool_name}: {e}")
            
            # Get inactive pools
            for pool_name in conn.listDefinedStoragePools():
                try:
                    pool = conn.storagePoolLookupByName(pool_name)
                    pools.append(self._get_storage_pool_info(pool))
                except libvirtError as e:
                    logger.warning(f"Failed to get storage pool info for {pool_name}: {e}")
            
            logger.info(f"Listed {len(pools)} storage pools")
            return pools
            
        except libvirtError as e:
            logger.error(f"Failed to list storage pools: {e}")
            raise LibvirtOperationError(f"Failed to list storage pools: {e}")
    
    def _get_storage_pool_info(self, pool) -> StoragePoolInfo:
        """Get storage pool information from libvirt storage pool object."""
        try:
            state_map = {
                libvirt.VIR_STORAGE_POOL_INACTIVE: StoragePoolState.INACTIVE,
                libvirt.VIR_STORAGE_POOL_BUILDING: StoragePoolState.BUILDING,
                libvirt.VIR_STORAGE_POOL_RUNNING: StoragePoolState.RUNNING,
                libvirt.VIR_STORAGE_POOL_DEGRADED: StoragePoolState.DEGRADED,
                libvirt.VIR_STORAGE_POOL_INACCESSIBLE: StoragePoolState.INACCESSIBLE,
            }
            
            info = pool.info()
            state = state_map.get(info[0], StoragePoolState.INACTIVE)
            
            return StoragePoolInfo(
                name=pool.name(),
                uuid=pool.UUIDString(),
                state=state,
                capacity=info[1],
                allocation=info[2],
                available=info[3],
                autostart=bool(pool.autostart()),
                persistent=bool(pool.isPersistent()),
            )
        except libvirtError as e:
            raise LibvirtOperationError(f"Failed to get storage pool info: {e}")
    
    async def get_domain_xml(self, domain_name: str) -> str:
        """Get domain XML configuration."""
        self._check_operation_allowed("domain.getxml")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            xml = domain.XMLDesc()
            logger.info(f"Retrieved XML for domain: {domain_name}")
            return xml
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to get domain XML for {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to get domain XML: {e}")
    
    async def create_domain(self, xml: str, ephemeral: bool = False) -> bool:
        """Create a new domain from XML configuration."""
        self._check_operation_allowed("domain.create")
        conn = self._ensure_connected()
        
        try:
            # Validate XML format
            try:
                ET.fromstring(xml)
            except ET.ParseError as e:
                raise LibvirtOperationError(f"Invalid XML format: {e}")
            
            if ephemeral:
                # Create an ephemeral domain (not persistent)
                domain = conn.createXML(xml)
                logger.info(f"Created ephemeral domain: {domain.name()}")
            else:
                # Define the domain (make it persistent) and optionally start it
                domain = conn.defineXML(xml)
                logger.info(f"Defined persistent domain: {domain.name()}")
            
            return True
            
        except libvirtError as e:
            logger.error(f"Failed to create domain: {e}")
            raise LibvirtOperationError(f"Failed to create domain: {e}")
    
    async def delete_domain(self, domain_name: str, remove_storage: bool = False, force: bool = False) -> bool:
        """Delete a domain and optionally its storage."""
        self._check_operation_allowed("domain.delete")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            # Check domain state
            state, _ = domain.state()
            
            # Force stop if running and force is requested
            if state == libvirt.VIR_DOMAIN_RUNNING:
                if force:
                    domain.destroy()
                    logger.info(f"Force stopped domain before deletion: {domain_name}")
                else:
                    raise LibvirtOperationError(
                        f"Domain {domain_name} is running. Use force=True to stop and delete it."
                    )
            
            # Collect storage paths if we need to remove them
            storage_paths = []
            if remove_storage:
                try:
                    xml_desc = domain.XMLDesc()
                    root = ET.fromstring(xml_desc)
                    for disk in root.findall('.//disk[@device="disk"]'):
                        source = disk.find('source')
                        if source is not None:
                            file_path = source.get('file')
                            if file_path:
                                storage_paths.append(file_path)
                except ET.ParseError:
                    logger.warning(f"Could not parse XML for storage cleanup: {domain_name}")
            
            # Undefine the domain
            if remove_storage and storage_paths:
                # Use flags to remove associated storage
                flags = libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
                if domain.hasManagedSaveImage():
                    flags |= libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
                
                # Try to remove associated storage
                try:
                    flags |= libvirt.VIR_DOMAIN_UNDEFINE_NVRAM
                    domain.undefineFlags(flags)
                except libvirtError:
                    # Fallback to basic undefine
                    domain.undefine()
                
                # Manually remove storage files if still present
                import os
                for path in storage_paths:
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                            logger.info(f"Removed storage file: {path}")
                    except OSError as e:
                        logger.warning(f"Failed to remove storage file {path}: {e}")
            else:
                domain.undefine()
            
            logger.info(f"Deleted domain: {domain_name}")
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to delete domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to delete domain: {e}")
    
    async def attach_device(self, domain_name: str, device_xml: str, live: bool = True, persistent: bool = True) -> bool:
        """Attach a device to a domain."""
        self._check_operation_allowed("domain.attach_device")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            # Validate device XML format
            try:
                ET.fromstring(device_xml)
            except ET.ParseError as e:
                raise LibvirtOperationError(f"Invalid device XML format: {e}")
            
            # Determine flags
            flags = 0
            if live and persistent:
                flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            elif live:
                flags = libvirt.VIR_DOMAIN_AFFECT_LIVE
            elif persistent:
                flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
            
            # Attach the device
            domain.attachDeviceFlags(device_xml, flags)
            logger.info(f"Attached device to domain: {domain_name}")
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to attach device to domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to attach device: {e}")
    
    async def detach_device(self, domain_name: str, device_xml: str, live: bool = True, persistent: bool = True) -> bool:
        """Detach a device from a domain."""
        self._check_operation_allowed("domain.detach_device")
        conn = self._ensure_connected()
        
        try:
            domain = conn.lookupByName(domain_name)
            
            # Validate device XML format
            try:
                ET.fromstring(device_xml)
            except ET.ParseError as e:
                raise LibvirtOperationError(f"Invalid device XML format: {e}")
            
            # Determine flags
            flags = 0
            if live and persistent:
                flags = libvirt.VIR_DOMAIN_AFFECT_LIVE | libvirt.VIR_DOMAIN_AFFECT_CONFIG
            elif live:
                flags = libvirt.VIR_DOMAIN_AFFECT_LIVE
            elif persistent:
                flags = libvirt.VIR_DOMAIN_AFFECT_CONFIG
            
            # Detach the device
            domain.detachDeviceFlags(device_xml, flags)
            logger.info(f"Detached device from domain: {domain_name}")
            return True
            
        except libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_DOMAIN:
                raise LibvirtResourceNotFoundError(f"Domain not found: {domain_name}")
            logger.error(f"Failed to detach device from domain {domain_name}: {e}")
            raise LibvirtOperationError(f"Failed to detach device: {e}")
    
    def generate_domain_xml(self, params: 'DomainCreateParams') -> str:
        """Generate domain XML from parameters."""
        from .xml_templates import DomainXMLGenerator
        generator = DomainXMLGenerator()
        return generator.generate(params)
