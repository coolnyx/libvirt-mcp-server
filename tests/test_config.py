"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from libvirt_mcp_server.config import (
    Config,
    LibvirtConfig,
    LoggingConfig,
    MCPConfig,
    SecurityConfig,
)


class TestLibvirtConfig:
    """Tests for LibvirtConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LibvirtConfig()
        assert config.uri == "qemu:///system"
        assert config.timeout == 30
        assert config.readonly is False
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = LibvirtConfig(
            uri="qemu:///system",
            timeout=60,
            readonly=True
        )
        assert config.uri == "qemu:///system"
        assert config.timeout == 60
        assert config.readonly is True
    
    def test_timeout_validation(self):
        """Test timeout validation."""
        with pytest.raises(ValidationError):
            LibvirtConfig(timeout=0)
        
        with pytest.raises(ValidationError):
            LibvirtConfig(timeout=500)


class TestMCPConfig:
    """Tests for MCPConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MCPConfig()
        assert config.server_name == "libvirt-manager"
        assert config.version == "1.0.0"
        assert config.host == "127.0.0.1"
        assert config.port == 8000
        assert config.transport == "stdio"
    
    def test_port_validation(self):
        """Test port validation."""
        with pytest.raises(ValidationError):
            MCPConfig(port=0)
        
        with pytest.raises(ValidationError):
            MCPConfig(port=70000)


class TestSecurityConfig:
    """Tests for SecurityConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = SecurityConfig()
        assert config.auth_required is True
        assert config.audit_log is True
        assert len(config.allowed_operations) > 0
        assert "domain.list" in config.allowed_operations
    
    def test_max_concurrent_ops_validation(self):
        """Test max concurrent operations validation."""
        with pytest.raises(ValidationError):
            SecurityConfig(max_concurrent_ops=0)
        
        with pytest.raises(ValidationError):
            SecurityConfig(max_concurrent_ops=200)


class TestLoggingConfig:
    """Tests for LoggingConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LoggingConfig()
        assert config.level == "INFO"
        assert config.file is None
        assert "%(asctime)s" in config.format
        assert config.max_size == 10485760
        assert config.backup_count == 5
    
    def test_log_level_validation(self):
        """Test log level validation."""
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"
        
        config = LoggingConfig(level="ERROR")
        assert config.level == "ERROR"
        
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID")


class TestConfig:
    """Tests for main Config class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        assert isinstance(config.libvirt, LibvirtConfig)
        assert isinstance(config.mcp, MCPConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)
    
    def test_from_yaml_file(self):
        """Test loading from YAML file."""
        config_data = {
            "libvirt": {"uri": "qemu:///system", "timeout": 60},
            "mcp": {"server_name": "test-server", "port": 9000},
            "security": {"auth_required": False},
            "logging": {"level": "DEBUG"}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = Config.from_yaml_file(temp_path)
            assert config.libvirt.uri == "qemu:///system"
            assert config.libvirt.timeout == 60
            assert config.mcp.server_name == "test-server"
            assert config.mcp.port == 9000
            assert config.security.auth_required is False
            assert config.logging.level == "DEBUG"
        finally:
            os.unlink(temp_path)
    
    def test_from_yaml_file_not_found(self):
        """Test loading from non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            Config.from_yaml_file("/nonexistent/config.yaml")
    
    def test_from_env(self):
        """Test loading from environment variables."""
        env_vars = {
            "LIBVIRT_URI": "qemu:///system",
            "LIBVIRT_TIMEOUT": "45",
            "LIBVIRT_READONLY": "true",
            "MCP_SERVER_NAME": "env-server",
            "MCP_HOST": "0.0.0.0",
            "MCP_PORT": "8080",
            "MCP_TRANSPORT": "http",
            "MCP_AUTH_REQUIRED": "false",
            "MCP_AUDIT_LOG": "true",
            "MCP_LOG_LEVEL": "WARNING",
            "MCP_LOG_FILE": "/tmp/test.log"
        }
        
        # Set environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        
        try:
            config = Config.from_env()
            assert config.libvirt.uri == "qemu:///system"
            assert config.libvirt.timeout == 45
            assert config.libvirt.readonly is True
            assert config.mcp.server_name == "env-server"
            assert config.mcp.host == "0.0.0.0"
            assert config.mcp.port == 8080
            assert config.mcp.transport == "http"
            assert config.security.auth_required is False
            assert config.security.audit_log is True
            assert config.logging.level == "WARNING"
            assert config.logging.file == "/tmp/test.log"
        finally:
            # Clean up environment variables
            for key in env_vars:
                os.environ.pop(key, None)
    
    def test_load_with_file_and_env(self):
        """Test loading with both file and environment variables."""
        config_data = {
            "libvirt": {"uri": "qemu:///system", "timeout": 30},
            "mcp": {"server_name": "file-server", "port": 8000},
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        # Set environment variable that should override file
        os.environ["MCP_SERVER_NAME"] = "env-server"
        os.environ["MCP_PORT"] = "9000"
        
        try:
            config = Config.load(temp_path)
            assert config.libvirt.uri == "qemu:///system"  # From file
            assert config.mcp.server_name == "env-server"  # From env (override)
            assert config.mcp.port == 9000  # From env (override)
        finally:
            os.unlink(temp_path)
            os.environ.pop("MCP_SERVER_NAME", None)
            os.environ.pop("MCP_PORT", None)
    
    def test_to_yaml_file(self):
        """Test saving to YAML file."""
        config = Config()
        config.libvirt.uri = "qemu:///system"
        config.mcp.server_name = "test-server"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            config.to_yaml_file(temp_path)
            
            # Load and verify
            with open(temp_path, 'r') as f:
                data = yaml.safe_load(f)
            
            assert data["libvirt"]["uri"] == "qemu:///system"
            assert data["mcp"]["server_name"] == "test-server"
        finally:
            os.unlink(temp_path)
    
    def test_validate_permissions(self):
        """Test permissions validation."""
        # Valid config should pass
        config = Config()
        assert config.validate_permissions() is True
        
        # Config missing required operations should fail
        config.security.allowed_operations = ["domain.start"]
        with pytest.raises(ValueError, match="Missing required operations"):
            config.validate_permissions()
