"""
Libvirt MCP Server - AI 驱动的虚拟化管理服务

这是一个基于 Model Context Protocol (MCP) 的服务器，
为 AI 模型提供安全、可控的虚拟化管理能力。
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "A Model Context Protocol server for libvirt virtualization management"
__url__ = "https://github.com/your-org/libvirt-mcp-server"

# 导出主要类和函数
from .config import Config
from .server import LibvirtMCPServer
from .libvirt_client import LibvirtClient
from .exceptions import (
    LibvirtConnectionError,
    LibvirtOperationError,
    LibvirtPermissionError,
    LibvirtResourceNotFoundError,
    ConfigurationError,
)

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "__url__",
    "Config",
    "LibvirtMCPServer",
    "LibvirtClient",
    "LibvirtConnectionError",
    "LibvirtOperationError",
    "LibvirtPermissionError", 
    "LibvirtResourceNotFoundError",
    "ConfigurationError",
]