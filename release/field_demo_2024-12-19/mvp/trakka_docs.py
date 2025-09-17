"""
Trakka documentation parser for built-in configuration options
Attempts to parse Trakka ZIP documentation to extract available configuration options
"""

import json
import zipfile
from pathlib import Path
from typing import Any

import yaml


def find_trakka_zip() -> Path | None:
    """Find Trakka ZIP file in common locations"""
    search_paths = [
        Path("docs"),
        Path("data"),
        Path("."),
        Path(".."),
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        for file_path in search_path.rglob("*.zip"):
            if "trakka" in file_path.name.lower():
                return file_path

    return None


def parse_trakka_config_options(zip_path: Path | None = None) -> dict[str, Any]:
    """
    Parse Trakka ZIP documentation to extract configuration options
    Returns a dictionary of {option_name: [possible_values]} or empty dict if parsing fails
    """
    if zip_path is None:
        zip_path = find_trakka_zip()

    if not zip_path or not zip_path.exists():
        return {}

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            # Look for common config file patterns
            config_files = [
                "config.json",
                "config.yaml",
                "config.yml",
                "trakka_config.json",
                "trakka_config.yaml",
                "settings.json",
                "settings.yaml",
                "README.md",
                "CONFIG.md",
                "SETTINGS.md",
            ]

            options = {}

            for file_name in config_files:
                try:
                    if file_name in zip_file.namelist():
                        content = zip_file.read(file_name).decode("utf-8")

                        # Try JSON first
                        if file_name.endswith(".json"):
                            try:
                                data = json.loads(content)
                                options.update(_extract_from_json(data))
                            except json.JSONDecodeError:
                                pass

                        # Try YAML
                        elif file_name.endswith((".yaml", ".yml")):
                            try:
                                data = yaml.safe_load(content)
                                options.update(_extract_from_yaml(data))
                            except yaml.YAMLError:
                                pass

                        # Try markdown text parsing
                        elif file_name.endswith(".md"):
                            options.update(_extract_from_markdown(content))

                except Exception:
                    continue

            return options

    except Exception as e:
        print(f"Failed to parse Trakka ZIP {zip_path}: {e}")
        return {}


def _extract_from_json(data: Any, prefix: str = "") -> dict[str, list[str]]:
    """Extract configuration options from JSON data"""
    options = {}

    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, list):
                # If it's a list of strings, treat as possible values
                if all(isinstance(item, str) for item in value):
                    options[full_key] = value
                else:
                    # Recursively process nested structures
                    options.update(_extract_from_json(value, full_key))
            elif isinstance(value, dict):
                # Recursively process nested objects
                options.update(_extract_from_json(value, full_key))
            elif isinstance(value, str) and value in [
                "true",
                "false",
                "on",
                "off",
                "enabled",
                "disabled",
            ]:
                # Boolean-like values
                options[full_key] = ["true", "false"]

    return options


def _extract_from_yaml(data: Any, prefix: str = "") -> dict[str, list[str]]:
    """Extract configuration options from YAML data"""
    return _extract_from_json(data, prefix)  # Same logic as JSON


def _extract_from_markdown(content: str) -> dict[str, list[str]]:
    """Extract configuration options from markdown documentation"""
    options = {}

    # Look for common patterns in markdown
    lines = content.split("\n")

    for line in lines:
        line = line.strip()

        # Look for configuration tables
        if "|" in line and any(
            keyword in line.lower()
            for keyword in ["option", "setting", "config", "parameter"]
        ):
            # This might be a table header, try to parse the next few lines
            continue

        # Look for key-value pairs with possible values
        if ":" in line and ("[" in line or "|" in line):
            try:
                key, value_part = line.split(":", 1)
                key = key.strip().strip("`*")

                # Extract possible values from brackets or pipes
                if "[" in value_part and "]" in value_part:
                    start = value_part.find("[")
                    end = value_part.find("]")
                    values_str = value_part[start + 1 : end]
                    values = [
                        v.strip().strip("`") for v in values_str.split("|") if v.strip()
                    ]
                    if values:
                        options[key] = values

                elif "|" in value_part:
                    values = [
                        v.strip().strip("`") for v in value_part.split("|") if v.strip()
                    ]
                    if len(values) > 1:
                        options[key] = values

            except Exception:
                continue

    return options


def get_trakka_builtin_options() -> dict[str, Any]:
    """
    Get Trakka built-in configuration options
    Returns a dictionary with option names and their possible values
    Falls back to static defaults if ZIP parsing fails
    """
    # Try to parse from ZIP first
    zip_options = parse_trakka_config_options()

    if zip_options:
        return {
            "source": "trakka_zip",
            "options": zip_options,
            "note": "Options extracted from Trakka documentation",
        }

    # Fallback to static defaults
    return {
        "source": "static_defaults",
        "options": {
            "TRAKKA_THRESHOLD": [
                "0.1",
                "0.2",
                "0.3",
                "0.4",
                "0.5",
                "0.6",
                "0.7",
                "0.8",
                "0.9",
            ],
            "TRAKKA_SENSITIVITY": ["low", "medium", "high"],
            "TRAKKA_ROI_MODE": ["auto", "manual", "fixed"],
            "TRAKKA_DETECTION_ALGORITHM": ["yolo", "rcnn", "ssd", "efficientdet"],
            "TRAKKA_CONFIDENCE_THRESHOLD": [
                "0.1",
                "0.2",
                "0.3",
                "0.4",
                "0.5",
                "0.6",
                "0.7",
                "0.8",
                "0.9",
            ],
            "TRAKKA_NMS_THRESHOLD": [
                "0.1",
                "0.2",
                "0.3",
                "0.4",
                "0.5",
                "0.6",
                "0.7",
                "0.8",
                "0.9",
            ],
            "TRAKKA_MAX_DETECTIONS": ["10", "20", "50", "100"],
            "TRAKKA_INPUT_SIZE": ["320", "416", "512", "640", "896", "960"],
        },
        "note": "Default options - see Trakka documentation for additional settings",
    }
