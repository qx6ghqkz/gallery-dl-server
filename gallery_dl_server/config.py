import os
import logging

from collections.abc import MutableMapping

from gallery_dl import config

from . import output


log = output.initialise_logging(__name__)

_config = config._config
_files = config._files


def clear():
    """Clear loaded configuration."""
    config.clear()


def get_default_configs():
    """Return default gallery-dl configuration file locations."""
    if os.name == "nt":
        _default_configs = [
            "%APPDATA%\\gallery-dl\\config.json",
            "%USERPROFILE%\\gallery-dl\\config.json",
            "%USERPROFILE%\\gallery-dl.conf",
        ]
    else:
        _default_configs = [
            "/etc/gallery-dl.conf",
            "${XDG_CONFIG_HOME}/gallery-dl/config.json"
            if os.environ.get("XDG_CONFIG_HOME")
            else "${HOME}/.config/gallery-dl/config.json",
            "${HOME}/.gallery-dl.conf",
        ]

    return _default_configs


def load(_configs):
    """Load configuration files."""
    exit_code = None
    loads = 0

    if not os.path.isfile("/.dockerenv"):
        _configs = get_default_configs()

    if config.log.level <= logging.ERROR:
        config.log.setLevel(logging.CRITICAL)

    for path in _configs:
        try:
            config.load([path], strict=True)
        except SystemExit as e:
            if not exit_code:
                exit_code = e.code
        else:
            loads += 1

    if loads > 0:
        log.info(f"Loaded gallery-dl configuration file(s): {_files}")
    elif exit_code:
        log.error(f"Unable to load configuration file: Exit code {exit_code}")

        if exit_code == 1:
            log.info(f"Valid configuration file locations: {_configs}")


def add(dict=None, conf=_config, fixed=False, **kwargs):
    """Add entries to a nested dictionary."""
    if dict:
        for k, v in dict.items():
            if isinstance(v, MutableMapping):
                if k in conf.keys() or not fixed:
                    conf[k] = add(v, conf.get(k) or {}, fixed=fixed)[0]
            elif isinstance(v, list):
                if k in conf.keys() or not fixed:
                    for i in v:
                        if not isinstance(i, MutableMapping):
                            if i not in conf.get(k, []) or not str(i).startswith("-"):
                                conf[k] = conf.get(k, []) + [i]
                        else:
                            if i not in conf.get(k, []):
                                conf[k] = conf.get(k, []) + [i]
            else:
                if k in conf.keys() or not fixed:
                    conf[k] = v

        while isinstance(d := list(dict.values())[0], MutableMapping):
            dict = d

    if kwargs:
        for key, val in kwargs.items():
            for k, v in conf.items():
                if isinstance(v, MutableMapping):
                    conf[k] = add(conf=v, fixed=fixed, **{key: val})[0]
                else:
                    if k == key and key in conf.keys():
                        conf[k] = val
        if dict:
            return (conf, [dict, kwargs])
        else:
            return (conf, [kwargs])

    return (conf, [dict])


def remove(path, item=None, key=None, value=None):
    """Remove entries from a nested dictionary."""
    entries = []
    removed = []

    if isinstance(path, list):
        _list = path

        for entry in _list:
            if item:
                if entry == item:
                    if value:
                        try:
                            entry_index = _list.index(entry)
                            entry_next = _list[entry_index + 1]
                        except IndexError:
                            if "any" == value:
                                entries.append(entry)
                        else:
                            if "any" == value:
                                entries.extend([entry, entry_next])
                            elif entry_next == value:
                                entries.extend([entry, entry_next])
                    else:
                        entries.append(entry)
            elif key:
                if value:
                    if entry.get(key) == value:
                        entries.append(entry)
                else:
                    if entry.get(key):
                        entries.append(entry)

        for entry in entries:
            try:
                _list.remove(entry)
            except Exception as e:
                log.error(f"Exception: {e}")
            else:
                removed.append(entry)

    if isinstance(path, dict):
        _dict = path

        if key:
            if value:
                for k, v in _dict.items():
                    if k == key and v == value:
                        entries.append(k)
            else:
                for k in _dict.keys():
                    if k == key:
                        entries.append(k)

        for entry in entries:
            try:
                val = _dict.pop(entry)
            except Exception as e:
                log.error(f"Exception: {e}")
            else:
                removed.append({entry: val})

    return removed
