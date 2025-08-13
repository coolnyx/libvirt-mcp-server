"""
Security and audit logging for libvirt-mcp-server.

This module provides security controls, audit logging, and access validation
to ensure safe operation of the libvirt MCP server.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .logging import get_logger
from .config import Config


class AuditLogger:
    """
    Audit logger for tracking all operations and security events.
    
    This logger records all operations, their parameters, results,
    and security-relevant events for compliance and debugging.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger("libvirt_mcp_server.audit")
    
    async def log_operation(
        self,
        operation: str,
        user: Optional[str],
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool,
        execution_time: float,
        client_info: Optional[Dict[str, str]] = None
    ) -> None:
        """Log an operation with full details."""
        if not self.config.security.audit_log:
            return
        
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_log_operation,
            operation,
            user,
            parameters,
            result,
            success,
            execution_time,
            client_info,
        )
    
    def _sync_log_operation(
        self,
        operation: str,
        user: Optional[str],
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool,
        execution_time: float,
        client_info: Optional[Dict[str, str]],
    ) -> None:
        """Synchronous operation logging."""
        self.logger.info(
            "operation_executed",
            operation=operation,
            user=user or "anonymous",
            parameters=self._sanitize_parameters(parameters),
            result_summary=self._summarize_result(result),
            success=success,
            execution_time=execution_time,
            timestamp=time.time(),
            client_info=client_info or {},
        )
    
    async def log_security_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any],
        user: Optional[str] = None,
        client_info: Optional[Dict[str, str]] = None
    ) -> None:
        """Log a security-related event."""
        await asyncio.get_event_loop().run_in_executor(
            None,
            self._sync_log_security_event,
            event_type,
            severity,
            message,
            details,
            user,
            client_info,
        )
    
    def _sync_log_security_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Dict[str, Any],
        user: Optional[str],
        client_info: Optional[Dict[str, str]],
    ) -> None:
        """Synchronous security event logging."""
        log_func = getattr(self.logger, severity.lower(), self.logger.info)
        log_func(
            "security_event",
            event_type=event_type,
            message=message,
            details=details,
            user=user or "anonymous",
            timestamp=time.time(),
            client_info=client_info or {},
        )
    
    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from parameters before logging."""
        sanitized = {}
        sensitive_keys = {"password", "secret", "token", "key", "auth"}
        
        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_parameters(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _summarize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of the result for logging."""
        summary = {}
        
        if isinstance(result, dict):
            # Include success status and message if present
            if "success" in result:
                summary["success"] = result["success"]
            if "message" in result:
                summary["message"] = result["message"]
            
            # Include count for list results
            if isinstance(result.get("data"), list):
                summary["count"] = len(result["data"])
            elif isinstance(result, list):
                summary["count"] = len(result)
            
            # Include basic type information
            summary["type"] = type(result).__name__
        
        return summary


