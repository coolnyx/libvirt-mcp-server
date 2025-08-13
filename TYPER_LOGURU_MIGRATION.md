# Typer & Loguru 迁移指南

本文档记录了从 Click + Structlog 迁移到 Typer + Loguru 的详细过程和改进内容。

## 🎯 迁移目标

1. **现代化 CLI 体验**: 使用 Typer 提供更美观、功能丰富的命令行界面
2. **简化日志配置**: 使用 Loguru 替代复杂的 Structlog 配置
3. **增强用户体验**: Rich 输出、颜色支持、更好的错误处理
4. **提升开发效率**: 更简洁的 API 和更好的类型安全

## 📦 依赖变更

### 移除的依赖
```toml
# 旧依赖
"click>=8.0.0"
"structlog>=23.0.0"
```

### 新增的依赖
```toml
# 新依赖
"typer[all]>=0.9.0"  # 包含 Rich 支持
"loguru>=0.7.0"
```

## 🚀 CLI 界面改进

### 1. 新的命令结构

**之前 (Click)**:
```bash
libvirt-mcp-server --config config.yaml --transport http --port 8000
```

**现在 (Typer)**:
```bash
libvirt-mcp-server start --config config.yaml --transport http --port 8000
libvirt-mcp-server validate-config --config config.yaml
libvirt-mcp-server check-libvirt --uri qemu:///system
libvirt-mcp-server info
libvirt-mcp-server generate-config --output custom-config.yaml
```

### 2. Rich 输出支持

- 🌈 **彩色输出**: 更好的视觉体验
- 📊 **表格显示**: 结构化信息展示
- 📦 **面板布局**: 重要信息突出显示
- ✅ **状态图标**: 清晰的成功/失败指示

### 3. 增强的帮助系统

```bash
# 更美观的帮助信息
$ libvirt-mcp-server --help

🚀 Libvirt MCP Server - AI 驱动的虚拟化管理服务

这是一个基于 Model Context Protocol (MCP) 的服务器，
为 AI 模型提供安全、可控的虚拟化管理能力。

Usage: libvirt-mcp-server [OPTIONS] COMMAND [ARGS]...

Commands:
  start            🚀 启动 Libvirt MCP Server
  validate-config  ✅ 验证配置文件
  check-libvirt    🔍 检查 Libvirt 连接
  info             ℹ️  显示系统信息
  generate-config  📝 生成示例配置文件
```

## 📝 日志系统升级

### 1. Loguru 优势

- **零配置**: 开箱即用的日志系统
- **异步安全**: 内置队列机制
- **自动轮转**: 灵活的文件轮转策略
- **结构化日志**: 原生 JSON 支持
- **上下文绑定**: 简化的上下文管理

### 2. 新的日志配置

```python
# 自动配置多种处理器
from libvirt_mcp_server.logging import configure_logging, get_logger

# 简单的配置
logging_config = configure_logging(server_config.logging)
logger = get_logger(__name__)

# 使用日志
logger.info("服务器启动", port=8000, host="0.0.0.0")
logger.error("连接失败", error=str(e), uri="qemu:///system")
```

### 3. 高级功能

#### 性能监控装饰器
```python
from libvirt_mcp_server.logging import log_async_performance

@log_async_performance(threshold_ms=1000.0)
async def slow_operation():
    # 自动记录执行时间
    pass
```

#### 上下文管理器
```python
from libvirt_mcp_server.logging import LogContext

with LogContext(vm_name="test-vm", operation="start") as logger:
    logger.info("开始启动虚拟机")  # 自动包含上下文
```

#### 函数调用跟踪
```python
from libvirt_mcp_server.logging import log_async_function_call

@log_async_function_call(level="DEBUG")
async def create_vm(name: str, config: dict):
    # 自动记录函数调用和返回值
    pass
```

## 🏗️ 代码结构改进

### 1. 新增模块

```
libvirt_mcp_server/
├── __init__.py          # 🆕 版本信息和导出
├── logging.py           # 🆕 统一日志管理
├── cli.py              # 🔄 完全重构，使用 Typer
├── server.py           # 🔄 更新日志导入
├── libvirt_client.py   # 🔄 更新日志导入
├── security.py         # 🔄 更新日志导入
└── tools.py            # 🔄 更新日志导入
```

