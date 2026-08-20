.PHONY: help setup new-challenge validate validate-all scan build build-images verify-solution deploy-staging deploy-staging-dry deploy-production test viewer clean

ARGS ?=

help: ## 顯示所有可用的 make targets
	@echo "IS1AB CTF Template - 可用指令："
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'
	@echo ""

setup: ## 初始設置（安裝依賴 + Git hooks + 驗證環境）
	uv sync --extra dev
	./scripts/setup-hooks.sh
	uv run python scripts/verify-setup.py

new-challenge: ## 建立新題目（例如 make new-challenge ARGS="web my_challenge easy"）
	uv run python scripts/create-challenge.py $(ARGS)

validate: ## 驗證單個題目（例如 make validate ARGS="challenges/examples/web/sql_injection"）
	uv run python scripts/validate-challenge.py $(ARGS)

validate-all: ## 驗證所有題目
	uv run python scripts/validate-all-challenges.py

scan: ## 執行敏感資料掃描
	uv run python scripts/scan-secrets.py --path challenges/

build: ## 建置公開發布版本
	./scripts/build.sh $(ARGS)

build-images: ## build 並 push 題目 container image 到 registry（例如 make build-images ARGS="--path challenges/web/my_chall"）
	uv run python scripts/build-images.py $(ARGS)

verify-solution: ## 驗題：跑起題目、執行官方解、比對 flag（例如 make verify-solution ARGS="challenges/web/my_chall"）
	uv run python scripts/verify-solution.py $(if $(ARGS),$(ARGS),challenges/)

deploy-staging: ## 同步題目到 staging CTFd（例如 make deploy-staging ARGS="--path challenges/web/my_chall"）
	uv run python scripts/sync-to-ctfd.py --target staging $(if $(ARGS),$(ARGS),--all)

deploy-staging-dry: ## 預覽會同步什麼到 staging，不實際送出
	uv run python scripts/sync-to-ctfd.py --target staging --dry-run $(if $(ARGS),$(ARGS),--all)

deploy-production: ## 同步到正式 CTFd（僅 ready_for_release 的題目，一律建成隱藏）
	uv run python scripts/sync-to-ctfd.py --target production $(if $(ARGS),$(ARGS),--all)

test: ## 執行測試套件
	uv run pytest tests/ -v

viewer: ## 生成 Viewer 資料
	uv run python scripts/generate-viewer-data.py

clean: ## 清理建置產物
	rm -rf public-release/ .pytest_cache/ __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
