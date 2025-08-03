#!/usr/bin/env python3
"""
敏感資料檢查腳本
防止 Flag、密碼等敏感資訊被意外提交
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

class SensitiveDataChecker:
    def __init__(self):
        # 敏感內容模式
        self.sensitive_patterns = [
            # Flag 模式
            (r'[a-zA-Z0-9]+CTF\{[^}]+\}', 'Flag'),
            (r'flag\{[^}]+\}', 'Flag'),
            (r'FLAG\{[^}]+\}', 'Flag'),
            
            # 密碼模式
            (r'password\s*[:=]\s*["\']?[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]+["\']?', 'Password'),
            (r'secret_key\s*[:=]\s*["\']?[a-zA-Z0-9]+["\']?', 'Secret Key'),
            (r'api_key\s*[:=]\s*["\']?[a-zA-Z0-9]+["\']?', 'API Key'),
            
            # 私鑰模式
            (r'-----BEGIN [A-Z ]*PRIVATE KEY-----', 'Private Key'),
            (r'ssh-rsa [A-Za-z0-9+/=]+', 'SSH Key'),
            
            # 資料庫連線字串
            (r'mysql://[^@]+:[^@]+@[^/]+', 'Database Connection'),
            (r'postgresql://[^@]+:[^@]+@[^/]+', 'Database Connection'),
            
            # JWT Token
            (r'eyJ[a-zA-Z0-9_=]+\.eyJ[a-zA-Z0-9_=]+\.[a-zA-Z0-9_\-=]+', 'JWT Token'),
            
            # 常見敏感詞
            (r'admin_password', 'Admin Password'),
            (r'root_password', 'Root Password'),
            (r'database_password', 'Database Password'),
        ]
        
        # 安全的 Flag 模式 (範例用)
        self.safe_patterns = [
            r'is1abCTF\{example\}',
            r'is1abCTF\{test\}',
            r'is1abCTF\{sample\}',
            r'is1abCTF\{placeholder\}',
            r'FLAGFORMAT\{.*\}',
            r'\[FLAG\]',
            r'<FLAG>',
        ]
        
        # 需要檢查的檔案類型
        self.file_extensions = {
            '.py', '.js', '.html', '.css', '.md', '.txt', '.yml', '.yaml', 
            '.json', '.sh', '.bat', '.ps1', '.env', '.conf', '.cfg', '.ini'
        }
        
        # 需要忽略的目錄
        self.ignore_dirs = {
            '.git', '.venv', 'venv', '__pycache__', 'node_modules', 
            '.idea', '.vscode', 'public-release'
        }

    def is_safe_pattern(self, content, match):
        """檢查是否為安全的 Flag 模式"""
        for safe_pattern in self.safe_patterns:
            if re.search(safe_pattern, match, re.IGNORECASE):
                return True
        
        # 檢查是否在註解中
        lines = content.split('\n')
        for line in lines:
            if match in line and (line.strip().startswith('#') or 
                                line.strip().startswith('//') or
                                line.strip().startswith('*') or
                                '<!--' in line):
                return True
        
        return False

    def check_file(self, file_path):
        """檢查單個檔案"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            return [(file_path, 0, 'File Read Error', str(e))]
        
        lines = content.split('\n')
        
        for pattern, pattern_type in self.sensitive_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                matched_text = match.group()
                
                # 檢查是否為安全模式
                if self.is_safe_pattern(content, matched_text):
                    continue
                
                # 找到匹配的行號
                line_number = content[:match.start()].count('\n') + 1
                
                issues.append((
                    file_path, 
                    line_number, 
                    pattern_type, 
                    matched_text[:50] + '...' if len(matched_text) > 50 else matched_text
                ))
        
        return issues

    def check_directory(self, directory_path):
        """檢查目錄下的所有檔案"""
        directory = Path(directory_path)
        all_issues = []
        
        for file_path in directory.rglob('*'):
            # 跳過目錄
            if file_path.is_dir():
                continue
            
            # 跳過忽略的目錄
            if any(ignore_dir in file_path.parts for ignore_dir in self.ignore_dirs):
                continue
            
            # 檢查檔案類型
            if file_path.suffix not in self.file_extensions:
                continue
            
            # 跳過太大的檔案 (>10MB)
            if file_path.stat().st_size > 10 * 1024 * 1024:
                continue
            
            issues = self.check_file(file_path)
            all_issues.extend(issues)
        
        return all_issues

    def check_staged_files(self):
        """檢查 Git staged 檔案"""
        try:
            # 獲取 staged 檔案列表
            result = subprocess.run(['git', 'diff', '--cached', '--name-only'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                print("❌ 無法獲取 staged 檔案列表")
                return []
            
            staged_files = result.stdout.strip().split('\n')
            staged_files = [f for f in staged_files if f]  # 移除空字串
            
            all_issues = []
            for file_path in staged_files:
                path = Path(file_path)
                if path.exists() and path.suffix in self.file_extensions:
                    issues = self.check_file(path)
                    all_issues.extend(issues)
            
            return all_issues
            
        except Exception as e:
            print(f"❌ 檢查 staged 檔案時發生錯誤: {e}")
            return []

    def report_issues(self, issues):
        """報告發現的問題"""
        if not issues:
            print("✅ 未發現敏感資料")
            return True
        
        print(f"🚨 發現 {len(issues)} 個潛在的敏感資料洩露:")
        print()
        
        for file_path, line_number, issue_type, content in issues:
            print(f"📁 檔案: {file_path}")
            print(f"📍 行號: {line_number}")
            print(f"🏷️  類型: {issue_type}")
            print(f"📝 內容: {content}")
            print("-" * 50)
        
        print()
        print("🔧 建議解決方案:")
        print("1. 將敏感資料移至環境變數或配置檔案")
        print("2. 使用 placeholder 或範例值")
        print("3. 確認這些資料不應該被版本控制")
        print("4. 考慮將檔案加入 .gitignore")
        
        return False

def main():
    parser = argparse.ArgumentParser(description='檢查敏感資料洩露')
    parser.add_argument('--staged', action='store_true',
                       help='只檢查 Git staged 檔案')
    parser.add_argument('--pr-mode', action='store_true',
                       help='PR 模式：檢查變更的檔案')
    parser.add_argument('path', nargs='?', default='.',
                       help='要檢查的路徑 (預設: 當前目錄)')
    
    args = parser.parse_args()
    
    checker = SensitiveDataChecker()
    
    print("🔍 開始檢查敏感資料...")
    
    if args.staged:
        issues = checker.check_staged_files()
    elif args.pr_mode:
        # PR 模式：檢查與 main 分支的差異
        try:
            result = subprocess.run(['git', 'diff', '--name-only', 'origin/main...HEAD'], 
                                  capture_output=True, text=True)
            changed_files = result.stdout.strip().split('\n')
            changed_files = [f for f in changed_files if f and Path(f).exists()]
            
            issues = []
            for file_path in changed_files:
                path = Path(file_path)
                if path.suffix in checker.file_extensions:
                    issues.extend(checker.check_file(path))
        except:
            # 如果無法獲取 diff，就檢查整個目錄
            issues = checker.check_directory(args.path)
    else:
        issues = checker.check_directory(args.path)
    
    success = checker.report_issues(issues)
    
    if success:
        print("🎉 敏感資料檢查通過！")
        sys.exit(0)
    else:
        print("❌ 發現敏感資料，請處理後再提交")
        sys.exit(1)

if __name__ == "__main__":
    main()