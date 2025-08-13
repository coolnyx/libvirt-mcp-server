"""
测试新增功能的单元测试

测试范围：
- 虚拟机创建功能
- 虚拟机删除功能  
- 设备附加/分离功能
- XML模板生成器
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock, patch

from libvirt_mcp_server.libvirt_client import LibvirtClient
from libvirt_mcp_server.xml_templates import DomainXMLGenerator, DeviceXMLGenerator
from libvirt_mcp_server.models import DomainCreateParams
from libvirt_mcp_server.config import Config
from libvirt_mcp_server.exceptions import (
    LibvirtOperationError,
    LibvirtResourceNotFoundError,
    LibvirtPermissionError
)


@pytest.fixture
def mock_config():
    """创建模拟配置对象。"""
    config = MagicMock(spec=Config)
    config.libvirt.uri = "test:///default"
    config.libvirt.readonly = False
    config.security.allowed_operations = [
        "domain.create",
        "domain.delete", 
        "domain.attach_device",
        "domain.detach_device",
        "domain.getxml"
    ]
    return config


@pytest.fixture
def libvirt_client(mock_config):
    """创建 LibvirtClient 实例。"""
    return LibvirtClient(mock_config)


class TestDomainXMLGenerator:
    """测试虚拟机 XML 生成器。"""
    
    def test_generate_basic_domain_xml(self):
        """测试基本虚拟机 XML 生成。"""
        generator = DomainXMLGenerator()
        
        params = DomainCreateParams(
            name="test-vm",
            memory=2097152,  # 2GB
            vcpus=2,
            network="default"
        )
        
        xml = generator.generate(params)
        
        # 验证 XML 格式正确
        root = ET.fromstring(xml)
        assert root.tag == "domain"
        assert root.get("type") == "kvm"
        
        # 验证基本元素
        assert root.find("name").text == "test-vm"
        assert root.find("memory").text == "2097152"
        assert root.find("vcpu").text == "2"
        
        # 验证设备存在
        devices = root.find("devices")
        assert devices is not None
        assert devices.find("emulator") is not None
        assert devices.find("disk") is not None
        assert devices.find("interface") is not None
    
    def test_generate_domain_xml_with_custom_disk(self):
        """测试带自定义磁盘的虚拟机 XML 生成。"""
        generator = DomainXMLGenerator()
        
        params = DomainCreateParams(
            name="test-vm-disk",
            memory=1048576,
            vcpus=1,
            disk_path="/custom/path/disk.qcow2"
        )
        
        xml = generator.generate(params)
        root = ET.fromstring(xml)
        
        # 验证磁盘配置
        disk = root.find(".//disk[@device='disk']")
        assert disk is not None
        source = disk.find("source")
        assert source.get("file") == "/custom/path/disk.qcow2"


class TestDeviceXMLGenerator:
    """测试设备 XML 生成器。"""
    
    def test_generate_disk_device_xml(self):
        """测试磁盘设备 XML 生成。"""
        generator = DeviceXMLGenerator()
        
        xml = generator.generate_disk_device(
            disk_path="/var/lib/libvirt/images/test.qcow2",
            target_dev="vdb",
            bus="virtio"
        )
        
        root = ET.fromstring(xml)
        assert root.tag == "disk"
        assert root.get("type") == "file"
        assert root.get("device") == "disk"
        
        source = root.find("source")
        assert source.get("file") == "/var/lib/libvirt/images/test.qcow2"
        
        target = root.find("target")
        assert target.get("dev") == "vdb"
        assert target.get("bus") == "virtio"
    
    def test_generate_network_device_xml(self):
        """测试网络设备 XML 生成。"""
        generator = DeviceXMLGenerator()
        
        xml = generator.generate_network_device(
            network_name="bridge0",
            model="e1000"
        )
        
        root = ET.fromstring(xml)
        assert root.tag == "interface"
        assert root.get("type") == "network"
        
        source = root.find("source")
        assert source.get("network") == "bridge0"
        
        model = root.find("model")
        assert model.get("type") == "e1000"
        
        # 验证 MAC 地址格式
        mac = root.find("mac")
        mac_addr = mac.get("address")
        assert mac_addr.startswith("52:54:00:")
        assert len(mac_addr.split(":")) == 6
    
    def test_generate_usb_device_xml(self):
        """测试 USB 设备 XML 生成。"""
        generator = DeviceXMLGenerator()
        
        xml = generator.generate_usb_device(
            vendor_id="0x1234",
            product_id="0x5678"
        )
        
        root = ET.fromstring(xml)
        assert root.tag == "hostdev"
        assert root.get("mode") == "subsystem"
        assert root.get("type") == "usb"
        
        source = root.find("source")
        vendor = source.find("vendor")
        product = source.find("product")
        
        assert vendor.get("id") == "0x1234"
        assert product.get("id") == "0x5678"
    
    def test_generate_cdrom_device_xml(self):
        """测试 CD-ROM 设备 XML 生成。"""
        generator = DeviceXMLGenerator()
        
        xml = generator.generate_cdrom_device(
            iso_path="/var/lib/libvirt/images/ubuntu.iso",
            target_dev="hdc"
        )
        
        root = ET.fromstring(xml)
        assert root.tag == "disk"
        assert root.get("type") == "file"
        assert root.get("device") == "cdrom"
        
        source = root.find("source")
        assert source.get("file") == "/var/lib/libvirt/images/ubuntu.iso"
        
        target = root.find("target")
        assert target.get("dev") == "hdc"
        assert target.get("bus") == "ide"
        
        # 验证只读属性
        readonly = root.find("readonly")
        assert readonly is not None


class TestLibvirtClientNewFeatures:
    """测试 LibvirtClient 新功能。"""
    
    @pytest.mark.asyncio
    async def test_create_domain_xml_validation(self, libvirt_client):
        """测试创建虚拟机时的 XML 验证。"""
        with patch.object(libvirt_client, '_ensure_connected') as mock_conn:
            mock_conn.return_value = MagicMock()
            
            # 测试无效 XML
            with pytest.raises(LibvirtOperationError, match="Invalid XML format"):
                await libvirt_client.create_domain("invalid xml")
    
    @pytest.mark.asyncio
    async def test_create_domain_permission_check(self, libvirt_client):
        """测试创建虚拟机的权限检查。"""
        libvirt_client.config.security.allowed_operations = []
        
        with pytest.raises(LibvirtPermissionError, match="Operation not allowed"):
            await libvirt_client.create_domain("<domain></domain>")
    
    @pytest.mark.asyncio
    async def test_delete_domain_permission_check(self, libvirt_client):
        """测试删除虚拟机的权限检查。"""
        libvirt_client.config.security.allowed_operations = []
        
        with pytest.raises(LibvirtPermissionError, match="Operation not allowed"):
            await libvirt_client.delete_domain("test-vm")
    
    @pytest.mark.asyncio
    async def test_attach_device_xml_validation(self, libvirt_client):
        """测试附加设备时的 XML 验证。"""
        with patch.object(libvirt_client, '_ensure_connected') as mock_conn:
            mock_domain = MagicMock()
            mock_conn.return_value.lookupByName.return_value = mock_domain
            
            # 测试无效设备 XML
            with pytest.raises(LibvirtOperationError, match="Invalid device XML format"):
                await libvirt_client.attach_device("test-vm", "invalid device xml")
    
    @pytest.mark.asyncio
    async def test_detach_device_xml_validation(self, libvirt_client):
        """测试分离设备时的 XML 验证。"""
        with patch.object(libvirt_client, '_ensure_connected') as mock_conn:
            mock_domain = MagicMock()
            mock_conn.return_value.lookupByName.return_value = mock_domain
            
            # 测试无效设备 XML
            with pytest.raises(LibvirtOperationError, match="Invalid device XML format"):
                await libvirt_client.detach_device("test-vm", "invalid device xml")
    
    def test_generate_domain_xml_integration(self, libvirt_client):
        """测试虚拟机 XML 生成集成。"""
        params = DomainCreateParams(
            name="integration-test-vm",
            memory=1048576,
            vcpus=1
        )
        
        xml = libvirt_client.generate_domain_xml(params)
        
        # 验证生成的 XML 可以被解析
        root = ET.fromstring(xml)
        assert root.find("name").text == "integration-test-vm"


class TestParameterValidation:
    """测试参数验证。"""
    
    def test_domain_create_params_validation(self):
        """测试虚拟机创建参数验证。"""
        # 有效参数
        params = DomainCreateParams(
            name="valid-vm",
            memory=1048576,
            vcpus=2
        )
        assert params.name == "valid-vm"
        assert params.memory == 1048576
        assert params.vcpus == 2
        
        # 无效内存大小（小于最小值）
        with pytest.raises(ValueError):
            DomainCreateParams(
                name="invalid-vm",
                memory=512,  # 小于 1024 KB 最小值
                vcpus=1
            )
        
        # 无效 vCPU 数量（超过最大值）
        with pytest.raises(ValueError):
            DomainCreateParams(
                name="invalid-vm",
                memory=1048576,
                vcpus=256  # 超过 128 最大值
            )


@pytest.mark.integration
class TestIntegrationNewFeatures:
    """集成测试（需要真实的 libvirt 环境）。"""
    
    @pytest.mark.asyncio
    async def test_full_vm_lifecycle(self):
        """测试完整的虚拟机生命周期（创建 -> 操作 -> 删除）。"""
        # 这个测试需要真实的 libvirt 环境
        # 在 CI/CD 环境中可能需要跳过
        pytest.skip("需要真实的 libvirt 环境")
    
    @pytest.mark.asyncio  
    async def test_device_attach_detach_cycle(self):
        """测试设备附加和分离的完整周期。"""
        # 这个测试需要真实的 libvirt 环境
        # 在 CI/CD 环境中可能需要跳过
        pytest.skip("需要真实的 libvirt 环境")