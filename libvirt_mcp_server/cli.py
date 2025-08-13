"""
命令行接口模块

提供了 libvirt-mcp-server 的命令行界面，支持：
- 启动 MCP 服务器
- 配置管理
- 调试和诊断功能
- 服务器状态检查
- 配置验证
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing_extensions import Annotated

from .config import Config
from .exceptions import ConfigurationError, LibvirtConnectionError
from .server import LibvirtMCPServer
from .logging import configure_logging, get_logger, log_startup_info

# 版本信息
__version__ = "1.0.0"

# 创建 Typer 应用实例
app = typer.Typer(
    name="libvirt-mcp-server",
    help="🚀 Libvirt MCP Server - AI 驱动的虚拟化管理服务",
    epilog="Made with ❤️  for the AI community. Visit: https://github.com/your-org/libvirt-mcp-server",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Rich Console 用于美化输出
console = Console()


def version_callback(value: bool):
    """显示版本信息并退出"""
    if value:
        from . import __version__
        console.print(f"[bold green]libvirt-mcp-server[/bold green] version [bold blue]{__version__}[/bold blue]")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", "-V",
            callback=version_callback,
            help="显示版本信息并退出"
        )
    ] = None,
):
    """
    🚀 Libvirt MCP Server - AI 驱动的虚拟化管理服务
    
    这是一个基于 Model Context Protocol (MCP) 的服务器，
    为 AI 模型提供安全、可控的虚拟化管理能力。
    """
    pass


@app.command()
def start(
    config: Annotated[
        Optional[Path],
        typer.Option(
            "--config", "-c",
            help="配置文件路径 (YAML 格式)",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ] = None,
    transport: Annotated[
        Optional[str],
        typer.Option(
            "--transport", "-t",
            help="传输协议类型",
        )
    ] = None,
    host: Annotated[
        Optional[str],
        typer.Option(
            "--host", "-h",
            help="服务器绑定地址"
        )
    ] = None,
    port: Annotated[
        Optional[int],
        typer.Option(
            "--port", "-p",
            help="服务器端口",
            min=1,
            max=65535
        )
    ] = None,
    libvirt_uri: Annotated[
        Optional[str],
        typer.Option(
            "--libvirt-uri",
            help="Libvirt 连接 URI (例如: qemu:///system)"
        )
    ] = None,
    readonly: Annotated[
        bool,
        typer.Option(
            "--readonly",
            help="使用只读模式连接 libvirt"
        )
    ] = False,
    log_level: Annotated[
        Optional[str],
        typer.Option(
            "--log-level", "-l",
            help="日志级别",
        )
    ] = None,
    log_file: Annotated[
        Optional[Path],
        typer.Option(
            "--log-file",
            help="日志文件路径"
        )
    ] = None,
    no_audit: Annotated[
        bool,
        typer.Option(
            "--no-audit",
            help="禁用审计日志"
        )
    ] = False,
    health_check: Annotated[
        bool,
        typer.Option(
            "--health-check",
            help="执行健康检查并退出"
        )
    ] = False,
    validate_config_flag: Annotated[
        bool,
        typer.Option(
            "--validate-config",
            help="验证配置并退出"
        )
    ] = False,
):
    """
    🚀 启动 Libvirt MCP Server
    
    启动服务器来处理来自 AI 模型的虚拟化管理请求。
    服务器将通过 MCP 协议暴露 libvirt 功能。
    """
    asyncio.run(_async_start(
        config=config,
        transport=transport,
        host=host,
        port=port,
        libvirt_uri=libvirt_uri,
        readonly=readonly,
        log_level=log_level,
        log_file=log_file,
        no_audit=no_audit,
        health_check=health_check,
        validate_config_flag=validate_config_flag,
    ))


async def _async_start(
    config: Optional[Path],
    transport: Optional[str],
    host: Optional[str],
    port: Optional[int],
    libvirt_uri: Optional[str],
    readonly: bool,
    log_level: Optional[str],
    log_file: Optional[Path],
    no_audit: bool,
    health_check: bool,
    validate_config_flag: bool,
) -> None:
    """异步启动函数"""
    try:
        # 加载配置
        server_config = _load_config(
            config_file=config,
            transport=transport,
            host=host,
            port=port,
            libvirt_uri=libvirt_uri,
            readonly=readonly,
            log_level=log_level,
            log_file=log_file,
            no_audit=no_audit,
        )
        
        # 配置日志系统
        logging_manager = configure_logging(server_config)
        logger = get_logger(__name__)
        
        # 验证配置
        if validate_config_flag:
            _validate_configuration(server_config)
            console.print("✅ 配置验证成功")
            return
        
        # 创建服务器实例
        server = LibvirtMCPServer(server_config)
        
        # 健康检查
        if health_check:
            await _perform_health_check(server)
            return
        
        # 显示启动信息
        _display_startup_info(server_config)
        log_startup_info(server_config)
        
        # 运行服务器
        logger.info("🚀 启动 libvirt MCP 服务器...")
        await server.run()
        
    except ConfigurationError as e:
        logger = get_logger(__name__)
        logger.error("配置错误: {}", str(e))
        console.print(f"[red]❌ 配置错误: {e}[/red]")
        raise typer.Exit(code=1)
    except LibvirtConnectionError as e:
        logger = get_logger(__name__)
        logger.critical("Libvirt 连接失败: {}", str(e))
        console.print(f"[red]❌ Libvirt 连接失败: {e}[/red]")
        raise typer.Exit(code=1)
    except KeyboardInterrupt:
        logger = get_logger(__name__)
        logger.info("收到中断信号，正在关闭服务器...")
        console.print("\n[yellow]⚠️  收到中断信号，正在关闭服务器...[/yellow]")
        raise typer.Exit(code=0)
    except Exception as e:
        logger = get_logger(__name__)
        logger.exception("发生未预期的错误")
        console.print(f"[red]❌ 发生未预期的错误: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def validate_config(
    config: Annotated[
        Optional[Path],
        typer.Option(
            "--config", "-c",
            help="要验证的配置文件路径",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
        )
    ] = None,
):
    """
    ✅ 验证配置文件
    
    检查配置文件的语法和有效性，确保所有设置都正确。
    """
    try:
        app_config = Config.from_yaml_file(str(config)) if config else Config.load()
        
        # 创建配置信息表格
        table = Table(title="📋 配置验证结果", show_header=True, header_style="bold magenta")
        table.add_column("配置项", style="cyan", no_wrap=True)
        table.add_column("当前值", style="green")
        table.add_column("状态", justify="center")
        
        # MCP 配置
        table.add_row("传输协议", app_config.mcp.transport, "✅")
        table.add_row("服务器地址", app_config.mcp.host, "✅")
        table.add_row("服务器端口", str(app_config.mcp.port), "✅")
        
        # Libvirt 配置
        table.add_row("Libvirt URI", app_config.libvirt.uri, "✅")
        table.add_row("只读模式", "是" if app_config.libvirt.readonly else "否", "✅")
        
        # 日志配置
        table.add_row("日志级别", app_config.logging.level, "✅")
        table.add_row("日志文件", app_config.logging.file or "无", "✅")
        
        # 安全配置
        table.add_row("审计日志", "启用" if app_config.security.audit_log else "禁用", "✅")
        
        console.print(table)
        
        # 显示警告和建议
        _display_config_warnings(app_config)
        
        console.print("[bold green]✅ 配置文件验证成功！[/bold green]")
        
    except ConfigurationError as e:
        console.print(f"[red]❌ 配置验证失败: {e}[/red]")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red]❌ 验证过程中发生错误: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def check_libvirt(
    uri: Annotated[
        Optional[str],
        typer.Option(
            "--uri",
            help="Libvirt 连接 URI"
        )
    ] = None,
):
    """
    🔍 检查 Libvirt 连接
    
    测试与 libvirt 守护进程的连接，验证权限和可用性。
    """
    from .libvirt_client import LibvirtClient
    
    try:
        # 使用提供的 URI 或默认值
        libvirt_uri = uri or "qemu:///system"
        
        console.print(f"[blue]🔍 正在检查 Libvirt 连接: {libvirt_uri}[/blue]")
        
        # 创建配置对象
        config = Config.load()
        config.libvirt.uri = libvirt_uri
        
        # 创建 libvirt 客户端
        client = LibvirtClient(config)
        
        # 尝试连接
        async def check_connection():
            await client.connect()
            
            # 获取基本信息
            domains = await client.list_domains()
            
            # 创建结果表格
            table = Table(title="🖥️  Libvirt 连接状态", show_header=True, header_style="bold blue")
            table.add_column("项目", style="cyan", no_wrap=True)
            table.add_column("值", style="green")
            
            table.add_row("连接 URI", libvirt_uri)
            table.add_row("连接状态", "✅ 已连接")
            table.add_row("虚拟机数量", str(len(domains)))
            
            if domains:
                table.add_row("虚拟机列表", ", ".join([vm.name for vm in domains[:5]]))
                if len(domains) > 5:
                    table.add_row("", f"... 还有 {len(domains) - 5} 个虚拟机")
            
            console.print(table)
            
            await client.disconnect()
        
        asyncio.run(check_connection())
        
        console.print("[bold green]✅ Libvirt 连接检查成功！[/bold green]")
        
    except Exception as e:
        console.print(f"[red]❌ Libvirt 连接检查失败: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def info():
    """
    ℹ️  显示系统信息
    
    显示服务器环境、版本信息和系统状态。
    """
    import platform
    import sys
    from . import __version__
    
    # 创建系统信息表格
    table = Table(title="ℹ️  系统信息", show_header=True, header_style="bold cyan")
    table.add_column("项目", style="cyan", no_wrap=True)
    table.add_column("值", style="white")
    
    # 应用信息
    table.add_row("应用名称", "libvirt-mcp-server")
    table.add_row("版本", __version__)
    
    # 系统信息
    table.add_row("操作系统", f"{platform.system()} {platform.release()}")
    table.add_row("架构", platform.machine())
    table.add_row("Python 版本", f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    table.add_row("Python 路径", sys.executable)
    
    # 环境信息
    table.add_row("工作目录", str(Path.cwd()))
    table.add_row("用户", os.getenv("USER", "未知"))
    
    console.print(table)
    
    # 依赖信息
    _display_dependency_info()


@app.command()
def generate_config(
    output: Annotated[
        Path,
        typer.Option(
            "--output", "-o",
            help="输出配置文件路径"
        )
    ] = Path("config.yaml"),
):
    """
    📝 生成示例配置文件
    
    生成一个包含所有可配置选项的示例配置文件。
    """
    try:
        config = Config()
        config.to_yaml_file(str(output))
        console.print(f"✅ 已生成示例配置文件: [bold blue]{output}[/bold blue]")
        console.print("请根据需要编辑配置文件后使用。")
    except Exception as e:
        console.print(f"[red]❌ 生成配置文件失败: {e}[/red]")
        raise typer.Exit(code=1)


def _load_config(
    config_file: Optional[Path],
    transport: Optional[str],
    host: Optional[str],
    port: Optional[int],
    libvirt_uri: Optional[str],
    readonly: bool,
    log_level: Optional[str],
    log_file: Optional[Path],
    no_audit: bool,
) -> Config:
    """从各种来源加载和合并配置"""
    # 加载基础配置
    if config_file:
        server_config = Config.from_yaml_file(str(config_file))
    else:
        server_config = Config.load()
    
    # 应用命令行覆盖
    if transport:
        server_config.mcp.transport = transport
    
    if host:
        server_config.mcp.host = host
    
    if port:
        server_config.mcp.port = port
    
    if libvirt_uri:
        server_config.libvirt.uri = libvirt_uri
    
    if readonly:
        server_config.libvirt.readonly = True
    
    if log_level:
        server_config.logging.level = log_level
    
    if log_file:
        server_config.logging.file = str(log_file)
    
    if no_audit:
        server_config.security.audit_log = False
    
    return server_config


def _validate_configuration(config: Config) -> None:
    """验证配置并报告任何问题"""
    try:
        # 验证基本配置结构
        config.validate_permissions()
        
        # 检查 libvirt URI 格式
        if not config.libvirt.uri:
            raise ConfigurationError("Libvirt URI 不能为空")
        
        # 检查传输特定设置
        if config.mcp.transport in ["http", "sse"]:
            if config.mcp.port < 1 or config.mcp.port > 65535:
                raise ConfigurationError(f"无效端口: {config.mcp.port}")
            
            if not config.mcp.host:
                raise ConfigurationError("HTTP/SSE 传输协议的主机地址不能为空")
        
        # 检查日志配置
        if config.logging.file:
            log_dir = Path(config.logging.file).parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    raise ConfigurationError(f"无法创建日志目录: {e}")
        
        # 检查安全配置
        if not config.security.allowed_operations:
            raise ConfigurationError("至少需要允许一个操作")
        
    except Exception as e:
        raise ConfigurationError(f"配置验证失败: {e}")


async def _perform_health_check(server: LibvirtMCPServer) -> None:
    """执行健康检查并显示结果"""
    console.print("🔍 正在执行健康检查...")
    
    try:
        # 获取健康状态
        health_status = await server.health_check()
        
        # 显示结果
        overall_status = health_status["status"]
        if overall_status == "healthy":
            console.print("✅ 总体状态: 健康")
        elif overall_status == "degraded":
            console.print("⚠️  总体状态: 降级")
        else:
            console.print("❌ 总体状态: 不健康")
        
        # 显示组件状态
        for component, status in health_status["components"].items():
            if status["status"] == "healthy":
                console.print(f"  ✅ {component}: 正常")
            else:
                console.print(f"  ❌ {component}: {status.get('error', status['status'])}")
        
        if overall_status != "healthy":
            raise typer.Exit(code=1)
            
    except Exception as e:
        console.print(f"❌ 健康检查失败: {e}")
        raise typer.Exit(code=1)


def _display_startup_info(config: Config) -> None:
    """显示启动信息"""
    readonly_color = 'red' if config.libvirt.readonly else 'green'
    readonly_status = '启用' if config.libvirt.readonly else '禁用'
    audit_color = 'green' if config.security.audit_log else 'red'
    audit_status = '启用' if config.security.audit_log else '禁用'
    
    startup_panel = Panel.fit(
        f"🚀 [bold green]Libvirt MCP Server[/bold green]\n\n"
        f"📡 传输协议: [bold blue]{config.mcp.transport}[/bold blue]\n"
        f"📍 服务器地址: [bold blue]{config.mcp.host}:{config.mcp.port}[/bold blue]\n"
        f"🔧 Libvirt URI: [bold yellow]{config.libvirt.uri}[/bold yellow]\n"
        f"🔒 只读模式: [bold {readonly_color}]{readonly_status}[/bold {readonly_color}]\n"
        f"📊 日志级别: [bold cyan]{config.logging.level}[/bold cyan]\n"
        f"🛡️  审计日志: [bold {audit_color}]{audit_status}[/bold {audit_color}]",
        title="启动配置",
        border_style="green"
    )
    console.print(startup_panel)


def _display_config_warnings(config: Config) -> None:
    """显示配置警告和建议"""
    warnings = []
    
    if not config.security.audit_log:
        warnings.append("⚠️  审计日志已禁用，生产环境建议启用")
    
    if config.mcp.host == "0.0.0.0":
        warnings.append("⚠️  服务器绑定到所有网络接口，确保防火墙配置正确")
    
    if config.libvirt.readonly:
        warnings.append("ℹ️  libvirt 连接为只读模式，无法执行修改操作")
    
    if warnings:
        warning_text = "\n".join(warnings)
        warning_panel = Panel.fit(
            warning_text,
            title="⚠️  警告和建议",
            border_style="yellow"
        )
        console.print(warning_panel)


def _display_dependency_info() -> None:
    """显示依赖信息"""
    try:
        import importlib.metadata
        
        deps = [
            "mcp",
            "libvirt-python", 
            "pydantic",
            "typer",
            "loguru",
            "pyyaml",
        ]
        
        table = Table(title="📦 依赖库版本", show_header=True, header_style="bold magenta")
        table.add_column("库名", style="cyan", no_wrap=True)
        table.add_column("版本", style="green")
        table.add_column("状态", justify="center")
        
        for dep in deps:
            try:
                version = importlib.metadata.version(dep)
                table.add_row(dep, version, "✅")
            except importlib.metadata.PackageNotFoundError:
                table.add_row(dep, "未安装", "❌")
        
        console.print(table)
        
    except ImportError:
        console.print("[yellow]⚠️  无法获取依赖信息（importlib.metadata 不可用）[/yellow]")


def main_cli():
    """主入口点"""
    app()


if __name__ == '__main__':
    main_cli()