import sys
import logging

from gallery_dl import output, job


LOG_LEVEL = logging.INFO
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_FORMAT_DATE = "%Y-%m-%d %H:%M:%S"


def initialise_logging(file=None, stream=sys.stdout):
    root = logging.getLogger()

    formatter = logging.Formatter(LOG_FORMAT, LOG_FORMAT_DATE)

    handler_console = logging.StreamHandler(stream)
    handler_console.setFormatter(formatter)

    root.addHandler(handler_console)

    if file:
        handler_file = logging.FileHandler(file)
        handler_file.setFormatter(formatter)

        root.addHandler(handler_file)

    root.setLevel(LOG_LEVEL)

    return logging.getLogger("gallery-dl-server")


def get_logger(name):
    return logging.getLogger(name)


def get_blank_logger(name="blank", stream=sys.stdout, level=logging.INFO):
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(stream)

    logger.addHandler(handler)
    logger.setLevel(level)

    logger.propagate = False

    return logger


def stdout_write(s):
    sys.stdout.write(s + "\n")
    sys.stdout.flush()


def setup_logging():
    logger = output.initialize_logging(LOG_LEVEL)

    output.configure_standard_streams()
    output.configure_logging(LOG_LEVEL)

    handler = output.setup_logging_handler("unsupportedfile", fmt="{message}")

    if handler:
        ulog = job.Job.ulog = logging.getLogger("unsupportedfile")
        ulog.addHandler(handler)
        ulog.propagate = False

    return logger
