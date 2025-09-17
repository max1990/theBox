#!/usr/bin/env python3
"""
Plugin Conformance Validation Script
====================================

Validates that all plugins conform to TheBox standards:
1. Bearing normalization to bow-relative (0°/0 rad)
2. Standardized JSON payload shapes
3. Proper event publishing patterns
4. Environment variable usage
5. Error handling and logging

Usage:
    python scripts/validate_plugin_conformance.py [--fix] [--verbose]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mvp.env_loader import load_thebox_env
from mvp.schemas import (
    CLSMessage,
    ConfidenceUpdate,
    NormalizedDetection,
    RangeEstimate,
    SGTMessage,
    VisionResult,
)


class PluginConformanceValidator:
    """Validates plugin conformance to TheBox standards"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.fixes_applied: List[str] = []

    def log(self, message: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled"""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {message}")

    def error(self, message: str):
        """Record an error"""
        self.errors.append(message)
        self.log(message, "ERROR")

    def warning(self, message: str):
        """Record a warning"""
        self.warnings.append(message)
        self.log(message, "WARNING")

    def fix(self, message: str):
        """Record a fix applied"""
        self.fixes_applied.append(message)
        self.log(message, "FIX")

    def validate_bearing_normalization(self, plugin_path: Path) -> bool:
        """Validate that plugin normalizes bearings to bow-relative"""
        self.log(f"Validating bearing normalization for {plugin_path.name}")

        # Check if plugin has bearing-related code
        bearing_files = list(plugin_path.rglob("*.py"))
        has_bearing_code = False
        has_normalization = False

        for file_path in bearing_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                # More specific check for actual bearing handling (not just angle calculations)
                if any(keyword in content.lower() for keyword in ["bearing", "azimuth"]) or \
                   ("angle" in content.lower() and any(pattern in content for pattern in ["bearing", "azimuth", "heading"])):
                    has_bearing_code = True
                    self.log(f"  Found bearing-related code in {file_path.name}")

                    # Check for proper normalization
                    if any(pattern in content for pattern in [
                        "wrap360", "normalize", "bow", "BOW_ZERO", "bearing_offset", "normalize_bearing"
                    ]):
                        has_normalization = True
                        self.log(f"  Found bearing normalization in {file_path.name}")

            except Exception as e:
                self.warning(f"Could not read {file_path}: {e}")

        if has_bearing_code and not has_normalization:
            self.error(f"Plugin {plugin_path.name} has bearing code but no normalization")
            return False

        return True

    def validate_json_schemas(self, plugin_path: Path) -> bool:
        """Validate JSON payload schemas"""
        self.log(f"Validating JSON schemas for {plugin_path.name}")

        # Check for schema definitions
        schema_files = list(plugin_path.rglob("*schema*.py"))
        if not schema_files:
            self.warning(f"Plugin {plugin_path.name} has no schema definitions")

        # Check for proper event publishing
        plugin_files = list(plugin_path.rglob("plugin.py"))
        for file_path in plugin_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check for proper event types
                if "publish(" in content:
                    # Look for standard event types
                    standard_events = [
                        "droneshield_detection",
                        "object.sighting.directional", 
                        "mara_detection",
                        "dspnor_detection",
                        "vision_detection",
                        "object.confidence",
                        "object.range"
                    ]
                    
                    found_events = [event for event in standard_events if event in content]
                    if found_events:
                        self.log(f"  Found standard events: {found_events}")
                    else:
                        self.warning(f"Plugin {plugin_path.name} uses non-standard event types")

            except Exception as e:
                self.warning(f"Could not read {file_path}: {e}")

        return True

    def validate_environment_usage(self, plugin_path: Path) -> bool:
        """Validate proper environment variable usage"""
        self.log(f"Validating environment usage for {plugin_path.name}")

        plugin_files = list(plugin_path.rglob("*.py"))
        has_env_usage = False
        has_proper_env_usage = False

        for file_path in plugin_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                if "os.getenv" in content or "getenv" in content:
                    has_env_usage = True
                    self.log(f"  Found environment usage in {file_path.name}")

                    # Check for proper env loading
                    if "load_thebox_env" in content or "env_loader" in content:
                        has_proper_env_usage = True
                        self.log(f"  Found proper env loading in {file_path.name}")

            except Exception as e:
                self.warning(f"Could not read {file_path}: {e}")

        if has_env_usage and not has_proper_env_usage:
            self.warning(f"Plugin {plugin_path.name} uses environment variables but may not load them properly")

        return True

    def validate_error_handling(self, plugin_path: Path) -> bool:
        """Validate proper error handling and logging"""
        self.log(f"Validating error handling for {plugin_path.name}")

        plugin_files = list(plugin_path.rglob("*.py"))
        has_error_handling = False
        has_logging = False

        for file_path in plugin_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                
                # Check for error handling
                if any(pattern in content for pattern in ["try:", "except", "finally"]):
                    has_error_handling = True
                    self.log(f"  Found error handling in {file_path.name}")

                # Check for logging
                if any(pattern in content for pattern in ["logging", "log.", "print("]):
                    has_logging = True
                    self.log(f"  Found logging in {file_path.name}")

            except Exception as e:
                self.warning(f"Could not read {file_path}: {e}")

        if not has_error_handling:
            self.warning(f"Plugin {plugin_path.name} may lack proper error handling")

        if not has_logging:
            self.warning(f"Plugin {plugin_path.name} may lack proper logging")

        return True

    def validate_plugin_interface(self, plugin_path: Path) -> bool:
        """Validate plugin implements PluginInterface correctly"""
        self.log(f"Validating plugin interface for {plugin_path.name}")

        plugin_file = plugin_path / "plugin.py"
        if not plugin_file.exists():
            self.error(f"Plugin {plugin_path.name} missing plugin.py")
            return False

        try:
            content = plugin_file.read_text(encoding="utf-8")
            
            # Check for PluginInterface inheritance
            if "PluginInterface" not in content:
                self.error(f"Plugin {plugin_path.name} does not inherit from PluginInterface")
                return False

            # Check for required methods
            required_methods = ["load", "unload"]
            for method in required_methods:
                if f"def {method}(" not in content:
                    self.error(f"Plugin {plugin_path.name} missing required method: {method}")
                    return False

            # Check for proper initialization
            if "__init__" in content and "event_manager" not in content:
                self.warning(f"Plugin {plugin_path.name} __init__ may not accept event_manager")

        except Exception as e:
            self.error(f"Could not read {plugin_file}: {e}")
            return False

        return True

    def validate_plugin(self, plugin_path: Path) -> bool:
        """Validate a single plugin"""
        self.log(f"Validating plugin: {plugin_path.name}")
        
        all_passed = True
        
        # Run all validation checks
        checks = [
            self.validate_plugin_interface,
            self.validate_bearing_normalization,
            self.validate_json_schemas,
            self.validate_environment_usage,
            self.validate_error_handling,
        ]
        
        for check in checks:
            if not check(plugin_path):
                all_passed = False
        
        return all_passed

    def validate_all_plugins(self, plugins_dir: Path) -> Dict[str, bool]:
        """Validate all plugins in the plugins directory"""
        self.log(f"Validating all plugins in {plugins_dir}")
        
        results = {}
        plugin_dirs = [d for d in plugins_dir.iterdir() if d.is_dir() and not d.name.startswith("__")]
        
        for plugin_dir in plugin_dirs:
            results[plugin_dir.name] = self.validate_plugin(plugin_dir)
        
        return results

    def generate_json_schemas(self, output_dir: Path):
        """Generate JSON schemas for plugin inputs/outputs"""
        self.log(f"Generating JSON schemas in {output_dir}")
        
        output_dir.mkdir(exist_ok=True)
        
        # Define standard event schemas
        schemas = {
            "droneshield_detection": {
                "type": "object",
                "properties": {
                    "detection": {
                        "type": "object",
                        "properties": {
                            "timestamp": {"type": "string"},
                            "bearing": {"type": "number", "minimum": 0, "maximum": 360},
                            "rssi": {"type": "number"},
                            "protocol": {"type": "string"},
                            "name": {"type": "string"}
                        },
                        "required": ["timestamp", "bearing"]
                    }
                },
                "required": ["detection"]
            },
            "object.sighting.directional": {
                "type": "object",
                "properties": {
                    "time_utc": {"type": "string"},
                    "freq_mhz": {"type": "number"},
                    "bearing_deg_true": {"type": "number", "minimum": 0, "maximum": 360},
                    "bearing_error_deg": {"type": "number", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["time_utc", "bearing_deg_true"]
            },
            "mara_detection": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "bearing_deg": {"type": "number", "minimum": 0, "maximum": 360},
                    "range_m": {"type": "number", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "sensor_type": {"type": "string"}
                },
                "required": ["timestamp", "bearing_deg"]
            },
            "dspnor_detection": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "bearing_deg": {"type": "number", "minimum": 0, "maximum": 360},
                    "range_m": {"type": "number", "minimum": 0},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "track_id": {"type": "string"}
                },
                "required": ["timestamp", "bearing_deg"]
            },
            "vision_detection": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "bearing_deg": {"type": "number", "minimum": 0, "maximum": 360},
                    "verified": {"type": "boolean"},
                    "label": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                },
                "required": ["timestamp", "bearing_deg", "verified"]
            },
            "object.confidence": {
                "type": "object",
                "properties": {
                    "track_id": {"type": "string"},
                    "confidence_0_1": {"type": "number", "minimum": 0, "maximum": 1},
                    "reason": {"type": "string"},
                    "details": {"type": "object"}
                },
                "required": ["track_id", "confidence_0_1", "reason"]
            },
            "object.range": {
                "type": "object",
                "properties": {
                    "track_id": {"type": "string"},
                    "range_km": {"type": "number", "minimum": 0},
                    "sigma_km": {"type": "number", "minimum": 0},
                    "mode": {"type": "string"},
                    "details": {"type": "object"}
                },
                "required": ["track_id", "range_km", "mode"]
            }
        }
        
        # Write schemas to files
        for event_type, schema in schemas.items():
            schema_file = output_dir / f"{event_type.replace('.', '_')}.json"
            with open(schema_file, 'w') as f:
                json.dump(schema, f, indent=2)
            self.log(f"Generated schema: {schema_file}")

    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("PLUGIN CONFORMANCE VALIDATION SUMMARY")
        print("="*60)
        
        if self.fixes_applied:
            print(f"\nFixes Applied: {len(self.fixes_applied)}")
            for fix in self.fixes_applied:
                print(f"  ✓ {fix}")
        
        if self.warnings:
            print(f"\nWarnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"  ⚠ {warning}")
        
        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for error in self.errors:
                print(f"  ✗ {error}")
        
        if not self.errors and not self.warnings:
            print("\n✓ All plugins passed validation!")
        elif not self.errors:
            print(f"\n✓ Validation completed with {len(self.warnings)} warnings")
        else:
            print(f"\n✗ Validation failed with {len(self.errors)} errors")


def main():
    parser = argparse.ArgumentParser(description="Validate plugin conformance")
    parser.add_argument("--fix", action="store_true", help="Apply automatic fixes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--plugins-dir", default="plugins", help="Plugins directory")
    parser.add_argument("--output-dir", default="docs/schemas", help="Schema output directory")
    
    args = parser.parse_args()
    
    # Load environment
    load_thebox_env()
    
    # Create validator
    validator = PluginConformanceValidator(verbose=args.verbose)
    
    # Validate plugins
    plugins_dir = Path(args.plugins_dir)
    if not plugins_dir.exists():
        print(f"Error: Plugins directory {plugins_dir} does not exist")
        sys.exit(1)
    
    results = validator.validate_all_plugins(plugins_dir)
    
    # Generate schemas
    output_dir = Path(args.output_dir)
    validator.generate_json_schemas(output_dir)
    
    # Print summary
    validator.print_summary()
    
    # Exit with error code if there were errors
    if validator.errors:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
