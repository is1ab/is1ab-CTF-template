"""Tests for validate-challenge.py — challenge structure validation."""

import tempfile
from pathlib import Path

import pytest
import yaml


class TestChallengeValidator:
    def test_validator_init(self, validate_challenge_module):
        validator = validate_challenge_module.ChallengeValidator()
        assert validator.errors == []
        assert validator.warnings == []

    def test_nonexistent_path_fails(self, validate_challenge_module):
        validator = validate_challenge_module.ChallengeValidator()
        result = validator.validate_challenge("/nonexistent/path")
        assert result is False
        assert len(validator.errors) > 0

    def test_file_instead_of_dir_fails(self, validate_challenge_module, tmp_path):
        f = tmp_path / "not_a_dir.txt"
        f.write_text("hello")
        validator = validate_challenge_module.ChallengeValidator()
        result = validator.validate_challenge(str(f))
        assert result is False

    def test_empty_dir_fails(self, validate_challenge_module, tmp_path):
        """A directory without public.yml should fail validation."""
        validator = validate_challenge_module.ChallengeValidator()
        result = validator.validate_challenge(str(tmp_path))
        assert result is False


class TestExampleChallengesValidation:
    """Validate that the included example challenges pass validation."""

    EXAMPLE_CHALLENGES = [
        "crypto/rsa_beginner",
        "pwn/buffer_overflow",
        "web/sql_injection",
        "reverse/simple_crackme",
        "misc/forensics_basic",
    ]

    @pytest.mark.parametrize("challenge_path", EXAMPLE_CHALLENGES)
    def test_example_has_public_yml(self, examples_dir, challenge_path):
        full_path = examples_dir / challenge_path
        public_yml = full_path / "public.yml"
        assert public_yml.exists(), f"Missing public.yml in {challenge_path}"

    @pytest.mark.parametrize("challenge_path", EXAMPLE_CHALLENGES)
    def test_example_public_yml_valid_yaml(self, examples_dir, challenge_path):
        full_path = examples_dir / challenge_path / "public.yml"
        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("challenge_path", EXAMPLE_CHALLENGES)
    def test_example_has_required_fields(self, examples_dir, challenge_path):
        full_path = examples_dir / challenge_path / "public.yml"
        with open(full_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for field in ["title", "category", "difficulty"]:
            assert field in data, f"Missing '{field}' in {challenge_path}/public.yml"
