# libvirt-mcp-server 开发指南

## 📚 项目概述

libvirt-mcp-server 是一个基于 Model Context Protocol (MCP) 的 Python 服务，通过 MCP 协议暴露 libvirt 虚拟化平台的能力，使 AI 模型能够安全、可控地查询和管理虚拟机资源。

## 🏗️ 项目架构

### 核心组件

```
libvirt_mcp_server/
├── __init__.py          # 包初始化
├── config.py            # 配置管理
├── server.py            # MCP 服务器主逻辑
├── libvirt_client.py    # libvirt 客户端封装
├── tools.py             # MCP 工具实现
├── models.py            # 数据模型定义
├── security.py         # 安全管理和审计
├── exceptions.py        # 自定义异常
└── cli.py              # 命令行接口
```

### 设计原则

1. **安全第一**: 所有操作都经过权限验证和审计
2. **最小权限**: 只暴露必要的功能
3. **可配置**: 支持灵活的配置管理
4. **可观测**: 完善的日志和监控
5. **可扩展**: 模块化设计便于扩展

## 🛠️ 开发环境设置

### 1. 系统要求

- Python 3.11+
- libvirt 开发库
- QEMU/KVM（用于测试）

### 2. 安装系统依赖

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y \
    python3-dev \
    libvirt-dev \
    libvirt-daemon-system \
    qemu-kvm \
    build-essential \
    pkg-config
```

#### CentOS/RHEL

```bash
sudo yum install -y \
    python3-devel \
    libvirt-devel \
    libvirt-daemon \
    qemu-kvm \
    gcc \
    pkgconfig
```

### 3. 设置开发环境

```bash
# 克隆项目
git clone https://github.com/your-org/libvirt-mcp-server.git
cd libvirt-mcp-server

# 安装 uv（推荐的包管理器）
pip install uv

# 创建虚拟环境并安装依赖
uv sync --dev

# 激活虚拟环境
source .venv/bin/activate

# 安装开发工具
uv add --dev pre-commit
pre-commit install
```

### 4. 配置开发环境

```bash
# 复制示例配置
cp config.example.yaml config.yaml
cp env.example .env

# 编辑配置以使用测试驱动
sed -i 's/qemu:\/\/\/system/test:\/\/\/default/' config.yaml
```

## 🧪 开发和测试

### 1. 运行开发服务器

```bash
# 使用开发脚本
./run_server.py

# 或直接运行
uv run libvirt-mcp-server --transport stdio --libvirt-uri qemu:///system
```

### 2. 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行特定测试
uv run pytest tests/test_config.py

# 运行带覆盖率的测试
uv run pytest --cov=libvirt_mcp_server --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 3. 代码质量检查

```bash
# 格式化代码
uv run black libvirt_mcp_server/ tests/

# 检查导入排序
uv run isort libvirt_mcp_server/ tests/

# 类型检查
uv run mypy libvirt_mcp_server/

# Lint 检查
uv run ruff check libvirt_mcp_server/ tests/

# 运行所有检查
pre-commit run --all-files
```

### 4. 客户端测试

```bash
# 基础功能测试
python examples/basic_usage.py

# 虚拟机管理测试
python examples/vm_management.py
```

## 🔧 核心模块开发

### 1. 添加新的 MCP 工具

#### 步骤 1: 在 `models.py` 中定义数据模型

```python
class NewOperationParams(BaseModel):
    """新操作的参数模型."""
    
    parameter1: str = Field(description="参数1描述")
    parameter2: int = Field(description="参数2描述", ge=1)
```

#### 步骤 2: 在 `libvirt_client.py` 中实现 libvirt 操作

```python
async def new_operation(self, param1: str, param2: int) -> OperationResult:
    """实现新的 libvirt 操作."""
    self._check_operation_allowed("new.operation")
    conn = self._ensure_connected()
    
    try:
        # 实现具体的 libvirt 操作
        result = conn.some_libvirt_method(param1, param2)
        logger.info(f"新操作完成: {param1}")
        return OperationResult(success=True, message="操作成功", details=result)
    except libvirtError as e:
        logger.error(f"新操作失败: {e}")
        raise LibvirtOperationError(f"操作失败: {e}")
```

#### 步骤 3: 在 `tools.py` 中注册 MCP 工具

```python
@mcp_server.tool()
async def new_operation(
    ctx: Context,
    parameter1: str,
    parameter2: int = 1
) -> Dict[str, Any]:
    """
    新操作的 MCP 工具。
    
    Args:
        parameter1: 参数1描述
        parameter2: 参数2描述
    
    Returns:
        操作结果字典
    """
    try:
        await ctx.info(f"执行新操作: {parameter1}")
        
        params = NewOperationParams(parameter1=parameter1, parameter2=parameter2)
        result = await libvirt_client.new_operation(params.parameter1, params.parameter2)
        
        await ctx.info(f"新操作完成: {parameter1}")
        return result.dict()
        
    except Exception as e:
        await ctx.error(f"新操作失败: {e}")
        raise
