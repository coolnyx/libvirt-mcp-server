# libvirt-mcp-server

一个基于Model Context Protocol (MCP) 的libvirt虚拟化管理服务器，允许AI模型安全、可控地查询和管理虚拟机资源。

## 🚀 特性

- **完整的虚拟机生命周期管理**：创建、启动、停止、监控、删除虚拟机
- **资源管理**：查询和配置CPU、内存、存储、网络资源
- **安全访问控制**：基于角色的权限管理和操作审计
- **实时监控**：虚拟机状态、性能指标、事件通知
- **标准化接口**：基于MCP协议的RESTful API和工具集
- **多种部署方式**：支持stdio、HTTP、Docker等多种运行模式

## 📋 要求

- Python 3.11+
- libvirt 系统库
- QEMU/KVM 或其他libvirt支持的虚拟化平台
- 适当的系统权限访问libvirt守护进程

## 🛠 安装

### 使用 uv（推荐）

```bash
# 克隆仓库
git clone https://github.com/your-org/libvirt-mcp-server.git
cd libvirt-mcp-server

# 安装依赖
uv sync

# 运行服务器
uv run libvirt-mcp-server start
```

### 使用 Docker

```bash
docker run -d \
  --name libvirt-mcp \
  --privileged \
  -v /var/run/libvirt:/var/run/libvirt \
  -p 8000:8000 \
  libvirt-mcp-server:latest
```

## 🔧 配置

### 生成示例配置

```bash
# 生成完整的示例配置文件
uv run libvirt-mcp-server generate-config --output config.yaml

# 验证配置文件
uv run libvirt-mcp-server validate-config --config config.yaml
```

### 完整配置示例

创建 `config.yaml` 文件：

```yaml
# libvirt 虚拟化连接配置
libvirt:
  uri: "qemu:///system"      # libvirt连接URI
  timeout: 30               # 连接超时时间（秒）
  readonly: false           # 是否使用只读连接

# MCP 服务器配置
mcp:
  server_name: "libvirt-manager"    # MCP服务器名称
  version: "1.0.0"                 # 服务器版本
  host: "127.0.0.1"                # 绑定地址
  port: 8000                       # 监听端口
  transport: "stdio"               # 传输协议: stdio, http, sse

# 安全和访问控制配置
security:
  auth_required: true              # 是否需要认证
  audit_log: true                  # 启用审计日志
  max_concurrent_ops: 10           # 最大并发操作数
  allowed_operations:              # 允许的操作列表
    - "domain.list"
    - "domain.info"
    - "domain.start"
    - "domain.stop"
    - "domain.reboot"
    - "domain.stats"
    - "host.info"
    - "network.list"
    - "storage.list"

# 日志配置
logging:
  level: "INFO"                    # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: null                       # 日志文件路径 (null表示仅控制台输出)
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  max_size: 10485760              # 最大日志文件大小 (10MB)
  backup_count: 5                 # 日志文件备份数量
```

### 多种传输协议配置

#### 1. STDIO 传输（推荐用于AI客户端）

```yaml
mcp:
  transport: "stdio"
```

启动服务器：
```bash
uv run libvirt-mcp-server start --transport stdio
```

#### 2. HTTP 传输（用于Web应用）

```yaml
mcp:
  transport: "http"
  host: "0.0.0.0"
  port: 8000
```

启动服务器：
```bash
uv run libvirt-mcp-server start --transport http --host 0.0.0.0 --port 8000
```

#### 3. Server-Sent Events (SSE) 传输

```yaml
mcp:
  transport: "sse"
  host: "127.0.0.1"
  port: 8080
```

### 环境变量配置

可以通过环境变量覆盖配置文件设置：

```bash
# libvirt 配置
export LIBVIRT_URI="qemu:///system"
export LIBVIRT_TIMEOUT=30
export LIBVIRT_READONLY=false

# MCP 服务器配置
export MCP_SERVER_NAME="libvirt-manager"
export MCP_HOST="127.0.0.1"
export MCP_PORT=8000
export MCP_TRANSPORT="stdio"

# 安全配置
export MCP_AUTH_REQUIRED=true
export MCP_AUDIT_LOG=true

# 日志配置
export MCP_LOG_LEVEL=INFO
export MCP_LOG_FILE="/var/log/libvirt-mcp-server.log"
```

