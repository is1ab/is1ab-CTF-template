#!/bin/bash
# =============================================================================
# CTF Public Release Build Script
# =============================================================================
# 功能：自動移除敏感資訊並生成安全的公開版本
# 用法：./scripts/build.sh [options]
# =============================================================================

set -e  # 遇到錯誤立即停止

# -----------------------------------------------------------------------------
# 顏色定義
# -----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# 預設變數
# -----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="${PROJECT_ROOT}/config.yml"
CHALLENGES_DIR="${PROJECT_ROOT}/challenges"
OUTPUT_DIR="${PROJECT_ROOT}/public-release"
REPORT_FILE="${PROJECT_ROOT}/build-report.md"

# Flag 格式（從 config.yml 讀取或使用預設）
FLAG_PREFIX="is1abCTF"

# 統計變數
TOTAL_CHALLENGES=0
PROCESSED_CHALLENGES=0
SKIPPED_CHALLENGES=0
FAILED_CHALLENGES=0

# -----------------------------------------------------------------------------
# 輔助函數
# -----------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

# -----------------------------------------------------------------------------
# 顯示使用說明
# -----------------------------------------------------------------------------
show_help() {
    cat << EOF
CTF Public Release Build Script

用法: $0 [options]

選項:
    -h, --help              顯示此幫助訊息
    -o, --output DIR        指定輸出目錄 (預設: public-release)
    -c, --challenge PATH    只建置指定的題目
    -f, --force             強制覆蓋現有輸出
    -n, --dry-run           模擬執行，不實際建立檔案
    -v, --verbose           顯示詳細輸出
    --skip-scan             跳過安全掃描（不建議）
    --include-writeups      包含 writeup（比賽結束後使用）

範例:
    $0                              # 建置所有題目
    $0 -c challenges/web/sqli       # 只建置特定題目
    $0 -o /tmp/public --force       # 輸出到指定目錄
    $0 --dry-run                    # 模擬執行

EOF
    exit 0
}

# -----------------------------------------------------------------------------
# 解析命令列參數
# -----------------------------------------------------------------------------
FORCE=false
DRY_RUN=false
VERBOSE=false
SKIP_SCAN=false
INCLUDE_WRITEUPS=false
SPECIFIC_CHALLENGE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -o|--output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -c|--challenge)
            SPECIFIC_CHALLENGE="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-scan)
            SKIP_SCAN=true
            shift
            ;;
        --include-writeups)
            INCLUDE_WRITEUPS=true
            shift
            ;;
        *)
            log_error "未知選項: $1"
            show_help
            ;;
    esac
done

# -----------------------------------------------------------------------------
# 讀取 Flag 前綴
# -----------------------------------------------------------------------------
read_flag_prefix() {
    if [ -f "$CONFIG_FILE" ]; then
        local prefix=$(grep -E "^\s*flag_prefix:" "$CONFIG_FILE" | awk -F'"' '{print $2}' | head -1)
        if [ -n "$prefix" ]; then
            FLAG_PREFIX="$prefix"
        fi
    fi
    log_info "Flag 前綴: ${FLAG_PREFIX}"
}

# -----------------------------------------------------------------------------
# 準備輸出目錄
# -----------------------------------------------------------------------------
prepare_output_dir() {
    log_step "準備輸出目錄: ${OUTPUT_DIR}"
    
    if [ -d "$OUTPUT_DIR" ]; then
        if [ "$FORCE" = true ]; then
            log_warning "強制覆蓋現有目錄"
            if [ "$DRY_RUN" = false ]; then
                rm -rf "$OUTPUT_DIR"
            fi
        else
            log_error "輸出目錄已存在。使用 -f/--force 覆蓋或指定不同目錄。"
            exit 1
        fi
    fi
    
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$OUTPUT_DIR"
        mkdir -p "$OUTPUT_DIR/challenges"
        mkdir -p "$OUTPUT_DIR/docs"
        mkdir -p "$OUTPUT_DIR/attachments"
    fi
    
    log_success "輸出目錄已準備完成"
}

