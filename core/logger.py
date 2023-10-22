# core/logger.py

import logging

# Define custom colors for logging levels
LOG_COLORS = {
    'DEBUG': 'cyan',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'red,bg_white',
}


class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to logging levels."""

    COLORS = {
        'green': '\033[0;32m',
        'yellow': '\033[0;33m',
        'red': '\033[0;31m',
        'cyan': '\033[0;36m',
        'bg_white': '\033[47m',
        'reset': '\033[0m'
    }

    def format(self, record):
        log_color = LOG_COLORS.get(record.levelname, 'reset')
        color_seq = self.colorize(log_color)
        record.msg = f"{color_seq}{record.msg}{self.COLORS['reset']}"
        return super().format(record)

    def colorize(self, log_color):
        colors = log_color.split(',')
        color_seq = ''
        for color in colors:
            color_seq += self.COLORS[color]
        return color_seq


# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# Create formatter and add it to the handlers
formatter = ColoredFormatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(ch)
