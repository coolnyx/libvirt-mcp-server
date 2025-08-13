"""
XML template generator for libvirt domains and devices.

This module provides classes to generate standardized XML configurations
for virtual machines and devices, following libvirt best practices.
"""

import uuid
from typing import Dict, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .models import DomainCreateParams


class DomainXMLGenerator:
    """Generator for domain XML configurations."""
    
    def __init__(self):
        """Initialize the generator with default settings."""
        self.default_settings = {
            "emulator": "/usr/bin/qemu-system-x86_64",
            "machine_type": "pc-q35-6.2",
            "disk_bus": "virtio",
            "network_model": "virtio",
            "video_model": "qxl",
            "sound_model": "ich6",
        }
    
    def generate(self, params: DomainCreateParams) -> str:
        """Generate domain XML from parameters."""
        # Create root domain element
        domain = ET.Element("domain", type="kvm")
        
        # Basic domain information
        name = ET.SubElement(domain, "name")
        name.text = params.name
        
        uuid_elem = ET.SubElement(domain, "uuid")
        uuid_elem.text = str(uuid.uuid4())
        
        # Memory configuration
        memory = ET.SubElement(domain, "memory", unit="KiB")
        memory.text = str(params.memory)
        
        current_memory = ET.SubElement(domain, "currentMemory", unit="KiB")
        current_memory.text = str(params.memory)
        
        # vCPU configuration
        vcpu = ET.SubElement(domain, "vcpu", placement="static")
        vcpu.text = str(params.vcpus)
        
        # OS configuration
        os_elem = self._generate_os_config(params)
        domain.append(os_elem)
        
        # Features
        features = self._generate_features()
        domain.append(features)
        
        # CPU configuration
        cpu = self._generate_cpu_config(params)
        if cpu is not None:
            domain.append(cpu)
        
        # Clock configuration
        clock = self._generate_clock_config()
        domain.append(clock)
        
        # Power management
        pm = self._generate_pm_config()
        domain.append(pm)
        
        # Devices
        devices = self._generate_devices(params)
        domain.append(devices)
        
        return self._prettify_xml(domain)
    
    def _generate_os_config(self, params: DomainCreateParams) -> ET.Element:
        """Generate OS configuration."""
        os_elem = ET.Element("os")
        
        # Type
        type_elem = ET.SubElement(os_elem, "type", arch=params.arch, machine=self.default_settings["machine_type"])
        type_elem.text = params.os_type
        
        # Boot order
        boot = ET.SubElement(os_elem, "boot", dev=params.boot_device)
        
        return os_elem
    
    def _generate_features(self) -> ET.Element:
        """Generate features configuration."""
        features = ET.Element("features")
        
        # ACPI
        ET.SubElement(features, "acpi")
        
        # APIC
        ET.SubElement(features, "apic")
        
        # VMPort
        ET.SubElement(features, "vmport", state="off")
        
        return features
    
    def _generate_cpu_config(self, params: DomainCreateParams) -> Optional[ET.Element]:
        """Generate CPU configuration."""
        cpu = ET.Element("cpu", mode="host-model", check="partial")
        return cpu
    
    def _generate_clock_config(self) -> ET.Element:
        """Generate clock configuration."""
        clock = ET.Element("clock", offset="utc")
        
        # RTC timer
        rtc_timer = ET.SubElement(clock, "timer", name="rtc", tickpolicy="catchup")
        
        # PIT timer
        pit_timer = ET.SubElement(clock, "timer", name="pit", tickpolicy="delay")
        
        # HPET timer
        hpet_timer = ET.SubElement(clock, "timer", name="hpet", present="no")
        
        return clock
    
    def _generate_pm_config(self) -> ET.Element:
        """Generate power management configuration."""
        pm = ET.Element("pm")
        
        # Suspend to memory
        suspend_to_mem = ET.SubElement(pm, "suspend-to-mem", enabled="no")
        
        # Suspend to disk
        suspend_to_disk = ET.SubElement(pm, "suspend-to-disk", enabled="no")
        
        return pm
    
    def _generate_devices(self, params: DomainCreateParams) -> ET.Element:
        """Generate devices configuration."""
        devices = ET.Element("devices")
        
        # Emulator
        emulator = ET.SubElement(devices, "emulator")
        emulator.text = self.default_settings["emulator"]
        
        # Disk
        if params.disk_path or params.disk_size:
            disk = self._generate_disk_device(params)
            devices.append(disk)
        
        # Network interface
        interface = self._generate_network_device(params)
        devices.append(interface)
        
        # Console and input devices
        console = self._generate_console_device()
        devices.append(console)
        
        input_tablet = self._generate_input_device("tablet")
        devices.append(input_tablet)
        
        input_mouse = self._generate_input_device("mouse")
        devices.append(input_mouse)
        
        input_keyboard = self._generate_input_device("keyboard")
        devices.append(input_keyboard)
        
        # Graphics
        graphics = self._generate_graphics_device()
        devices.append(graphics)
        
        # Sound
        sound = self._generate_sound_device()
        devices.append(sound)
        
        # Video
        video = self._generate_video_device()
        devices.append(video)
        
        # Memory balloon
        memballoon = self._generate_memballoon_device()
        devices.append(memballoon)
        
        return devices
    
    def _generate_disk_device(self, params: DomainCreateParams) -> ET.Element:
        """Generate disk device configuration."""
        disk = ET.Element("disk", type="file", device="disk")
        
        # Driver
        driver = ET.SubElement(disk, "driver", name="qemu", type="qcow2")
        
        # Source
        if params.disk_path:
            source = ET.SubElement(disk, "source", file=params.disk_path)
        else:
            # Generate default disk path
            disk_path = f"/var/lib/libvirt/images/{params.name}.qcow2"
            source = ET.SubElement(disk, "source", file=disk_path)
        
        # Target
        target = ET.SubElement(disk, "target", dev="vda", bus=self.default_settings["disk_bus"])
        
        # Address
        address = ET.SubElement(disk, "address", type="pci", domain="0x0000", bus="0x04", slot="0x00", function="0x0")
        
        return disk
    
    def _generate_network_device(self, params: DomainCreateParams) -> ET.Element:
        """Generate network interface device configuration."""
        interface = ET.Element("interface", type="network")
        
        # MAC address (auto-generated)
        mac = ET.SubElement(interface, "mac", address=self._generate_mac_address())
        
        # Source network
        source = ET.SubElement(interface, "source", network=params.network or "default")
        
        # Model
        model = ET.SubElement(interface, "model", type=self.default_settings["network_model"])
        
        # Address
        address = ET.SubElement(interface, "address", type="pci", domain="0x0000", bus="0x01", slot="0x00", function="0x0")
        
        return interface
    
    def _generate_console_device(self) -> ET.Element:
        """Generate console device configuration."""
        console = ET.Element("console", type="pty")
        
        # Target
        target = ET.SubElement(console, "target", type="serial", port="0")
        
        return console
    
    def _generate_input_device(self, device_type: str) -> ET.Element:
        """Generate input device configuration."""
        input_dev = ET.Element("input", type=device_type, bus="ps2")
        return input_dev
    
    def _generate_graphics_device(self) -> ET.Element:
        """Generate graphics device configuration."""
        graphics = ET.Element("graphics", type="vnc", port="-1", autoport="yes")
        
        # Listen
        listen = ET.SubElement(graphics, "listen", type="address")
        
        return graphics
    
    def _generate_sound_device(self) -> ET.Element:
        """Generate sound device configuration."""
        sound = ET.Element("sound", model=self.default_settings["sound_model"])
        
        # Address
        address = ET.SubElement(sound, "address", type="pci", domain="0x0000", bus="0x00", slot="0x1b", function="0x0")
        
        return sound
    
    def _generate_video_device(self) -> ET.Element:
        """Generate video device configuration."""
        video = ET.Element("video")
        
        # Model
        model = ET.SubElement(video, "model", type=self.default_settings["video_model"], ram="65536", vram="65536", vgamem="16384", heads="1", primary="yes")
        
        # Address
        address = ET.SubElement(video, "address", type="pci", domain="0x0000", bus="0x00", slot="0x01", function="0x0")
        
        return video
    
    def _generate_memballoon_device(self) -> ET.Element:
        """Generate memory balloon device configuration."""
        memballoon = ET.Element("memballoon", model="virtio")
        
        # Address
        address = ET.SubElement(memballoon, "address", type="pci", domain="0x0000", bus="0x05", slot="0x00", function="0x0")
        
        return memballoon
    
    def _generate_mac_address(self) -> str:
        """Generate a random MAC address."""
        import random
        
        # Use QEMU/KVM OUI prefix
        mac = "52:54:00"
        
        for _ in range(3):
            mac += ":" + "{:02x}".format(random.randint(0, 255))
        
        return mac
    
    def _prettify_xml(self, element: ET.Element) -> str:
        """Pretty print XML with proper indentation."""
        rough_string = ET.tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")[23:]  # Remove XML declaration