```

#### 步骤 4: 更新安全配置

在 `config.example.yaml` 中添加新操作到允许列表：

```yaml
security:
  allowed_operations:
    - "new.operation"  # 新操作
```

#### 步骤 5: 编写测试

```python
# tests/test_new_operation.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_new_operation():
    """测试新操作."""
    # 实现测试逻辑
    pass
```

### 2. 安全考虑

在开发新功能时，请遵循以下安全原则：

1. **输入验证**: 使用 Pydantic 模型验证所有输入
2. **权限检查**: 在 libvirt 操作前检查权限
3. **审计日志**: 记录所有操作和结果
4. **错误处理**: 不暴露敏感的错误信息
5. **资源限制**: 防止资源滥用

### 3. 错误处理模式

```python
async def some_operation(self, param: str) -> Result:
    """操作示例，展示错误处理模式."""
    try:
        # 权限检查
        self._check_operation_allowed("some.operation")
        
        # 输入验证
        if not await self.security_manager.validate_input(param):
            raise ValidationError("无效输入")
        
        # 执行操作
        result = await self._execute_operation(param)
        
        # 记录成功
        logger.info(f"操作成功: {param}")
        return result
        
    except LibvirtConnectionError:
        # 连接错误，尝试重连
        await self.reconnect()
        raise
    except LibvirtPermissionError as e:
        # 权限错误，记录并抛出
        logger.warning(f"权限拒绝: {e}")
        raise
    except Exception as e:
        # 未预期错误，记录并抛出
        logger.error(f"未预期错误: {e}", exc_info=True)
        raise
```

## 🔍 调试和排错

### 1. 启用调试日志

```yaml
# config.yaml
logging:
  level: "DEBUG"
  file: "/tmp/libvirt-mcp-debug.log"
```

### 2. 使用测试驱动

```yaml
# config.yaml
libvirt:
  uri: "qemu:///system"  # 使用测试驱动，无需真实 VM
```

### 3. 常见问题解决

#### 连接问题

```bash
# 检查 libvirt 服务状态
sudo systemctl status libvirtd

# 检查权限
sudo usermod -a -G libvirt $USER
newgrp libvirt

# 测试连接
virsh -c qemu:///system list
```

#### 权限问题

```bash
# 检查 libvirt 组成员
groups $USER

# 检查 socket 权限
ls -l /var/run/libvirt/libvirt-sock
```

### 4. 性能分析

```python
# 使用 cProfile 分析性能
python -m cProfile -o profile.stats run_server.py

# 分析结果
python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

## 📦 构建和发布

### 1. 构建包

```bash
# 构建 wheel 包
uv build

# 检查包内容
unzip -l dist/*.whl
```

### 2. 发布到 PyPI

```bash
# 安装发布工具
uv add --dev twine

# 检查包
uv run twine check dist/*

# 发布到测试 PyPI
uv run twine upload --repository testpypi dist/*

# 发布到正式 PyPI
uv run twine upload dist/*
```

### 3. Docker 镜像

```bash
# 构建镜像
docker build -t libvirt-mcp-server:latest .

# 运行容器
docker run -d \
  --name libvirt-mcp \
  -v /var/run/libvirt:/var/run/libvirt \
  -p 8000:8000 \
  libvirt-mcp-server:latest
```

## 🤝 贡献指南

### 1. 开发流程

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 进行开发并编写测试
4. 运行所有测试和检查
5. 提交更改: `git commit -m 'Add new feature'`
6. 推送分支: `git push origin feature/new-feature`
7. 创建 Pull Request

### 2. 代码规范

- 遵循 PEP 8 风格指南
- 使用类型注解
- 编写文档字符串
- 保持测试覆盖率 > 80%
- 通过所有 lint 检查

### 3. 提交信息格式

```
类型(范围): 简短描述

详细描述（可选）

Fixes #123
```

类型：
- `feat`: 新功能
- `fix`: bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

### 4. Pull Request 检查清单

- [ ] 代码通过所有测试
- [ ] 添加了必要的测试
- [ ] 更新了文档
- [ ] 通过了 lint 检查
- [ ] 遵循了安全最佳实践
- [ ] 更新了 CHANGELOG

## 📚 更多资源

- [Model Context Protocol 规范](https://modelcontextprotocol.io/)
- [libvirt 官方文档](https://libvirt.org/docs.html)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [项目 Wiki](https://github.com/your-org/libvirt-mcp-server/wiki)

## 💬 获取帮助

- 📖 [FAQ](https://github.com/your-org/libvirt-mcp-server/wiki/FAQ)
- 🐛 [问题报告](https://github.com/your-org/libvirt-mcp-server/issues)
- 💬 [讨论区](https://github.com/your-org/libvirt-mcp-server/discussions)
- 📧 邮件: support@example.com
