# -*- coding: utf-8 -*-

import os
import sys

import asyncio
import io
import logging
import pickle
import queue
import re
import threading

from mmap import mmap
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Lock
from typing import TextIO, Any

import aiofiles

from gallery_dl import output, job

from . import options, utils

if utils.WINDOWS:
    import msvcrt
else:
    import termios
    import tty

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

async_lock: asyncio.Lock | None = asyncio.Lock()
thread_lock: "threading.Lock | None" = threading.Lock()


def initialise_logging(
    name=utils.get_package_name(),
    stream: TextIO | Any = sys.__stdout__,
    file=LOG_FILE,
    level=LOG_LEVEL,
    lock: Lock | None = None,
):
    """Set up basic logging functionality for gallery-dl-server."""
    logger = Logger(name, level, lock)
    logger.propagate = False

    if not logger.hasHandlers():
        formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)

        handler_console = setup_stream_handler(stream, formatter)
        logger.addHandler(handler_console)

        if file:
            handler_file = setup_file_handler(file, formatter)
            logger.addHandler(handler_file)

    return logger


class Logger(logging.Logger):
    """Custom logger which supports async logging and has a method to log multi-line messages."""

    def __init__(self, name: str, level=logging.NOTSET, process_lock: Lock | None = None):
        super().__init__(name, level)
        self.async_lock = async_lock
        self.process_lock = process_lock

    def log_multiline(self, level: int, msg: str):
        """Log each line of a multi-line message separately."""
        for line in msg.split("\n"):
            if line.strip():
                self.log(level, line)

    def handle(self, record):
        """Override handle method to call the async version."""
        if self.process_lock:
            with self.process_lock:
                self._handle_record(record)
        else:
            self._handle_record(record)

    def _handle_record(self, record: logging.LogRecord):
        """Handle log records in an event loop."""
        try:
            event_loop = asyncio.get_running_loop()
            event_loop.create_task(self.handle_async(record))
        except RuntimeError:
            asyncio.run(self.handle_async(record))

    async def handle_async(self, record: logging.LogRecord):
        """Perform asynchronous handling of log records."""
        if self.async_lock:
            async with self.async_lock:
                super().handle(record)
        else:
            super().handle(record)


class Formatter(logging.Formatter):
    """Custom formatter for log messages."""

    def format(self, record):
        record.levelname = record.levelname.lower()

        msg = super().format(record)
        return remove_ansi_escape_sequences(msg).rstrip()


def remove_ansi_escape_sequences(text: str, /):
    """Remove ANSI escape sequences from the given text."""
    ansi_escape_pattern = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape_pattern.sub("", text)


def setup_stream_handler(stream: TextIO | Any, formatter: logging.Formatter):
    """Set up a console handler for logging."""
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setFormatter(formatter)
    register_handler(stream_handler)

    return stream_handler


def setup_file_handler(file: str, formatter: logging.Formatter):
    """Set up a file handler for logging."""
    os.makedirs(os.path.dirname(file), exist_ok=True)

    file_handler = logging.FileHandler(file, mode="a", encoding="utf-8", delay=False)
    file_handler.setFormatter(formatter)
    register_handler(file_handler)

    return file_handler


def get_logger(name: str | None = None):
    """Return a logger with the specified name."""
    return logging.getLogger(name)


def get_blank_logger(name="blank", stream=sys.stdout, level=logging.INFO):
    """Return a basic logger with no formatter."""
    logger = Logger(name, level)
    logger.propagate = False

    if not logger.hasHandlers():
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        register_handler(handler)

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


def capture_logs(log_queue: Queue[dict[str, Any]]):
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

    def __init__(self, queue: Queue[dict[str, Any]]):
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


def redirect_standard_streams(level=logging.INFO, lock: Lock | None = None):
    """Redirect stdout and stderr streams and log at level."""
    logger_writer = LoggerWriter(level, lock)

    setattr(sys, "stdout", logger_writer)
    setattr(sys, "stderr", logger_writer)


