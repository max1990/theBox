#!/usr/bin/env python3
"""
Release Packaging Script for TheBox
==================================

Creates a complete release package for field deployment.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mvp.env_loader import load_thebox_env


def create_release_directory(release_name: str) -> Path:
    """Create release directory structure"""
    release_dir = project_root / "release" / release_name
    release_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    subdirs = [
        "bin",
        "config",
        "docs",
        "docker",
        "scripts",
        "tests",
        "sbom",
        "logs"
    ]
    
    for subdir in subdirs:
        (release_dir / subdir).mkdir(exist_ok=True)
    
    return release_dir


def copy_essential_files(release_dir: Path):
    """Copy essential files to release directory"""
    
    # Core application files
    core_files = [
        "app.py",
        "config.json",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-gpu.txt",
        "requirements-jetson.txt",
        "pyproject.toml",
        "README.md"
    ]
    
    for file in core_files:
        src = project_root / file
        if src.exists():
            shutil.copy2(src, release_dir / file)
    
    # Copy mvp directory
    mvp_dir = release_dir / "mvp"
    if (project_root / "mvp").exists():
        shutil.copytree(project_root / "mvp", mvp_dir, dirs_exist_ok=True)
    
    # Copy plugins directory
    plugins_dir = release_dir / "plugins"
    if (project_root / "plugins").exists():
        shutil.copytree(project_root / "plugins", plugins_dir, dirs_exist_ok=True)
    
    # Copy thebox directory
    thebox_dir = release_dir / "thebox"
    if (project_root / "thebox").exists():
        shutil.copytree(project_root / "thebox", thebox_dir, dirs_exist_ok=True)
    
    # Copy webui directory
    webui_dir = release_dir / "webui"
    if (project_root / "webui").exists():
        shutil.copytree(project_root / "webui", webui_dir, dirs_exist_ok=True)
    
    # Copy templates directory
    templates_dir = release_dir / "templates"
    if (project_root / "templates").exists():
        shutil.copytree(project_root / "templates", templates_dir, dirs_exist_ok=True)
    
    # Copy static directory
    static_dir = release_dir / "static"
    if (project_root / "static").exists():
        shutil.copytree(project_root / "static", static_dir, dirs_exist_ok=True)


def copy_scripts(release_dir: Path):
    """Copy essential scripts to release directory"""
    
    scripts_dir = release_dir / "scripts"
    
    # Essential scripts
    essential_scripts = [
        "smoke_test.py",
        "udp_simulator.py",
        "replay_harness.py",
        "health_check.py",
        "run_tests.py",
        "validate_plugin_conformance.py"
    ]
    
    for script in essential_scripts:
        src = project_root / "scripts" / script
        if src.exists():
            shutil.copy2(src, scripts_dir / script)
    
    # Copy Windows scripts
    windows_dir = scripts_dir / "windows"
    windows_dir.mkdir(exist_ok=True)
    
    windows_scripts = [
        "run_demo.ps1",
        "SET_ENV.ps1"
    ]
    
    for script in windows_scripts:
        src = project_root / "scripts" / "windows" / script
        if src.exists():
            shutil.copy2(src, windows_dir / script)
    
    # Copy shell scripts
    shell_scripts = [
        "start.sh",
        "start.bat"
    ]
    
    for script in shell_scripts:
        src = project_root / script
        if src.exists():
            shutil.copy2(src, scripts_dir / script)


def copy_docker_files(release_dir: Path):
    """Copy Docker files to release directory"""
    
    docker_dir = release_dir / "docker"
    
    # Docker files
    docker_files = [
        "Dockerfile.workstation",
        "Dockerfile.jetson",
        "docker-compose.yml",
        "docker-compose.jetson.yml",
        ".dockerignore"
    ]
    
    for file in docker_files:
        src = project_root / file
        if src.exists():
            shutil.copy2(src, docker_dir / file)


def copy_documentation(release_dir: Path):
    """Copy documentation to release directory"""
    
    docs_dir = release_dir / "docs"
    
    # Copy all documentation
    if (project_root / "docs").exists():
        shutil.copytree(project_root / "docs", docs_dir, dirs_exist_ok=True)
    
    # Copy README files
    readme_files = [
        "README.md",
        "mvp/README_MVP.md",
        "plugins/search_planner/README-search_planner.md",
        "plugins/silvus_listener/README-silvus_plugin.md"
    ]
    
    for readme in readme_files:
        src = project_root / readme
        if src.exists():
            dest = docs_dir / readme.replace("/", "_")
            shutil.copy2(src, dest)


def copy_config_files(release_dir: Path):
    """Copy configuration files to release directory"""
    
    config_dir = release_dir / "config"
    
    # Environment files
    env_files = [
        "docs/env.sample",
        "docs/env.schema.json"
    ]
    
    for env_file in env_files:
        src = project_root / env_file
        if src.exists():
            shutil.copy2(src, config_dir / Path(env_file).name)
    
    # Copy config.json
    src = project_root / "config.json"
    if src.exists():
        shutil.copy2(src, config_dir / "config.json")


def copy_tests(release_dir: Path):
    """Copy test files to release directory"""
    
    tests_dir = release_dir / "tests"
    
    # Copy all tests
    if (project_root / "tests").exists():
        shutil.copytree(project_root / "tests", tests_dir, dirs_exist_ok=True)
    
    # Copy test configuration
    test_configs = [
        "pytest.ini"
    ]
    
    for config in test_configs:
        src = project_root / config
        if src.exists():
            shutil.copy2(src, tests_dir / config)


def copy_sbom_files(release_dir: Path):
    """Copy SBOM files to release directory"""
    
    sbom_dir = release_dir / "sbom"
    
    # Copy SBOM files
    sbom_files = [
        "sbom.json"
    ]
    
    for sbom_file in sbom_files:
        src = project_root / sbom_file
        if src.exists():
            shutil.copy2(src, sbom_dir / sbom_file)


def create_release_manifest(release_dir: Path, release_name: str):
    """Create release manifest"""
    
    manifest = {
        "release_name": release_name,
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "platforms": ["windows", "jetson", "docker"],
        "components": {
            "core": "TheBox main application",
            "plugins": "Sensor integration plugins",
            "mvp": "MVP framework components",
            "webui": "Web user interface",
            "scripts": "Utility and test scripts",
            "docker": "Container configurations",
            "docs": "Documentation and runbooks",
            "tests": "Test suite and validation",
            "config": "Configuration files and schemas",
            "sbom": "Software Bill of Materials"
        },
        "requirements": {
            "python": ">=3.8",
            "platforms": ["Windows 10+", "Jetson L4T", "Docker"],
            "dependencies": "See requirements.txt files"
        },
        "quickstart": {
            "windows": "See docs/QUICKSTART_WINDOWS.md",
            "jetson": "See docs/QUICKSTART_JETSON.md",
            "docker": "See docs/QUICKSTART_DOCKER.md"
        }
    }
    
    manifest_file = release_dir / "MANIFEST.json"
    with open(manifest_file, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"Created release manifest: {manifest_file}")


def create_release_archive(release_dir: Path, release_name: str, format: str = "zip"):
    """Create release archive"""
    
    archive_name = f"{release_name}.{format}"
    archive_path = release_dir.parent / archive_name
    
    if format == "zip":
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(release_dir):
                for file in files:
                    file_path = Path(root) / file
                    arc_path = file_path.relative_to(release_dir.parent)
                    zipf.write(file_path, arc_path)
    
    elif format == "tar.gz":
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(release_dir, arcname=release_name)
    
    print(f"Created release archive: {archive_path}")
    return archive_path


def create_docker_images(release_dir: Path):
    """Create Docker images for release"""
    
    docker_dir = release_dir / "docker"
    
    # Build workstation image
    workstation_dockerfile = docker_dir / "Dockerfile.workstation"
    if workstation_dockerfile.exists():
        print("Building workstation Docker image...")
        try:
            subprocess.run([
                "docker", "build", 
                "-f", str(workstation_dockerfile),
                "-t", "thebox:workstation",
                str(project_root)
            ], check=True)
            print("✓ Workstation image built successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to build workstation image: {e}")
    
    # Build Jetson image
    jetson_dockerfile = docker_dir / "Dockerfile.jetson"
    if jetson_dockerfile.exists():
        print("Building Jetson Docker image...")
        try:
            subprocess.run([
                "docker", "build", 
                "-f", str(jetson_dockerfile),
                "-t", "thebox:jetson",
                str(project_root)
            ], check=True)
            print("✓ Jetson image built successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to build Jetson image: {e}")


def create_release_notes(release_dir: Path, release_name: str):
    """Create release notes"""
    
    release_notes = f"""# TheBox Release Notes - {release_name}

