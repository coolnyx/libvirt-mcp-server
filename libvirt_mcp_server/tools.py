"""
MCP tools for libvirt virtualization management.

This module defines all the MCP tools that expose libvirt functionality
to AI models through the Model Context Protocol.
"""

from typing import Any, Dict, List, Optional

import mcp.types as types
from mcp.server.fastmcp import Context, FastMCP

from .exceptions import (
    LibvirtConnectionError,
    LibvirtOperationError,
    LibvirtPermissionError,
    LibvirtResourceNotFoundError,
)
from .libvirt_client import LibvirtClient
from .logging import get_logger, log_async_function_call
from .models import (
    DomainActionParams,
    DomainCreateParams,
    DomainDeleteParams,
    DomainListParams,
    DomainStatsParams,
    DeviceOperationParams,
    OperationResult,
)


logger = get_logger(__name__)


def register_tools(mcp_server: FastMCP, libvirt_client: LibvirtClient) -> None:
    """Register all libvirt MCP tools with the server."""
    
    @mcp_server.tool()
    async def list_domains(
        ctx: Context,
        state: str = "all",
        include_inactive: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List virtual machine domains.
        
        Args:
            state: Filter by domain state (all, running, stopped, active, inactive)
            include_inactive: Whether to include inactive domains
        
        Returns:
            List of domain information dictionaries
        """
        try:
            await ctx.info(f"Listing domains with state filter: {state}")
            
            # Validate parameters
            params = DomainListParams(state=state, include_inactive=include_inactive)
            
            domains = await libvirt_client.list_domains(
                include_inactive=params.include_inactive
            )
            
            # Filter by state if requested
            if params.state != "all":
                if params.state in ["running", "active"]:
                    domains = [d for d in domains if d.state.value == "running"]
                elif params.state in ["stopped", "inactive"]:
                    domains = [d for d in domains if d.state.value == "shutoff"]
            
            result = [domain.dict() for domain in domains]
            await ctx.info(f"Found {len(result)} domains")
            
            return result
            
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to list domains: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error listing domains: {e}")
            raise
    
    @mcp_server.tool()
    async def domain_info(ctx: Context, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific virtual machine domain.
        
        Args:
            name: Domain name
        
        Returns:
            Domain information dictionary
        """
        try:
            await ctx.info(f"Getting info for domain: {name}")
            
            domain = await libvirt_client.get_domain_info(name)
            result = domain.dict()
            
            await ctx.info(f"Retrieved info for domain: {name}")
            return result
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            raise
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to get domain info: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error getting domain info: {e}")
            raise
    
    @mcp_server.tool()
    async def start_domain(
        ctx: Context,
        name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Start a virtual machine domain.
        
        Args:
            name: Domain name
            force: Force start even if domain is already running
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Starting domain: {name} (force={force})")
            
            params = DomainActionParams(name=name, force=force)
            success = await libvirt_client.start_domain(params.name, params.force)
            
            result = OperationResult(
                success=success,
                message=f"Domain {name} started successfully",
                details={"domain": name, "force": force}
            )
            
            await ctx.info(f"Domain {name} started successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {name} not found",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to start domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to start domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error starting domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error starting domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def stop_domain(
        ctx: Context,
        name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Stop a virtual machine domain.
        
        Args:
            name: Domain name
            force: Force stop (destroy) instead of graceful shutdown
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Stopping domain: {name} (force={force})")
            
            params = DomainActionParams(name=name, force=force)
            success = await libvirt_client.stop_domain(params.name, params.force)
            
            result = OperationResult(
                success=success,
                message=f"Domain {name} stopped successfully",
                details={"domain": name, "force": force}
            )
            
            await ctx.info(f"Domain {name} stopped successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {name} not found",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to stop domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to stop domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error stopping domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error stopping domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def reboot_domain(
        ctx: Context,
        name: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Reboot a virtual machine domain.
        
        Args:
            name: Domain name
            force: Force reboot instead of graceful reboot
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Rebooting domain: {name} (force={force})")
            
            params = DomainActionParams(name=name, force=force)
            success = await libvirt_client.reboot_domain(params.name, params.force)
            
            result = OperationResult(
                success=success,
                message=f"Domain {name} rebooted successfully",
                details={"domain": name, "force": force}
            )
            
            await ctx.info(f"Domain {name} rebooted successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {name} not found",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to reboot domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to reboot domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error rebooting domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error rebooting domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def domain_stats(
        ctx: Context,
        name: str,
        flags: List[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance statistics for a virtual machine domain.
        
        Args:
            name: Domain name
            flags: Statistics flags (state, cpu-total, balloon, vcpu, interface, block)
        
        Returns:
            Domain statistics dictionary
        """
        try:
            await ctx.info(f"Getting stats for domain: {name}")
            
            if flags is None:
                flags = ["state", "cpu-total", "balloon", "vcpu", "interface", "block"]
            
            params = DomainStatsParams(name=name, flags=flags)
            stats = await libvirt_client.get_domain_stats(params.name)
            result = stats.dict()
            
            await ctx.info(f"Retrieved stats for domain: {name}")
            return result
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            raise
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to get domain stats: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error getting domain stats: {e}")
            raise
    
    @mcp_server.tool()
    async def host_info(ctx: Context) -> Dict[str, Any]:
        """
        Get host system information.
        
        Returns:
            Host information dictionary
        """
        try:
            await ctx.info("Getting host system information")
            
            host = await libvirt_client.get_host_info()
            result = host.dict()
            
            await ctx.info("Retrieved host system information")
            return result
            
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to get host info: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error getting host info: {e}")
            raise
    
    @mcp_server.tool()
    async def list_networks(ctx: Context) -> List[Dict[str, Any]]:
        """
        List virtual networks.
        
        Returns:
            List of network information dictionaries
        """
        try:
            await ctx.info("Listing virtual networks")
            
            networks = await libvirt_client.list_networks()
            result = [network.dict() for network in networks]
            
            await ctx.info(f"Found {len(result)} networks")
            return result
            
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to list networks: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error listing networks: {e}")
            raise
    
    @mcp_server.tool()
    async def list_storage_pools(ctx: Context) -> List[Dict[str, Any]]:
        """
        List storage pools.
        
        Returns:
            List of storage pool information dictionaries
        """
        try:
            await ctx.info("Listing storage pools")
            
            pools = await libvirt_client.list_storage_pools()
            result = [pool.dict() for pool in pools]
            
            await ctx.info(f"Found {len(result)} storage pools")
            return result
            
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to list storage pools: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error listing storage pools: {e}")
            raise
    
    @mcp_server.tool()
    async def get_domain_xml(ctx: Context, name: str) -> str:
        """
        Get XML configuration for a virtual machine domain.
        
        Args:
            name: Domain name
        
        Returns:
            Domain XML configuration as string
        """
        try:
            await ctx.info(f"Getting XML configuration for domain: {name}")
            
            xml = await libvirt_client.get_domain_xml(name)
            
            await ctx.info(f"Retrieved XML configuration for domain: {name}")
            return xml
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            raise
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to get domain XML: {e}")
            raise
        except Exception as e:
            await ctx.error(f"Unexpected error getting domain XML: {e}")
            raise
    
    @mcp_server.tool()
    async def create_domain(
        ctx: Context,
        name: str,
        memory: int = 2097152,  # 2GB in KB
        vcpus: int = 2,
        disk_size: Optional[int] = None,
        disk_path: Optional[str] = None,
        network: str = "default",
        os_type: str = "hvm",
        arch: str = "x86_64",
        boot_device: str = "hd",
        xml: Optional[str] = None,
        ephemeral: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new virtual machine domain.
        
        Args:
            name: Domain name
            memory: Memory size in KB (default: 2GB)
            vcpus: Number of virtual CPUs (default: 2)
            disk_size: Disk size in GB (optional)
            disk_path: Path to disk image (optional)
            network: Network name (default: "default")
            os_type: OS type (default: "hvm")
            arch: Architecture (default: "x86_64")
            boot_device: Boot device (default: "hd")
            xml: Custom XML configuration (optional)
            ephemeral: Create ephemeral domain (default: False)
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Creating domain: {name}")
            
            if xml:
                # Use provided XML directly
                domain_xml = xml
            else:
                # Generate XML from parameters
                params = DomainCreateParams(
                    name=name,
                    memory=memory,
                    vcpus=vcpus,
                    disk_size=disk_size,
                    disk_path=disk_path,
                    network=network,
                    os_type=os_type,
                    arch=arch,
                    boot_device=boot_device
                )
                domain_xml = libvirt_client.generate_domain_xml(params)
            
            success = await libvirt_client.create_domain(domain_xml, ephemeral)
            
            result = OperationResult(
                success=success,
                message=f"Domain {name} created successfully",
                details={
                    "domain": name,
                    "ephemeral": ephemeral,
                    "memory": memory,
                    "vcpus": vcpus
                }
            )
            
            await ctx.info(f"Domain {name} created successfully")
            return result.dict()
            
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to create domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to create domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error creating domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error creating domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def delete_domain(
        ctx: Context,
        name: str,
        remove_storage: bool = False,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Delete a virtual machine domain.
        
        Args:
            name: Domain name
            remove_storage: Remove associated storage files
            force: Force delete even if domain is running
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Deleting domain: {name} (remove_storage={remove_storage}, force={force})")
            
            params = DomainDeleteParams(name=name, remove_storage=remove_storage, force=force)
            success = await libvirt_client.delete_domain(
                params.name, 
                params.remove_storage, 
                params.force
            )
            
            result = OperationResult(
                success=success,
                message=f"Domain {name} deleted successfully",
                details={
                    "domain": name,
                    "remove_storage": remove_storage,
                    "force": force
                }
            )
            
            await ctx.info(f"Domain {name} deleted successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {name} not found",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to delete domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to delete domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error deleting domain: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error deleting domain {name}: {e}",
                details={"domain": name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def attach_device(
        ctx: Context,
        domain_name: str,
        device_xml: str,
        live: bool = True,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """
        Attach a device to a virtual machine domain.
        
        Args:
            domain_name: Domain name
            device_xml: Device XML configuration
            live: Apply to live domain
            persistent: Apply to persistent configuration
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Attaching device to domain: {domain_name}")
            
            params = DeviceOperationParams(
                domain_name=domain_name,
                device_xml=device_xml,
                live=live,
                persistent=persistent
            )
            
            success = await libvirt_client.attach_device(
                params.domain_name,
                params.device_xml,
                params.live,
                params.persistent
            )
            
            result = OperationResult(
                success=success,
                message=f"Device attached to domain {domain_name} successfully",
                details={
                    "domain": domain_name,
                    "live": live,
                    "persistent": persistent
                }
            )
            
            await ctx.info(f"Device attached to domain {domain_name} successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {domain_name} not found",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to attach device: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to attach device to domain {domain_name}: {e}",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error attaching device: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error attaching device to domain {domain_name}: {e}",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def detach_device(
        ctx: Context,
        domain_name: str,
        device_xml: str,
        live: bool = True,
        persistent: bool = True
    ) -> Dict[str, Any]:
        """
        Detach a device from a virtual machine domain.
        
        Args:
            domain_name: Domain name
            device_xml: Device XML configuration
            live: Apply to live domain
            persistent: Apply to persistent configuration
        
        Returns:
            Operation result
        """
        try:
            await ctx.info(f"Detaching device from domain: {domain_name}")
            
            params = DeviceOperationParams(
                domain_name=domain_name,
                device_xml=device_xml,
                live=live,
                persistent=persistent
            )
            
            success = await libvirt_client.detach_device(
                params.domain_name,
                params.device_xml,
                params.live,
                params.persistent
            )
            
            result = OperationResult(
                success=success,
                message=f"Device detached from domain {domain_name} successfully",
                details={
                    "domain": domain_name,
                    "live": live,
                    "persistent": persistent
                }
            )
            
            await ctx.info(f"Device detached from domain {domain_name} successfully")
            return result.dict()
            
        except LibvirtResourceNotFoundError as e:
            await ctx.error(f"Domain not found: {e}")
            result = OperationResult(
                success=False,
                message=f"Domain {domain_name} not found",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
        except (LibvirtConnectionError, LibvirtOperationError, LibvirtPermissionError) as e:
            await ctx.error(f"Failed to detach device: {e}")
            result = OperationResult(
                success=False,
                message=f"Failed to detach device from domain {domain_name}: {e}",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
        except Exception as e:
            await ctx.error(f"Unexpected error detaching device: {e}")
            result = OperationResult(
                success=False,
                message=f"Unexpected error detaching device from domain {domain_name}: {e}",
                details={"domain": domain_name, "error": str(e)}
            )
            return result.dict()
    
    @mcp_server.tool()
    async def generate_device_xml(
        ctx: Context,
        device_type: str,
        **kwargs
    ) -> str:
        """
        Generate device XML configuration.
        
        Args:
            device_type: Type of device (disk, network, usb, cdrom)
            **kwargs: Device-specific parameters
        
        Returns:
            Device XML configuration
        """
        try:
            await ctx.info(f"Generating {device_type} device XML")
            
            from .xml_templates import DeviceXMLGenerator
            generator = DeviceXMLGenerator()
            
            if device_type == "disk":
                disk_path = kwargs.get("disk_path", "/var/lib/libvirt/images/new-disk.qcow2")
                target_dev = kwargs.get("target_dev", "vdb")
                bus = kwargs.get("bus", "virtio")
                xml = generator.generate_disk_device(disk_path, target_dev, bus)
            
            elif device_type == "network":
                network_name = kwargs.get("network_name", "default")
                model = kwargs.get("model", "virtio")
                xml = generator.generate_network_device(network_name, model)
            
            elif device_type == "usb":
                vendor_id = kwargs.get("vendor_id", "0x1234")
                product_id = kwargs.get("product_id", "0x5678")
                xml = generator.generate_usb_device(vendor_id, product_id)
            
            elif device_type == "cdrom":
                iso_path = kwargs.get("iso_path", "/var/lib/libvirt/images/cdrom.iso")
                target_dev = kwargs.get("target_dev", "hdc")
                xml = generator.generate_cdrom_device(iso_path, target_dev)
            
            else:
                raise ValueError(f"Unsupported device type: {device_type}")
            
            await ctx.info(f"Generated {device_type} device XML")
            return xml
            
        except Exception as e:
            await ctx.error(f"Failed to generate device XML: {e}")
            raise
