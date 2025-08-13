#!/usr/bin/env python3
"""
虚拟机生命周期管理示例

此示例展示如何使用 libvirt-mcp-server 的新功能来：
1. 创建虚拟机
2. 管理虚拟机设备
3. 删除虚拟机

使用前请确保：
- libvirt 服务正在运行
- 您有适当的权限访问 libvirt
- 配置文件中启用了相应的操作权限
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def demonstrate_vm_lifecycle():
    """演示完整的虚拟机生命周期管理。"""
    
    # 配置 MCP 客户端
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        env={"LIBVIRT_URI": "qemu:///system"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("🚀 连接到 libvirt MCP 服务器成功")
            
            # 1. 创建新虚拟机
            print("\n📦 创建新虚拟机...")
            vm_name = "test-mcp-vm"
            
            try:
                create_result = await session.call_tool("create_domain", {
                    "name": vm_name,
                    "memory": 1048576,  # 1GB in KB
                    "vcpus": 1,
                    "network": "default"
                })
                
                print(f"✅ 虚拟机创建结果: {create_result.content[0].text}")
                
            except Exception as e:
                print(f"❌ 创建虚拟机失败: {e}")
                return
            
            # 2. 获取虚拟机信息
            print(f"\n📊 获取虚拟机 {vm_name} 信息...")
            try:
                vm_info = await session.call_tool("domain_info", {"name": vm_name})
                print(f"ℹ️  虚拟机信息: {vm_info.content[0].text}")
            except Exception as e:
                print(f"❌ 获取虚拟机信息失败: {e}")
            
            # 3. 启动虚拟机
            print(f"\n▶️  启动虚拟机 {vm_name}...")
            try:
                start_result = await session.call_tool("start_domain", {"name": vm_name})
                print(f"✅ 启动结果: {start_result.content[0].text}")
            except Exception as e:
                print(f"❌ 启动虚拟机失败: {e}")
            
            # 4. 生成设备 XML 配置
            print("\n🔧 生成磁盘设备配置...")
            try:
                disk_xml = await session.call_tool("generate_device_xml", {
                    "device_type": "disk",
                    "disk_path": "/var/lib/libvirt/images/additional-disk.qcow2",
                    "target_dev": "vdb",
                    "bus": "virtio"
                })
                print(f"📝 磁盘设备 XML:\n{disk_xml.content[0].text}")
                
                # 5. 附加磁盘设备
                print(f"\n💽 向虚拟机 {vm_name} 附加磁盘...")
                attach_result = await session.call_tool("attach_device", {
                    "domain_name": vm_name,
                    "device_xml": disk_xml.content[0].text,
                    "live": False,  # 仅配置，不立即生效
                    "persistent": True
                })
                print(f"✅ 设备附加结果: {attach_result.content[0].text}")
                
            except Exception as e:
                print(f"❌ 设备操作失败: {e}")
            
            # 6. 生成网络设备配置
            print("\n🌐 生成网络设备配置...")
            try:
                network_xml = await session.call_tool("generate_device_xml", {
                    "device_type": "network",
                    "network_name": "default",
                    "model": "virtio"
                })
                print(f"📝 网络设备 XML:\n{network_xml.content[0].text}")
                
            except Exception as e:
                print(f"❌ 生成网络设备配置失败: {e}")
            
            # 7. 获取虚拟机 XML 配置
            print(f"\n📄 获取虚拟机 {vm_name} 的完整 XML 配置...")
            try:
                vm_xml = await session.call_tool("get_domain_xml", {"name": vm_name})
                print(f"📝 虚拟机 XML 配置已获取（{len(vm_xml.content[0].text)} 字符）")
                # 不打印完整 XML，因为太长
                
            except Exception as e:
                print(f"❌ 获取 XML 配置失败: {e}")
            
            # 8. 停止虚拟机
            print(f"\n⏹️  停止虚拟机 {vm_name}...")
            try:
                stop_result = await session.call_tool("stop_domain", {
                    "name": vm_name,
                    "force": True
                })
                print(f"✅ 停止结果: {stop_result.content[0].text}")
            except Exception as e:
                print(f"❌ 停止虚拟机失败: {e}")
            
            # 9. 清理：删除虚拟机
            print(f"\n🗑️  删除虚拟机 {vm_name}...")
            try:
                delete_result = await session.call_tool("delete_domain", {
                    "name": vm_name,
                    "remove_storage": True,  # 同时删除存储
                    "force": True
                })
                print(f"✅ 删除结果: {delete_result.content[0].text}")
            except Exception as e:
                print(f"❌ 删除虚拟机失败: {e}")
            
            print("\n🎉 虚拟机生命周期管理演示完成！")


async def demonstrate_device_management():
    """演示设备管理功能。"""
    
    print("\n" + "="*50)
    print("🔧 设备管理功能演示")
    print("="*50)
    
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        env={"LIBVIRT_URI": "qemu:///system"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 演示不同类型设备的 XML 生成
            device_types = [
                {
                    "type": "disk",
                    "params": {
                        "disk_path": "/var/lib/libvirt/images/data-disk.qcow2",
                        "target_dev": "vdc",
                        "bus": "virtio"
                    }
                },
                {
                    "type": "network",
                    "params": {
                        "network_name": "bridge0",
                        "model": "e1000"
                    }
                },
                {
                    "type": "cdrom",
                    "params": {
                        "iso_path": "/var/lib/libvirt/images/ubuntu-20.04.iso",
                        "target_dev": "hdc"
                    }
                },
                {
                    "type": "usb",
                    "params": {
                        "vendor_id": "0x1d6b",
                        "product_id": "0x0002"
                    }
                }
            ]
            
            for device in device_types:
                print(f"\n📝 生成 {device['type']} 设备配置...")
                try:
                    xml_result = await session.call_tool("generate_device_xml", {
                        "device_type": device["type"],
                        **device["params"]
                    })
                    print(f"✅ {device['type']} 设备 XML:")
                    print(xml_result.content[0].text)
                    print("-" * 40)
                    
                except Exception as e:
                    print(f"❌ 生成 {device['type']} 设备配置失败: {e}")


async def main():
    """主函数。"""
    print("🖥️  libvirt MCP 服务器新功能演示")
    print("="*60)
    
    try:
        # 演示虚拟机生命周期管理
        await demonstrate_vm_lifecycle()
        
        # 演示设备管理
        await demonstrate_device_management()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了演示")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print(__doc__)
    
    # 确认用户要继续
    input("\n按 Enter 键开始演示（确保 libvirt 服务正在运行）...")
    
    # 运行演示
    asyncio.run(main())