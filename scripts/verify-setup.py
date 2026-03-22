#!/usr/bin/env python3
"""
驗證專案設置是否完整
檢查必要的配置、secrets、hooks 等
"""

import os
import sys
from pathlib import Path
import yaml

def check_git_hooks():
    """檢查 Git Hooks 是否啟用"""
    print("\n🔍 檢查 Git Hooks...")

    hooks_dir = Path(".git/hooks")
    required_hooks = ["pre-commit", "pre-push"]
    missing_hooks = []

    for hook in required_hooks:
        hook_path = hooks_dir / hook
        if not hook_path.exists():
            missing_hooks.append(hook)
        elif not os.access(hook_path, os.X_OK):
            print(f"  ⚠️  {hook} 存在但無執行權限")

    if missing_hooks:
        print(f"  ❌ 缺少以下 hooks: {', '.join(missing_hooks)}")
        print(f"     建議: 啟用 pre-commit hook 以防止提交敏感資料")
        return False
    else:
        print("  ✅ Git Hooks 已啟用")
        return True

def check_config():
    """檢查 config.yml 配置"""
    print("\n🔍 檢查配置文件...")

    if not Path("config.yml").exists():
        print("  ❌ config.yml 不存在")
        return False

    with open("config.yml") as f:
        config = yaml.safe_load(f)

    issues = []

    # 檢查必要欄位
    if not config.get("project", {}).get("flag_prefix"):
        issues.append("未設置 flag_prefix")

    # 檢查公開倉庫配置（可選，公開發布時才需要）
    repo_name = config.get("public_release", {}).get("repository", {}).get("name", "")
    if not repo_name:
        print("  ⚠️  未配置 public_release.repository.name（公開發布時需要）")

    # 檢查通知配置（可選）
    # Slack webhook 為可選配置，不顯示提示以避免干擾

    if issues:
        print(f"  ❌ 配置問題: {', '.join(issues)}")
        return False
    else:
        print("  ✅ 配置文件完整")
        return True

def check_github_secrets():
    """檢查 GitHub Secrets (僅提示)"""
    print("\n🔍 檢查 GitHub Secrets...")
    print("  ℹ️  請手動驗證以下 secrets 已在 GitHub 設置:")
    print("     - PUBLIC_REPO_TOKEN (必須)")
    print("     - SLACK_WEBHOOK_URL (可選)")
    print("  📖 參考: wiki/GitHub-Secrets-Setup.md")
    return True

def check_documentation():
    """檢查關鍵文檔是否存在"""
    print("\n🔍 檢查文檔...")

    required_docs = [
        "README.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "docs/quick-reference.md",
        "docs/security-checklist.md"
    ]

    missing_docs = [doc for doc in required_docs if not Path(doc).exists()]

    if missing_docs:
        print(f"  ⚠️  缺少文檔: {', '.join(missing_docs)}")
        return False
    else:
        print("  ✅ 關鍵文檔完整")
        return True

def check_gitignore():
    """檢查 .gitignore 是否包含敏感文件規則"""
    print("\n🔍 檢查 .gitignore...")

    if not Path(".gitignore").exists():
        print("  ❌ .gitignore 不存在")
        return False

    with open(".gitignore") as f:
        content = f.read()

    required_patterns = [
        "**/flag.txt",
        "**/private.yml",
        "**/secrets.yml",
        "*.key",
        "*.pem"
    ]

    missing_patterns = [p for p in required_patterns if p not in content]

    if missing_patterns:
        print(f"  ⚠️  缺少保護規則: {', '.join(missing_patterns)}")
        return False
    else:
        print("  ✅ .gitignore 配置完善")
        return True

def main():
    print("=" * 60)
    print("🔧 IS1AB CTF Template - 設置驗證工具")
    print("=" * 60)

    checks = [
        check_git_hooks(),
        check_config(),
        check_github_secrets(),
        check_documentation(),
        check_gitignore()
    ]

    print("\n" + "=" * 60)

    if all(checks):
        print("✅ 所有檢查通過!")
        print("🎉 專案設置完整,可以開始使用")
        print()
        print("🎯 下一步：建立你的第一個題目")
        print("   make new-challenge ARGS=\"<category> <name> <difficulty>\"")
        print()
        print("   範例：")
        print("   make new-challenge ARGS=\"web my_first_web easy\"")
        print("   make new-challenge ARGS=\"crypto rsa_baby baby\"")
        print("   make new-challenge ARGS=\"pwn buffer_overflow easy\"")
        print()
        print("📖 完整教學：QUICKSTART.md")
        print("❓ 遇到問題：docs/troubleshooting.md")
        return 0
    else:
        print("⚠️  部分檢查未通過")
        print("請根據上述提示完成配置")
        print()
        print("💡 提示：執行 make setup 可自動修復大部分問題")
        return 1

if __name__ == "__main__":
    sys.exit(main())