class SecurityManager:
    """
    Security manager for access control and operation validation.
    
    This manager enforces security policies, validates operations,
    and maintains security state for the MCP server.
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.audit = AuditLogger(config)
        self._operation_counts: Dict[str, int] = {}
        self._last_reset = time.time()
        self._lock = asyncio.Lock()
    
    async def validate_operation(
        self,
        operation: str,
        user: Optional[str] = None,
        client_info: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Validate if an operation is allowed.
        
        Args:
            operation: Operation name (e.g., 'domain.start')
            user: User identifier
            client_info: Client information
        
        Returns:
            True if operation is allowed, False otherwise
        
        Raises:
            SecurityError: If operation is denied
        """
        async with self._lock:
            # Check if operation is in allowed list
            if operation not in self.config.security.allowed_operations:
                await self.audit.log_security_event(
                    event_type="operation_denied",
                    severity="warning",
                    message=f"Operation {operation} not in allowed operations",
                    details={"operation": operation, "allowed": self.config.security.allowed_operations},
                    user=user,
                    client_info=client_info,
                )
                return False
            
            # Check rate limiting
            if not await self._check_rate_limit(operation, user, client_info):
                return False
            
            await self.audit.log_security_event(
                event_type="operation_authorized",
                severity="info",
                message=f"Operation {operation} authorized",
                details={"operation": operation},
                user=user,
                client_info=client_info,
            )
            
            return True
    
    async def _check_rate_limit(
        self,
        operation: str,
        user: Optional[str],
        client_info: Optional[Dict[str, str]]
    ) -> bool:
        """Check if operation is within rate limits."""
        current_time = time.time()
        
        # Reset counters every minute
        if current_time - self._last_reset > 60:
            self._operation_counts.clear()
            self._last_reset = current_time
        
        # Count operations per user/operation combination
        key = f"{user or 'anonymous'}:{operation}"
        current_count = self._operation_counts.get(key, 0)
        
        if current_count >= self.config.security.max_concurrent_ops:
            await self.audit.log_security_event(
                event_type="rate_limit_exceeded",
                severity="warning",
                message=f"Rate limit exceeded for {operation}",
                details={
                    "operation": operation,
                    "current_count": current_count,
                    "limit": self.config.security.max_concurrent_ops,
                },
                user=user,
                client_info=client_info,
            )
            return False
        
        self._operation_counts[key] = current_count + 1
        return True
    
    async def log_operation_start(
        self,
        operation: str,
        parameters: Dict[str, Any],
        user: Optional[str] = None,
        client_info: Optional[Dict[str, str]] = None
    ) -> float:
        """Log the start of an operation and return start time."""
        start_time = time.time()
        
        await self.audit.log_security_event(
            event_type="operation_started",
            severity="debug",
            message=f"Operation {operation} started",
            details={
                "operation": operation,
                "parameters": parameters,
                "start_time": start_time,
            },
            user=user,
            client_info=client_info,
        )
        
        return start_time
    
    async def log_operation_complete(
        self,
        operation: str,
        parameters: Dict[str, Any],
        result: Dict[str, Any],
        success: bool,
        start_time: float,
        user: Optional[str] = None,
        client_info: Optional[Dict[str, str]] = None
    ) -> None:
        """Log the completion of an operation."""
        execution_time = time.time() - start_time
        
        await self.audit.log_operation(
            operation=operation,
            user=user,
            parameters=parameters,
            result=result,
            success=success,
            execution_time=execution_time,
            client_info=client_info,
        )
        
        # Decrement operation count
        async with self._lock:
            key = f"{user or 'anonymous'}:{operation}"
            if key in self._operation_counts:
                self._operation_counts[key] = max(0, self._operation_counts[key] - 1)
    
    async def validate_domain_name(self, domain_name: str) -> bool:
        """
        Validate domain name for security.
        
        Args:
            domain_name: Domain name to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Basic validation rules
        if not domain_name:
            return False
        
        # Check length
        if len(domain_name) > 255:
            return False
        
        # Check for path traversal attempts
        dangerous_patterns = ["../", "..\\", "/etc/", "/proc/", "/sys/", "\\windows\\"]
        domain_lower = domain_name.lower()
        
        for pattern in dangerous_patterns:
            if pattern in domain_lower:
                await self.audit.log_security_event(
                    event_type="suspicious_domain_name",
                    severity="warning",
                    message=f"Suspicious domain name pattern detected: {domain_name}",
                    details={"domain_name": domain_name, "pattern": pattern},
                )
                return False
        
        # Check for null bytes and control characters
        if any(ord(c) < 32 for c in domain_name if c not in "\t\n\r"):
            await self.audit.log_security_event(
                event_type="invalid_domain_name",
                severity="warning",
                message=f"Domain name contains control characters: {domain_name}",
                details={"domain_name": domain_name},
            )
            return False
        
        return True
    
    async def validate_xml_input(self, xml_content: str) -> bool:
        """
        Validate XML input for security issues.
        
        Args:
            xml_content: XML content to validate
        
        Returns:
            True if safe, False otherwise
        """
        if not xml_content:
            return False
        
        # Check for XXE (XML External Entity) attacks
        dangerous_xml_patterns = [
            "<!ENTITY",
            "<!DOCTYPE",
            "SYSTEM",
            "PUBLIC",
            "file://",
            "http://",
            "https://",
            "ftp://",
        ]
        
        xml_upper = xml_content.upper()
        for pattern in dangerous_xml_patterns:
            if pattern in xml_upper:
                await self.audit.log_security_event(
                    event_type="suspicious_xml_content",
                    severity="error",
                    message=f"Suspicious XML pattern detected: {pattern}",
                    details={"pattern": pattern, "content_length": len(xml_content)},
                )
                return False
        
        # Check size limits
        if len(xml_content) > 1024 * 1024:  # 1MB limit
            await self.audit.log_security_event(
                event_type="xml_size_limit_exceeded",
                severity="warning",
                message="XML content exceeds size limit",
                details={"content_length": len(xml_content), "limit": 1024 * 1024},
            )
            return False
        
        return True
    
    async def get_security_summary(self) -> Dict[str, Any]:
        """Get current security status summary."""
        async with self._lock:
            return {
                "audit_enabled": self.config.security.audit_log,
                "auth_required": self.config.security.auth_required,
                "allowed_operations": len(self.config.security.allowed_operations),
                "max_concurrent_ops": self.config.security.max_concurrent_ops,
                "current_operation_counts": dict(self._operation_counts),
                "last_reset": self._last_reset,
            }