class DeviceXMLGenerator:
    """Generator for device XML configurations."""
    
    def generate_disk_device(self, disk_path: str, target_dev: str = "vdb", bus: str = "virtio") -> str:
        """Generate disk device XML."""
        disk = ET.Element("disk", type="file", device="disk")
        
        # Driver
        driver = ET.SubElement(disk, "driver", name="qemu", type="qcow2")
        
        # Source
        source = ET.SubElement(disk, "source", file=disk_path)
        
        # Target
        target = ET.SubElement(disk, "target", dev=target_dev, bus=bus)
        
        return self._prettify_xml(disk)
    
    def generate_network_device(self, network_name: str = "default", model: str = "virtio") -> str:
        """Generate network interface device XML."""
        interface = ET.Element("interface", type="network")
        
        # MAC address (auto-generated)
        mac = ET.SubElement(interface, "mac", address=self._generate_mac_address())
        
        # Source network
        source = ET.SubElement(interface, "source", network=network_name)
        
        # Model
        model_elem = ET.SubElement(interface, "model", type=model)
        
        return self._prettify_xml(interface)
    
    def generate_usb_device(self, vendor_id: str, product_id: str) -> str:
        """Generate USB device XML."""
        hostdev = ET.Element("hostdev", mode="subsystem", type="usb", managed="yes")
        
        # Source
        source = ET.SubElement(hostdev, "source")
        vendor = ET.SubElement(source, "vendor", id=vendor_id)
        product = ET.SubElement(source, "product", id=product_id)
        
        return self._prettify_xml(hostdev)
    
    def generate_cdrom_device(self, iso_path: str, target_dev: str = "hdc") -> str:
        """Generate CD-ROM device XML."""
        disk = ET.Element("disk", type="file", device="cdrom")
        
        # Driver
        driver = ET.SubElement(disk, "driver", name="qemu", type="raw")
        
        # Source
        source = ET.SubElement(disk, "source", file=iso_path)
        
        # Target
        target = ET.SubElement(disk, "target", dev=target_dev, bus="ide")
        
        # Readonly
        readonly = ET.SubElement(disk, "readonly")
        
        return self._prettify_xml(disk)
    
    def _generate_mac_address(self) -> str:
        """Generate a random MAC address."""
        import random
        
        # Use QEMU/KVM OUI prefix
        mac = "52:54:00"
        
        for _ in range(3):
            mac += ":" + "{:02x}".format(random.randint(0, 255))
        
        return mac
    
    def _prettify_xml(self, element: ET.Element) -> str:
        """Pretty print XML with proper indentation."""
        rough_string = ET.tostring(element, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")[23:]  # Remove XML declaration