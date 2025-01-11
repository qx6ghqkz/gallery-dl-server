import os
import sys
import logging
import pickle
import re

from gallery_dl import output, job


LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "app.log")
LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FORMAT_DEBUG = (
    "%(asctime)s [%(name)s] [%(filename)s:%(lineno)d] [%(levelname)s] %(message)s"
)
LOG_FORMAT_DATE = "%Y-%m-%d %H:%M:%S"


def initialise_logging(
    name="gallery-dl-server", stream=sys.stdout, file=LOG_FILE, level=LOG_LEVEL
):
    """Set up basic logging functionality for gallery-dl-server."""
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        formatter = Formatter(LOG_FORMAT, LOG_FORMAT_DATE)

        handler_console = logging.StreamHandler(stream)
        handler_console.setFormatter(formatter)

        logger.addHandler(handler_console)

        if file:
            os.makedirs(os.path.dirname(file), exist_ok=True)

            handler_file = logging.FileHandler(
                file, mode="a", encoding="utf-8", delay=False
            )
            handler_file.setFormatter(formatter)

            logger.addHandler(handler_file)

    logger.setLevel(level)

    logger.propagate = False

    return logger


class Formatter(logging.Formatter):
    """Custom formatter which removes ANSI escape sequences."""

    def format(self, record):
        record.levelname = record.levelname.lower()

        message = super().format(record)
        return remove_ansi_escape_sequences(message)


def remove_ansi_escape_sequences(text):
    """Remove ANSI escape sequences from the given text."""
    ansi_escape_pattern = re.compile(r"\x1B\[[0-?9;]*[mGKH]")
    return ansi_escape_pattern.sub("", text)


def get_logger(name):
    """Return a logger with the specified name."""
    return logging.getLogger(name)


def get_blank_logger(name="blank", stream=sys.stdout, level=logging.INFO):
    """Return a basic logger with no formatter."""
    logger = logging.getLogger(name)
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
        ulog = logging.getLogger("unsupportedfile")
        ulog.addHandler(handler)
        ulog.propagate = False

        setattr(job.Job, "ulog", ulog)

    return logger


def capture_logs(log_queue):
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

    def __init__(self, queue):
        super().__init__()
        self.queue = queue

    def emit(self, record):
        record.msg = remove_ansi_escape_sequences(self.format(record))
        record.args = ()
        record_dict = record_to_dict(record)

        self.queue.put(record_dict)


def record_to_dict(record):
    """Convert a log record into a dictionary."""
    record_dict = record.__dict__.copy()
    record_dict["level"] = record.levelno

    sanitise_dict(record_dict)

    return record_dict


def sanitise_dict(record_dict):
    """Remove non-serialisable values from a dictionary."""
    keys_to_remove = []

    for key, value in record_dict.items():
        if not is_serialisable(value):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        record_dict.pop(key)


def is_serialisable(value):
    """Check if a value can be serialised."""
    try:
        pickle.dumps(value)
        return True
    except Exception:
        return False


def dict_to_record(record_dict):
    """Convert a dictionary back into a log record."""
    return logging.LogRecord(**record_dict)


def stdout_write(s):
    """Write directly to stdout."""
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def stderr_write(s):
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

    def write(self, msg):
        if not msg.strip():
            return

        if msg.startswith("# "):
            msg = f"File already exists or its ID is in a download archive: {msg.removeprefix('# ')}"
            self.level = logging.WARNING

        self.logger.log(self.level, msg.strip())

    def flush(self):
        pass


class NullWriter:
    """Suppress writes to stdout or stderr."""

    def write(self, msg):
        pass

    def flush(self):
        pass