### 不同环境的配置示例

#### 开发环境配置

```yaml
libvirt:
  uri: "test:///default"           # 使用测试驱动
  readonly: false

mcp:
  transport: "stdio"
  
security:
  auth_required: false             # 开发环境可禁用认证
  audit_log: false
  allowed_operations:              # 开发环境允许更多操作
    - "domain.*"                   # 允许所有domain操作
    - "host.*"
    - "network.*"
    - "storage.*"

logging:
  level: "DEBUG"                   # 详细日志
  file: "logs/debug.log"
```

#### 生产环境配置

```yaml
libvirt:
  uri: "qemu:///system"
  readonly: false
  timeout: 60                      # 更长的超时时间

mcp:
  transport: "http"
  host: "127.0.0.1"               # 仅本地访问
  port: 8000

security:
  auth_required: true              # 必须认证
  audit_log: true                  # 启用审计
  max_concurrent_ops: 5            # 限制并发操作
  allowed_operations:              # 严格限制操作
    - "domain.list"
    - "domain.info"
    - "domain.stats"
    - "host.info"

logging:
  level: "WARNING"                 # 仅记录警告和错误
  file: "/var/log/libvirt-mcp-server.log"
  max_size: 52428800              # 50MB
  backup_count: 10
```

#### 只读监控配置

```yaml
libvirt:
  uri: "qemu:///system"
  readonly: true                   # 只读连接

security:
  allowed_operations:              # 仅允许查询操作
    - "domain.list"
    - "domain.info"
    - "domain.stats"
    - "host.info"
    - "network.list"
    - "storage.list"
```

## 🔧 MCP工具列表

### 虚拟机管理工具

| 工具名称 | 描述 | 参数 | 返回值 |
|---------|------|------|--------|
| `list_domains` | 列出所有虚拟机 | `state`: running/stopped/all | 虚拟机列表 |
| `domain_info` | 获取虚拟机详细信息 | `name`: 虚拟机名称 | 虚拟机状态、资源配置 |
| `start_domain` | 启动虚拟机 | `name`: 虚拟机名称 | 操作结果 |
| `stop_domain` | 停止虚拟机 | `name`: 虚拟机名称, `force`: 强制关闭 | 操作结果 |
| `reboot_domain` | 重启虚拟机 | `name`: 虚拟机名称 | 操作结果 |
| `create_domain` | 创建虚拟机 | `name`, `memory`, `vcpus`, `disk_path`, `network`, `xml` 等 | 创建结果 |
| `delete_domain` | 删除虚拟机 | `name`: 虚拟机名称, `remove_storage`: 删除存储, `force`: 强制删除 | 删除结果 |

### 资源监控工具

| 工具名称 | 描述 | 参数 | 返回值 |
|---------|------|------|--------|
| `domain_stats` | 获取虚拟机性能统计 | `name`: 虚拟机名称 | CPU、内存、磁盘、网络统计 |
| `host_info` | 获取主机系统信息 | 无 | 主机CPU、内存、存储信息 |
| `list_networks` | 列出虚拟网络 | 无 | 网络列表和配置 |
| `list_storage_pools` | 列出存储池 | 无 | 存储池信息 |

### 配置管理工具

| 工具名称 | 描述 | 参数 | 返回值 |
|---------|------|------|--------|
| `get_domain_xml` | 获取虚拟机XML配置 | `name`: 虚拟机名称 | XML配置文件 |
| `update_domain_config` | 更新虚拟机配置 | `name`: 虚拟机名称, `xml`: 新配置 | 更新结果 |
| `attach_device` | 附加设备到虚拟机 | `domain_name`: 虚拟机名称, `device_xml`: 设备配置, `live`: 实时操作, `persistent`: 持久化 | 操作结果 |
| `detach_device` | 从虚拟机分离设备 | `domain_name`: 虚拟机名称, `device_xml`: 设备配置, `live`: 实时操作, `persistent`: 持久化 | 操作结果 |
| `generate_device_xml` | 生成设备XML配置 | `device_type`: 设备类型 (disk/network/usb/cdrom), 设备参数 | 设备XML |

## 🔗 MCP 客户端配置

