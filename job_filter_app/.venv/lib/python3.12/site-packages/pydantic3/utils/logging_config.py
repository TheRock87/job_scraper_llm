"""
Simple logger wrapper over Loguru
"""
import sys
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import colorlog
import json


class LogConsole:
    """Class for pretty log output with colored module name"""

    def __init__(self, name):
        """Initialize with module name"""
        self.name = name
        self.console = Console(width=120)

    def print_json(self, message="", data=None):
        """Print JSON with colored module name and nice panel"""

        # print with colorlog
        colorlog.basicConfig(
            level='INFO',
            format='%(log_color) s%(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Format JSON as a string with indentation and ensure all Unicode symbols are properly displayed
        json_str = json.dumps(
            data,
            indent=2,
            ensure_ascii=False,  # Important: disable ASCII-only output to support Unicode characters
            sort_keys=False  # Preserve original key order
        )

        # Create syntax-highlighted JSON
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True, word_wrap=True)

        # Create panel with border and title
        panel = Panel(
            syntax,
            title=f"[bold blue]{message}[/bold blue]" if message else "[bold blue]Form Data[/bold blue]",
            border_style="green",
            expand=True,
            padding=(0, 1),
            width=115
        )

        # Print the panel
        self.console.print(panel)


class SimpleLogger:
    """Simple wrapper over Loguru with global log visibility management"""

    # Static field to control visibility of agent module logs
    _show_agents_logs = True
    _verbose = False
    _instances = {}
    _name = "pydantic3.agents"

    def __init__(self, name, extra=None):
        """
        Initialize logger

        Args:
            name: Logger name
            extra: Additional fields to bind to the logger
        """
        self.name = name

        # Save additional fields
        self.extra = extra or {}

        # Add instance to dictionary
        SimpleLogger._instances[name] = self

        # Configure basic formatting
        self._configure_logger()
        self.console = LogConsole(name)

        # If agent logs are disabled but this is a logger from the agents module - enable it
        if not SimpleLogger._show_agents_logs and name.startswith(SimpleLogger._name):
            logger.enable(name)

    @classmethod
    def set_verbose(cls, verbose):
        """Set verbose mode"""
        cls._verbose = verbose

    @classmethod
    def set_agents_logs_visible(cls, visible):
        """
        Globally enables or disables logs from pydantic3.agents modules

        Args:
            visible: True - show logs from agents, False - hide
        """
        cls._show_agents_logs = visible

        # Globally enable or disable agent logs
        if visible:
            logger.enable(cls._name)
        else:
            logger.disable(cls._name)

            # Exception for active loggers so they can see their own logs
            for name, instance in cls._instances.items():
                if name.startswith(cls._name):
                    logger.enable(name)

    def _configure_logger(self):
        """Configure logger with basic parameters"""
        # Configure basic formatting
        logger.configure(
            handlers=[{
                "sink": sys.stdout,
                "format": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
                "level": "DEBUG",
                "serialize": False  # Disable serialization to preserve Unicode characters
            }]
        )

        # Disable logs from external libraries
        for lib in ["httpx", "httpcore", "urllib3"]:
            logger.disable(lib)

    def _prepare_json_message(self, obj, *args, **kwargs):
        """Prepare objects for logging with Unicode support"""
        # If the first argument is a string, return it as is
        if isinstance(obj, str):
            return obj

        # If it's a dictionary, list or other object that can be serialized to JSON
        try:
            # Try to serialize with Unicode support
            return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False)
        except (TypeError, ValueError):
            # If serialization failed, return string representation
            return str(obj)

    def trace(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).trace(message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).info(message, *args, **kwargs)

    def success(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).success(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).error(message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).exception(message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).critical(message, *args, **kwargs)

    def log(self, level, message, *args, **kwargs):
        message = self._prepare_json_message(message, *args, **kwargs)
        return logger.bind(name=self.name, **self.extra).log(level, message, *args, **kwargs)

    def bind(self, **kwargs):
        """Bind additional data to the logger"""
        # Create new extra data by combining existing with new
        new_extra = {**self.extra, **kwargs}
        # Return a new SimpleLogger instance with the same parameters but updated extra
        return SimpleLogger(self.name, extra=new_extra)

    def log_json(self, level, message, data):
        """Log JSON with colored formatting via console"""
        self.console.print_json(message=message, data=data)


# Basic logger configuration
logger.remove()  # Remove default handlers
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    level="INFO",  # Default level INFO
    serialize=False  # Disable serialization to preserve Unicode characters
)
