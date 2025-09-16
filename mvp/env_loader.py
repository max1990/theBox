"""
Environment loader for TheBox
Loads environment variables from mvp/env/.thebox.env early in startup
"""
import os
from pathlib import Path
from dotenv import load_dotenv


def load_thebox_env():
    """
    Load environment variables from mvp/env/.thebox.env
    This should be called before any other imports that depend on environment variables
    """
    # Get the path to the .thebox.env file
    env_file = Path(__file__).parent / "env" / ".thebox.env"
    
    if env_file.exists():
        load_dotenv(env_file)
        print(f"Loaded environment from {env_file}")
    else:
        print(f"Warning: Environment file not found at {env_file}")
    
    return env_file.exists()


def get_bearing_offset(plugin_name: str) -> float:
    """
    Get the bearing offset for a specific plugin
    Applies global BOW_ZERO_DEG first, then plugin-specific offset
    """
    global_offset = float(os.getenv("BOW_ZERO_DEG", "0.0"))
    plugin_offset = float(os.getenv(f"{plugin_name.upper()}_BEARING_OFFSET_DEG", "0.0"))
    return global_offset + plugin_offset


def normalize_bearing(bearing_deg: float) -> float:
    """
    Normalize bearing to [0, 360) degrees
    """
    while bearing_deg < 0:
        bearing_deg += 360
    while bearing_deg >= 360:
        bearing_deg -= 360
    return bearing_deg


def apply_bearing_offsets(bearing_deg: float, plugin_name: str) -> float:
    """
    Apply global and plugin-specific bearing offsets, then normalize
    """
    offset = get_bearing_offset(plugin_name)
    adjusted = bearing_deg + offset
    return normalize_bearing(adjusted)
