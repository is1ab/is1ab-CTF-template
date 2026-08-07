# 📋 Challenge Metadata 標準格式（已廢除）

> ⚠️ **本文件已廢除。** 題目 schema 的單一真相已移至 **[challenge-schema.md](challenge-schema.md)**。
>
> 舊版本描述的 schema（`challenge_type` 五值、`flag_type`、`owners`/`assignee`、物件陣列 `files`、
> 巢狀 `solution_steps` 等）與實際 pipeline 不一致，已收斂。請改讀 canonical 定義：
>
> **→ [docs/challenge-schema.md](challenge-schema.md)**
>
> 重點變更：
> - `challenge_type`（5 值）→ `deploy_type`（attachment/container/none）+ `deploy_info.connection_type`
> - `flag_type` → flag 三軸 `flag_load` × `flag_scope` × `flag_match`
> - `owners`/`assignee` → 單一 `author`
> - 解題步驟不進 YAML → `solution/exploit.py` + `writeup/README.md`
> - flag 統一格式（如 `is1abCTF{}`）由 `config.yml` 的 `project.flag_prefix` 設定，validator 會檢查
