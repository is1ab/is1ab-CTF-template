"""Tests for scan-secrets.py — flag/secret detection logic."""

import re
import tempfile
from pathlib import Path

import pytest


class TestSeverityEnum:
    def test_severity_values(self, scan_secrets_module):
        Severity = scan_secrets_module.Severity
        assert Severity.CRITICAL.value == "CRITICAL"
        assert Severity.HIGH.value == "HIGH"
        assert Severity.MEDIUM.value == "MEDIUM"
        assert Severity.LOW.value == "LOW"
        assert Severity.INFO.value == "INFO"


class TestFinding:
    def test_finding_creation(self, scan_secrets_module):
        Finding = scan_secrets_module.Finding
        Severity = scan_secrets_module.Severity
        f = Finding(
            file_path="test.py",
            line_number=10,
            severity=Severity.CRITICAL,
            category="flag_leak",
            description="Flag detected",
        )
        assert f.file_path == "test.py"
        assert f.line_number == 10
        assert f.severity == Severity.CRITICAL


class TestScanResult:
    def test_empty_result(self, scan_secrets_module):
        result = scan_secrets_module.ScanResult()
        assert result.scanned_files == 0
        assert result.has_critical is False
        assert result.has_high is False
        assert len(result.findings) == 0

    def test_has_critical(self, scan_secrets_module):
        ScanResult = scan_secrets_module.ScanResult
        Finding = scan_secrets_module.Finding
        Severity = scan_secrets_module.Severity

        result = ScanResult()
        result.findings.append(
            Finding("f.py", 1, Severity.CRITICAL, "leak", "flag found")
        )
        assert result.has_critical is True
        assert result.has_high is False

    def test_count_by_severity(self, scan_secrets_module):
        ScanResult = scan_secrets_module.ScanResult
        Finding = scan_secrets_module.Finding
        Severity = scan_secrets_module.Severity

        result = ScanResult()
        result.findings.append(Finding("a.py", 1, Severity.HIGH, "x", "y"))
        result.findings.append(Finding("b.py", 2, Severity.HIGH, "x", "y"))
        result.findings.append(Finding("c.py", 3, Severity.LOW, "x", "y"))

        counts = result.count_by_severity()
        assert counts[Severity.HIGH] == 2
        assert counts[Severity.LOW] == 1
        assert counts[Severity.CRITICAL] == 0


class TestFlagPatternDetection:
    """Test that common flag patterns are detected."""

    def test_flag_prefix_regex(self):
        """The standard flag format should be detectable."""
        pattern = re.compile(r"is1abCTF\{[^}]+\}")
        assert pattern.search("is1abCTF{test_flag_123}")
        assert pattern.search('flag = "is1abCTF{s3cret}"')
        assert not pattern.search("is1abCTF{}")  # empty braces — no content
        assert not pattern.search("some random text")

    def test_aws_key_pattern(self):
        pattern = re.compile(r"AKIA[0-9A-Z]{16}")
        assert pattern.search("AKIAIOSFODNN7EXAMPLE")
        assert not pattern.search("not_an_aws_key")

    def test_private_key_pattern(self):
        pattern = re.compile(r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----")
        assert pattern.search("-----BEGIN RSA PRIVATE KEY-----")
        assert pattern.search("-----BEGIN PRIVATE KEY-----")
        assert not pattern.search("-----BEGIN PUBLIC KEY-----")


class TestScannerWithTempFiles:
    """Test the scanner against temporary files with known content."""

    def test_scanner_init(self, scan_secrets_module, config_path):
        if config_path.exists():
            scanner = scan_secrets_module.SecretsScanner(str(config_path))
            assert scanner is not None

    def test_clean_file_no_findings(self, scan_secrets_module, tmp_path):
        clean_file = tmp_path / "clean.py"
        clean_file.write_text("print('hello world')\nx = 42\n")

        scanner = scan_secrets_module.SecretsScanner()
        result = scanner.scan(str(tmp_path))
        critical_findings = [
            f for f in result.findings if f.severity == scan_secrets_module.Severity.CRITICAL
        ]
        assert len(critical_findings) == 0
