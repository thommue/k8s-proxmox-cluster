import sys
import logging
from colorama import Fore, Style, init


# Initialize colorama for cross-platform compatibility
init(autoreset=True)

# Define colors for each log level using colorama Fore colors
LOG_COLORS = {
    "DEBUG": Fore.CYAN,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


class ColoredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Get color for the specific log level, or no color if not found
        log_color = LOG_COLORS.get(record.levelname, "")
        # Format the log message with the color and reset it afterward
        message = super().format(record)
        return f"{log_color}{message}{Style.RESET_ALL}"


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColoredFormatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
