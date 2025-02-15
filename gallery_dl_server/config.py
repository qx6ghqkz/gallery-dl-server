# -*- coding: utf-8 -*-

import os
import sys
import logging

from typing import Any

from gallery_dl import config

from . import output, utils

log = output.initialise_logging(__name__)

_config: dict[str, Any] = config._config
_files: list[str] = config._files


def clear(conf: dict[str, Any] = _config):
    """Clear loaded configuration."""
    conf.clear()


def get_default_configs():
    """Return default gallery-dl configuration file locations."""
    if utils.WINDOWS:
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

    if utils.EXECUTABLE:
        _default_configs.extend(
            utils.join_paths(
                os.path.dirname(sys.executable),
                "gallery-dl.conf",
                "config.json",
            )
        )

    return _default_configs


def get_new_configs(_configs: list[str], exts: list[str]) -> list[str]:
    """Return list of original paths and paths with new extensions."""
    _new_configs = []

    for path in _configs:
        _new_configs.append(path)

        for ext in exts:
            base_path = path.rsplit(".", 1)[0]
            _new_configs.append(base_path + ext)

    return _new_configs


def load(_configs: list[str]):
    """Load configuration files."""
    configs_found: list[str] = []
    configs_loaded: list[str] = []

    exit_codes: list[int | str | None] = []
    messages: list[str] = []

    new_exts = [".yaml", ".yml", ".toml"]

    if utils.CONTAINER:
        _configs = get_new_configs(_configs, new_exts)
    else:
        _configs = get_new_configs(get_default_configs(), new_exts)

    log_buffer = output.StringLogger()

    for path in _configs:
        normal_path = utils.normalise_path(path)

        if os.path.isfile(normal_path):
            configs_found.append(normal_path)
            log.info(f"Configuration file found: {normal_path}")

            try:
                if path.endswith((".conf", ".json")):
                    config.load([path], strict=True)
                elif path.endswith((".yaml", ".yml")):
                    try:
                        if not utils.is_imported("yaml"):
                            import yaml
                    except ImportError as e:
                        exit_codes.append(3)
                        messages.append(f"{type(e).__name__}: {e}")
                        continue

                    config.load([path], strict=True, loads=yaml.safe_load)
                elif path.endswith(".toml"):
                    try:
                        if not utils.is_imported("tomllib"):
                            import tomllib as toml
                    except ImportError:
                        try:
                            if not utils.is_imported("toml"):
                                import toml  # type: ignore
                        except ImportError as e:
                            exit_codes.append(4)
                            messages.append(f"{type(e).__name__}: {e}")
                            continue

                    config.load([path], strict=True, loads=toml.loads)

                configs_loaded.append(path)
            except SystemExit as e:
                exit_codes.append(e.code)
                messages.append(log_buffer.get_logs().split(output.LOG_SEPARATOR)[-1])

    log_buffer.close()

    if configs_loaded:
        log.info(f"Loaded gallery-dl configuration file(s): [{output.join(_files)}]")
    else:
        if all(code not in exit_codes for code in [2, 3, 4]):
            log.error("Loading configuration files failed with exit code: 1")

            if not configs_found:
                log.info(f"Valid configuration file locations: [{output.join(_configs)}]")
        elif all(code not in exit_codes for code in [3, 4]):
            log.error("Loading configuration files failed with exit code: 2")
        elif 2 not in exit_codes:
            log.error("Loading configuration files failed due to missing imports.")

    for message in messages:
        log.log_multiline(logging.ERROR, message)

    if 3 in exit_codes:
        log.info("Install 'PyYAML' to load YAML configuration files")

    if 4 in exit_codes:
        log.info("Install 'toml' or use Python >= 3.11 to load TOML configuration files")

    if exit_codes:
        unique_exit_codes = sorted(set(utils.filter_integers(exit_codes)))

        if unique_exit_codes:
            log.debug(f"Exit codes: {unique_exit_codes}")

    if not configs_loaded:
        raise SystemExit(1)


def get(path: list[str], default: Any = None, conf: dict[str, Any] = _config):
    """Get a value from a nested dictionary or return a default value."""
    if isinstance(path, (list, tuple)):
        try:
            for p in path:
                conf = conf[p]
            return conf
        except Exception:
            return default


def add(
    _dict: dict[str, Any] | None = None, conf: dict[str, Any] = _config, fixed=False, **kwargs: Any
):
    """Add entries to a nested dictionary or list."""
    if _dict:
        for k, v in _dict.items():
            if k in conf.keys() or not fixed:
                if isinstance(v, dict):
                    conf[k] = add(v, conf.get(k) or {}, fixed=fixed)[0]
                elif isinstance(v, list):
                    for i in v:
                        if not isinstance(i, dict):
                            if i not in conf.get(k, []) or not str(i).startswith("-"):
                                conf[k] = conf.get(k, []) + [i]
                        else:
                            if i not in conf.get(k, []):
                                conf[k] = conf.get(k, []) + [i]
                else:
                    conf[k] = v

        while isinstance(d := list(_dict.values())[0], dict):
            _dict = d

    if kwargs:
        for key, val in kwargs.items():
            for k, v in conf.items():
                if k == key and key in conf.keys():
                    conf[k] = val
                elif isinstance(v, dict):
                    conf[k] = add(conf=v, fixed=fixed, **{key: val})[0]

    return (conf, [_dict] if not kwargs else [kwargs] if not _dict else [_dict, kwargs])


def remove(
    path: dict[str, Any] | list, item: str | None = None, key: str | None = None, value: Any = None
):
    """Remove entries from a nested dictionary or list."""
    entries_removed = []

    if isinstance(path, dict) and key:
        entries_removed.extend(remove_from_dict(path, key, value))
    elif isinstance(path, list) and (item or key):
        entries_removed.extend(remove_from_list(path, item, key, value))

    return entries_removed


def remove_from_dict(_dict: dict[str, Any], key: str, value: Any):
    """Remove keys from a nested dictionary."""
    keys_to_remove = []

    for k, v in _dict.items():
        if k == key and (value is None or v == value):
            keys_to_remove.append(k)

    keys_removed = []
    for k in keys_to_remove:
        try:
            v = _dict.pop(k)
            keys_removed.append({k: v})
        except Exception as e:
            log.error(f"Exception: {type(e).__name__}", exc_info=True)

    return keys_removed


def remove_from_list(_list: list, item: str | None, key: str | None, value: Any):
    """Remove elements from a nested list."""
    elements_to_remove = []

    for element in _list:
        if isinstance(element, dict):
            if key and (element.get(key) == value or not value and element.get(key)):
                elements_to_remove.append(element)
        elif item and element == item:
            try:
                element_index = _list.index(element)
                element_next = _list[element_index + 1] if element_index + 1 < len(_list) else None
                if value == "any" or (element_next == value):
                    elements_to_remove.append(element)
                    if element_next:
                        elements_to_remove.append(element_next)
            except IndexError:
                if value == "any":
                    elements_to_remove.append(element)

    elements_removed = []
    for element in elements_to_remove:
        try:
            _list.remove(element)
            elements_removed.append(element)
        except Exception as e:
            log.error(f"Exception: {type(e).__name__}", exc_info=True)

    return elements_removed
