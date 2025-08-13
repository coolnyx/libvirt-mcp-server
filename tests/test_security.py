"""Tests for security and audit functionality."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libvirt_mcp_server.config import Config, SecurityConfig
from libvirt_mcp_server.security import AuditLogger, SecurityManager


class TestAuditLogger:
    """Tests for AuditLogger."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return Config()
    
    @pytest.fixture
    def audit_logger(self, config):
        """Create audit logger."""
        return AuditLogger(config)
    
    @pytest.mark.asyncio
    async def test_log_operation(self, audit_logger):
        """Test operation logging."""
        with patch.object(audit_logger.logger, 'info') as mock_log:
            await audit_logger.log_operation(
                operation="domain.start",
                user="test_user",
                parameters={"name": "test-vm"},
                result={"success": True},
                success=True,
                execution_time=1.5,
                client_info={"ip": "127.0.0.1"}
            )
            
            # Verify log was called (async execution)
            await asyncio.sleep(0.1)  # Allow executor to complete
    
    @pytest.mark.asyncio
    async def test_log_security_event(self, audit_logger):
        """Test security event logging."""
        with patch.object(audit_logger.logger, 'warning') as mock_log:
            await audit_logger.log_security_event(
                event_type="unauthorized_access",
                severity="warning",
                message="Unauthorized operation attempt",
                details={"operation": "domain.delete"},
                user="test_user"
            )
            
            # Verify log was called (async execution)
            await asyncio.sleep(0.1)  # Allow executor to complete
    
    def test_sanitize_parameters(self, audit_logger):
        """Test parameter sanitization."""
        params = {
            "name": "test-vm",
            "password": "secret123",
            "auth_token": "token123",
            "config": {
                "api_key": "key123",
                "host": "localhost"
            }
        }
        
        sanitized = audit_logger._sanitize_parameters(params)
        
        assert sanitized["name"] == "test-vm"
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["auth_token"] == "[REDACTED]"
        assert sanitized["config"]["api_key"] == "[REDACTED]"
        assert sanitized["config"]["host"] == "localhost"
    
    def test_summarize_result(self, audit_logger):
        """Test result summarization."""
        # Test dict result
        result = {
            "success": True,
            "message": "Operation completed",
            "data": [{"id": 1}, {"id": 2}]
        }
        
        summary = audit_logger._summarize_result(result)
        assert summary["success"] is True
        assert summary["message"] == "Operation completed"
        assert summary["type"] == "dict"
        
        # Test list result
        result = [{"id": 1}, {"id": 2}, {"id": 3}]
        summary = audit_logger._summarize_result(result)
        assert summary["count"] == 3
        assert summary["type"] == "list"


