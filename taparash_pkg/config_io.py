"""Load and save QualityConfig from YAML or TOML files.

Supported formats
-----------------
*.toml   Pure stdlib on Python 3.11+; requires ``pip install tomli`` on 3.9/3.10.
*.yaml   Requires ``pip install taparash[yaml]`` (pyyaml).
*.yml    Same as *.yaml.

Usage
-----
    from taparash import load_config, save_config

    config = load_config("pipeline.yaml")
    save_config(config, "pipeline.toml")
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Union

try:
    from taparash.config import QualityConfig
except ImportError:
    from config import QualityConfig  # type: ignore[no-redef]

_VALID_FIELDS = {f.name for f in dataclasses.fields(QualityConfig)}


# ---------------------------------------------------------------------------
# Internal loaders
# ---------------------------------------------------------------------------

def _load_toml(path: str) -> dict:
    try:
        import tomllib  # stdlib Python 3.11+
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            raise ImportError(
                "TOML config requires Python 3.11+ or: pip install tomli"
            ) from None
    with open(path, "rb") as fh:
        return tomllib.load(fh)


def _load_yaml(path: str) -> dict:
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "YAML config requires pyyaml: pip install taparash[yaml]"
        ) from None
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _dump_toml(data: dict) -> str:
    lines = []
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, bool):
            lines.append(f"{key} = {str(value).lower()}")
        elif isinstance(value, str):
            lines.append(f'{key} = "{value}"')
        else:
            lines.append(f"{key} = {value}")
    return "\n".join(lines) + "\n"


def _dump_yaml(data: dict) -> str:
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "Saving YAML requires pyyaml: pip install taparash[yaml]"
        ) from None
    return yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_config(path: Union[str, Path]) -> QualityConfig:
    """Load a ``QualityConfig`` from a YAML or TOML file.

    Args:
        path: Path to a ``.yaml``, ``.yml``, or ``.toml`` config file.

    Returns:
        A fully validated ``QualityConfig`` instance.

    Raises:
        ValueError: If the file extension is unsupported or unknown keys are
                    present.
        ImportError: If the required parser library is not installed.
        FileNotFoundError: If the file does not exist.
    """
    path = str(path)
    lower = path.lower()

    if lower.endswith(".toml"):
        raw = _load_toml(path)
    elif lower.endswith((".yaml", ".yml")):
        raw = _load_yaml(path)
    else:
        raise ValueError(
            f"Unsupported config format: {Path(path).suffix!r}. "
            "Use .yaml, .yml, or .toml."
        )

    unknown = set(raw) - _VALID_FIELDS
    if unknown:
        raise ValueError(
            f"Unknown config key(s): {', '.join(sorted(unknown))}. "
            f"Valid keys: {', '.join(sorted(_VALID_FIELDS))}"
        )

    return QualityConfig(**{k: v for k, v in raw.items() if k in _VALID_FIELDS})


def save_config(config: QualityConfig, path: Union[str, Path]) -> None:
    """Serialise a ``QualityConfig`` to a YAML or TOML file.

    Only non-default values are written when the format supports sparse output
    (both YAML and TOML write all fields for explicitness).  ``None`` values
    (optional model paths, callbacks) are omitted.

    Args:
        config: The ``QualityConfig`` instance to save.
        path: Destination path.  Format is inferred from the extension
              (``.yaml``/``.yml`` or ``.toml``).
    """
    path = str(path)
    lower = path.lower()

    data = {
        f.name: getattr(config, f.name)
        for f in dataclasses.fields(config)
        if getattr(config, f.name) is not None
        and not callable(getattr(config, f.name))
    }

    if lower.endswith(".toml"):
        content = _dump_toml(data)
    elif lower.endswith((".yaml", ".yml")):
        content = _dump_yaml(data)
    else:
        raise ValueError(
            f"Unsupported config format: {Path(path).suffix!r}. "
            "Use .yaml, .yml, or .toml."
        )

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