## Overview

This release contains the complete TheBox system for field deployment.

## Components

- **Core Application**: Main Flask application with plugin architecture
- **Sensor Plugins**: Integration for DroneShield, Silvus, Trakka, MARA, Dspnor
- **MVP Framework**: Modular components for detection processing
- **Web UI**: Settings and monitoring interface
- **Docker Support**: Containerized deployment for Windows and Jetson
- **Test Suite**: Comprehensive validation and smoke tests
- **Documentation**: Complete runbooks and configuration guides

## Quick Start

### Windows
```powershell
# Set environment
.\\scripts\\windows\\SET_ENV.ps1

# Run application
python app.py
```

### Jetson
```bash
# Set environment
source scripts/setup_jetson.sh

# Run application
python app.py
```

### Docker
```bash
# Workstation
docker-compose up

# Jetson
docker-compose -f docker-compose.jetson.yml up
```

## Configuration

1. Copy `config/env.sample` to `.env`
2. Edit `.env` with your specific settings
3. Run smoke test: `python scripts/smoke_test.py`

## Validation

Run the complete test suite:
```bash
python scripts/run_tests.py --coverage
```

## Support

See `docs/` directory for detailed documentation and troubleshooting.

## Security

- SBOM files available in `sbom/` directory
- Security report in `docs/SECURITY_REPORT.md`
- All dependencies pinned to specific versions