### Claude Desktop 配置

在 Claude Desktop 的配置文件中添加 libvirt MCP 服务器：

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "libvirt-manager": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/libvirt-mcp-server", "libvirt-mcp-server", "start", "--transport", "stdio"],
      "env": {
        "LIBVIRT_URI": "qemu:///system"
      }
    }
  }
}
```

### 使用配置文件的客户端配置

```json
{
  "mcpServers": {
    "libvirt-production": {
      "command": "uv",
      "args": [
        "run", "libvirt-mcp-server", "start", 
        "--config", "/path/to/production-config.yaml",
        "--transport", "stdio"
      ]
    },
    "libvirt-readonly": {
      "command": "uv", 
      "args": [
        "run", "libvirt-mcp-server", "start",
        "--readonly",
        "--transport", "stdio"
      ],
      "env": {
        "MCP_LOG_LEVEL": "WARNING"
      }
    }
  }
}
```

### Cline (VSCode 扩展) 配置

在 VSCode 的 Cline 扩展设置中添加：

```json
{
  "cline.mcp.servers": [
    {
      "name": "libvirt-manager",
      "command": "uv",
      "args": ["run", "libvirt-mcp-server", "start"],
      "env": {
        "LIBVIRT_URI": "qemu:///system",
        "MCP_LOG_LEVEL": "INFO"
      }
    }
  ]
}
```

### Python MCP 客户端配置

#### 基础 STDIO 客户端

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def connect_to_libvirt_mcp():
    # 基础配置
    server_params = StdioServerParameters(
        command="uv",
        args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"],
        env={"LIBVIRT_URI": "qemu:///system"}
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 获取服务器信息
            server_info = await session.get_server_version()
            print(f"Connected to: {server_info}")
            
            # 列出可用工具
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            return session
```

#### 带配置文件的客户端

```python
server_params = StdioServerParameters(
    command="uv",
    args=[
        "run", "libvirt-mcp-server", "start",
        "--config", "/path/to/config.yaml",
        "--transport", "stdio"
    ]
)
```

#### HTTP 客户端配置

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.http import HttpClientTransport

async def connect_via_http():
    transport = HttpClientTransport("http://localhost:8000")
    
    async with ClientSession(transport) as session:
        await session.initialize()
        
        # 使用HTTP连接的客户端
        result = await session.call_tool("list_domains", {"state": "all"})
        return result
```

### 配置验证和故障排除

```bash
# 验证libvirt连接
uv run libvirt-mcp-server check-libvirt --uri qemu:///system

# 验证配置文件
uv run libvirt-mcp-server validate-config --config config.yaml

# 检查系统信息
uv run libvirt-mcp-server info

# 以调试模式启动服务器
uv run libvirt-mcp-server start --log-level DEBUG
```

## 📚 使用示例

### 快速开始示例

```python
import asyncio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def quick_vm_check():
    """快速检查虚拟机状态"""
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "libvirt-mcp-server", "start"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 获取主机信息
            host_info = await session.call_tool("host_info", {})
            print(f"主机信息: {host_info.content[0].text}")
            
            # 列出所有虚拟机
            domains = await session.call_tool("list_domains", {"state": "all"})
            print(f"虚拟机列表: {domains.content[0].text}")
            
            # 列出网络
            networks = await session.call_tool("list_networks", {})
            print(f"虚拟网络: {networks.content[0].text}")

asyncio.run(quick_vm_check())
```

### 虚拟机管理示例

#### 1. 创建和管理虚拟机

```python
async def create_and_manage_vm():
    """创建和管理虚拟机示例"""
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "libvirt-mcp-server", "start"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            vm_name = "my-new-vm"
            
            # 1. 创建新虚拟机
            print("创建虚拟机...")
            create_result = await session.call_tool("create_domain", {
                "name": vm_name,
                "memory": 2097152,  # 2GB in KB
                "vcpus": 2,
                "disk_path": "/var/lib/libvirt/images/my-vm.qcow2",
                "network": "default"
            })
            print(f"创建结果: {create_result.content[0].text}")
            
            # 2. 启动虚拟机
            start_result = await session.call_tool("start_domain", {"name": vm_name})
            print(f"启动结果: {start_result.content[0].text}")
            
            # 3. 获取虚拟机信息
            vm_info = await session.call_tool("domain_info", {"name": vm_name})
            print(f"虚拟机信息: {vm_info.content[0].text}")
            
            # 4. 获取性能统计
            stats = await session.call_tool("domain_stats", {"name": vm_name})
            print(f"性能统计: {stats.content[0].text}")
            
            # 5. 停止并删除虚拟机
            await session.call_tool("stop_domain", {"name": vm_name, "force": True})
            delete_result = await session.call_tool("delete_domain", {
                "name": vm_name,
                "remove_storage": True,
                "force": True
            })
            print(f"删除结果: {delete_result.content[0].text}")