### 2. 版本管理

```python
# libvirt_mcp_server/__init__.py
__version__ = "1.0.0"
__author__ = "Your Name"

# 统一的版本信息
from libvirt_mcp_server import __version__
```

## 🧪 测试和示例更新

### 1. 示例脚本更新

所有示例脚本都已更新以使用新的 CLI 命令:

```python
# 更新前
server_params = StdioServerParameters(
    command="uv",
    args=["run", "libvirt-mcp-server", "--transport", "stdio"]
)

# 更新后
server_params = StdioServerParameters(
    command="uv",
    args=["run", "libvirt-mcp-server", "start", "--transport", "stdio"]
)
```

### 2. 开发脚本改进

`run_server.py` 也已更新以使用新的日志系统:

```python
# 使用新的日志配置
from libvirt_mcp_server.logging import configure_logging, get_logger

logging_config = configure_logging(config.logging)
logger = get_logger(__name__)
```

## 🚦 使用指南

### 1. 基本启动

```bash
# 使用默认配置启动
libvirt-mcp-server start

# 使用自定义配置
libvirt-mcp-server start --config custom-config.yaml

# 调试模式
libvirt-mcp-server start --log-level DEBUG --libvirt-uri qemu:///system
```

### 2. 配置管理

```bash
# 生成示例配置
libvirt-mcp-server generate-config --output my-config.yaml

# 验证配置
libvirt-mcp-server validate-config --config my-config.yaml
```

### 3. 诊断工具

```bash
# 检查系统信息
libvirt-mcp-server info

# 测试 libvirt 连接
libvirt-mcp-server check-libvirt --uri qemu:///system

# 健康检查
libvirt-mcp-server start --health-check
```

## 🔧 开发者注意事项

### 1. 日志使用模式

```python
# 推荐的日志使用方式
from libvirt_mcp_server.logging import get_logger

logger = get_logger(__name__)

# 结构化日志
logger.info("操作完成", operation="start_vm", vm_name="test", duration_ms=1500)

# 错误日志 (自动包含异常信息)
try:
    # some operation
    pass
except Exception as e:
    logger.error("操作失败", operation="start_vm", error=str(e))
```

### 2. CLI 扩展

添加新命令很简单:

```python
@app.command()
def new_command(
    param: Annotated[str, typer.Option("--param", help="参数说明")]
):
    """新命令的说明"""
    console.print(f"执行新命令: {param}")
```

### 3. 配置更新

如果添加新的配置选项，记得同时更新:
- `Config` 模型
- CLI 选项
- 配置验证逻辑
- 文档示例

## 📈 性能和可靠性改进

### 1. 日志性能

- **异步队列**: Loguru 的 `enqueue=True` 避免 I/O 阻塞
- **智能轮转**: 基于大小和时间的自动日志轮转
- **压缩存储**: 自动压缩旧日志文件

### 2. 错误处理

- **全局异常捕获**: 自动记录未处理的异常
- **优雅退出**: Ctrl+C 时的清理和关闭
- **丰富的错误信息**: 包含上下文的错误报告

### 3. 类型安全

- **Typer 类型检查**: 自动的参数验证
- **Rich 注解**: 更好的 IDE 支持
- **Pydantic 集成**: 配置数据的自动验证

## 🔄 迁移检查清单

- [x] 更新 `pyproject.toml` 依赖
- [x] 重构 `cli.py` 使用 Typer
- [x] 创建新的 `logging.py` 模块
- [x] 更新所有模块的日志导入
- [x] 更新示例脚本
- [x] 更新开发脚本
- [x] 更新 README 文档
- [x] 创建版本管理模块
- [x] 测试新功能
- [x] 完成迁移文档

## 🚀 后续改进建议

1. **交互式配置**: 添加 `libvirt-mcp-server init` 命令引导用户配置
2. **插件系统**: 支持第三方扩展和自定义工具
3. **Web 界面**: 基于 FastAPI 的可选 Web 管理界面
4. **监控集成**: Prometheus 指标和健康检查端点
5. **配置模板**: 针对不同部署场景的预定义配置

---

**迁移完成！** 🎉

项目现在具备了现代化的 CLI 界面和强大的日志系统，为用户提供更好的体验和为开发者提供更好的调试能力。

