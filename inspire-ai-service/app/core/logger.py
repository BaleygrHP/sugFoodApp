import logging
import os
import sys

DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_LEVEL = "INFO"

# Global logger dictionary to avoid creating multiple loggers for the same name
_loggers = {}


class ColoredFormatter(logging.Formatter):
    """Custom formatter with color support for console output"""
    # ANSI color codes
    green = "\x1b[1;32m"
    blue = "\x1b[36m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: blue + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logger(
    name: str,
    log_level: str | None = None,
    use_colors: bool = True,
    log_file: str | None = None,
) -> logging.Logger:
    """
    Get or create a logger with the given name

    Args:
        name: Logger name (typically __name__ from the calling module)
        log_level: Optional log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_colors: Whether to use colored output for console logging
        log_file: Optional log file path

    Returns:
        Configured logger instance
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)

    if not logger.handlers:
        level = getattr(logging, log_level or DEFAULT_LOG_LEVEL)
        logger.setLevel(level)

        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
            file_format = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

        if use_colors:
            # Debug handler
            debug_handler = logging.StreamHandler(sys.stdout)
            debug_handler.setLevel(logging.DEBUG)
            debug_handler.setFormatter(ColoredFormatter())
            debug_handler.addFilter(lambda record: record.levelno == logging.DEBUG)

            # Info handler
            info_handler = logging.StreamHandler(sys.stdout)
            info_handler.setLevel(logging.INFO)
            info_handler.setFormatter(ColoredFormatter())
            info_handler.addFilter(lambda record: record.levelno == logging.INFO)

            # Warning handler
            warn_handler = logging.StreamHandler(sys.stdout)
            warn_handler.setLevel(logging.WARNING)
            warn_handler.setFormatter(ColoredFormatter())
            warn_handler.addFilter(lambda record: record.levelno == logging.WARNING)

            # Error and Critical handler
            error_handler = logging.StreamHandler(sys.stderr)
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(ColoredFormatter())

            # Add all handlers
            logger.addHandler(debug_handler)
            logger.addHandler(info_handler)
            logger.addHandler(warn_handler)
            logger.addHandler(error_handler)
        else:
            # Simple console handler without colors
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            format_str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            console_format = logging.Formatter(format_str)
            console_handler.setFormatter(console_format)
            logger.addHandler(console_handler)

    _loggers[name] = logger

    return logger


# Default application logger
logger = get_logger(
    "jarvis_helpdesk_agentic",
    use_colors=True
)