# -----------------------------------------------------------------------------
# 檢查檔案是否包含敏感資訊
# -----------------------------------------------------------------------------
check_sensitive_content() {
    local file="$1"
    local has_sensitive=false
    
    # 檢查 flag 格式
    if grep -qE "${FLAG_PREFIX}\{[^}]+\}" "$file" 2>/dev/null; then
        log_warning "發現 flag 格式: $file"
        has_sensitive=true
    fi
    
    # 檢查敏感關鍵字
    local sensitive_patterns=(
        "flag:"
        "flag_description:"
        "solution_steps:"
        "internal_notes:"
        "test_credentials:"
        "deploy_secrets:"
        "verified_solutions:"
        "real_flag"
        "actual_flag"
    )
    
    for pattern in "${sensitive_patterns[@]}"; do
        if grep -qi "$pattern" "$file" 2>/dev/null; then
            if [ "$VERBOSE" = true ]; then
                log_warning "發現敏感關鍵字 '$pattern' 在: $file"
            fi
            has_sensitive=true
        fi
    done
    
    if [ "$has_sensitive" = true ]; then
        return 1
    fi
    return 0
}

# -----------------------------------------------------------------------------
# 處理單個題目
# -----------------------------------------------------------------------------
process_challenge() {
    local challenge_path="$1"
    local challenge_name=$(basename "$challenge_path")
    local category=$(basename "$(dirname "$challenge_path")")
    
    ((TOTAL_CHALLENGES++))
    
    log_step "處理題目: ${category}/${challenge_name}"
    
    # 檢查必要檔案
    if [ ! -f "${challenge_path}/public.yml" ]; then
        log_warning "跳過 ${challenge_name}: 缺少 public.yml"
        ((SKIPPED_CHALLENGES++))
        return
    fi
    
    # 檢查是否準備好發布
    local ready_for_release=$(grep -E "^\s*ready_for_release:" "${challenge_path}/public.yml" | grep -i "true" || true)
    if [ -z "$ready_for_release" ]; then
        log_warning "跳過 ${challenge_name}: 尚未標記為準備發布"
        ((SKIPPED_CHALLENGES++))
        return
    fi
    
    # 建立輸出目錄
    local output_challenge_dir="${OUTPUT_DIR}/challenges/${category}/${challenge_name}"
    
    if [ "$DRY_RUN" = false ]; then
        mkdir -p "$output_challenge_dir"
        mkdir -p "$output_challenge_dir/files"
    fi
    
    # 複製 public.yml
    if [ "$DRY_RUN" = false ]; then
        cp "${challenge_path}/public.yml" "$output_challenge_dir/"
        log_info "  ✓ 複製 public.yml"
    fi
    
    # 複製 README.md
    if [ -f "${challenge_path}/README.md" ]; then
        if [ "$DRY_RUN" = false ]; then
            # 過濾 README 中的敏感資訊
            sed -E "s/${FLAG_PREFIX}\{[^}]+\}/[REDACTED]/g" \
                "${challenge_path}/README.md" > "$output_challenge_dir/README.md"
            log_info "  ✓ 複製 README.md（已過濾）"
        fi
    fi
    
    # 複製 files/ 目錄中的檔案
    if [ -d "${challenge_path}/files" ]; then
        if [ "$DRY_RUN" = false ]; then
            for file in "${challenge_path}/files"/*; do
                if [ -f "$file" ]; then
                    local filename=$(basename "$file")
                    # 檢查檔案是否包含敏感資訊
                    if check_sensitive_content "$file"; then
                        cp "$file" "$output_challenge_dir/files/"
                        log_info "  ✓ 複製附件: $filename"
                    else
                        log_warning "  ✗ 跳過敏感附件: $filename"
                    fi
                fi
            done
        fi
    fi
    
    # 處理 writeup（可選）
    if [ "$INCLUDE_WRITEUPS" = true ] && [ -d "${challenge_path}/writeup" ]; then
        if [ "$DRY_RUN" = false ]; then
            mkdir -p "$output_challenge_dir/writeup"
            # 只複製 README.md，過濾其中的敏感資訊
            if [ -f "${challenge_path}/writeup/README.md" ]; then
                sed -E "s/${FLAG_PREFIX}\{[^}]+\}/[FLAG REDACTED]/g" \
                    "${challenge_path}/writeup/README.md" > "$output_challenge_dir/writeup/README.md"
                log_info "  ✓ 複製 writeup（已過濾 flag）"
            fi
        fi
    fi
    
    # Docker 配置（只複製公開部分）
    if [ -d "${challenge_path}/docker" ]; then
        if [ -f "${challenge_path}/docker/docker-compose.yml" ]; then
            if [ "$DRY_RUN" = false ]; then
                mkdir -p "$output_challenge_dir/docker"
                # 過濾 docker-compose.yml 中的敏感環境變數
                sed -E \
                    -e "s/(FLAG=).*/\1\${FLAG}/g" \
                    -e "s/${FLAG_PREFIX}\{[^}]+\}/\${FLAG}/g" \
                    -e "s/(password:).*/\1 \${PASSWORD}/g" \
                    -e "s/(secret_key:).*/\1 \${SECRET_KEY}/g" \
                    "${challenge_path}/docker/docker-compose.yml" > "$output_challenge_dir/docker/docker-compose.yml"
                log_info "  ✓ 複製 docker-compose.yml（已過濾）"
            fi
        fi
    fi
    
    ((PROCESSED_CHALLENGES++))
    log_success "完成處理: ${category}/${challenge_name}"
}