class LoggerWriter:
    """Log writes to stdout and stderr."""

    def __init__(self, level=logging.INFO, process_lock: Lock | None = None):
        self.level = level
        self.stream = sys.__stdout__
        self.logger = initialise_logging(type(self).__name__, lock=process_lock)

        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)

        self.stream_handler = ConsoleProgress(self.stream)
        self.file_handler = FileProgress()

        self.logger.addHandler(self.stream_handler)
        self.logger.addHandler(self.file_handler)

        register_handler(self.stream_handler, self.file_handler)

    def write(self, msg: str, /):
        """Prepare and log messages."""
        msg = msg.strip()

        if not msg:
            return

        if msg.startswith("* "):
            msg = f"Download successful: {msg[2:]}"

        if msg.startswith("# "):
            msg = f"File already exists or is in download archive: {msg[2:]}"
            return self.logger.log(logging.WARNING, msg)

        self.logger.log(self.level, msg)

    def flush(self):
        pass


class NullStream(io.TextIOBase):
    """Suppress writes to stdout or stderr."""

    def write(self, _: str, /):
        pass

    def flush(self):
        pass


class ConsoleProgress(logging.StreamHandler):
    """Custom stream handler that can handle progress updates."""

    def __init__(self, stream: TextIO | Any = NullStream()):
        super().__init__(stream)
        self.stream: TextIO | Any
        self.console_manager = ConsoleManager(self.stream)
        self.formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)
        self.last_msg = ""
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.process_queue, daemon=True)
        self.thread.start()

    def emit(self, record):
        """Override emit method to queue progress updates."""
        msg = self.format(record)

        if "B/s" in msg and "B/s" in self.last_msg:
            self.queue.put(msg)
        else:
            super().emit(record)

        self.last_msg = msg

    def process_queue(self):
        """Process logging queue in a separate thread."""
        while True:
            msg = self.queue.get()
            if msg is None:
                break
            self.write_to_console(msg)

    def write_to_console(self, msg: str):
        """Write progress updates to stdout asynchronously."""
        with self.console_manager as cm:
            cm.restore_position()

            self.stream.write(f"\033[A\033[K{msg}\n")
            self.stream.flush()

            cm.save_position()

    def close(self):
        """Stop logging thread and close handler."""
        self.queue.put(None)
        self.thread.join()
        super().close()


class ConsoleManager:
    """Save and restore cursor positions in the terminal."""

    def __init__(self, stream: TextIO | Any = sys.__stdout__):
        self.stream = stream
        self.lock = thread_lock
        self.saved_positions: list[tuple[int, int]] = []
        self.original_position = None

    def getch(self):
        """Read a single character from stdin without waiting for Enter."""
        if os.name == "nt":
            return msvcrt.getch().decode("utf-8")
        else:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch

    def get_cursor_position(self):
        """Get the current cursor position."""
        self.stream.write("\033[6n")
        self.stream.flush()

        response = ""
        while True:
            char = self.getch()
            response += char
            if char == "R":
                break
        try:
            y, x = map(int, response[2:-1].split(";"))
            return y, x
        except ValueError:
            return None

    def save_position(self):
        """Save the current cursor position."""
        if self.lock:
            self.lock.acquire()
        try:
            position = self.get_cursor_position()
            if position:
                self.saved_positions.append(position)
        finally:
            if self.lock:
                self.lock.release()

    def restore_position(self):
        """Restore the last saved cursor position."""
        if self.lock:
            self.lock.acquire()
        try:
            if self.saved_positions:
                y, x = self.saved_positions.pop()
                self.stream.write(f"\033[{y};{x}H")
                self.stream.flush()
        finally:
            if self.lock:
                self.lock.release()

    def __enter__(self):
        """Save the original position when entering the context."""
        if self.lock:
            self.lock.acquire()
        try:
            self.original_position = self.get_cursor_position()
            return self
        finally:
            if self.lock:
                self.lock.release()

    def __exit__(self, exc_type, exc_value, traceback):
        """Restore the original position when exiting the context."""
        if self.lock:
            self.lock.acquire()
        try:
            if self.original_position:
                y, x = self.original_position
                self.stream.write(f"\033[{y};{x}H")
                self.stream.flush()
        finally:
            if self.lock:
                self.lock.release()


