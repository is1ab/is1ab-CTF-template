#!/bin/bash
# =============================================================================
# Git Hooks 設置腳本
# =============================================================================
# 功能：
# 1. 安裝 pre-commit hook（防止提交 flag 和敏感資料）
# 2. 安裝 pre-push hook（防止推送敏感資料到遠端）
# 3. 設置執行權限
# =============================================================================

set -e

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 取得專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🔧 IS1AB CTF - Git Hooks 設置${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 檢查是否在 git repository 中
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}❌ 錯誤: 不在 Git repository 中${NC}"
    echo -e "請在專案根目錄執行此腳本"
    exit 1
fi

echo -e "${YELLOW}專案目錄: $PROJECT_ROOT${NC}"
echo -e "${YELLOW}Hooks 目錄: $HOOKS_DIR${NC}"
echo ""

# =============================================================================
# 函數: 創建 pre-commit hook
# =============================================================================
create_precommit_hook() {
    echo -e "${BLUE}📝 創建 pre-commit hook...${NC}"

    cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook: 防止提交 flag 和敏感資料

set -e

echo "🔍 執行 pre-commit 安全檢查..."

# 讀取 flag 前綴
FLAG_PREFIX=$(grep -E "^\s*flag_prefix:" config.yml 2>/dev/null | awk -F'"' '{print $2}' | head -1)
FLAG_PREFIX=${FLAG_PREFIX:-is1abCTF}

# 檢查暫存區的文件
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(yml|yaml|py|js|md|txt)$' || true)

if [ -z "$STAGED_FILES" ]; then
  echo "✅ 無需檢查的文件"
  exit 0
fi

# 掃描 flag 格式
echo "🔍 掃描 flag 格式: ${FLAG_PREFIX}{...}"
FLAG_FOUND=false

for file in $STAGED_FILES; do
  # 跳過 template、private.yml、文件、測試
  if [[ "$file" == *"template"* ]] || [[ "$file" == *"private.yml"* ]]; then
    continue
  fi
  if [[ "$file" == docs/* ]] || [[ "$file" == tests/* ]] || [[ "$file" == QUICKSTART.md ]]; then
    continue
  fi
  if [[ "$file" == CHALLENGE_TYPES_REFERENCE.md ]]; then
    continue
  fi

  # 檢查是否有 flag pattern，排除已知 placeholder
  if git diff --cached "$file" | grep -q "${FLAG_PREFIX}{"; then
    # 排除 fake/example/test placeholder
    real_flags=$(git diff --cached "$file" | grep "${FLAG_PREFIX}{" | grep -v -E "(fake_flag|example|placeholder|test_flag|your_flag|xxx|\.\.\.)" || true)
    if [ -n "$real_flags" ]; then
      echo "❌ 錯誤: 在 $file 中發現 flag!"
      FLAG_FOUND=true
    fi
  fi
done

# 檢查敏感文件
echo "🔍 檢查敏感文件..."
SENSITIVE_FILES=(
  "private.yml"
  "secrets.yml"
  "secrets.json"
  "credentials.json"
  ".env.local"
  ".env.production"
)

for pattern in "${SENSITIVE_FILES[@]}"; do
  if echo "$STAGED_FILES" | grep -q "$pattern"; then
    echo "⚠️  警告: 嘗試提交敏感文件: $pattern"
    echo "如確定要提交,請使用: git commit --no-verify"
    exit 1
  fi
done

if [ "$FLAG_FOUND" = true ]; then
  echo ""
  echo "❌ Pre-commit 檢查失敗!"
  echo "請移除 flag 後再提交,或使用 --no-verify 強制提交"
  exit 1
fi

echo "✅ Pre-commit 檢查通過"
exit 0
EOF

    chmod +x "$HOOKS_DIR/pre-commit"
    echo -e "${GREEN}✅ Pre-commit hook 已創建${NC}"
}

# =============================================================================
# 函數: 創建 pre-push hook
# =============================================================================
create_prepush_hook() {
    echo -e "${BLUE}📝 創建 pre-push hook...${NC}"

    cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook: 防止推送包含 flag 和敏感資料的 commits

set -e

echo "🚀 執行 pre-push 安全檢查..."

# 讀取標準輸入中的推送信息
while read local_ref local_sha remote_ref remote_sha
do
  # 如果是刪除操作，跳過
  if [ "$local_sha" = "0000000000000000000000000000000000000000" ]; then
    continue
  fi

  # 如果遠端分支是新的，從第一個 commit 開始檢查
  if [ "$remote_sha" = "0000000000000000000000000000000000000000" ]; then
    range="$local_sha"
  else
    range="$remote_sha..$local_sha"
  fi

  # 讀取 flag 前綴
  FLAG_PREFIX=$(grep -E "^\s*flag_prefix:" config.yml 2>/dev/null | awk -F'"' '{print $2}' | head -1)
  FLAG_PREFIX=${FLAG_PREFIX:-is1abCTF}

  echo "🔍 檢查範圍: $range"
  echo "🚩 Flag 前綴: $FLAG_PREFIX"

  # 檢查將要推送的 commits 中的檔案內容
  FLAG_FOUND=false
  SENSITIVE_FOUND=false

  # 獲取將要推送的文件列表
  files=$(git diff --name-only "$range" 2>/dev/null || git diff-tree --no-commit-id --name-only -r "$range" 2>/dev/null || true)

  if [ -z "$files" ]; then
    echo "✅ 無文件變更"
    continue
  fi

  # 敏感文件列表
  SENSITIVE_FILES=(
    "private.yml"
    "private.yaml"
    "secrets.yml"
    "secrets.yaml"
    "secrets.json"
    "credentials.json"
    ".env.local"
    ".env.production"
  )

  echo "📁 檢查 $(echo "$files" | wc -l) 個文件..."

  for file in $files; do
    # 跳過已刪除的文件
    if [ ! -f "$file" ]; then
      continue
    fi

    # 跳過 template 文件
    if [[ "$file" == *"template"* ]]; then
      continue
    fi

    # 檢查是否為敏感文件
    for pattern in "${SENSITIVE_FILES[@]}"; do
      if [[ "$file" == *"$pattern"* ]]; then
        echo "❌ 錯誤: 嘗試推送敏感文件: $file"
        SENSITIVE_FOUND=true
      fi
    done

    # 檢查文件內容中的 flag（排除 private.yml、文件、測試）
    if [[ "$file" != *"private.yml"* ]] && [[ "$file" != *"private.yaml"* ]] \
       && [[ "$file" != docs/* ]] && [[ "$file" != tests/* ]] \
       && [[ "$file" != QUICKSTART.md ]] && [[ "$file" != CHALLENGE_TYPES_REFERENCE.md ]]; then
      if grep -q "${FLAG_PREFIX}{" "$file" 2>/dev/null; then
        # 排除 fake/example/test placeholder
        real_flags=$(grep "${FLAG_PREFIX}{" "$file" | grep -v -E "(fake_flag|example|placeholder|test_flag|your_flag|xxx|\.\.\.)" || true)
        if [ -n "$real_flags" ]; then
          echo "❌ 錯誤: 在 $file 中發現 flag!"
          FLAG_FOUND=true
        fi
      fi
    fi

    # 檢查公開目錄
    if [[ "$file" == public-release/* ]]; then
      if [[ "$file" == *"private.yml"* ]] || [[ "$file" == *"private.yaml"* ]]; then
        echo "❌ 嚴重錯誤: public-release 中發現 private.yml: $file"
        SENSITIVE_FOUND=true
      fi

      if grep -q "${FLAG_PREFIX}{" "$file" 2>/dev/null; then
        echo "❌ 嚴重錯誤: public-release 中發現 flag: $file"
        FLAG_FOUND=true
      fi
    fi
  done

  # 檢查是否推送到受保護的分支
  if [[ "$remote_ref" == "refs/heads/main" ]] || [[ "$remote_ref" == "refs/heads/master" ]]; then
    echo "⚠️  警告: 正在推送到主分支 $remote_ref"

    if [ "$FLAG_FOUND" = true ] || [ "$SENSITIVE_FOUND" = true ]; then
      echo ""
      echo "❌ Pre-push 檢查失敗!"
      echo "不能推送包含敏感資料的 commits 到主分支"
      echo ""
      echo "請修復問題後再推送，或使用 --no-verify 強制推送"
      exit 1
    fi
  fi

  if [ "$FLAG_FOUND" = true ] || [ "$SENSITIVE_FOUND" = true ]; then
    echo ""
    echo "❌ Pre-push 檢查失敗!"
    echo "發現以下問題："
    [ "$FLAG_FOUND" = true ] && echo "  - Flag 洩漏"
    [ "$SENSITIVE_FOUND" = true ] && echo "  - 敏感文件"
    echo ""
    echo "請修復問題後再推送，或使用 --no-verify 強制推送"
    exit 1
  fi
done

echo "✅ Pre-push 檢查通過"
exit 0
EOF

    chmod +x "$HOOKS_DIR/pre-push"
    echo -e "${GREEN}✅ Pre-push hook 已創建${NC}"
}

# =============================================================================
# 主程序
# =============================================================================

# 備份現有的 hooks
if [ -f "$HOOKS_DIR/pre-commit" ] && [ ! -L "$HOOKS_DIR/pre-commit" ]; then
    echo -e "${YELLOW}⚠️  備份現有的 pre-commit hook...${NC}"
    cp "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/pre-commit.backup.$(date +%Y%m%d_%H%M%S)"
fi

if [ -f "$HOOKS_DIR/pre-push" ] && [ ! -L "$HOOKS_DIR/pre-push" ]; then
    echo -e "${YELLOW}⚠️  備份現有的 pre-push hook...${NC}"
    cp "$HOOKS_DIR/pre-push" "$HOOKS_DIR/pre-push.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo ""

# 創建 hooks
create_precommit_hook
echo ""
create_prepush_hook

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✅ Git Hooks 設置完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "已安裝的 hooks:"
echo -e "  ${GREEN}✓${NC} pre-commit  - 防止提交 flag 和敏感資料"
echo -e "  ${GREEN}✓${NC} pre-push    - 防止推送敏感資料到遠端"
echo ""
echo -e "${YELLOW}測試 hooks:${NC}"
echo -e "  # 測試 pre-commit"
echo -e "  echo 'is1abCTF{test_flag}' > test.txt"
echo -e "  git add test.txt"
echo -e "  git commit -m 'test'  # 應該被阻止"
echo -e "  rm test.txt"
echo ""
echo -e "${YELLOW}繞過 hooks (不建議):${NC}"
echo -e "  git commit --no-verify"
echo -e "  git push --no-verify"
echo ""
echo -e "📖 更多資訊: docs/security-workflow-guide.md"
echo ""

# 提示 pre-commit 框架
if command -v pre-commit &> /dev/null; then
    echo -e "${GREEN}✨ 偵測到 pre-commit 已安裝！${NC}"
    echo -e "   建議使用 pre-commit 框架取代手動 hooks："
    echo -e "   ${YELLOW}pre-commit install${NC}"
    echo ""
else
    echo -e "${YELLOW}💡 提示：${NC}也可以使用 pre-commit 框架管理 hooks："
    echo -e "   ${YELLOW}uv tool install pre-commit && pre-commit install${NC}"
    echo ""
fi
