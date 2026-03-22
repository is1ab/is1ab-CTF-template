"""Shared test fixtures for IS1AB CTF Template tests."""

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
EXAMPLES_DIR = PROJECT_ROOT / "challenges" / "examples"


def load_script(name: str, filename: str):
    """Load a Python script with hyphens in filename as a module."""
    path = SCRIPTS_DIR / filename
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def project_root():
    return PROJECT_ROOT


@pytest.fixture
def scripts_dir():
    return SCRIPTS_DIR


@pytest.fixture
def examples_dir():
    return EXAMPLES_DIR


@pytest.fixture
def config_path():
    return PROJECT_ROOT / "config.yml"


@pytest.fixture
def scan_secrets_module():
    """Load scan-secrets.py as a module."""
    return load_script("scan_secrets", "scan-secrets.py")


@pytest.fixture
def validate_challenge_module():
    """Load validate-challenge.py as a module."""
    return load_script("validate_challenge", "validate-challenge.py")