## Performance

- Performance notes in `docs/PERF_NOTES.md`
- Monitoring probes available
- Fail-open behavior implemented

## Changelog

- Initial release
- Complete plugin architecture
- Docker support for Windows and Jetson
- Comprehensive test suite
- Security hardening
- Performance monitoring
"""

    release_notes_file = release_dir / "RELEASE_NOTES.md"
    with open(release_notes_file, 'w') as f:
        f.write(release_notes)
    
    print(f"Created release notes: {release_notes_file}")


def main():
    parser = argparse.ArgumentParser(description="Package TheBox release")
    parser.add_argument("--name", default="field_demo_2024-12-19", help="Release name")
    parser.add_argument("--format", choices=["zip", "tar.gz"], default="zip", help="Archive format")
    parser.add_argument("--docker", action="store_true", help="Build Docker images")
    parser.add_argument("--no-archive", action="store_true", help="Skip creating archive")
    
    args = parser.parse_args()
    
    # Load environment
    load_thebox_env()
    
    print(f"Creating release package: {args.name}")
    print(f"Format: {args.format}")
    print(f"Build Docker: {args.docker}")
    print("-" * 60)
    
    # Create release directory
    release_dir = create_release_directory(args.name)
    print(f"Created release directory: {release_dir}")
    
    # Copy files
    print("Copying essential files...")
    copy_essential_files(release_dir)
    
    print("Copying scripts...")
    copy_scripts(release_dir)
    
    print("Copying Docker files...")
    copy_docker_files(release_dir)
    
    print("Copying documentation...")
    copy_documentation(release_dir)
    
    print("Copying configuration files...")
    copy_config_files(release_dir)
    
    print("Copying tests...")
    copy_tests(release_dir)
    
    print("Copying SBOM files...")
    copy_sbom_files(release_dir)
    
    # Create manifest
    print("Creating release manifest...")
    create_release_manifest(release_dir, args.name)
    
    # Create release notes
    print("Creating release notes...")
    create_release_notes(release_dir, args.name)
    
    # Build Docker images
    if args.docker:
        print("Building Docker images...")
        create_docker_images(release_dir)
    
    # Create archive
    if not args.no_archive:
        print(f"Creating {args.format} archive...")
        archive_path = create_release_archive(release_dir, args.name, args.format)
        print(f"Release package created: {archive_path}")
    
    print("✓ Release packaging completed successfully!")
    
    # Print summary
    print("\nRelease Summary:")
    print(f"  Directory: {release_dir}")
    print(f"  Components: Core, Plugins, MVP, WebUI, Docker, Docs, Tests, Config, SBOM")
    print(f"  Platforms: Windows, Jetson, Docker")
    print(f"  Quickstart: See docs/QUICKSTART_*.md")
    print(f"  Validation: python scripts/smoke_test.py")


if __name__ == "__main__":
    main()
