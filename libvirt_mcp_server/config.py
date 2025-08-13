"""
Configuration management for libvirt-mcp-server.

This module handles loading and validating configuration from various sources
including YAML files, environment variables, and command-line arguments.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator


class LibvirtConfig(BaseModel):
    """Libvirt connection configuration."""
    
    uri: str = Field(default="qemu:///system", description="Libvirt connection URI")
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout in seconds")
    readonly: bool = Field(default=False, description="Use read-only connection")


class MCPConfig(BaseModel):
    """MCP server configuration."""
    
    server_name: str = Field(default="libvirt-manager", description="MCP server name")
    version: str = Field(default="1.0.0", description="Server version")
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    transport: str = Field(default="stdio", description="Transport type (stdio, http, sse)")


class SecurityConfig(BaseModel):
    """Security and access control configuration."""
    
    auth_required: bool = Field(default=True, description="Require authentication")
    allowed_operations: List[str] = Field(
        default_factory=lambda: [
            "domain.list",
            "domain.info",
            "domain.start",
            "domain.stop",
            "domain.reboot",
            "domain.stats",
            "host.info",
            "network.list",
            "storage.list",
        ],
        description="List of allowed operations"
    )
    audit_log: bool = Field(default=True, description="Enable audit logging")
    max_concurrent_ops: int = Field(default=10, ge=1, le=100, description="Maximum concurrent operations")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO", description="Log level")
    file: Optional[str] = Field(default=None, description="Log file path")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    max_size: int = Field(default=10485760, ge=1024, description="Maximum log file size in bytes")
    backup_count: int = Field(default=5, ge=1, description="Number of backup log files")

    @validator('level')
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class Config(BaseModel):
    """Main configuration class."""
    
    libvirt: LibvirtConfig = Field(default_factory=LibvirtConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml_file(cls, file_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(**data)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        config_data = {}
        
        # Libvirt configuration
        if uri := os.getenv("LIBVIRT_URI"):
            config_data.setdefault("libvirt", {})["uri"] = uri
        if timeout := os.getenv("LIBVIRT_TIMEOUT"):
            config_data.setdefault("libvirt", {})["timeout"] = int(timeout)
        if readonly := os.getenv("LIBVIRT_READONLY"):
            config_data.setdefault("libvirt", {})["readonly"] = readonly.lower() == "true"
        
        # MCP configuration
        if server_name := os.getenv("MCP_SERVER_NAME"):
            config_data.setdefault("mcp", {})["server_name"] = server_name
        if host := os.getenv("MCP_HOST"):
            config_data.setdefault("mcp", {})["host"] = host
        if port := os.getenv("MCP_PORT"):
            config_data.setdefault("mcp", {})["port"] = int(port)
        if transport := os.getenv("MCP_TRANSPORT"):
            config_data.setdefault("mcp", {})["transport"] = transport
        
        # Security configuration
        if auth := os.getenv("MCP_AUTH_REQUIRED"):
            config_data.setdefault("security", {})["auth_required"] = auth.lower() == "true"
        if audit := os.getenv("MCP_AUDIT_LOG"):
            config_data.setdefault("security", {})["audit_log"] = audit.lower() == "true"
        
        # Logging configuration
        if log_level := os.getenv("MCP_LOG_LEVEL"):
            config_data.setdefault("logging", {})["level"] = log_level
        if log_file := os.getenv("MCP_LOG_FILE"):
            config_data.setdefault("logging", {})["file"] = log_file
        
        return cls(**config_data)

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "Config":
        """
        Load configuration from multiple sources with precedence:
        1. YAML file (if provided)
        2. Environment variables
        3. Default values
        """
        # Start with defaults
        config = cls()
        
        # Override with file configuration if provided
        if config_file:
            try:
                file_config = cls.from_yaml_file(config_file)
                config = file_config
            except FileNotFoundError:
                # If file doesn't exist, continue with defaults
                pass
        
        # Override with environment variables
        env_config = cls.from_env()
        config = cls(**{
            **config.dict(),
            **{k: v for k, v in env_config.dict().items() if v != cls().dict()[k]}
        })
        
        return config

    def to_yaml_file(self, file_path: str) -> None:
        """Save configuration to YAML file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(self.dict(), f, default_flow_style=False, indent=2)

    def validate_permissions(self) -> bool:
        """Validate that the configuration allows required operations."""
        required_ops = ["domain.list", "domain.info"]
        missing_ops = [op for op in required_ops if op not in self.security.allowed_operations]
        
        if missing_ops:
            raise ValueError(f"Missing required operations: {missing_ops}")
        
        return True