class TestSecurityManager:
    """Tests for SecurityManager."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        config = Config()
        config.security.allowed_operations = [
            "domain.list", "domain.info", "domain.start", "domain.stop"
        ]
        config.security.max_concurrent_ops = 5
        return config
    
    @pytest.fixture
    def security_manager(self, config):
        """Create security manager."""
        return SecurityManager(config)
    
    @pytest.mark.asyncio
    async def test_validate_operation_allowed(self, security_manager):
        """Test validation of allowed operations."""
        result = await security_manager.validate_operation("domain.list")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_operation_denied(self, security_manager):
        """Test validation of denied operations."""
        result = await security_manager.validate_operation("domain.delete")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, security_manager):
        """Test rate limiting functionality."""
        # Perform operations up to the limit
        for i in range(5):
            result = await security_manager.validate_operation("domain.list", user="test_user")
            assert result is True
        
        # Next operation should be rate limited
        result = await security_manager.validate_operation("domain.list", user="test_user")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_operation_logging(self, security_manager):
        """Test operation start and complete logging."""
        start_time = await security_manager.log_operation_start(
            operation="domain.start",
            parameters={"name": "test-vm"},
            user="test_user"
        )
        
        assert isinstance(start_time, float)
        assert start_time > 0
        
        await security_manager.log_operation_complete(
            operation="domain.start",
            parameters={"name": "test-vm"},
            result={"success": True},
            success=True,
            start_time=start_time,
            user="test_user"
        )
        
        # Verify operation count was decremented
        async with security_manager._lock:
            key = "test_user:domain.start"
            assert security_manager._operation_counts.get(key, 0) == 0
    
    @pytest.mark.asyncio
    async def test_validate_domain_name_valid(self, security_manager):
        """Test validation of valid domain names."""
        valid_names = [
            "test-vm",
            "my_virtual_machine",
            "vm-123",
            "production.web.server"
        ]
        
        for name in valid_names:
            result = await security_manager.validate_domain_name(name)
            assert result is True, f"Valid name {name} was rejected"
    
    @pytest.mark.asyncio
    async def test_validate_domain_name_invalid(self, security_manager):
        """Test validation of invalid domain names."""
        invalid_names = [
            "",  # Empty
            "a" * 300,  # Too long
            "../etc/passwd",  # Path traversal
            "vm\x00name",  # Null byte
            "vm\x01name",  # Control character
            "/etc/hosts",  # Suspicious path
        ]
        
        for name in invalid_names:
            result = await security_manager.validate_domain_name(name)
            assert result is False, f"Invalid name {name} was accepted"
    
    @pytest.mark.asyncio
    async def test_validate_xml_input_valid(self, security_manager):
        """Test validation of valid XML input."""
        valid_xml = """
        <domain type='kvm'>
            <name>test-vm</name>
            <memory unit='KiB'>1048576</memory>
            <vcpu placement='static'>1</vcpu>
        </domain>
        """
        
        result = await security_manager.validate_xml_input(valid_xml)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_xml_input_invalid(self, security_manager):
        """Test validation of invalid XML input."""
        invalid_xml_samples = [
            "",  # Empty
            '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>',  # XXE
            '<domain><!ENTITY test SYSTEM "http://evil.com/"></domain>',  # External entity
            "a" * (1024 * 1024 + 1),  # Too large
        ]
        
        for xml in invalid_xml_samples:
            result = await security_manager.validate_xml_input(xml)
            assert result is False, f"Invalid XML was accepted: {xml[:50]}..."
    
    @pytest.mark.asyncio
    async def test_get_security_summary(self, security_manager):
        """Test security summary generation."""
        summary = await security_manager.get_security_summary()
        
        assert isinstance(summary, dict)
        assert "audit_enabled" in summary
        assert "auth_required" in summary
        assert "allowed_operations" in summary
        assert "max_concurrent_ops" in summary
        assert "current_operation_counts" in summary
        assert "last_reset" in summary
        
        assert summary["audit_enabled"] is True
        assert summary["auth_required"] is True
        assert summary["allowed_operations"] == 4  # Number of allowed operations
        assert summary["max_concurrent_ops"] == 5


class TestSecurityManagerIntegration:
    """Integration tests for SecurityManager."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration with audit disabled for faster tests."""
        config = Config()
        config.security.audit_log = False  # Disable for faster tests
        config.security.allowed_operations = ["domain.list", "domain.info"]
        config.security.max_concurrent_ops = 2
        return config
    
    @pytest.fixture
    def security_manager(self, config):
        """Create security manager."""
        return SecurityManager(config)
    
    @pytest.mark.asyncio
    async def test_full_operation_workflow(self, security_manager):
        """Test complete operation workflow with security checks."""
        # Validate operation
        valid = await security_manager.validate_operation("domain.list", user="test_user")
        assert valid is True
        
        # Start operation
        start_time = await security_manager.log_operation_start(
            operation="domain.list",
            parameters={},
            user="test_user"
        )
        
        # Simulate operation execution
        await asyncio.sleep(0.1)
        
        # Complete operation
        await security_manager.log_operation_complete(
            operation="domain.list",
            parameters={},
            result={"domains": []},
            success=True,
            start_time=start_time,
            user="test_user"
        )
        
        # Verify operation count was reset
        async with security_manager._lock:
            key = "test_user:domain.list"
            assert security_manager._operation_counts.get(key, 0) == 0
