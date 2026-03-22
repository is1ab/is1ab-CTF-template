"""Smoke tests for example challenge directory structure."""

from pathlib import Path

import pytest
import yaml


EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "challenges" / "examples"

EXPECTED_EXAMPLES = [
    "crypto/rsa_beginner",
    "pwn/buffer_overflow",
    "web/sql_injection",
    "reverse/simple_crackme",
    "misc/forensics_basic",
]


class TestExampleDirectoryStructure:
    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_directory_exists(self, challenge):
        assert (EXAMPLES_DIR / challenge).is_dir()

    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_has_public_yml(self, challenge):
        assert (EXAMPLES_DIR / challenge / "public.yml").exists()

    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_has_readme(self, challenge):
        assert (EXAMPLES_DIR / challenge / "README.md").exists()

    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_public_yml_parseable(self, challenge):
        path = EXAMPLES_DIR / challenge / "public.yml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert "title" in data
        assert "category" in data
        assert "difficulty" in data

    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_valid_difficulty(self, challenge):
        path = EXAMPLES_DIR / challenge / "public.yml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        valid = {"baby", "easy", "middle", "hard", "impossible"}
        assert data["difficulty"] in valid, f"Invalid difficulty: {data['difficulty']}"

    @pytest.mark.parametrize("challenge", EXPECTED_EXAMPLES)
    def test_valid_category(self, challenge):
        path = EXAMPLES_DIR / challenge / "public.yml"
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        valid = {"web", "pwn", "crypto", "reverse", "misc", "forensic", "general"}
        assert data["category"] in valid, f"Invalid category: {data['category']}"

    def test_docker_challenges_have_dockerfile(self):
        """Challenges with docker/ dir should have a Dockerfile."""
        for challenge in EXPECTED_EXAMPLES:
            docker_dir = EXAMPLES_DIR / challenge / "docker"
            if docker_dir.exists():
                assert (docker_dir / "Dockerfile").exists(), (
                    f"{challenge} has docker/ but no Dockerfile"
                )
