"""
Main MCP server implementation for libvirt virtualization management.

This module implements the MCP server that exposes libvirt functionality
through the Model Context Protocol, providing AI models with secure
access to virtualization management capabilities.
"""

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP

from .config import Config
from .exceptions import ConfigurationError, LibvirtConnectionError
from .libvirt_client import LibvirtClient
from .security import SecurityManager
from .tools import register_tools
from .logging import get_logger, LogContext, log_async_performance

logger = get_logger(__name__)


class LibvirtMCPServer:
    """
    Main MCP server for libvirt virtualization management.
    
    This server provides a secure, controlled interface to libvirt
    functionality through MCP tools, enabling AI models to manage
    virtual machines and related resources.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the libvirt MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config
        self.libvirt_client: Optional[LibvirtClient] = None
        self.security_manager: Optional[SecurityManager] = None
        self.mcp_server: Optional[FastMCP] = None
    
    @asynccontextmanager
    async def _lifespan(self, server: FastMCP) -> AsyncIterator[dict]:
        """
        Manage server lifecycle with proper resource initialization and cleanup.
        
        Args:
            server: The FastMCP server instance
        
        Yields:
            Application context with initialized resources
        """
        logger.info("Starting libvirt MCP server", config=self.config.dict())
        
        try:
            # Initialize security manager
            self.security_manager = SecurityManager(self.config)
            logger.info("Security manager initialized")
            
            # Initialize libvirt client
            self.libvirt_client = LibvirtClient(self.config)
            await self.libvirt_client.connect()
            logger.info("Libvirt client connected", uri=self.config.libvirt.uri)
            
            # Validate configuration
            self.config.validate_permissions()
            logger.info("Configuration validated")
            
            # Register MCP tools
            register_tools(server, self.libvirt_client)
            logger.info("MCP tools registered")
            
            # Yield application context
            yield {
                "libvirt_client": self.libvirt_client,
                "security_manager": self.security_manager,
                "config": self.config,
            }
            
        except Exception as e:
            logger.error("Failed to initialize server", error=str(e), exc_info=True)
            raise
        finally:
            # Cleanup resources
            if self.libvirt_client:
                try:
                    await self.libvirt_client.disconnect()
                    logger.info("Libvirt client disconnected")
                except Exception as e:
                    logger.warning("Error disconnecting libvirt client", error=str(e))
            
            logger.info("Libvirt MCP server stopped")
    
    def create_server(self) -> FastMCP:
        """
        Create and configure the FastMCP server.
        
        Returns:
            Configured FastMCP server instance
        """
        # Prepare server instructions
        instructions = f"""
        You are a libvirt virtualization management assistant powered by the {self.config.mcp.server_name} MCP server.
        
        You can help manage virtual machines and virtualization infrastructure through libvirt.
        
        Available capabilities:
        - List and inspect virtual machine domains
        - Start, stop, and reboot virtual machines
        - Monitor VM performance and resource usage
        - Query host system information
        - Manage virtual networks and storage pools
        - Retrieve and analyze VM configurations
        
        Security notes:
        - All operations are subject to security policy validation
        - Operations are logged for audit purposes
        - Only pre-approved operations are allowed
        - Input validation is performed on all requests
        
        When performing operations:
        1. Always verify the domain/resource exists before attempting operations
        2. Use appropriate force flags only when necessary
        3. Monitor operation results and provide clear feedback
        4. Be cautious with destructive operations (stop, reboot, delete)
        
        For assistance with specific libvirt concepts or troubleshooting,
        feel free to ask for explanations or guidance.
        """
        
        # Create FastMCP server with instructions and lifespan management
        mcp_server = FastMCP(
            name=self.config.mcp.server_name,
            instructions=instructions,
            lifespan=self._lifespan,
        )
        
        self.mcp_server = mcp_server
        return mcp_server
    
    async def run_stdio(self) -> None:
        """Run the server using stdio transport."""
        logger.info("Starting MCP server with stdio transport")
        
        try:
            server = self.create_server()
            await server.run_stdio_async()
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error("Server error", error=str(e), exc_info=True)
            raise
    
    async def run_http(self, host: str = None, port: int = None) -> None:
        """
        Run the server using HTTP transport.
        
        Args:
            host: Server host (defaults to config)
            port: Server port (defaults to config)
        """
        server_host = host or self.config.mcp.host
        server_port = port or self.config.mcp.port
        
        logger.info(
            "Starting MCP server with HTTP transport",
            host=server_host,
            port=server_port
        )
        
        try:
            server = self.create_server()
            await server.run(transport="streamable-http", host=server_host, port=server_port)
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error("Server error", error=str(e), exc_info=True)
            raise
    
    async def run_sse(self, host: str = None, port: int = None) -> None:
        """
        Run the server using SSE transport.
        
        Args:
            host: Server host (defaults to config)
            port: Server port (defaults to config)
        """
        server_host = host or self.config.mcp.host
        server_port = port or self.config.mcp.port
        
        logger.info(
            "Starting MCP server with SSE transport",
            host=server_host,
            port=server_port
        )
        
        try:
            server = self.create_server()
            await server.run(transport="sse", host=server_host, port=server_port)
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error("Server error", error=str(e), exc_info=True)
            raise
    
    async def run(self, transport: str = None, host: str = None, port: int = None) -> None:
        """
        Run the server with the specified transport.
        
        Args:
            transport: Transport type (stdio, http, sse) - defaults to config
            host: Server host (defaults to config)
            port: Server port (defaults to config)
        """
        transport_type = transport or self.config.mcp.transport
        
        if transport_type == "stdio":
            await self.run_stdio()
        elif transport_type == "http":
            await self.run_http(host, port)
        elif transport_type == "sse":
            await self.run_sse(host, port)
        else:
            raise ConfigurationError(f"Unsupported transport type: {transport_type}")
    
    async def health_check(self) -> dict:
        """
        Perform a health check of the server and its dependencies.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }
        
        try:
            # Check libvirt connection
            if self.libvirt_client:
                try:
                    await self.libvirt_client.get_host_info()
                    health_status["components"]["libvirt"] = {
                        "status": "healthy",
                        "uri": self.config.libvirt.uri
                    }
                except Exception as e:
                    health_status["components"]["libvirt"] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
                    health_status["status"] = "degraded"
            else:
                health_status["components"]["libvirt"] = {
                    "status": "not_initialized"
                }
                health_status["status"] = "degraded"
            
            # Check security manager
            if self.security_manager:
                security_summary = await self.security_manager.get_security_summary()
                health_status["components"]["security"] = {
                    "status": "healthy",
                    "summary": security_summary
                }
            else:
                health_status["components"]["security"] = {
                    "status": "not_initialized"
                }
                health_status["status"] = "degraded"
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
