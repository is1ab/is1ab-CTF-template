#!/usr/bin/env python3
"""
CTF Secrets Scanner - 敏感資料掃描工具

功能：
1. 掃描 Flag 格式字串
2. 檢測敏感檔案
3. 分析 YAML/JSON 中的敏感欄位
4. 檢查 Docker 環境變數
5. 生成掃描報告

用法：
    python scan-secrets.py --path ./public-release
    python scan-secrets.py --path ./challenges --verbose
    python scan-secrets.py --path . --fix  # 嘗試自動修復
"""

import argparse
import os
import re
import sys
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """問題嚴重程度"""
    CRITICAL = "CRITICAL"  # 絕對不能有
    HIGH = "HIGH"          # 高風險
    MEDIUM = "MEDIUM"      # 中風險
    LOW = "LOW"            # 低風險
    INFO = "INFO"          # 資訊提示


@dataclass
class Finding:
    """掃描發現的問題"""
    file_path: str
    line_number: int
    severity: Severity
    category: str
    description: str
    matched_content: str = ""
    suggestion: str = ""


@dataclass
class ScanResult:
    """掃描結果"""
    scanned_files: int = 0
    scanned_dirs: int = 0
    findings: List[Finding] = field(default_factory=list)
    skipped_files: List[str] = field(default_factory=list)
    scan_time: float = 0.0
    
    @property
    def has_critical(self) -> bool:
        return any(f.severity == Severity.CRITICAL for f in self.findings)
    
    @property
    def has_high(self) -> bool:
        return any(f.severity == Severity.HIGH for f in self.findings)
    
    def count_by_severity(self) -> Dict[Severity, int]:
        counts = {s: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts


class SecretsScanner:
    """敏感資料掃描器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化掃描器"""
        self.config = self._load_config(config_path)
        self.flag_prefix = self.config.get('flag_prefix', 'is1abCTF')
        self.result = ScanResult()
        
        # 敏感檔案名稱
        self.sensitive_filenames = {
            'private.yml', 'private.yaml',
            'secrets.yml', 'secrets.yaml', 'secrets.json',
            'flag.txt', 'flag', 'FLAG', 'FLAG.txt',
            '.env', '.env.local', '.env.production',
            'solution.py', 'exploit.py', 'solve.py',
            'credentials.json', 'auth.json',
            'id_rsa', 'id_rsa.pub', 'id_ed25519',
            '.htpasswd', '.htaccess',
            'shadow', 'passwd',
        }
        
        # 敏感 YAML 欄位
        self.sensitive_yaml_fields = {
            'flag', 'flags', 'real_flag', 'actual_flag',
            'flag_description', 'flag_type', 'dynamic_flag',
            'solution_steps', 'solution', 'solutions',
            'internal_notes', 'internal_note', 'private_notes',
            'test_credentials', 'credentials', 'admin_password',
            'deploy_secrets', 'secrets', 'secret_key',
            'verified_solutions', 'exploits',
            'password', 'api_key', 'token', 'secret',
        }
        
        # 敏感內容模式
        self.sensitive_patterns = [
            # Flag 格式
            (rf'{self.flag_prefix}\{{[^}}]+\}}', Severity.CRITICAL, 'Flag 洩漏'),
            # 通用 CTF Flag 格式
            (r'[A-Za-z0-9_]+CTF\{[^}]+\}', Severity.HIGH, '可能的 Flag 格式'),
            # Base64 編碼的 Flag
            (r'[A-Za-z0-9+/]{40,}={0,2}', Severity.MEDIUM, '可能的 Base64 編碼'),
            # 硬編碼密碼
            (r'password\s*[:=]\s*["\'][^"\']{4,}["\']', Severity.HIGH, '硬編碼密碼'),
            (r'passwd\s*[:=]\s*["\'][^"\']{4,}["\']', Severity.HIGH, '硬編碼密碼'),
            # API Keys
            (r'api[_-]?key\s*[:=]\s*["\'][A-Za-z0-9]{16,}["\']', Severity.HIGH, 'API Key'),
            # AWS Keys
            (r'AKIA[0-9A-Z]{16}', Severity.CRITICAL, 'AWS Access Key'),
            (r'[A-Za-z0-9/+=]{40}', Severity.MEDIUM, '可能的 AWS Secret Key'),
            # Private Keys
            (r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', Severity.CRITICAL, '私鑰'),
            # JWT
            (r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', Severity.HIGH, 'JWT Token'),
            # Database URLs
            (r'(mysql|postgres|mongodb)://[^:]+:[^@]+@', Severity.HIGH, '資料庫連接字串'),
        ]
        
        # 要跳過的目錄
        self.skip_dirs = {
            '.git', '__pycache__', 'node_modules', '.venv', 'venv',
            '.idea', '.vscode', '.cache', 'dist', 'build',
        }
        
        # 要跳過的檔案類型
        self.skip_extensions = {
            '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
            '.jpg', '.jpeg', '.png', '.gif', '.ico', '.svg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx',
            '.mp3', '.mp4', '.wav', '.avi', '.mov',
            '.zip', '.tar', '.gz', '.rar', '.7z',
            '.woff', '.woff2', '.ttf', '.eot',
        }
    
    def _load_config(self, config_path: Optional[str]) -> dict:
        """載入配置檔案"""
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    project = config.get('project', {})
                    return {'flag_prefix': project.get('flag_prefix', 'is1abCTF')}
            except Exception:
                pass
        return {'flag_prefix': 'is1abCTF'}
    
    def scan(self, path: str, verbose: bool = False) -> ScanResult:
        """執行掃描"""
        import time
        start_time = time.time()
        
        path = Path(path)
        if not path.exists():
            print(f"❌ 路徑不存在: {path}")
            sys.exit(1)
        
        if path.is_file():
            self._scan_file(path, verbose)
        else:
            self._scan_directory(path, verbose)
        
        self.result.scan_time = time.time() - start_time
        return self.result
    
    def _scan_directory(self, dir_path: Path, verbose: bool = False):
        """掃描目錄"""
        self.result.scanned_dirs += 1
        
        for item in dir_path.iterdir():
            if item.is_dir():
                if item.name in self.skip_dirs:
                    if verbose:
                        print(f"  ⏭️  跳過目錄: {item}")
                    continue
                self._scan_directory(item, verbose)
            elif item.is_file():
                self._scan_file(item, verbose)
    
    def _scan_file(self, file_path: Path, verbose: bool = False):
        """掃描單一檔案"""
        # 檢查是否應該跳過
        if file_path.suffix.lower() in self.skip_extensions:
            self.result.skipped_files.append(str(file_path))
            return
        
        # 檢查敏感檔案名稱
        if file_path.name in self.sensitive_filenames:
            self.result.findings.append(Finding(
                file_path=str(file_path),
                line_number=0,
                severity=Severity.CRITICAL,
                category='敏感檔案',
                description=f'發現敏感檔案: {file_path.name}',
                suggestion='此檔案不應該出現在公開目錄中'
            ))
        
        self.result.scanned_files += 1
        
        if verbose:
            print(f"  📄 掃描: {file_path}")
        
        try:
            # 讀取檔案內容
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # 根據檔案類型進行特殊處理
            if file_path.suffix.lower() in ('.yml', '.yaml'):
                self._scan_yaml_file(file_path, content)
            elif file_path.suffix.lower() == '.json':
                self._scan_json_file(file_path, content)
            elif file_path.name == 'Dockerfile':
                self._scan_dockerfile(file_path, content)
            elif file_path.name == 'docker-compose.yml':
                self._scan_docker_compose(file_path, content)
            
            # 掃描敏感模式
            self._scan_patterns(file_path, lines)
            
        except Exception as e:
            if verbose:
                print(f"  ⚠️  無法讀取: {file_path} ({e})")
            self.result.skipped_files.append(str(file_path))
    
    def _scan_patterns(self, file_path: Path, lines: List[str]):
        """掃描敏感模式"""
        for line_num, line in enumerate(lines, 1):
            for pattern, severity, category in self.sensitive_patterns:
                matches = re.findall(pattern, line, re.IGNORECASE)
                for match in matches:
                    # 排除明顯的假陽性
                    if self._is_false_positive(match, line):
                        continue
                    
                    self.result.findings.append(Finding(
                        file_path=str(file_path),
                        line_number=line_num,
                        severity=severity,
                        category=category,
                        description=f'發現敏感內容',
                        matched_content=match[:50] + ('...' if len(match) > 50 else ''),
                        suggestion='請移除或替換此敏感內容'
                    ))
    
    def _is_false_positive(self, match: str, line: str) -> bool:
        """檢查是否為假陽性"""
        # 檢查是否為範例或佔位符
        false_positive_indicators = [
            'example', 'sample', 'test', 'demo', 'fake',
            'placeholder', 'your_', 'xxx', 'TODO', 'FIXME',
            '${', '{{', '<', '>',
        ]
        
        line_lower = line.lower()
        match_lower = match.lower()
        
        for indicator in false_positive_indicators:
            if indicator.lower() in line_lower or indicator.lower() in match_lower:
                return True
        
        return False
    
    def _scan_yaml_file(self, file_path: Path, content: str):
        """掃描 YAML 檔案"""
        try:
            data = yaml.safe_load(content)
            if data:
                self._scan_dict_for_sensitive_keys(file_path, data)
        except yaml.YAMLError:
            pass
    
    def _scan_json_file(self, file_path: Path, content: str):
        """掃描 JSON 檔案"""
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                self._scan_dict_for_sensitive_keys(file_path, data)
        except json.JSONDecodeError:
            pass
    
    def _scan_dict_for_sensitive_keys(self, file_path: Path, data: dict, path: str = ""):
        """遞迴掃描字典中的敏感鍵"""
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            key_lower = key.lower()
            
            if key_lower in self.sensitive_yaml_fields:
                self.result.findings.append(Finding(
                    file_path=str(file_path),
                    line_number=0,
                    severity=Severity.HIGH,
                    category='敏感欄位',
                    description=f'發現敏感欄位: {current_path}',
                    matched_content=str(value)[:50] if value else '',
                    suggestion='此欄位不應該出現在公開版本中'
                ))
            
            if isinstance(value, dict):
                self._scan_dict_for_sensitive_keys(file_path, value, current_path)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        self._scan_dict_for_sensitive_keys(file_path, item, f"{current_path}[{i}]")
    
    def _scan_dockerfile(self, file_path: Path, content: str):
        """掃描 Dockerfile"""
        lines = content.split('\n')
        for line_num, line in enumerate(lines, 1):
            # 檢查 ENV 指令中的敏感資訊
            if line.strip().startswith('ENV'):
                if re.search(rf'{self.flag_prefix}\{{[^}}]+\}}', line):
                    self.result.findings.append(Finding(
                        file_path=str(file_path),
                        line_number=line_num,
                        severity=Severity.CRITICAL,
                        category='Docker Flag 洩漏',
                        description='Dockerfile 中包含硬編碼的 Flag',
                        matched_content=line.strip()[:50],
                        suggestion='使用環境變數 ${FLAG} 替代硬編碼的 Flag'
                    ))
    
    def _scan_docker_compose(self, file_path: Path, content: str):
        """掃描 docker-compose.yml"""
        try:
            data = yaml.safe_load(content)
            if not data or 'services' not in data:
                return
            
            for service_name, service_config in data.get('services', {}).items():
                # 檢查環境變數
                environment = service_config.get('environment', [])
                if isinstance(environment, list):
                    for env in environment:
                        if isinstance(env, str) and '=' in env:
                            key, value = env.split('=', 1)
                            if re.search(rf'{self.flag_prefix}\{{[^}}]+\}}', value):
                                self.result.findings.append(Finding(
                                    file_path=str(file_path),
                                    line_number=0,
                                    severity=Severity.CRITICAL,
                                    category='Docker Compose Flag 洩漏',
                                    description=f'服務 {service_name} 包含硬編碼的 Flag',
                                    matched_content=f'{key}={value[:30]}...',
                                    suggestion='使用 ${FLAG} 環境變數'
                                ))
                elif isinstance(environment, dict):
                    for key, value in environment.items():
                        if value and re.search(rf'{self.flag_prefix}\{{[^}}]+\}}', str(value)):
                            self.result.findings.append(Finding(
                                file_path=str(file_path),
                                line_number=0,
                                severity=Severity.CRITICAL,
                                category='Docker Compose Flag 洩漏',
                                description=f'服務 {service_name} 包含硬編碼的 Flag',
                                matched_content=f'{key}={str(value)[:30]}...',
                                suggestion='使用 ${FLAG} 環境變數'
                            ))
        except yaml.YAMLError:
            pass
    
    def generate_report(self, output_format: str = 'text') -> str:
        """生成掃描報告"""
        if output_format == 'json':
            return self._generate_json_report()
        elif output_format == 'markdown':
            return self._generate_markdown_report()
        else:
            return self._generate_text_report()
    
    def _generate_text_report(self) -> str:
        """生成文字報告"""
        lines = []
        lines.append("=" * 60)
        lines.append("  CTF Secrets Scanner Report")
        lines.append("=" * 60)
        lines.append("")
        
        # 統計
        counts = self.result.count_by_severity()
        lines.append("📊 掃描統計:")
        lines.append(f"  - 掃描檔案: {self.result.scanned_files}")
        lines.append(f"  - 掃描目錄: {self.result.scanned_dirs}")
        lines.append(f"  - 掃描時間: {self.result.scan_time:.2f}s")
        lines.append("")
        
        # 發現統計
        lines.append("🔍 發現統計:")
        lines.append(f"  - CRITICAL: {counts[Severity.CRITICAL]}")
        lines.append(f"  - HIGH:     {counts[Severity.HIGH]}")
        lines.append(f"  - MEDIUM:   {counts[Severity.MEDIUM]}")
        lines.append(f"  - LOW:      {counts[Severity.LOW]}")
        lines.append(f"  - INFO:     {counts[Severity.INFO]}")
        lines.append("")
        
        # 發現詳情
        if self.result.findings:
            lines.append("🚨 發現詳情:")
            lines.append("-" * 60)
            
            for finding in sorted(self.result.findings, key=lambda f: f.severity.value):
                severity_emoji = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🟢",
                    Severity.INFO: "🔵",
                }[finding.severity]
                
                lines.append(f"{severity_emoji} [{finding.severity.value}] {finding.category}")
                lines.append(f"   檔案: {finding.file_path}")
                if finding.line_number > 0:
                    lines.append(f"   行號: {finding.line_number}")
                lines.append(f"   說明: {finding.description}")
                if finding.matched_content:
                    lines.append(f"   內容: {finding.matched_content}")
                if finding.suggestion:
                    lines.append(f"   建議: {finding.suggestion}")
                lines.append("")
        else:
            lines.append("✅ 未發現任何問題")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _generate_markdown_report(self) -> str:
        """生成 Markdown 報告"""
        lines = []
        lines.append("# CTF Secrets Scanner Report")
        lines.append("")
        lines.append(f"📅 掃描時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # 統計表格
        counts = self.result.count_by_severity()
        lines.append("## 📊 掃描統計")
        lines.append("")
        lines.append("| 項目 | 數量 |")
        lines.append("|------|------|")
        lines.append(f"| 掃描檔案 | {self.result.scanned_files} |")
        lines.append(f"| 掃描目錄 | {self.result.scanned_dirs} |")
        lines.append(f"| CRITICAL | {counts[Severity.CRITICAL]} |")
        lines.append(f"| HIGH | {counts[Severity.HIGH]} |")
        lines.append(f"| MEDIUM | {counts[Severity.MEDIUM]} |")
        lines.append(f"| LOW | {counts[Severity.LOW]} |")
        lines.append("")
        
        # 發現詳情
        if self.result.findings:
            lines.append("## 🚨 發現詳情")
            lines.append("")
            
            for finding in sorted(self.result.findings, key=lambda f: f.severity.value):
                lines.append(f"### [{finding.severity.value}] {finding.category}")
                lines.append("")
                lines.append(f"- **檔案**: `{finding.file_path}`")
                if finding.line_number > 0:
                    lines.append(f"- **行號**: {finding.line_number}")
                lines.append(f"- **說明**: {finding.description}")
                if finding.matched_content:
                    lines.append(f"- **內容**: `{finding.matched_content}`")
                if finding.suggestion:
                    lines.append(f"- **建議**: {finding.suggestion}")
                lines.append("")
        else:
            lines.append("## ✅ 掃描結果")
            lines.append("")
            lines.append("未發現任何安全問題。")
        
        return "\n".join(lines)
    
    def _generate_json_report(self) -> str:
        """生成 JSON 報告"""
        report = {
            "scan_time": datetime.now().isoformat(),
            "statistics": {
                "scanned_files": self.result.scanned_files,
                "scanned_dirs": self.result.scanned_dirs,
                "scan_duration": self.result.scan_time,
            },
            "severity_counts": {s.value: c for s, c in self.result.count_by_severity().items()},
            "findings": [
                {
                    "file_path": f.file_path,
                    "line_number": f.line_number,
                    "severity": f.severity.value,
                    "category": f.category,
                    "description": f.description,
                    "matched_content": f.matched_content,
                    "suggestion": f.suggestion,
                }
                for f in self.result.findings
            ]
        }
        return json.dumps(report, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(
        description='CTF Secrets Scanner - 敏感資料掃描工具',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--path', '-p', default='.',
                       help='要掃描的路徑 (預設: 當前目錄)')
    parser.add_argument('--config', '-c', default='config.yml',
                       help='配置檔案路徑 (預設: config.yml)')
    parser.add_argument('--format', '-f', choices=['text', 'markdown', 'json'],
                       default='text', help='輸出格式 (預設: text)')
    parser.add_argument('--output', '-o', help='輸出報告檔案路徑')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細輸出')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='只輸出結果碼')
    parser.add_argument('--fail-on-high', action='store_true',
                       help='發現 HIGH 等級問題時返回非零結果碼')
    parser.add_argument('--fail-on-critical', action='store_true', default=True,
                       help='發現 CRITICAL 等級問題時返回非零結果碼 (預設)')
    
    args = parser.parse_args()
    
    # 初始化掃描器
    scanner = SecretsScanner(args.config)
    
    if not args.quiet:
        print("🔍 CTF Secrets Scanner")
        print(f"   掃描路徑: {args.path}")
        print("")
    
    # 執行掃描
    result = scanner.scan(args.path, args.verbose)
    
    # 生成報告
    report = scanner.generate_report(args.format)
    
    # 輸出報告
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        if not args.quiet:
            print(f"📄 報告已儲存: {args.output}")
    elif not args.quiet:
        print(report)
    
    # 決定結果碼
    if result.has_critical:
        if not args.quiet:
            print("\n❌ 掃描失敗：發現 CRITICAL 等級問題")
        sys.exit(1)
    elif args.fail_on_high and result.has_high:
        if not args.quiet:
            print("\n⚠️  掃描警告：發現 HIGH 等級問題")
        sys.exit(1)
    else:
        if not args.quiet and not result.findings:
            print("\n✅ 掃描通過：未發現問題")
        sys.exit(0)


if __name__ == "__main__":
    main()

