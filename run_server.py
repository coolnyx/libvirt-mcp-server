#!/usr/bin/env python3
"""
Development server runner for libvirt-mcp-server.

This script provides a convenient way to run the server during development
with various configuration options.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from libvirt_mcp_server import LibvirtMCPServer
from libvirt_mcp_server.config import Config
from libvirt_mcp_server.logging import configure_logging, get_logger


async def main():
    """Main function to run the development server."""
    print("🚀 Starting libvirt-mcp-server (Development Mode)")
    print("=" * 50)
    
    try:
        # Load configuration
        config_file = project_root / "config.yaml"
        if config_file.exists():
            print(f"📁 Loading configuration from: {config_file}")
            config = Config.from_yaml_file(str(config_file))
        else:
            print("📁 Using default configuration")
            config = Config.load()
        
        # Override for development
        config.logging.level = "INFO"
        # config.libvirt.uri = "qemu:///system"  # Use test driver for development
        
        # Configure logging
        logging_manager = configure_logging(config)
        logger = get_logger(__name__)
        
        print(f"🔗 Libvirt URI: {config.libvirt.uri}")
        print(f"🚦 Transport: {config.mcp.transport}")
        
        if config.mcp.transport != "stdio":
            print(f"🌐 Host: {config.mcp.host}:{config.mcp.port}")
        
        print(f"📝 Audit Log: {'Enabled' if config.security.audit_log else 'Disabled'}")
        print()
        
        # Create and run server
        server = LibvirtMCPServer(config)
        print("✅ Server initialized successfully")
        print("🔄 Starting server... (Press Ctrl+C to stop)")
        print()
        
        logger.info("🚀 启动开发服务器")
        await server.run()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        logger = get_logger(__name__)
        print(f"❌ Error: {e}")
        logger.exception("Server error")
        sys.exit(1)


if __name__ == "__main__":
    # Run the server
    asyncio.run(main())
