"""
Custom exceptions for libvirt-mcp-server.

This module defines specific exception classes for different types of errors
that can occur during libvirt operations and MCP interactions.
"""


class LibvirtMCPError(Exception):
    """Base exception for all libvirt-mcp-server errors."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LibvirtConnectionError(LibvirtMCPError):
    """Raised when libvirt connection fails or is lost."""
    pass


class LibvirtOperationError(LibvirtMCPError):
    """Raised when a libvirt operation fails."""
    pass


class LibvirtPermissionError(LibvirtMCPError):
    """Raised when an operation is not allowed by security configuration."""
    pass


class LibvirtResourceNotFoundError(LibvirtMCPError):
    """Raised when a requested libvirt resource is not found."""
    pass


class MCPServerError(LibvirtMCPError):
    """Raised when MCP server encounters an error."""
    pass


class ConfigurationError(LibvirtMCPError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(LibvirtMCPError):
    """Raised when input validation fails."""
    pass
