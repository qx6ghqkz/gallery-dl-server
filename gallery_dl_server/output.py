# -*- coding: utf-8 -*-

import os
import sys
import logging
import re
import pickle
import io

from mmap import mmap
from multiprocessing import Queue
from typing import TextIO, Any

import aiofiles

from gallery_dl import output, job

from . import options, utils

args = options.custom_args

if args is not None:
    log_dir = args.log_dir
    log_level = args.log_level.upper()
    access_log = args.access_log

    if args.log_level == "trace":
        log_level = "DEBUG"
else:
    log_dir = os.path.expanduser("~")
    log_level = "INFO"
    access_log = False

LOG_FILE = utils.get_log_file_path(log_dir, "app.log")
LOG_LEVEL: int = getattr(logging, log_level, logging.INFO)
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
            if line.strip():
                self.log(level, line.rstrip())


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

    register_handler(handler)
    return handler


def setup_file_handler(file: str, formatter: logging.Formatter):
    """Set up a file handler for logging."""
    os.makedirs(os.path.dirname(file), exist_ok=True)

    handler = logging.FileHandler(file, mode="a", encoding="utf-8", delay=False)
    handler.setFormatter(formatter)

    register_handler(handler)
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
        register_handler(handler)

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

        register_handler(handler)
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
                handler.close()
                root.removeHandler(handler)

    root.addHandler(queue_handler)
    register_handler(handler)


class QueueHandler(logging.Handler):
    """Custom logging handler that sends log messages to a queue."""

    def __init__(self, queue: Queue):
        super().__init__()
        self.queue = queue

    def emit(self, record: logging.LogRecord):
        record.msg = self.format(record).strip()
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
    logger_writer = LoggerWriter()
    null_writer = NullWriter()

    if stdout:
        setattr(sys, "stdout", logger_writer)
    else:
        setattr(sys, "stdout", null_writer)

    if stderr:
        setattr(sys, "stderr", logger_writer)
    else:
        setattr(sys, "stderr", null_writer)


class LoggerWriter:
    """Log writes to stdout and stderr."""

    def __init__(self, level=logging.INFO):
        self.level = level
        self.logger = initialise_logging(type(self).__name__)

        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        self.console_handler = ConsoleProgress(self.logger)
        self.file_handler = FileProgress(self.logger)

        self.logger.addHandler(self.console_handler)
        self.logger.addHandler(self.file_handler)

        register_handler(self.console_handler, self.file_handler)

    def write(self, msg: str):
        """Prepare and then log messages."""
        if not msg.strip():
            return

        if msg.startswith("\r" + "* "):
            msg = f"Download successful: {msg[3:]}"

        if msg.startswith("# "):
            msg = f"File already exists or its ID is in a download archive: {msg[2:]}"
            self.level = logging.WARNING

        self.logger.log(self.level, msg.strip())

    def flush(self):
        pass


class ConsoleProgress(logging.Handler):
    """Custom handler for writing progress messages to the console."""

    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger
        self.formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)
        self.last_msg = ""

    def emit(self, record):
        """Write progress updates to stdout on the same line."""
        msg = self.format(record).strip()

        assert sys.__stdout__
        stdout = sys.__stdout__

        if "B/s" in msg and "B/s" in self.last_msg:
            stdout.write("\033[A")

            if len(msg) < len(self.last_msg):
                msg = msg.ljust(len(self.last_msg))

        stdout.write(msg + "\n")
        stdout.flush()

        self.last_msg = msg


class FileProgress(logging.FileHandler):
    """Custom FileHandler that handles progress updates."""

    def __init__(self, logger: logging.Logger):
        super().__init__(filename=LOG_FILE, mode="a", encoding="utf-8", delay=False)
        self.logger = logger
        self.formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)
        self.last_msg = ""

    def emit(self, record):
        """Override the emit method to handle progress updates."""
        msg = self.format(record).strip()

        if "B/s" in msg and "B/s" in self.last_msg:
            self.update_progress(msg)
        else:
            super().emit(record)

        self.last_msg = msg

    def update_progress(self, msg: str):
        """Write download progress to the log file on the same line."""
        mmapped_file = None
        try:
            with open(self.baseFilename, "r+b") as f:
                mmapped_file = mmap(f.fileno(), 0)
                self.overwrite_last_line(mmapped_file, msg)
        except Exception as e:
            self.logger.debug(f"Exception: {type(e).__name__}: {e}")
        finally:
            if mmapped_file:
                mmapped_file.close()

    def overwrite_last_line(self, mmapped_file: mmap, msg: str):
        """Overwrite the last line of a memory-mapped file with the given message."""
        last_newline_pos = mmapped_file.rfind(b"\n")
        second_last_newline_pos = mmapped_file.rfind(b"\n", 0, last_newline_pos)

        mmapped_file.seek(second_last_newline_pos + 1)

        new_msg = msg.encode("utf-8") + b"\n"
        new_size = mmapped_file.tell() + len(new_msg)

        mmapped_file.resize(new_size)
        mmapped_file.write(new_msg)
        mmapped_file.flush()


