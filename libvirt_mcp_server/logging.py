"""
Loguru 配置模块 - 统一管理项目的日志记录

此模块提供了基于 Loguru 的日志配置，支持：
- 控制台和文件日志输出
- 结构化日志记录
- 日志轮转和压缩
- 开发和生产环境的不同配置
- 异步安全的日志记录
- 上下文绑定和过滤
"""

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .config import Config

# 默认日志格式
DEFAULT_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS ZZ}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 简化的生产环境格式
PRODUCTION_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS ZZ} | "
    "{level: <8} | "
    "{name}:{function}:{line} | "
    "{message}"
)

# JSON 格式用于结构化日志
JSON_FORMAT = "{message}"

# 控制台格式（带颜色）
CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan> | "
    "<level>{message}</level>"
)


class LoggingManager:
    """日志系统管理器"""
    
    def __init__(self, config: Config):
        """
        初始化日志管理器
        
        Args:
            config: 服务器配置对象
        """
        self.config = config
        self._handler_ids: List[int] = []
    
    def setup_logging(self) -> None:
        """设置 Loguru 日志配置"""
        # 移除默认处理器
        logger.remove()
        
        # 添加控制台处理器
        self._add_console_handler()
        
        # 添加文件处理器
        self._add_file_handlers()
        
        # 配置第三方库日志级别
        self._configure_third_party_loggers()
        
        # 设置全局异常处理器
        self._setup_exception_handler()
    
    def _add_console_handler(self) -> None:
        """添加控制台日志处理器"""
        # 根据日志级别判断是否为调试模式
        is_debug = self.config.logging.level == "DEBUG"
        console_format = CONSOLE_FORMAT if is_debug else PRODUCTION_FORMAT
        
        handler_id = logger.add(
            sys.stderr,
            format=console_format,
            level=self.config.logging.level,
            colorize=True,
            backtrace=is_debug,
            diagnose=is_debug,
            enqueue=True,  # 线程安全
            catch=True
        )
        self._handler_ids.append(handler_id)
    
    def _add_file_handlers(self) -> None:
        """添加文件日志处理器"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # 主日志文件
        main_log_file = log_dir / "libvirt-mcp-server.log"
        handler_id = logger.add(
            str(main_log_file),
            format=PRODUCTION_FORMAT,
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            backtrace=False,
            diagnose=False,
            enqueue=True,
            catch=True
        )
        self._handler_ids.append(handler_id)
        
        # 错误日志文件
        error_log_file = log_dir / "errors.log"
        handler_id = logger.add(
            str(error_log_file),
            format=PRODUCTION_FORMAT,
            level="ERROR",
            rotation="5 MB",
            retention="60 days",
            compression="zip",
            backtrace=True,
            diagnose=True,
            enqueue=True,
            catch=True
        )
        self._handler_ids.append(handler_id)
        
        # 调试模式下的调试日志文件
        if self.config.logging.level == "DEBUG":
            debug_log_file = log_dir / "debug.log"
            handler_id = logger.add(
                str(debug_log_file),
                format=DEFAULT_FORMAT,
                level="DEBUG",
                rotation="20 MB",
                retention="7 days",
                compression="zip",
                backtrace=True,
                diagnose=True,
                enqueue=True,
                catch=True
            )
            self._handler_ids.append(handler_id)
    
    def _configure_third_party_loggers(self) -> None:
        """配置第三方库的日志级别"""
        import logging

        # 根据日志级别判断是否为调试模式
        is_debug = self.config.logging.level == "DEBUG"        
        # 降低第三方库的日志级别
        third_party_loggers = [
            "uvicorn",
            "uvicorn.access",
            "uvicorn.error",
            "fastapi",
            "asyncio",
            "mcp",
        ]
        
        for logger_name in third_party_loggers:
            logging.getLogger(logger_name).setLevel(
                logging.WARNING if not is_debug else logging.INFO
            )
    
    def _setup_exception_handler(self) -> None:
        """设置全局异常处理器"""
        def handle_exception(exc_type, exc_value, traceback):
            """全局异常处理器"""
            logger.error(
                "Uncaught exception: {}: {}",
                exc_type.__name__,
                exc_value
            )
        
        sys.excepthook = handle_exception
    
    def cleanup(self) -> None:
        """清理日志处理器"""
        for handler_id in self._handler_ids:
            try:
                logger.remove(handler_id)
            except ValueError:
                # 处理器已被移除
                pass
        self._handler_ids.clear()


def get_logger(name: str) -> Any:
    """
    获取带有模块名称绑定的 logger 实例
    
    Args:
        name: 模块名称，通常是 __name__
    
    Returns:
        绑定了模块名称的 logger 实例
    """
    return logger.bind(name=name)


def configure_logging(config: Config) -> LoggingManager:
    """
    配置项目日志系统
    
    Args:
        config: 服务器配置对象
    
    Returns:
        日志管理器实例
    """
    logging_manager = LoggingManager(config)
    logging_manager.setup_logging()
    return logging_manager


# 便捷的日志记录函数
def log_startup_info(config: Config) -> None:
    """记录启动信息"""
    startup_logger = get_logger(__name__)
    startup_logger.info("🚀 Starting libvirt-mcp-server")
    startup_logger.info("Configuration: {}", config.model_dump_json(indent=2))
    startup_logger.info("Debug mode: {}", config.logging.level == "DEBUG")
    startup_logger.info("Log level: {}", config.logging.level)


def log_shutdown_info() -> None:
    """记录关闭信息"""
    shutdown_logger = get_logger(__name__)
    shutdown_logger.info("🛑 Shutting down libvirt-mcp-server")


# 上下文管理器，用于结构化日志记录
class LogContext:
    """日志上下文管理器，用于绑定结构化数据到日志记录"""
    
    def __init__(self, **context_data):
        """
        初始化日志上下文
        
        Args:
            **context_data: 要绑定到日志的上下文数据
        """
        self.context_data = context_data
        self.bound_logger = None
    
    def __enter__(self):
        """进入上下文"""
        self.bound_logger = logger.bind(**self.context_data)
        return self.bound_logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        self.bound_logger = None


# 装饰器，用于自动记录函数调用
def log_function_call(
    level: str = "DEBUG",
    include_args: bool = True,
    include_result: bool = True
):
    """
    装饰器，自动记录函数调用和返回值
    
    Args:
        level: 日志级别
        include_args: 是否包含函数参数
        include_result: 是否包含函数返回值
    """
    def decorator(func: Callable) -> Callable:
        import functools
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = get_logger(func.__module__)
            
            # 记录函数调用
            if include_args:
                func_logger.log(
                    level,
                    "🔄 Calling {}() with args={}, kwargs={}",
                    func.__name__,
                    args,
                    kwargs
                )
            else:
                func_logger.log(level, "🔄 Calling {}()", func.__name__)
            
            try:
                result = func(*args, **kwargs)
                
                # 记录函数返回
                if include_result:
                    func_logger.log(
                        level,
                        "✅ {}() returned: {}",
                        func.__name__,
                        result
                    )
                else:
                    func_logger.log(level, "✅ {}() completed", func.__name__)
                
                return result
            except Exception as e:
                # 记录函数异常
                func_logger.error(
                    "❌ {}() failed with {}: {}",
                    func.__name__,
                    type(e).__name__,
                    str(e)
                )
                raise
        
        return wrapper
    return decorator


# 异步版本的函数调用装饰器
def log_async_function_call(
    level: str = "DEBUG",
    include_args: bool = True,
    include_result: bool = True
):
    """
    异步装饰器，自动记录异步函数调用和返回值
    
    Args:
        level: 日志级别
        include_args: 是否包含函数参数
        include_result: 是否包含函数返回值
    """
    def decorator(func: Callable) -> Callable:
        import functools
        import asyncio
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_logger = get_logger(func.__module__)
            
            # 记录函数调用
            if include_args:
                func_logger.log(
                    level,
                    "🔄 Calling async {}() with args={}, kwargs={}",
                    func.__name__,
                    args,
                    kwargs
                )
            else:
                func_logger.log(level, "🔄 Calling async {}()", func.__name__)
            
            try:
                result = await func(*args, **kwargs)
                
                # 记录函数返回
                if include_result:
                    func_logger.log(
                        level,
                        "✅ async {}() returned: {}",
                        func.__name__,
                        result
                    )
                else:
                    func_logger.log(level, "✅ async {}() completed", func.__name__)
                
                return result
            except Exception as e:
                # 记录函数异常
                func_logger.error(
                    "❌ async {}() failed with {}: {}",
                    func.__name__,
                    type(e).__name__,
                    str(e)
                )
                raise
        
        return wrapper
    return decorator


# 性能监控装饰器
def log_performance(threshold_ms: float = 1000.0, level: str = "INFO"):
    """
    性能监控装饰器，记录函数执行时间
    
    Args:
        threshold_ms: 执行时间阈值（毫秒），超过此值会记录警告
        level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        import functools
        import time
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = get_logger(func.__module__)
            start_time = time.perf_counter()
            
            try:
                result = func(*args, **kwargs)
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                if duration_ms > threshold_ms:
                    func_logger.warning(
                        "⚠️ {}() took {:.2f}ms (threshold: {:.2f}ms)",
                        func.__name__,
                        duration_ms,
                        threshold_ms
                    )
                else:
                    func_logger.log(
                        level,
                        "⏱️ {}() took {:.2f}ms",
                        func.__name__,
                        duration_ms
                    )
                
                return result
            except Exception as e:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                func_logger.error(
                    "❌ {}() failed after {:.2f}ms with {}: {}",
                    func.__name__,
                    duration_ms,
                    type(e).__name__,
                    str(e)
                )
                raise
        
        return wrapper
    return decorator


# 异步性能监控装饰器
def log_async_performance(threshold_ms: float = 1000.0, level: str = "INFO"):
    """
    异步性能监控装饰器，记录异步函数执行时间
    
    Args:
        threshold_ms: 执行时间阈值（毫秒），超过此值会记录警告
        level: 日志级别
    """
    def decorator(func: Callable) -> Callable:
        import functools
        import time
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            func_logger = get_logger(func.__module__)
            start_time = time.perf_counter()
            
            try:
                result = await func(*args, **kwargs)
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                if duration_ms > threshold_ms:
                    func_logger.warning(
                        "⚠️ async {}() took {:.2f}ms (threshold: {:.2f}ms)",
                        func.__name__,
                        duration_ms,
                        threshold_ms
                    )
                else:
                    func_logger.log(
                        level,
                        "⏱️ async {}() took {:.2f}ms",
                        func.__name__,
                        duration_ms
                    )
                
                return result
            except Exception as e:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                func_logger.error(
                    "❌ async {}() failed after {:.2f}ms with {}: {}",
                    func.__name__,
                    duration_ms,
                    type(e).__name__,
                    str(e)
                )
                raise
        
        return wrapper
    return decorator

