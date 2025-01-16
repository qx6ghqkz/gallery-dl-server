# -*- coding: utf-8 -*-

import os
import sys
import logging
import re
import pickle
import io

from multiprocessing import Queue
from typing import TextIO, Any

from gallery_dl import output, job

from . import utils


LOG_FILE = os.path.join(utils.dirname_parent(__file__), "logs", "app.log")
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FORMAT_DEBUG = "%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s"
LOG_FORMAT_DATE = "%Y-%m-%d %H:%M:%S"
LOG_SEPARATOR = "/sep/"


def initialise_logging(
    name=utils.get_package_name(), stream=sys.stdout, file=LOG_FILE, level=LOG_LEVEL
):
    """Set up basic logging functionality for gallery-dl-server."""
    logger = Logger(name)

    if not logger.hasHandlers():
        formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)

        handler_console = setup_stream_handler(stream, formatter)
        logger.addHandler(handler_console)

        if file:
            handler_file = setup_file_handler(file, formatter)
            logger.addHandler(handler_file)

    logger.setLevel(level)
    logger.propagate = False

    return logger


class Logger(logging.Logger):
    """Custom logger which has a method to log multi-line messages."""

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)

    def log_multiline(self, level: int, message: str):
        """Log each line of a multi-line message separately."""
        for line in message.split("\n"):
            self.log(level, line)


class Formatter(logging.Formatter):
    """Custom formatter which removes ANSI escape sequences."""

    def format(self, record):
        record.levelname = record.levelname.lower()

        message = super().format(record)
        return remove_ansi_escape_sequences(message)


def remove_ansi_escape_sequences(text: str):
    """Remove ANSI escape sequences from the given text."""
    ansi_escape_pattern = re.compile(r"\x1B\[[0-?9;]*[mGKH]")
    return ansi_escape_pattern.sub("", text)


def setup_stream_handler(stream: TextIO | Any, formatter: logging.Formatter):
    """Set up a console handler for logging."""
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    return handler


def setup_file_handler(file: str, formatter: logging.Formatter):
    """Set up a file handler for logging."""
    os.makedirs(os.path.dirname(file), exist_ok=True)

    handler = logging.FileHandler(file, mode="a", encoding="utf-8", delay=False)
    handler.setFormatter(formatter)

    return handler


def get_logger(name: str | None = None):
    """Return a logger with the specified name."""
    return logging.getLogger(name)


def get_blank_logger(name="blank", stream=sys.stdout, level=logging.INFO):
    """Return a basic logger with no formatter."""
    logger = Logger(name)

    if not logger.hasHandlers():
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False

    return logger


def setup_logging(level=LOG_LEVEL):
    """Set up gallery-dl logging."""
    logger = output.initialize_logging(level)

    output.configure_standard_streams()
    output.configure_logging(level)

    handler = output.setup_logging_handler("unsupportedfile", fmt="{message}")

    if handler:
        ulog = logging.getLogger("unsupported")
        ulog.addHandler(handler)
        ulog.propagate = False

        setattr(job.Job, "ulog", ulog)

    return logger


def capture_logs(log_queue: Queue):
    """Send logs that reach the root logger to a queue."""
    root = logging.getLogger()
    queue_handler = QueueHandler(log_queue)

    if root.handlers:
        existing_handler = root.handlers[0]
        queue_handler.setFormatter(existing_handler.formatter)

        for handler in root.handlers[:]:
            if isinstance(handler, logging.StreamHandler):
                root.removeHandler(handler)

    root.addHandler(queue_handler)


class QueueHandler(logging.Handler):
    """Custom logging handler that sends log messages to a queue."""

    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        record.msg = remove_ansi_escape_sequences(self.format(record))
        record.args = ()
        record_dict = record_to_dict(record)

        self.queue.put(record_dict)


def record_to_dict(record: logging.LogRecord):
    """Convert a log record into a dictionary."""
    record_dict = record.__dict__.copy()
    record_dict["level"] = record.levelno

    sanitise_dict(record_dict)

    return record_dict


def sanitise_dict(record_dict: dict[str, Any]):
    """Remove non-serialisable values from a dictionary."""
    keys_to_remove = []

    for key, value in record_dict.items():
        if not is_serialisable(value):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        record_dict.pop(key)


def is_serialisable(value: Any):
    """Check if a value can be serialised."""
    try:
        pickle.dumps(value)
        return True
    except Exception:
        return False


def dict_to_record(record_dict: dict[str, Any]):
    """Convert a dictionary back into a log record."""
    return logging.LogRecord(**record_dict)


def stdout_write(s: str, /):
    """Write directly to stdout."""
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def stderr_write(s: str, /):
    """Write directly to stderr."""
    sys.stderr.write(s + "\n")
    sys.stderr.flush()


def redirect_standard_streams(stdout=True, stderr=True):
    """Redirect stdout and stderr to a logger or suppress them."""
    if stdout:
        setattr(sys, "stdout", LoggerWriter(level=logging.INFO))
    else:
        setattr(sys, "stdout", NullWriter())

    if stderr:
        setattr(sys, "stderr", LoggerWriter(level=logging.DEBUG))
    else:
        setattr(sys, "stderr", NullWriter())


class LoggerWriter:
    """Log writes to stdout and stderr."""

    def __init__(self, level=logging.INFO):
        self.level = level
        self.logger = initialise_logging(__name__)

    def write(self, msg: str):
        """Prepare and then log messages."""
        if not msg.strip():
            return

        if msg.startswith("# "):
            msg = f"File already exists or its ID is in a download archive: {msg[2:]}"
            self.level = logging.WARNING

        self.logger.log(self.level, msg.strip())

    def flush(self):
        pass


class NullWriter:
    """Suppress writes to stdout or stderr."""

    def write(self, msg: str):
        pass

    def flush(self):
        pass


class StringLogger:
    """Add StringHandler to the root logger and get logs."""

    def __init__(self, level=LOG_LEVEL):
        self.root = logging.getLogger()

        self.handler = StringHandler()
        self.handler.setLevel(level)

        self.root.addHandler(self.handler)

    def get_logs(self):
        """Return logs captured by StringHandler."""
        return self.handler.get_logs()

    def close(self):
        """Remove StringHandler from the root logger and close buffer."""
        self.root.removeHandler(self.handler)
        self.handler.close()


class StringHandler(logging.Handler):
    """Capture log messages and write them to a string object."""

    def __init__(self):
        super().__init__()
        self.buffer = io.StringIO()
        self.terminator = LOG_SEPARATOR

    def emit(self, record):
        msg = self.format(record)
        self.buffer.write(msg + self.terminator)

    def get_logs(self):
        """Retrieve logs from the string object."""
        logs = self.buffer.getvalue()
        return logs.rstrip(self.terminator)

    def close(self):
        super().close()
        self.buffer.close()


def last_line(message: str, string: str, case_sensitive=True):
    """Get the last line containing a string in a message."""
    lines = message.split("\n")

    for line in reversed(lines):
        if (string in line) if case_sensitive else (string.lower() in line.lower()):
            return line

    return message


def join(_list: list[str]):
    """Join a list of strings with commas and single quotes."""
    formatted_list = []

    for item in _list:
        formatted_list.append(f"'{item}'")

    return ", ".join(formatted_list)