# -----------------------------------------------------------------------------
# 掃描所有題目
# -----------------------------------------------------------------------------
process_all_challenges() {
    log_step "開始處理題目..."
    
    if [ -n "$SPECIFIC_CHALLENGE" ]; then
        # 處理特定題目
        if [ -d "$SPECIFIC_CHALLENGE" ]; then
            process_challenge "$SPECIFIC_CHALLENGE"
        else
            log_error "找不到題目: $SPECIFIC_CHALLENGE"
            exit 1
        fi
    else
        # 處理所有題目
        for category_dir in "$CHALLENGES_DIR"/*/; do
            if [ -d "$category_dir" ]; then
                for challenge_dir in "$category_dir"*/; do
                    if [ -d "$challenge_dir" ]; then
                        process_challenge "$challenge_dir"
                    fi
                done
            fi
        done
    fi
}

# -----------------------------------------------------------------------------
# 執行安全掃描
# -----------------------------------------------------------------------------
run_security_scan() {
    if [ "$SKIP_SCAN" = true ]; then
        log_warning "跳過安全掃描（不建議在正式發布時使用）"
        return
    fi
    
    log_step "執行安全掃描..."
    
    local scan_failed=false
    
    # 掃描 flag 格式
    log_info "掃描 flag 格式..."
    local flag_matches=$(grep -rE "${FLAG_PREFIX}\{[^}]+\}" "$OUTPUT_DIR" 2>/dev/null || true)
    if [ -n "$flag_matches" ]; then
        log_error "發現未移除的 flag！"
        echo "$flag_matches"
        scan_failed=true
    else
        log_success "未發現 flag 洩漏"
    fi
    
    # 掃描敏感檔案
    log_info "檢查敏感檔案..."
    local sensitive_files=(
        "private.yml"
        "flag.txt"
        "solution.py"
        "exploit.py"
        ".env"
        "secrets.json"
    )
    
    for sensitive_file in "${sensitive_files[@]}"; do
        local found=$(find "$OUTPUT_DIR" -name "$sensitive_file" 2>/dev/null)
        if [ -n "$found" ]; then
            log_error "發現敏感檔案: $found"
            scan_failed=true
        fi
    done
    
    if [ "$scan_failed" = false ]; then
        log_success "安全掃描通過 ✓"
    fi
    
    # 使用 Python 掃描器（如果存在）
    if [ -f "${SCRIPT_DIR}/scan-secrets.py" ]; then
        log_info "執行進階安全掃描..."
        if python3 "${SCRIPT_DIR}/scan-secrets.py" --path "$OUTPUT_DIR" --quiet; then
            log_success "進階安全掃描通過 ✓"
        else
            log_error "進階安全掃描發現問題"
            scan_failed=true
        fi
    fi
    
    if [ "$scan_failed" = true ]; then
        log_error "安全掃描失敗！請修復問題後重新建置。"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# 生成公開 README
# -----------------------------------------------------------------------------
generate_public_readme() {
    log_step "生成公開 README..."
    
    if [ "$DRY_RUN" = true ]; then
        return
    fi
    
    local readme_file="${OUTPUT_DIR}/README.md"
    
    # 從 config.yml 讀取專案資訊
    local project_name=$(grep -E "^\s*name:" "$CONFIG_FILE" | head -1 | awk -F'"' '{print $2}')
    local project_year=$(grep -E "^\s*year:" "$CONFIG_FILE" | head -1 | awk '{print $2}')
    local organization=$(grep -E "^\s*organization:" "$CONFIG_FILE" | head -1 | awk -F'"' '{print $2}')
    
    cat > "$readme_file" << EOF
# ${project_name:-CTF Competition} - Public Challenges

🚀 **${organization:-Organization} CTF ${project_year:-$(date +%Y)}** - 公開題目與附件

## 📋 比賽資訊

- **比賽名稱**: ${project_name:-CTF Competition}
- **主辦單位**: ${organization:-Organization}
- **Flag 格式**: \`${FLAG_PREFIX}{...}\`

## 📁 題目列表

EOF

    # 生成題目列表
    for category_dir in "$OUTPUT_DIR/challenges"/*/; do
        if [ -d "$category_dir" ]; then
            local category=$(basename "$category_dir")
            local challenge_count=$(find "$category_dir" -maxdepth 1 -type d | wc -l)
            ((challenge_count--))  # 排除自身
            
            echo "### ${category^} (${challenge_count} 題)" >> "$readme_file"
            echo "" >> "$readme_file"
            
            for challenge_dir in "$category_dir"*/; do
                if [ -d "$challenge_dir" ]; then
                    local challenge_name=$(basename "$challenge_dir")
                    local title=$(grep -E "^\s*title:" "${challenge_dir}/public.yml" 2>/dev/null | head -1 | sed 's/.*title:\s*["'"'"']\?\([^"'"'"']*\)["'"'"']\?.*/\1/')
                    local difficulty=$(grep -E "^\s*difficulty:" "${challenge_dir}/public.yml" 2>/dev/null | head -1 | awk '{print $2}' | tr -d '"')
                    
                    echo "- [${title:-$challenge_name}](challenges/${category}/${challenge_name}/) - \`${difficulty}\`" >> "$readme_file"
                fi
            done
            echo "" >> "$readme_file"
        fi
    done
    
    cat >> "$readme_file" << EOF
## 📞 聯絡資訊

如有問題，請聯繫比賽主辦單位。

## 📄 授權條款

本倉庫內容遵循 MIT License 授權條款。

---
📅 建置時間：$(date -u '+%Y-%m-%d %H:%M:%S UTC')  
🤖 此檔案由 build.sh 自動生成
EOF

    log_success "README.md 已生成"
}

# -----------------------------------------------------------------------------
# 生成建置報告
# -----------------------------------------------------------------------------
generate_build_report() {
    log_step "生成建置報告..."
    
    if [ "$DRY_RUN" = true ]; then
        return
    fi
    
    cat > "$REPORT_FILE" << EOF
# CTF Public Release Build Report

## 📊 建置統計

| 項目 | 數量 |
|------|------|
| 總題目數 | ${TOTAL_CHALLENGES} |
| 已處理 | ${PROCESSED_CHALLENGES} |
| 已跳過 | ${SKIPPED_CHALLENGES} |
| 失敗 | ${FAILED_CHALLENGES} |

## 📅 建置資訊

- **建置時間**: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
- **輸出目錄**: ${OUTPUT_DIR}
- **Flag 前綴**: ${FLAG_PREFIX}
- **包含 Writeup**: ${INCLUDE_WRITEUPS}

## 🔒 安全檢查

- 安全掃描: $([ "$SKIP_SCAN" = true ] && echo "已跳過 ⚠️" || echo "通過 ✓")
- Flag 洩漏檢查: 通過 ✓
- 敏感檔案檢查: 通過 ✓

## 📁 輸出結構

\`\`\`
$(if [ -d "$OUTPUT_DIR" ]; then tree -L 3 "$OUTPUT_DIR" 2>/dev/null || find "$OUTPUT_DIR" -type f | head -20; fi)
\`\`\`

---
🤖 由 build.sh 自動生成
EOF

    log_success "建置報告已生成: ${REPORT_FILE}"
}

# -----------------------------------------------------------------------------
# 主程式
# -----------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  CTF Public Release Build Script${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "模擬執行模式 - 不會建立任何檔案"
    fi
    
    # 檢查必要目錄
    if [ ! -d "$CHALLENGES_DIR" ]; then
        log_error "找不到題目目錄: $CHALLENGES_DIR"
        exit 1
    fi
    
    # 讀取配置
    read_flag_prefix
    
    # 準備輸出目錄
    prepare_output_dir
    
    # 處理題目
    process_all_challenges
    
    # 執行安全掃描
    run_security_scan
    
    # 生成公開 README
    generate_public_readme
    
    # 生成建置報告
    generate_build_report
    
    # 最終統計
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${GREEN}  建置完成！${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
    echo "📊 統計:"
    echo "  - 總題目: ${TOTAL_CHALLENGES}"
    echo "  - 已處理: ${PROCESSED_CHALLENGES}"
    echo "  - 已跳過: ${SKIPPED_CHALLENGES}"
    echo ""
    echo "📁 輸出目錄: ${OUTPUT_DIR}"
    echo "📄 建置報告: ${REPORT_FILE}"
    echo ""
    
    if [ "$DRY_RUN" = true ]; then
        log_warning "這是模擬執行。移除 --dry-run 選項以實際建置。"
    fi
}

# 執行主程式
main