class FileProgress(logging.FileHandler):
    """Custom file handler that can handle progress updates."""

    def __init__(self, filename=LOG_FILE, mode="a", encoding="utf-8", delay=False):
        super().__init__(filename, mode, encoding, delay)
        self.logger = logging.getLogger("LoggerWriter")
        self.formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)
        self.last_msg = ""
        self.last_pos = 0
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self.process_queue, daemon=True)
        self.thread.start()

    def emit(self, record):
        """Override emit method to queue progress updates."""
        msg = self.format(record)

        if "B/s" in msg and "B/s" in self.last_msg:
            self.queue.put(msg)
        else:
            super().emit(record)

        self.last_msg = msg

    def process_queue(self):
        """Process logging queue in a separate thread."""
        while True:
            msg = self.queue.get()
            if msg is None:
                break
            self.write_to_file(msg)

    def write_to_file(self, msg: str):
        """Write download progress to the log file asynchronously."""
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
        """Overwrite line from last saved position in memory-mapped file."""
        if self.last_pos == 0:
            last_npos = mmapped_file.rfind(b"\n")
            self.last_pos = mmapped_file.rfind(b"\n", 0, last_npos) + 1

        mmapped_file.seek(self.last_pos)

        new_msg = msg.encode("utf-8")
        new_msg_length = len(new_msg)
        last_msg_length = len(self.last_msg.encode("utf-8"))

        new_size = self.last_pos + new_msg_length + 1
        if new_size > os.path.getsize(self.baseFilename):
            mmapped_file.resize(new_size)

        padding = b""
        if new_msg_length < last_msg_length:
            padding = b" " * (last_msg_length - new_msg_length)

        mmapped_file.write(new_msg + padding + b"\n")
        mmapped_file.flush()

    def close(self):
        """Stop logging thread and close handler."""
        self.queue.put(None)
        self.thread.join()
        super().close()


async def read_previous_line(file_path: str, last_position: int):
    """Return the previous line of a file or from a given position."""
    async with aiofiles.open(file_path, "r", encoding="utf-8") as file:
        previous_line = ""
        found_last_line = False

        if last_position == 0:
            position = await file.seek(0, os.SEEK_END)
            if position == 0:
                return previous_line, position

            while position > 0:
                await file.seek(position - 1)
                char = await file.read(1)
                if char == "\n":
                    if found_last_line:
                        previous_line = await file.readline()
                        break
                    else:
                        found_last_line = True
                position -= 1
        else:
            position = await file.seek(last_position)
            previous_line = await file.readline()

        return previous_line, position


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
            self.buffer.write(msg + self.terminator)

    def get_logs(self):
        """Retrieve logs from the buffer."""
        logs = self.buffer.getvalue()
        return logs.rstrip(self.terminator)

    def close(self):
        """Close the log buffer and handler."""
        self.buffer.close()
        super().close()


def last_line(msg: str, string: str, case_sensitive=True):
    """Get the last line containing a string in a message."""
    lines = msg.split("\n")

    for line in reversed(lines):
        if (string in line) if case_sensitive else (string.lower() in line.lower()):
            return line

    return None


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
        msg = record.getMessage()
        strings = ["WebSocket /ws/logs", "connection open", "connection closed"]
        return not any(string in msg for string in strings)


def register_handler(*handlers: logging.Handler):
    """Add handler to the logging manager."""
    logging_manager = LoggingManager()

    for handler in handlers:
        logging_manager.add_handler(handler)


def close_handlers():
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
        self.propagate = False

    def close(self):
        """Close and remove all handlers from the logger."""
        for handler in self.handlers[:]:
            handler.close()
            self.removeHandler(handler)


class BasicHandler(logging.Handler):
    """Basic handler for debugging."""

    def __init__(self):
        super().__init__()
        self.formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)

    def emit(self, record):
        sys.stdout.write(self.format(record) + "\n")