```

#### 2. 设备管理示例

```python
async def manage_vm_devices():
    """虚拟机设备管理示例"""
    server_params = StdioServerParameters(
        command="uv", 
        args=["run", "libvirt-mcp-server", "start"]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            vm_name = "existing-vm"
            
            # 1. 生成磁盘设备配置
            disk_xml = await session.call_tool("generate_device_xml", {
                "device_type": "disk",
                "disk_path": "/var/lib/libvirt/images/additional-disk.qcow2",
                "target_dev": "vdb",
                "bus": "virtio"
            })
            print(f"磁盘配置: {disk_xml.content[0].text}")
            
            # 2. 附加磁盘到虚拟机
            attach_result = await session.call_tool("attach_device", {
                "domain_name": vm_name,
                "device_xml": disk_xml.content[0].text,
                "live": True,
                "persistent": True
            })
            print(f"附加结果: {attach_result.content[0].text}")
            
            # 3. 生成网络设备配置
            network_xml = await session.call_tool("generate_device_xml", {
                "device_type": "network",
                "network_name": "bridge0",
                "model": "e1000"
            })
            
            # 4. 后续分离设备
            detach_result = await session.call_tool("detach_device", {
                "domain_name": vm_name,
                "device_xml": disk_xml.content[0].text,
                "live": True,
                "persistent": True
            })
            print(f"分离结果: {detach_result.content[0].text}")
```

#### 3. 使用自定义XML创建虚拟机

```python
async def create_vm_with_custom_xml():
    """使用自定义XML创建虚拟机"""
    
    custom_xml = """
    <domain type='kvm'>
        <name>custom-vm</name>
        <memory unit='KiB'>1048576</memory>
        <vcpu placement='static'>1</vcpu>
        <os>
            <type arch='x86_64' machine='pc-q35-6.2'>hvm</type>
            <boot dev='hd'/>
        </os>
        <devices>
            <emulator>/usr/bin/qemu-system-x86_64</emulator>
            <disk type='file' device='disk'>
                <driver name='qemu' type='qcow2'/>
                <source file='/var/lib/libvirt/images/custom-vm.qcow2'/>
                <target dev='vda' bus='virtio'/>
            </disk>
            <interface type='network'>
                <source network='default'/>
                <model type='virtio'/>
            </interface>
        </devices>
    </domain>
    """
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # 使用自定义XML创建虚拟机
            create_result = await session.call_tool("create_domain", {
                "xml": custom_xml,
                "ephemeral": False  # 创建持久化虚拟机
            })
            print(f"创建结果: {create_result.content[0].text}")
```

### 命令行使用

```bash
# 启动MCP服务器（stdio模式，推荐用于AI客户端）
uv run libvirt-mcp-server start --transport stdio

# 启动MCP服务器（HTTP模式，用于Web应用）
uv run libvirt-mcp-server start --transport http --host 0.0.0.0 --port 8000

# 使用特定配置文件启动
uv run libvirt-mcp-server start --config /path/to/config.yaml

# 只读模式启动（仅允许查询操作）
uv run libvirt-mcp-server start --readonly --libvirt-uri qemu:///system

# 调试模式启动
uv run libvirt-mcp-server start --log-level DEBUG --no-audit

# 连接到远程libvirt主机
uv run libvirt-mcp-server start --libvirt-uri qemu+ssh://user@remote-host/system
```

## 🎯 部署配置示例

### 本地开发环境

```yaml
# dev-config.yaml
libvirt:
  uri: "test:///default"  # 使用测试驱动，无需真实虚拟机
  readonly: false

mcp:
  transport: "stdio"
  
security:
  auth_required: false
  audit_log: false
  allowed_operations: ["*"]  # 开发环境允许所有操作

logging:
  level: "DEBUG"
  file: "logs/dev.log"
```

启动命令：
```bash
uv run libvirt-mcp-server start --config dev-config.yaml
```

### 生产环境只读监控

```yaml
# production-readonly.yaml
libvirt:
  uri: "qemu:///system"
  readonly: true  # 强制只读
  timeout: 60

mcp:
  transport: "http"
  host: "127.0.0.1"  # 仅本地访问
  port: 8000

security:
  auth_required: true
  audit_log: true
  max_concurrent_ops: 3
  allowed_operations:
    - "domain.list"
    - "domain.info"
    - "domain.stats"
    - "host.info"
    - "network.list"
    - "storage.list"

logging:
  level: "WARNING"
  file: "/var/log/libvirt-mcp-readonly.log"
  max_size: 104857600  # 100MB
  backup_count: 5
```

### 集群管理配置

```yaml
# cluster-config.yaml
libvirt:
  uri: "qemu+tcp://cluster-manager:16509/system"
  timeout: 120

mcp:
  transport: "http"
  host: "0.0.0.0"
  port: 8080

security:
  auth_required: true
  audit_log: true
  max_concurrent_ops: 20
  allowed_operations:
    - "domain.*"
    - "host.info"
    - "network.list"
    - "storage.*"

logging:
  level: "INFO"
  file: "/var/log/libvirt-mcp-cluster.log"
```

### Docker 容器配置

```yaml
# docker-config.yaml
libvirt:
  uri: "qemu:///system"
  timeout: 30

mcp:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

security:
  auth_required: false  # 容器内部通信
  audit_log: true
  allowed_operations:
    - "domain.list"
    - "domain.info"
    - "domain.start"
    - "domain.stop"
    - "domain.reboot"

logging:
  level: "INFO"
  file: null  # 输出到容器日志
```

Docker 运行命令：
```bash
docker run -d \
  --name libvirt-mcp \
  --privileged \
  -v /var/run/libvirt:/var/run/libvirt:ro \
  -v $(pwd)/docker-config.yaml:/app/config.yaml \
  -p 8000:8000 \
  libvirt-mcp-server:latest \
  start --config /app/config.yaml
```

## 🔐 安全性

### 最小权限原则

- 服务器默认运行在受限权限下
- 只暴露明确配置的操作
- 支持基于角色的访问控制

### 审计和日志

- 所有操作都被记录和审计
- 支持结构化日志输出
- 集成系统日志和外部日志系统

### 输入验证

- 严格的参数验证和清理
- XML配置的Schema验证
- 防止注入攻击

## 🧪 测试

### 运行测试套件

```bash
# 运行所有测试
uv run pytest

# 运行特定测试模块
uv run pytest tests/test_mcp_tools.py

# 生成覆盖率报告
uv run pytest --cov=libvirt_mcp_server --cov-report=html
```

### 集成测试

```bash
# 启动测试环境
uv run pytest tests/integration/ --libvirt-uri="qemu:///system"
```

## 📦 部署

### 系统服务

```bash
# 安装systemd服务
sudo cp deployment/libvirt-mcp-server.service /etc/systemd/system/
sudo systemctl enable libvirt-mcp-server
sudo systemctl start libvirt-mcp-server
```

### Docker部署

```bash
# 构建镜像
docker build -t libvirt-mcp-server .

# 运行容器
docker-compose up -d
```

### Kubernetes部署

```bash
kubectl apply -f deployment/k8s/
```

## 🤝 贡献

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/new-feature`)
3. 提交更改 (`git commit -am 'Add new feature'`)
4. 推送到分支 (`git push origin feature/new-feature`)
5. 创建 Pull Request

## 📝 许可证

本项目使用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 支持

- 📖 [文档](https://github.com/your-org/libvirt-mcp-server/wiki)
- 🐛 [问题报告](https://github.com/your-org/libvirt-mcp-server/issues)
- 💬 [讨论区](https://github.com/your-org/libvirt-mcp-server/discussions)

## 🔗 相关链接

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [libvirt 官方文档](https://libvirt.org/docs.html)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
