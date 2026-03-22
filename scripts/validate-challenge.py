#!/usr/bin/env python3
# scripts/validate-challenge.py

import yaml
import sys
from pathlib import Path
import argparse
import subprocess
import json
import re

class ChallengeValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_challenge(self, challenge_path):
        """驗證單個題目"""
        try:
            challenge_path = Path(challenge_path)
            
            if not challenge_path.exists():
                self.errors.append(f"Challenge path does not exist: {challenge_path}")
                return False
                
            if not challenge_path.is_dir():
                self.errors.append(f"Challenge path is not a directory: {challenge_path}")
                return False
                
            print(f"🔍 Validating challenge: {challenge_path}")
            
            # 讀取 public.yml 以確定題目類型
            challenge_type = self.get_challenge_type(challenge_path)
            if challenge_type is None:
                self.errors.append(f"Cannot determine challenge type from {challenge_path}")
                return False
            
            # 驗證目錄結構
            self.validate_directory_structure(challenge_path, challenge_type)
            
            # 驗證 public.yml
            self.validate_public_yml(challenge_path)
            
            # 驗證 Docker 檔案
            self.validate_docker_files(challenge_path, challenge_type)
            
            # 驗證敏感資料
            self.check_sensitive_data(challenge_path)
            
            # 特定類型驗證
            if challenge_type == 'nc_challenge':
                self.validate_nc_challenge(challenge_path)
            
            return len(self.errors) == 0
            
        except PermissionError as e:
            self.errors.append(f"Permission error accessing {challenge_path}: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Unexpected error validating {challenge_path}: {e}")
            return False
    
    def get_challenge_type(self, challenge_path):
        """取得題目類型"""
        public_yml = challenge_path / 'public.yml'
        if public_yml.exists():
            try:
                with open(public_yml, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    challenge_type = data.get('challenge_type', 'static_attachment')
                    print(f"📝 Detected challenge type: {challenge_type}")
                    return challenge_type
            except yaml.YAMLError as e:
                self.errors.append(f"YAML parsing error in public.yml: {e}")
                return None
            except IOError as e:
                self.errors.append(f"Cannot read public.yml: {e}")
                return None
            except Exception as e:
                self.errors.append(f"Error reading challenge type: {e}")
                return None
        else:
            self.errors.append(f"Missing public.yml file in {challenge_path}")
            return None
        
    def validate_directory_structure(self, challenge_path, challenge_type):
        """驗證目錄結構"""
        base_required_dirs = ['src', 'docker', 'writeup', 'files']
        required_files = ['README.md', 'public.yml']
        
        # 根據題目類型調整必要目錄
        if challenge_type == 'nc_challenge':
            base_required_dirs.append('bin')
        
        for dir_name in base_required_dirs:
            dir_path = challenge_path / dir_name
            if not dir_path.exists():
                self.warnings.append(f"Missing directory: {dir_path}")
                
        for file_name in required_files:
            file_path = challenge_path / file_name
            if not file_path.exists():
                self.errors.append(f"Missing required file: {file_path}")
                
    def validate_public_yml(self, challenge_path):
        """驗證 public.yml 格式"""
        public_yml = challenge_path / 'public.yml'
        
        if not public_yml.exists():
            return
            
        try:
            with open(public_yml, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # 必要欄位檢查
            required_fields = ['title', 'author', 'difficulty', 'category', 'description', 'challenge_type', 'source_code_provided']
            for field in required_fields:
                if field not in data:
                    self.errors.append(f"Missing required field in public.yml: {field}")
                elif field == 'source_code_provided':
                    # source_code_provided 應該是布林值
                    if not isinstance(data[field], bool):
                        self.errors.append(f"Field '{field}' should be boolean (true/false)")
                elif not data[field] or str(data[field]).startswith("TODO"):
                    self.warnings.append(f"Field '{field}' needs to be updated in public.yml")
                    
            # 值驗證
            valid_difficulties = ['baby', 'easy', 'middle', 'hard', 'impossible']
            if data.get('difficulty') not in valid_difficulties:
                self.errors.append(f"Invalid difficulty: {data.get('difficulty')}")
                
            valid_categories = ['web', 'pwn', 'reverse', 'crypto', 'forensic', 'misc', 'general']
            if data.get('category') not in valid_categories:
                self.errors.append(f"Invalid category: {data.get('category')}")
                
            valid_types = ['static_attachment', 'static_container', 'dynamic_attachment', 'dynamic_container', 'nc_challenge']
            if data.get('challenge_type') not in valid_types:
                self.errors.append(f"Invalid challenge_type: {data.get('challenge_type')}")
                
            valid_statuses = ['planning', 'developing', 'testing', 'completed', 'deployed']
            if data.get('status') not in valid_statuses:
                self.warnings.append(f"Invalid status: {data.get('status')}")
                
            # NC 題目特殊驗證
            if data.get('challenge_type') == 'nc_challenge':
                deploy_info = data.get('deploy_info', {})
                if 'nc_port' not in deploy_info:
                    self.warnings.append("NC challenge missing nc_port in deploy_info")
                if 'timeout' not in deploy_info:
                    self.warnings.append("NC challenge missing timeout in deploy_info")
                
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in public.yml: {e}")
        except Exception as e:
            self.errors.append(f"Error reading public.yml: {e}")
            
    def validate_docker_files(self, challenge_path, challenge_type):
        """驗證 Docker 檔案"""
        docker_dir = challenge_path / 'docker'
        
        if not docker_dir.exists():
            return
            
        dockerfile = docker_dir / 'Dockerfile'
        compose_file = docker_dir / 'docker-compose.yml'
        
        if dockerfile.exists():
            self.validate_dockerfile(dockerfile, challenge_type)
            
        if compose_file.exists():
            self.validate_compose_file(compose_file, challenge_type)
        
        # NC 題目特殊檔案驗證
        if challenge_type == 'nc_challenge':
            self.validate_nc_docker_files(docker_dir)
            
    def validate_dockerfile(self, dockerfile_path, challenge_type):
        """驗證 Dockerfile"""
        try:
            with open(dockerfile_path, 'r') as f:
                content = f.read()
                
            # 基本檢查
            if 'FROM' not in content:
                self.errors.append("Dockerfile missing FROM instruction")
                
            if 'EXPOSE' not in content:
                self.warnings.append("Dockerfile should include EXPOSE instruction")
            
            # NC 題目特殊檢查
            if challenge_type == 'nc_challenge':
                if 'socat' not in content and 'xinetd' not in content:
                    self.warnings.append("NC challenge should use socat or xinetd")
                if 'useradd' not in content and 'adduser' not in content:
                    self.warnings.append("NC challenge should create a non-root user")
                    
            # 安全性檢查
            if 'root' in content.lower() and 'user' not in content.lower() and challenge_type != 'nc_challenge':
                self.warnings.append("Consider using non-root user in Dockerfile")
                
        except Exception as e:
            self.errors.append(f"Error reading Dockerfile: {e}")
            
    def validate_compose_file(self, compose_path, challenge_type):
        """驗證 docker-compose.yml"""
        try:
            with open(compose_path, 'r') as f:
                data = yaml.safe_load(f)
                
            if 'services' not in data:
                self.errors.append("docker-compose.yml missing services section")
                return
                
            for service_name, service_config in data['services'].items():
                # 檢查端口配置
                if 'ports' in service_config:
                    for port_mapping in service_config['ports']:
                        if isinstance(port_mapping, str) and ':' in port_mapping:
                            host_port = port_mapping.split(':')[0]
                            if host_port.isdigit() and int(host_port) < 1024:
                                self.warnings.append(f"Service {service_name} uses privileged port {host_port}")
                
                # NC 題目端口檢查
                if challenge_type == 'nc_challenge':
                    if 'ports' in service_config:
                        has_nc_port = any('9999' in str(port) for port in service_config['ports'])
                        if not has_nc_port:
                            self.warnings.append("NC challenge should expose port 9999")
                            
                # 檢查環境變數
                if 'environment' in service_config:
                    env_vars = service_config['environment']
                    if isinstance(env_vars, list):
                        for env_var in env_vars:
                            if 'FLAG=' in env_var and 'placeholder' not in env_var:
                                self.warnings.append("Hardcoded flag found in docker-compose.yml")
                                
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in docker-compose.yml: {e}")
        except Exception as e:
            self.errors.append(f"Error reading docker-compose.yml: {e}")
    
    def validate_nc_docker_files(self, docker_dir):
        """驗證 NC 題目的特殊檔案"""
        start_sh = docker_dir / 'start.sh'
        run_sh = docker_dir / 'run.sh'

        # start.sh 和 run.sh 是可選的（Dockerfile 可直接用 socat CMD）
        if start_sh.exists():
            self.validate_nc_script(start_sh, 'start.sh')

        if run_sh.exists():
            self.validate_nc_script(run_sh, 'run.sh')
    
    def validate_nc_script(self, script_path, script_name):
        """驗證 NC 題目的腳本檔案"""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
            
            # 檢查 shebang
            if not content.startswith('#!/bin/bash'):
                self.warnings.append(f"{script_name} should start with #!/bin/bash")
            
            if script_name == 'start.sh':
                # start.sh 應該包含 socat 或 xinetd 設定
                if 'socat' not in content and 'xinetd' not in content:
                    self.warnings.append("start.sh should contain socat or xinetd configuration")
                if 'FLAG' not in content:
                    self.warnings.append("start.sh should handle FLAG environment variable")
            
            elif script_name == 'run.sh':
                # run.sh 應該執行題目程式
                if 'timeout' not in content:
                    self.warnings.append("run.sh should include timeout mechanism")
                if '/bin/bash' in content:
                    self.warnings.append("run.sh contains bash shell - remove for production")
                    
        except Exception as e:
            self.errors.append(f"Error reading {script_name}: {e}")
            
    def validate_nc_challenge(self, challenge_path):
        """驗證 NC 題目特殊需求"""
        src_dir = challenge_path / 'src'
        bin_dir = challenge_path / 'docker' / 'bin'
        
        # 檢查源碼目錄
        if src_dir.exists():
            # 檢查是否有 Makefile
            makefile = src_dir / 'Makefile'
            if not makefile.exists():
                self.warnings.append("NC challenge should include Makefile for compilation")
            
            # 檢查是否有 C/C++ 檔案
            c_files = list(src_dir.glob('*.c')) + list(src_dir.glob('*.cpp'))
            if c_files:
                self.validate_c_source(c_files[0])
        
        # 檢查 bin 目錄
        if not bin_dir.exists():
            self.warnings.append("NC challenge should have docker/bin directory for executables")
            
    def validate_c_source(self, c_file):
        """驗證 C 源碼檔案"""
        try:
            with open(c_file, 'r') as f:
                content = f.read()
            
            # 檢查危險函數
            dangerous_funcs = ['gets', 'strcpy', 'strcat', 'sprintf']
            for func in dangerous_funcs:
                if f'{func}(' in content:
                    self.warnings.append(f"Potentially dangerous function '{func}' found in {c_file.name}")
            
            # 檢查是否讀取 flag 檔案
            if 'flag.txt' not in content and 'FLAG' not in content:
                self.warnings.append("Source code should read flag from flag.txt or environment")
                
        except Exception as e:
            self.warnings.append(f"Could not validate C source: {e}")
            
    def check_sensitive_data(self, challenge_path):
        """檢查敏感資料 - 強化版本"""
        # 載入 config.yml 獲取 flag_prefix
        flag_prefix = "is1abCTF"
        try:
            config_path = Path(__file__).parent.parent / "config.yml"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    flag_prefix = config.get('project', {}).get('flag_prefix', 'is1abCTF')
        except Exception:
            pass
        
        # 強化敏感資料模式
        sensitive_patterns = [
            # Flag 格式（動態使用 flag_prefix）
            (rf'{re.escape(flag_prefix)}\{{[^}}]+\}}', 'CRITICAL', 'Flag 洩漏'),
            # 通用 CTF Flag 格式
            (r'[A-Za-z0-9_]+CTF\{[^}]+\}', 'HIGH', '可能的 Flag 格式'),
            # 硬編碼密碼
            (r'password\s*[:=]\s*["\']?[^"\s\']{4,}', 'HIGH', '硬編碼密碼'),
            (r'passwd\s*[:=]\s*["\']?[^"\s\']{4,}', 'HIGH', '硬編碼密碼'),
            # Secret/Token
            (r'secret\s*[:=]\s*["\']?[^"\s\']+', 'HIGH', 'Secret 洩漏'),
            (r'token\s*[:=]\s*["\']?[^"\s\']+', 'HIGH', 'Token 洩漏'),
            (r'api[_-]?key\s*[:=]\s*["\']?[A-Za-z0-9]{16,}', 'HIGH', 'API Key'),
            # 私鑰
            (r'-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----', 'CRITICAL', '私鑰洩漏'),
            # 資料庫連接字串
            (r'(mysql|postgres|mongodb)://[^:]+:[^@]+@', 'HIGH', '資料庫連接字串'),
        ]
        
        # 檢查所有公開檔案（排除 private 目錄）
        public_files = [
            'README.md',
            'public.yml',
            'docker/Dockerfile',
            'docker/docker-compose.yml',
            'docker/start.sh',
            'docker/run.sh',
        ]
        
        # 遞迴檢查 files/ 目錄（公開檔案）
        files_dir = challenge_path / 'files'
        if files_dir.exists():
            for file_path in files_dir.rglob('*'):
                if file_path.is_file():
                    public_files.append(str(file_path.relative_to(challenge_path)))
        
        # 檢查 src/ 目錄（源碼可能被公開）
        src_dir = challenge_path / 'src'
        if src_dir.exists():
            for file_path in src_dir.rglob('*'):
                if file_path.is_file() and file_path.suffix in ['.py', '.js', '.html', '.php', '.c', '.cpp']:
                    public_files.append(str(file_path.relative_to(challenge_path)))
        
        # 執行檢查
        critical_issues = []
        for file_name in public_files:
            file_path = challenge_path / file_name
            if file_path.exists():
                issues = self.check_file_for_sensitive_data(file_path, sensitive_patterns, flag_prefix)
                critical_issues.extend(issues)
        
        # 如果有 CRITICAL 問題，標記為錯誤
        for issue in critical_issues:
            self.errors.append(issue)
                
    def check_file_for_sensitive_data(self, file_path, patterns, flag_prefix):
        """檢查檔案中的敏感資料 - 強化版本"""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # 檢查檔案大小（避免檢查二進制檔案）
            if len(content) > 1000000:  # 1MB
                return issues
                
            for pattern, severity, description in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
                if matches:
                    for match in matches[:3]:  # 只顯示前 3 個匹配
                        # 檢查是否為 placeholder 或範例
                        is_placeholder = any(keyword in content.lower() for keyword in [
                            'placeholder', 'example', 'fake', 'demo', 'test', 
                            'your_flag_here', 'flag_here', 'replace_this'
                        ])
                        
                        # 檢查是否在註釋中
                        lines = content.split('\n')
                        match_line = None
                        for i, line in enumerate(lines, 1):
                            if match in line:
                                match_line = i
                                # 檢查是否在註釋中
                                stripped = line.strip()
                                if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
                                    is_placeholder = True
                                break
                        
                        if not is_placeholder:
                            match_preview = match[:30] + '...' if len(match) > 30 else match
                            issue_msg = f"{severity}: {description} 在 {file_path.name}"
                            if match_line:
                                issue_msg += f" (第 {match_line} 行)"
                            issue_msg += f": {match_preview}"
                            
                            if severity == 'CRITICAL':
                                issues.append(issue_msg)
                            else:
                                self.warnings.append(issue_msg)
                        
        except UnicodeDecodeError:
            # 二進制檔案，跳過
            pass
        except Exception as e:
            self.warnings.append(f"無法檢查 {file_path.name}: {e}")
        
        return issues
            
    def validate_all_challenges(self):
        """驗證所有題目"""
        challenges_dir = Path('challenges')
        if not challenges_dir.exists():
            print("❌ No challenges directory found")
            return False
            
        all_valid = True
        
        for category_dir in challenges_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            for challenge_dir in category_dir.iterdir():
                if not challenge_dir.is_dir():
                    continue
                    
                # 重置錯誤列表
                self.errors = []
                self.warnings = []
                
                if not self.validate_challenge(challenge_dir):
                    all_valid = False
                    
                self.print_results(challenge_dir)
                
        return all_valid
        
    def print_results(self, challenge_path):
        """列印驗證結果"""
        if not self.errors and not self.warnings:
            print(f"✅ {challenge_path.name}: All checks passed")
            return
            
        print(f"\n📋 Validation results for {challenge_path.name}:")
        
        if self.errors:
            print("❌ Errors:")
            for error in self.errors:
                print(f"   - {error}")
                
        if self.warnings:
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
                
        print()

def main():
    try:
        parser = argparse.ArgumentParser(description='Validate CTF challenges')
        parser.add_argument('path', nargs='?', help='Path to specific challenge (optional)')
        parser.add_argument('--all', action='store_true', help='Validate all challenges')
        parser.add_argument('--pr', type=int, help='PR number to validate')
        
        args = parser.parse_args()
        
        validator = ChallengeValidator()
        
        if args.pr:
            # 取得 PR 變更的檔案
            try:
                result = subprocess.run(['git', 'diff', '--name-only', f'origin/main...HEAD'], 
                                      capture_output=True, text=True, check=True)
                changed_files = result.stdout.strip().split('\n')
                
                # 找出變更的 challenge 目錄
                challenge_dirs = set()
                for file_path in changed_files:
                    if file_path.startswith('challenges/'):
                        parts = Path(file_path).parts
                        if len(parts) >= 3:  # challenges/category/name/...
                            challenge_dir = Path(parts[0]) / parts[1] / parts[2]
                            challenge_dirs.add(challenge_dir)
                            
                if not challenge_dirs:
                    print("✅ No challenges to validate")
                    return
                    
                all_valid = True
                for challenge_dir in challenge_dirs:
                    validator.errors = []
                    validator.warnings = []
                    if not validator.validate_challenge(challenge_dir):
                        all_valid = False
                    validator.print_results(challenge_dir)
                    
                sys.exit(0 if all_valid else 1)
                
            except subprocess.CalledProcessError as e:
                print(f"❌ Could not get PR diff: {e}")
                sys.exit(1)
            except Exception as e:
                print(f"❌ Error processing PR: {e}")
                sys.exit(1)
                
        elif args.all:
            try:
                success = validator.validate_all_challenges()
                sys.exit(0 if success else 1)
            except Exception as e:
                print(f"❌ Error validating all challenges: {e}")
                sys.exit(1)
            
        elif args.path:
            try:
                validator.errors = []
                validator.warnings = []
                success = validator.validate_challenge(args.path)
                validator.print_results(Path(args.path))
                sys.exit(0 if success else 1)
            except Exception as e:
                print(f"❌ Error validating challenge {args.path}: {e}")
                sys.exit(1)
            
        else:
            print("❌ Please specify --all, --pr <number>, or a specific challenge path")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()