async def read_previous_line(file_path: str):
    """Return the previous line of a file."""
    async with aiofiles.open(file_path, "rb") as file:
        await file.seek(0, os.SEEK_END)
        position = await file.tell()

        if position == 0:
            return None

        last_line_found = False
        previous_line = b""

        while position > 0:
            await file.seek(position - 1)
            char = await file.read(1)
            if char == b"\n":
                if last_line_found:
                    previous_line = await file.readline()
                    break
                else:
                    last_line_found = True
            position -= 1

        if previous_line:
            return previous_line.decode("utf-8").rstrip()
        else:
            return None


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
        """Return logs captured by the handler."""
        return self.handler.get_logs()

    def close(self):
        """Close and remove the handler from the root logger."""
        self.handler.close()
        self.root.removeHandler(self.handler)


class StringHandler(logging.Handler):
    """Capture log messages and write them to a string object."""

    def __init__(self):
        super().__init__()
        self.buffer = io.StringIO()
        self.terminator = LOG_SEPARATOR

    def emit(self, record):
        msg = self.format(record)

        if msg.strip():
            self.buffer.write(msg.strip() + self.terminator)

    def get_logs(self):
        """Retrieve logs from the buffer."""
        logs = self.buffer.getvalue()
        return logs.rstrip(self.terminator)

    def close(self):
        """Close the log buffer and handler."""
        self.buffer.close()
        super().close()


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


def configure_uvicorn_logs():
    """Configure uvicorn logging behaviour."""
    main = logging.getLogger("uvicorn")
    error = logging.getLogger("uvicorn.error")

    if not access_log:
        error.addFilter(WebSocketFilter())

    return main


class WebSocketFilter(logging.Filter):
    """Filter out WebSocket connection logs."""

    def filter(self, record):
        return not (
            "WebSocket /ws/logs" in record.getMessage()
            or "connection open" in record.getMessage()
            or "connection closed" in record.getMessage()
        )


def register_handler(*handlers: logging.Handler):
    """Add handler to the logging manager."""
    logging_manager = LoggingManager()

    for handler in handlers:
        logging_manager.add_handler(handler)


async def close_handlers():
    """Close all registered logging handlers."""
    logging_manager = LoggingManager()
    logging_manager.close_all()


class LoggingManager:
    """Store logging handler instances for closure."""

    _instance: "LoggingManager | None" = None
    logger: "BasicLogger"

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(LoggingManager, cls).__new__(cls)
            cls._instance.logger = BasicLogger()
            cls._instance.logger.debug("Created new instance of LoggingManager.")

        return cls._instance

    def __init__(self):
        if not hasattr(self, "handlers"):
            self.handlers: list[logging.Handler] = []
            self.logger.debug("Initialized handlers list.")

    def add_handler(self, handler: logging.Handler):
        """Add handler to list of handlers."""
        self.handlers.append(handler)
        self.logger.debug(f"Added handler: {handler}")

    def close_all(self):
        """Close all logging handlers and clear the list."""
        for handler in self.handlers[:]:
            handler.close()
            self.logger.debug(f"Closed handler: {handler}")

        self.handlers.clear()
        self.logger.debug("Cleared handlers list.")
        self.logger.close()


class BasicLogger(logging.Logger):
    """Basic logger for debugging."""

    def __init__(self):
        super().__init__(name=type(self).__name__, level=LOG_LEVEL)
        self.addHandler(BasicHandler())

    def close(self):
        """Close and remove all handlers from the logger."""
        for handler in self.handlers[:]:
            handler.close()
            self.removeHandler(handler)


class BasicHandler(logging.Handler):
    """Basic handler for debugging."""

    def __init__(self):
        super().__init__()
        self.formatter = Formatter(LOG_FORMAT_DEBUG, LOG_FORMAT_DATE)

    def emit(self, record):
        sys.stdout.write(self.format(record) + "\n")
