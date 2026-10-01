# Research: 回归基线（条目 7）

- **Query**: 三条测试套件实跑数字 + TEMPLATE-CONTENTS.md 表格行格式
- **Scope**: internal（只读实跑，未改任何文件）
- **Date**: 2026-09-26

## 实跑结果（真实数字，2026-09-26 本机 Windows PowerShell 5.1）

### 1. 模板套件

命令：

```powershell
python -B -m unittest discover -s templates/embedded-c-overlay/.trellis/scripts/tests -p "test_*.py"
```

结果：**Ran 212 tests in 9.293s — OK（0 失败）**。

- 测试文件共 11 个（`templates/embedded-c-overlay/.trellis/scripts/tests/test_*.py`）：
  test_active_task_session_isolation、test_codex_native_wait_contract、test_execution_plan、
  test_opencode_platform_contract、test_planning_gate、test_review_fix_ownership_contract、
  test_review_profile_contract、test_small_patch_and_sequel_contract、
  test_subagent_prompt_contract、test_trellis_channel_contract、test_write_json_lf。
- 注意：stdout 会混入被测 CLI 的正常打印（plan.py 演示输出、argparse usage 等），PowerShell 会把它显示为
  NativeCommandError 红字，但退出码与 `OK` 判定不受影响。

### 2. 根套件（只读运行，未改根文件）

命令：

```powershell
python -B -m unittest discover -s .trellis/scripts/tests -p "test_*.py"
```

结果：**Ran 154 tests in 5.783s — OK（0 失败）**。

### 3. 仓库级套件（红基线）

命令：

```powershell
python -B -m unittest discover -s tests -p "test_*.py"
```

结果：**Ran 48 tests in 58.080s — FAILED (failures=26)**，26 个失败全部位于
`tests/test_overlay_tools.py`。失败根因（从 traceback 读出）：升级/安装工具在
`tools/lib/TrellisForgeOverlay.psm1:588` 抛出“检测到 live 模板与 1.2 manifest 不匹配 → fail closed”，
即当前 live 模板正文已领先于冻结的 `history/embedded-c-overlay/versions/1.2` manifest（1.3 开发期结构性红基线）。
`test_live_template_matches_12_manifest` 自身断言 1.2 manifest 含 151 个文件并要求 live 模板逐字节一致
（tests/test_overlay_tools.py，`self.assertEqual(len(v12["files"]), 151)`），因此任何模板正文改动都会保持/扩大该红基线，而不会新增失败类别。

**26 个失败用例精确清单**（`Select-String '^(FAIL|ERROR):'` 去重结果）：

| # | 测试类 | 用例名 |
|---|---|---|
| 1 | UpgradeFrom11Tests | test_11_upgrade_conflict_zero_write_keeps_11_receipt |
| 2 | UpgradeFrom11Tests | test_11_upgrade_multiple_conflicts_are_reported_with_candidate |
| 3 | UpgradeFrom11Tests | test_11_upgrade_preserves_nonoverlapping_customization |
| 4 | InstallTests | test_blank_target_install_without_force |
| 5 | UpgradeFrom10Tests | test_clean_10_bodies_merge_once_from_10_canonical_never_land_11 |
| 6 | UpgradeFrom10Tests | test_clean_10_command_reference_gets_rules_and_drops_blank |
| 7 | UpgradeFrom10Tests | test_clean_10_upgrade_applies_and_is_idempotent |
| 8 | UpgradeFrom11Tests | test_clean_11_receipt_upgrade_applies_and_is_idempotent |
| 9 | InstallTests | test_conflict_preview_blocks_without_force |
| 10 | UpgradeFrom10Tests | test_crlf_target_clean |
| 11 | InstallTests | test_force_backup_and_placeholder_replacement |
| 12 | InstallTests | test_fresh_install_full_12_writes_receipt |
| 13 | UpgradeFrom10Tests | test_from_version_10_explicit_accepted |
| 14 | InstallTests | test_install_does_not_touch_trellis_state_or_user_files |
| 15 | UpgradeFrom10Tests | test_lf_target_clean |
| 16 | LiveTemplateConsistencyTests | test_live_template_matches_12_manifest |
| 17 | UpgradeFrom10Tests | test_new_file_conflict |
| 18 | UpgradeFrom10Tests | test_open_code_new_path_existing_different_conflicts_zero_write |
| 19 | UpgradeFrom10Tests | test_open_code_new_path_existing_identical_is_already_current |
| 20 | UpgradeFrom10Tests | test_open_code_new_paths_added_on_upgrade |
| 21 | InstallTests | test_receipt_baseline_eq_installed_on_clean_install |
| 22 | UpgradeFrom10Tests | test_unmodified_canonical_paths_do_not_rewrite_worktree |
| 23 | UpgradeFrom10Tests | test_upgrade_does_not_touch_state_or_user_files |
| 24 | UpgradeFrom10Tests | test_user_edit_away_from_change_regions_merges |
| 25 | UpgradeFrom10Tests | test_user_edit_overlapping_change_region_conflicts_zero_write |
| 26 | StructuralAndSafetyTests | test_write_failure_rolls_back |

## TEMPLATE-CONTENTS.md 表格行格式（登记新测试文件用）

文件：`templates/embedded-c-overlay/TEMPLATE-CONTENTS.md`（共 55 行）。

- 表头（第 5-6 行）：`| 路径 | 安装策略 | 说明 |`。
- 既有测试登记行样式（第 11-14 行）：
  - 第 11 行：`| .trellis/scripts/tests/test_trellis_channel_contract.py | 覆盖前备份（\`add\`，1.1 新增） | Channel Skill 树完整性、公共镜像一致、Codex 终端术语作用域与唯一等待契约测试 |`
  - 第 12 行：`| .trellis/scripts/tests/test_opencode_platform_contract.py | 覆盖后新增（1.2 新增） | OpenCode 平台闭包、JS 行为（Node harness）、会话隔离、五级审查与提示规范化跨平台合同测试 |`
  - 第 13 行：`| .trellis/scripts/tests/test_codex_native_wait_contract.py | 覆盖后新增（1.3 新增） | 等待合同送达链路真实 CLI 考查：…2.1.2 原生静默等待合同冻结文本 |`
  - 第 14 行：`| .trellis/scripts/tests/test_write_json_lf.py | 覆盖后新增（1.3 新增） | write_json 原子写换行稳定性：输出保持 LF、不含 CRLF、无 .tmp 残留 |`
- “1.3 新增”标注写法即 `覆盖后新增（1.3 新增）`；当前开发版本为 1.3（正文第 29 行仍写“当前 `VERSION`，即 `1.2`”）。
- **硬性联动**：`test_codex_native_wait_contract.py:306-309`
  （`test_template_contents_registers_new_tests`）断言 TEMPLATE-CONTENTS.md 正文包含
  `test_codex_native_wait_contract.py` 与 `test_write_json_lf.py` 两个文件名——先例表明新增测试文件应在该表格登记（该断言目前只锁这两个名字，不会因新增行而失败，但登记是既有惯例）。

## Caveats

- 仓库级 26 失败为改动前既有红基线（本次调研未修改任何模板/根文件，`git status --short` 中模板目录无未提交改动）；实施后重跑时以“失败集合 ⊆ 上表 26 项、模板套件与根套件保持 OK”为回归判据。
- 模板套件运行时长约 9s、仓库级约 58s（含临时 Git 仓库自动化），CI 预算需按此估计。
