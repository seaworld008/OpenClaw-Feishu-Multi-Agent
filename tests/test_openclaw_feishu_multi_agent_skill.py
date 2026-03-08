import json
import importlib.util
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_FILE = REPO_ROOT / "README.md"
SKILL_FILE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/SKILL.md"
BUILD_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/build_openclaw_feishu_snippets.py"
CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v3_dispatch_canary.sh"
V4_3_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_3_canary.py"
V4_3_1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md"
V4_3_1_C1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md"
V4_3_SQL = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql"
V4_3_1_CONFIG_SNAPSHOT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc"
V4_3_REGISTRY = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_job_registry.py"
V4_3_HYGIENE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_session_hygiene.py"
V4_3_QUICKSTART_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md"
V5_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-team-orchestrator-design.md"
V5_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-team-orchestrator-implementation.md"
V5_INPUT_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-team-orchestrator.json"
V5_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md"
V5_CONFIG_SNAPSHOT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc"
LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist"
V5_SYSTEMD_SERVICE_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.service"
V5_SYSTEMD_TIMER_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.timer"
V5_LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v5-team-watchdog.plist"
WSL_CONF_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/windows/wsl.conf.example"
WINDOWS_WSL2_NOTES = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md"
MERGE_GAP_ANALYSIS = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/merge-gap-analysis.md"
V4_3_1_STABILITY_PLAN = REPO_ROOT / "docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md"


def load_build_module():
    spec = importlib.util.spec_from_file_location("build_openclaw_feishu_snippets", BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BuildSnippetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_build_module()

    def base_input(self):
        return {
            "mode": "plugin",
            "accounts": [
                {
                    "accountId": "main",
                    "appId": "cli_xxx",
                    "appSecret": "secret",
                    "encryptKey": "",
                    "verificationToken": "",
                }
            ],
            "routes": [
                {
                    "agentId": "sales_agent",
                    "accountId": "main",
                    "peer": {"kind": "group", "id": "oc_group_sales"},
                }
            ],
        }

    def test_string_agents_are_not_emitted_in_patch(self):
        data = self.base_input()
        data["agents"] = ["sales_agent", "ops_agent"]

        patch = self.module.build_plugin_patch(data)

        self.assertNotIn("agents", patch)

    def test_agent_objects_are_preserved_when_requested(self):
        data = self.base_input()
        data["agents"] = [
            {"id": "sales_agent", "systemPrompt": "sales prompt"},
            {"id": "ops_agent", "systemPrompt": "ops prompt"},
        ]

        patch = self.module.build_plugin_patch(data)

        self.assertEqual(patch["agents"]["list"], data["agents"])

    def test_blank_encrypt_fields_are_omitted(self):
        data = self.base_input()

        patch = self.module.build_plugin_patch(data)
        account_cfg = patch["channels"]["feishu"]["accounts"]["main"]

        self.assertEqual(account_cfg["appId"], "cli_xxx")
        self.assertEqual(account_cfg["appSecret"], "secret")
        self.assertNotIn("encryptKey", account_cfg)
        self.assertNotIn("verificationToken", account_cfg)


class BuildSnippetV5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_build_module()

    def team_input(self):
        return {
            "mode": "plugin",
            "connectionMode": "websocket",
            "defaultAccount": "marketing-bot",
            "messages": {
                "groupChat": {
                    "mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"],
                }
            },
            "accounts": [
                {
                    "accountId": "marketing-bot",
                    "appId": "cli_marketing",
                    "appSecret": "secret_marketing",
                },
                {
                    "accountId": "ops-bot",
                    "appId": "cli_ops",
                    "appSecret": "secret_ops",
                },
                {
                    "accountId": "finance-bot",
                    "appId": "cli_finance",
                    "appSecret": "secret_finance",
                },
            ],
            "agents": {
                "defaults": {
                    "sandbox": {
                        "sessionToolsVisibility": "all",
                    }
                }
            },
            "agentToAgent": {
                "enabled": True,
            },
            "session": {
                "sendPolicy": {
                    "default": "allow",
                }
            },
            "teams": [
                {
                    "teamKey": "market_sz",
                    "displayName": "深圳团队",
                    "group": {
                        "peerId": "oc_team_sz",
                        "entryAccountId": "marketing-bot",
                        "requireMention": True,
                    },
                    "supervisor": {
                        "agentId": "supervisor_market_sz",
                        "roleKey": "supervisor",
                        "name": "奥特曼",
                        "role": "主管总控",
                        "responsibility": "接单、拆解、调度、收口",
                        "mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"],
                        "systemPrompt": "supervisor prompt",
                    },
                    "workers": [
                        {
                            "agentId": "ops_market_sz",
                            "roleKey": "ops",
                            "accountId": "ops-bot",
                            "name": "小龙虾找妈妈",
                            "role": "运营专家",
                            "responsibility": "活动打法",
                            "visibility": "visible",
                            "systemPrompt": "ops prompt",
                        },
                        {
                            "agentId": "finance_market_sz",
                            "roleKey": "finance",
                            "accountId": "finance-bot",
                            "name": "易燃易爆",
                            "role": "财务专家",
                            "responsibility": "预算和 ROI",
                            "visibility": "visible",
                            "systemPrompt": "finance prompt",
                        },
                    ],
                    "workflow": {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_market_sz"},
                            {"agentId": "finance_market_sz"},
                        ],
                    },
                }
            ],
        }

    def test_v5_team_input_generates_team_scoped_agents_and_bindings(self):
        patch = self.module.build_plugin_patch(self.team_input())

        agents = patch["agents"]["list"]
        bindings = patch["bindings"]

        self.assertEqual([agent["id"] for agent in agents], ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"])
        self.assertEqual([binding["agentId"] for binding in bindings], ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"])
        self.assertTrue(all(binding["match"]["peer"]["id"] == "oc_team_sz" for binding in bindings))
        self.assertEqual(agents[0]["workspace"], "~/.openclaw/teams/market_sz/workspaces/supervisor")
        self.assertEqual(agents[1]["workspace"], "~/.openclaw/teams/market_sz/workspaces/ops")
        self.assertEqual(agents[2]["workspace"], "~/.openclaw/teams/market_sz/workspaces/finance")

    def test_v5_team_input_generates_group_prompts_per_account(self):
        patch = self.module.build_plugin_patch(self.team_input())
        accounts = patch["channels"]["feishu"]["accounts"]

        self.assertEqual(accounts["marketing-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "supervisor prompt")
        self.assertEqual(accounts["ops-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "ops prompt")
        self.assertEqual(accounts["finance-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "finance prompt")

    def test_v5_team_input_builds_agent_to_agent_allowlist_from_generated_agents(self):
        patch = self.module.build_plugin_patch(self.team_input())

        self.assertEqual(
            patch["tools"]["agentToAgent"]["allow"],
            ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"],
        )

    def test_v5_team_input_generates_group_require_mention_and_messages_defaults(self):
        patch = self.module.build_plugin_patch(self.team_input())

        self.assertEqual(patch["channels"]["feishu"]["groups"]["oc_team_sz"]["requireMention"], True)
        self.assertEqual(
            patch["messages"]["groupChat"]["mentionPatterns"],
            ["@奥特曼", "奥特曼", "主管机器人"],
        )
        self.assertEqual(
            patch["agents"]["defaults"]["sandbox"]["sessionToolsVisibility"],
            "all",
        )

    def test_v5_team_input_builds_team_runtime_manifest(self):
        manifest = self.module.build_v5_runtime_manifest(self.team_input())

        self.assertEqual(manifest["teams"][0]["teamKey"], "market_sz")
        self.assertEqual(
            manifest["teams"][0]["runtime"]["hiddenMainSessionKey"],
            "agent:supervisor_market_sz:main",
        )
        self.assertEqual(
            [stage["agentId"] for stage in manifest["teams"][0]["workflow"]["stages"]],
            ["ops_market_sz", "finance_market_sz"],
        )
        self.assertEqual(
            manifest["teams"][0]["workers"][0]["visibility"],
            "visible",
        )

    def test_v5_team_input_rejects_duplicate_team_keys(self):
        data = self.team_input()
        data["teams"].append(dict(data["teams"][0]))

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)

    def test_v5_team_input_rejects_invalid_team_key(self):
        data = self.team_input()
        data["teams"][0]["teamKey"] = "市场一组"

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)


class CanaryScriptTests(unittest.TestCase):
    def run_script(self, log_content, *extra_args):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "openclaw.log"
            log_path.write_text(log_content, encoding="utf-8")
            result = subprocess.run(
                [
                    "bash",
                    str(CANARY_SCRIPT),
                    "--log",
                    str(log_path),
                    "--start-line",
                    "0",
                    *extra_args,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            return result

    def test_canary_requires_dispatch_evidence(self):
        result = self.run_script(
            "\n".join(
                [
                    "task demo-v3-001",
                    "session=agent:sales_agent:abc",
                    "session=agent:ops_agent:def",
                    "session=agent:finance_agent:ghi",
                ]
            ),
            "--task-id",
            "demo-v3-001",
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("DISPATCH_UNVERIFIED", result.stdout)

    def test_canary_succeeds_with_dispatch_evidence(self):
        result = self.run_script(
            "\n".join(
                [
                    "task demo-v3-001",
                    "tool=sessions_send target=session=agent:sales_agent:abc",
                    "tool=sessions_send target=session=agent:ops_agent:def",
                    "tool=sessions_send target=session=agent:finance_agent:ghi",
                ]
            ),
            "--task-id",
            "demo-v3-001",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("DISPATCH_OK", result.stdout)


class DocumentationConsistencyTests(unittest.TestCase):
    def test_readme_documents_platform_matrix(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("平台兼容矩阵", content)
        self.assertIn("Windows + WSL2", content)
        self.assertIn("launchd", content)
        self.assertIn("WSL2", content)

    def test_skill_documents_platform_policy(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("平台兼容策略", content)
        self.assertIn("Windows + WSL2", content)
        self.assertIn("launchd", content)
        self.assertIn("systemd --user", content)

    def test_readme_keeps_mainline_versions_and_preserves_c1_variant(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("V3.1", content)
        self.assertIn("V4.3.1", content)
        self.assertIn("V5 Team Orchestrator", content)
        self.assertIn("V4.3.1-C1.0", content)
        self.assertNotIn("V4.2.1", content)
        self.assertNotIn("V4.2", content)
        self.assertNotIn("V4.1", content)
        self.assertNotIn("V4：单群高级", content)

    def test_v431_c1_customer_doc_is_preserved(self):
        content = V4_3_1_C1_DOC.read_text(encoding="utf-8")

        self.assertIn("V4.3.1-C1.0 单群生产稳定版（客户定制版）", content)
        self.assertIn("oc_426bc13db95838b2aa9a327a20ee71ea", content)
        self.assertIn("marketing-bot", content)
        self.assertIn("ecom-market-bot", content)
        self.assertIn("default", content)
        self.assertIn("@3-营销机器人", content)

    def test_merge_gap_analysis_has_been_removed_after_mainline_consolidation(self):
        self.assertFalse(MERGE_GAP_ANALYSIS.exists())

    def test_v431_stability_plan_no_longer_references_deleted_v43_base_doc(self):
        content = V4_3_1_STABILITY_PLAN.read_text(encoding="utf-8")

        self.assertNotIn("codex-prompt-templates-v4.3-single-group-production.md", content)
        self.assertIn("codex-prompt-templates-v4.3.1-single-group-production.md", content)

    def test_v43_1_doc_requires_watchdog_and_one_time_init(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("watchdog", content)
        self.assertIn("一次性", content)
        self.assertIn("WARMUP", content)
        self.assertIn("主管已接单", content)
        self.assertIn("最终统一收口", content)

    def test_v43_1_doc_documents_cross_platform_delivery(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("平台兼容策略", content)
        self.assertIn("Windows + WSL2", content)
        self.assertIn("launchd", content)
        self.assertIn("systemd --user", content)

    def test_v43_1_doc_keeps_full_codex_delivery_template(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("Codex 真实交付模板（V4.3.1，完整可执行版）", content)
        self.assertIn("accountMappings", content)
        self.assertIn("routes", content)
        self.assertIn("部署后测试顺序", content)
        self.assertIn("READY_FOR_TEAM_GROUP|agentId=ops_agent", content)
        self.assertIn("V4_3_CANARY_OK", content)
        self.assertIn("status=queued", content)

    def test_v43_sql_schema_enforces_single_active_job(self):
        content = V4_3_SQL.read_text(encoding="utf-8")

        self.assertIn("idx_jobs_group_single_active", content)
        self.assertIn("WHERE status = 'active'", content)

    def test_launchd_template_targets_watchdog_registry(self):
        content = LAUNCHD_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("bot.molt.v4-3-watchdog", content)
        self.assertIn("v4_3_job_registry.py", content)
        self.assertIn("StartInterval", content)
        self.assertIn("__TEAM_GROUP_PEER_ID__", content)

    def test_windows_wsl2_notes_prefer_wsl_and_systemd(self):
        content = WINDOWS_WSL2_NOTES.read_text(encoding="utf-8")

        self.assertIn("WSL2", content)
        self.assertIn("systemd=true", content)
        self.assertIn("Windows 原生", content)
        self.assertIn("不推荐", content)

    def test_wsl_conf_template_enables_systemd(self):
        content = WSL_CONF_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("[boot]", content)
        self.assertIn("systemd=true", content)


class V43RegistryTests(unittest.TestCase):
    def run_registry(self, db_path, *args):
        result = subprocess.run(
            [
                "python3",
                str(V4_3_REGISTRY),
                "--db",
                str(db_path),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def test_registry_initializes_schema(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            result = self.run_registry(db_path, "init-db")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("initialized", result.stdout)

    def test_registry_starts_active_then_queues_second_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            first = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            second = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "五月预算看板",
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn('"status": "active"', first.stdout)
            self.assertIn('"status": "queued"', second.stdout)
            self.assertIn('"queuePosition": 1', second.stdout)

    def test_registry_marks_worker_complete_and_ready_to_rollup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            ops = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_agent",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--progress-message-id",
                "om_ops_progress",
                "--final-message-id",
                "om_ops_final",
                "--summary",
                "运营方案已完成",
            )
            finance = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_agent",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
                "--progress-message-id",
                "om_fin_progress",
                "--final-message-id",
                "om_fin_final",
                "--summary",
                "财务方案已完成",
                "--details",
                "预算与ROI校验完成",
            )
            ready = self.run_registry(db_path, "ready-to-rollup", "--job-ref", job_ref)
            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)

            self.assertEqual(ops.returncode, 0, ops.stderr)
            self.assertEqual(finance.returncode, 0, finance.stderr)
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertIn('"ready": true', ready.stdout)
            self.assertEqual(details.returncode, 0, details.stderr)
            self.assertIn('"completionPackets"', details.stdout)
            self.assertIn("预算与ROI校验完成", details.stdout)

    def test_registry_mark_worker_complete_backfills_account_and_role(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            dispatched = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_agent",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
                "--status",
                "accepted",
                "--dispatch-run-id",
                "run-fin-001",
                "--dispatch-status",
                "pending",
            )
            completed = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_agent",
                "--progress-message-id",
                "om_fin_progress",
                "--final-message-id",
                "om_fin_final",
                "--summary",
                "财务方案已完成",
            )
            import sqlite3

            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT account_id, role FROM job_participants WHERE job_ref = ? AND agent_id = ?",
                (job_ref, "finance_agent"),
            ).fetchone()
            conn.close()

            self.assertEqual(dispatched.returncode, 0, dispatched.stderr)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('"agentId": "finance_agent"', completed.stdout)
            self.assertEqual(row[0], "yiran_yibao")
            self.assertEqual(row[1], "财务执行")

    def test_registry_begin_turn_recovers_stale_job_before_reporting_active(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            import sqlite3
            from datetime import datetime, timedelta, timezone

            stale_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(timespec="seconds")

            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE jobs SET created_at = ?, updated_at = ? WHERE job_ref = ?",
                (stale_at, stale_at, job_ref),
            )
            conn.commit()
            conn.close()

            prepared = self.run_registry(
                db_path,
                "begin-turn",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "1",
            )

            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertIn('"recover"', prepared.stdout)
            self.assertIn('"stale_recovered"', prepared.stdout)
            self.assertIn('"active": null', prepared.stdout)

    def test_registry_begin_turn_preserves_non_stale_active_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            prepared = self.run_registry(
                db_path,
                "begin-turn",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(prepared.returncode, 0, prepared.stderr)
            self.assertIn('"active_ok"', prepared.stdout)
            self.assertIn(f'"jobRef": "{job_ref}"', prepared.stdout)

    def test_registry_appends_note_to_active_job_without_creating_new_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            note = self.run_registry(
                db_path,
                "append-note",
                "--group-peer-id",
                "oc_demo",
                "--sender-id",
                "ou_user",
                "--text",
                "预算上限改成18万，并补一个直播方案",
            )
            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")

            self.assertEqual(note.returncode, 0, note.stderr)
            self.assertIn(job_ref, note.stdout)
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn(job_ref, active.stdout)

    def test_registry_recovers_stale_active_and_promotes_queued_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            first = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            second = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "五月促销方案",
            )
            first_ref = first.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            second_ref = second.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            # Force the first job to look stale.
            subprocess.run(
                [
                    "python3",
                    "-c",
                    (
                        "import sqlite3; "
                        "from datetime import datetime, timedelta, timezone; "
                        "stale=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(timespec='seconds'); "
                        f"conn=sqlite3.connect({str(db_path)!r}); "
                        "conn.execute(\"UPDATE jobs SET created_at=?, updated_at=? WHERE job_ref=?\", "
                        f"(stale, stale, {first_ref!r})); "
                        "conn.commit()"
                    ),
                ],
                check=True,
            )

            recovered = self.run_registry(
                db_path,
                "recover-stale",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "1",
            )
            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")

            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            self.assertIn('"status": "stale_recovered"', recovered.stdout)
            self.assertIn(first_ref, recovered.stdout)
            self.assertIn(second_ref, recovered.stdout)
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn(second_ref, active.stdout)
            self.assertIn('"participantCount": 0', active.stdout)

    def test_registry_get_active_includes_runtime_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")

            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn(job_ref, active.stdout)
            self.assertIn('"createdAt"', active.stdout)
            self.assertIn('"updatedAt"', active.stdout)
            self.assertIn('"participantCount": 0', active.stdout)
            self.assertIn('"completedParticipantCount": 0', active.stdout)

    def test_registry_marks_dispatch_and_reports_job_details(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            marked = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_agent",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--status",
                "accepted",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "ping_ok",
            )
            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)

            self.assertEqual(marked.returncode, 0, marked.stderr)
            self.assertIn('"dispatchStatus": "ping_ok"', marked.stdout)
            self.assertEqual(details.returncode, 0, details.stderr)
            self.assertIn('"ops_agent"', details.stdout)
            self.assertIn('"dispatchStatus": "ping_ok"', details.stdout)

    def test_registry_watchdog_marks_stale_active_failed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            subprocess.run(
                [
                    "python3",
                    "-c",
                        (
                            "import sqlite3; "
                            "from datetime import datetime, timedelta, timezone; "
                            "stale=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(timespec='seconds'); "
                            f"conn=sqlite3.connect({str(db_path)!r}); "
                            "conn.execute(\"UPDATE jobs SET updated_at=? WHERE job_ref=?\", "
                            f"(stale, {job_ref!r})); "
                            "conn.commit()"
                        ),
                ],
                check=True,
            )

            watchdog = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "1",
            )
            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")

            self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
            self.assertIn('"stale_recovered"', watchdog.stdout)
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn('"active": null', active.stdout)


class V43CanaryTests(unittest.TestCase):
    def run_registry(self, db_path, *args):
        result = subprocess.run(
            ["python3", str(V4_3_REGISTRY), "--db", str(db_path), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def run_canary(self, db_path, session_root, *args):
        result = subprocess.run(
            ["python3", str(V4_3_CANARY_SCRIPT), "--db", str(db_path), "--session-root", str(session_root), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def test_v43_canary_requires_done_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            session_root = Path(tmpdir) / "agents"
            session_root.mkdir()

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            result = self.run_canary(db_path, session_root, "--job-ref", job_ref)

            self.assertEqual(result.returncode, 2)
            self.assertIn("PARTICIPANTS_MISSING", result.stdout)

    def test_v43_canary_accepts_done_job_with_visible_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            session_root = Path(tmpdir) / "agents"
            for agent in ("ops_agent", "finance_agent"):
                (session_root / agent / "sessions").mkdir(parents=True)

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_agent",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--progress-message-id",
                "om_ops_progress",
                "--final-message-id",
                "om_ops_final",
                "--summary",
                "运营方案已完成",
            )
            self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_agent",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
                "--progress-message-id",
                "om_fin_progress",
                "--final-message-id",
                "om_fin_final",
                "--summary",
                "财务方案已完成",
            )
            self.run_registry(db_path, "close-job", "--job-ref", job_ref, "--status", "done")

            (session_root / "ops_agent" / "sessions" / "ops.jsonl").write_text(
                "om_ops_progress\nom_ops_final\n", encoding="utf-8"
            )
            (session_root / "finance_agent" / "sessions" / "fin.jsonl").write_text(
                "om_fin_progress\nom_fin_final\n", encoding="utf-8"
            )

            result = self.run_canary(
                db_path,
                session_root,
                "--job-ref",
                job_ref,
                "--require-visible-messages",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("V4_3_CANARY_OK", result.stdout)

    def test_v43_canary_rejects_protocol_leak_in_visible_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            session_root = Path(tmpdir) / "agents"
            for agent in ("ops_agent", "finance_agent", "supervisor_agent"):
                (session_root / agent / "sessions").mkdir(parents=True)

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "四月促销方案",
            )
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_agent",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--progress-message-id",
                "om_ops_progress",
                "--final-message-id",
                "om_ops_final",
                "--summary",
                "运营方案已完成",
            )
            self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_agent",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
                "--progress-message-id",
                "om_fin_progress",
                "--final-message-id",
                "om_fin_final",
                "--summary",
                "财务方案已完成",
            )
            self.run_registry(db_path, "close-job", "--job-ref", job_ref, "--status", "done")

            (session_root / "ops_agent" / "sessions" / "ops.jsonl").write_text(
                "om_ops_progress\nom_ops_final\n", encoding="utf-8"
            )
            (session_root / "finance_agent" / "sessions" / "fin.jsonl").write_text(
                "om_fin_progress\nom_fin_final\n", encoding="utf-8"
            )
            (session_root / "supervisor_agent" / "sessions" / "sup.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": [{"type": "text", "text": f"ACK_READY|jobRef={job_ref}|agent=ops_agent"}],
                                }
                            },
                            ensure_ascii=False,
                        )
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_canary(
                db_path,
                session_root,
                "--job-ref",
                job_ref,
                "--require-visible-messages",
            )

            self.assertEqual(result.returncode, 3)
            self.assertIn("VISIBLE_PROTOCOL_LEAK", result.stdout)

class V431DocumentationContentTests(unittest.TestCase):
    def test_v431_doc_mentions_hidden_control_session(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("agent:supervisor_agent:main", content)
        self.assertIn("COMPLETE_PACKET", content)
        self.assertIn("NO_REPLY", content)

    def test_v431_doc_describes_visible_sequence_and_real_success(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("主管接单", content)
        self.assertIn("运营进度", content)
        self.assertIn("财务结论", content)
        self.assertIn("TG-20260307-031", content)
        self.assertIn("V4_3_CANARY_OK", content)
        self.assertIn("om_x100b55f5beb1a908b3df8e78d8a7bc5", content)

    def test_v431_doc_embeds_real_production_config_values(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("当前最新生产配置快照（真实值）", content)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", content)
        self.assertIn("aoteman", content)
        self.assertIn("xiaolongxia", content)
        self.assertIn("yiran_yibao", content)
        self.assertIn("cli_a923c749bab6dcba", content)
        self.assertIn("cli_a9f1849b67f9dcc2", content)
        self.assertIn("cli_a923c71498b8dcc9", content)
        self.assertIn('"mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"]', content)

    def test_v431_doc_embeds_real_system_prompts_and_identity_sections(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("当前最新生产 systemPrompt（真实值）", content)
        self.assertIn("supervisor 群级 systemPrompt（真实值）", content)
        self.assertIn("ops 群级 systemPrompt（真实值）", content)
        self.assertIn("finance 群级 systemPrompt（真实值）", content)
        self.assertIn("收到 TASK_DISPATCH 后必须", content)
        self.assertIn("当前最新 workspace 身份文件（真实值）", content)
        self.assertIn("奥特曼", content)
        self.assertIn("小龙虾找妈妈", content)
        self.assertIn("易燃易爆", content)

    def test_v431_doc_includes_step_by_step_test_flow(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("部署后测试顺序（必须写给客户和 Codex）", content)
        self.assertIn("v4_3_session_hygiene.py", content)
        self.assertIn("@小龙虾找妈妈 WARMUP", content)
        self.assertIn("@易燃易爆 WARMUP", content)
        self.assertIn("群里预期顺序", content)
        self.assertIn("命令行验收", content)
        self.assertIn("队列与恢复测试", content)

    def test_v431_doc_mentions_history_guard_after_warmup(self):
        content = V4_3_1_DOC.read_text(encoding="utf-8")

        self.assertIn("Chat history since last reply", content)
        self.assertIn("WARMUP", content)
        self.assertIn("不能把本轮正式任务误判成初始化消息", content)

    def test_v431_config_snapshot_exists_and_covers_core_fields(self):
        content = V4_3_1_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        self.assertIn("V4.3.1 单群生产稳定版去敏配置快照", content)
        self.assertIn("marketing-bot", content)
        self.assertIn("ops-bot", content)
        self.assertIn("finance-bot", content)
        self.assertIn("group:sessions", content)
        self.assertIn("agent:supervisor_agent:main", content)
        self.assertIn("resetByType", content)
        self.assertIn("oc_team_group_peer_id", content)

    def test_readme_links_v431_config_snapshot(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("openclaw-v4-3-1-single-group-production.example.jsonc", content)

class V431QuickStartAndHygieneTests(unittest.TestCase):
    def run_hygiene(self, home_path, *args, group_peer_id="oc_demo_group"):
        result = subprocess.run(
            [
                "python3",
                str(V4_3_HYGIENE_SCRIPT),
                "--home",
                str(home_path),
                "--group-peer-id",
                group_peer_id,
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def test_quickstart_doc_covers_hygiene_then_warmup_then_canary(self):
        content = V4_3_QUICKSTART_DOC.read_text(encoding="utf-8")

        self.assertIn("v4_3_session_hygiene.py", content)
        self.assertIn("WARMUP", content)
        self.assertIn("check_v4_3_canary.py", content)
        self.assertIn("3 天限时促销", content)

    def test_deployment_inputs_document_runtime_hygiene(self):
        content = (REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml").read_text(encoding="utf-8")

        self.assertIn("runtime_hygiene", content)
        self.assertIn("group systemPrompt", content)
        self.assertIn("hidden main session consumer", content)

    def test_hygiene_script_removes_group_and_main_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".openclaw"
            sup_dir = home / "agents" / "supervisor_agent" / "sessions"
            sup_dir.mkdir(parents=True, exist_ok=True)
            sessions_json = sup_dir / "sessions.json"
            sessions_json.write_text(
                json.dumps(
                    {
                        "agent:supervisor_agent:feishu:group:oc_demo_group": "sup-group-1",
                        "agent:supervisor_agent:main": {
                            "sessionId": "sup-main-1",
                            "sessionFile": str(sup_dir / "sup-main-1.jsonl"),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (sup_dir / "sup-group-1.jsonl").write_text("old group transcript", encoding="utf-8")
            (sup_dir / "sup-main-1.jsonl").write_text("old main transcript", encoding="utf-8")

            result = self.run_hygiene(home, "--delete-transcripts")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            statuses = {(item["agentId"], item["sessionKey"]): item["status"] for item in payload["results"]}
            self.assertEqual(statuses[("supervisor_agent", "agent:supervisor_agent:feishu:group:oc_demo_group")], "removed")
            self.assertEqual(statuses[("supervisor_agent", "agent:supervisor_agent:main")], "removed")

            current = json.loads(sessions_json.read_text(encoding="utf-8"))
            self.assertEqual(current, {})
            self.assertFalse((sup_dir / "sup-group-1.jsonl").exists())
            self.assertFalse((sup_dir / "sup-main-1.jsonl").exists())

    def test_hygiene_script_include_workers_and_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".openclaw"
            for agent_id, session_id in [("ops_agent", "ops-1"), ("finance_agent", "fin-1")]:
                session_dir = home / "agents" / agent_id / "sessions"
                session_dir.mkdir(parents=True, exist_ok=True)
                (session_dir / "sessions.json").write_text(
                    json.dumps(
                        {
                            f"agent:{agent_id}:feishu:group:oc_demo_group": {
                                "sessionId": session_id,
                                "sessionFile": str(session_dir / f"{session_id}.jsonl"),
                            }
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )
                (session_dir / f"{session_id}.jsonl").write_text("worker transcript", encoding="utf-8")

            result = self.run_hygiene(home, "--include-workers", "--delete-transcripts", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["includeWorkers"], True)
            statuses = [item["status"] for item in payload["results"] if item["agentId"] in {"ops_agent", "finance_agent"}]
            self.assertTrue(all(status == "would_remove" for status in statuses))
            self.assertTrue((home / "agents" / "ops_agent" / "sessions" / "ops-1.jsonl").exists())
            self.assertTrue((home / "agents" / "finance_agent" / "sessions" / "fin-1.jsonl").exists())

    def test_hygiene_script_supports_team_scoped_supervisor_main(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / ".openclaw"
            sup_dir = home / "agents" / "supervisor_market_sz" / "sessions"
            sup_dir.mkdir(parents=True, exist_ok=True)
            sessions_json = sup_dir / "sessions.json"
            sessions_json.write_text(
                json.dumps(
                    {
                        "agent:supervisor_market_sz:feishu:group:oc_team_sz": "sup-group-1",
                        "agent:supervisor_market_sz:main": {
                            "sessionId": "sup-main-1",
                            "sessionFile": str(sup_dir / "sup-main-1.jsonl"),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (sup_dir / "sup-group-1.jsonl").write_text("old group transcript", encoding="utf-8")
            (sup_dir / "sup-main-1.jsonl").write_text("old main transcript", encoding="utf-8")

            result = self.run_hygiene(
                home,
                "--supervisor-agent",
                "supervisor_market_sz",
                "--worker-agents",
                "ops_market_sz,finance_market_sz",
                "--team-key",
                "market_sz",
                "--delete-transcripts",
                group_peer_id="oc_team_sz",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["teamKey"], "market_sz")
            statuses = {(item["agentId"], item["sessionKey"]): item["status"] for item in payload["results"]}
            self.assertEqual(
                statuses[("supervisor_market_sz", "agent:supervisor_market_sz:main")],
                "removed",
            )
            self.assertEqual(
                statuses[("supervisor_market_sz", "agent:supervisor_market_sz:feishu:group:oc_team_sz")],
                "removed",
            )


class V5RuntimeArtifactsTests(unittest.TestCase):
    def run_canary(self, db_path, session_root, *args):
        return subprocess.run(
            [
                "python3",
                str(V4_3_CANARY_SCRIPT),
                "--db",
                str(db_path),
                "--session-root",
                str(session_root),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_v5_watchdog_templates_use_team_placeholders(self):
        systemd_service = V5_SYSTEMD_SERVICE_TEMPLATE.read_text(encoding="utf-8")
        systemd_timer = V5_SYSTEMD_TIMER_TEMPLATE.read_text(encoding="utf-8")
        launchd = V5_LAUNCHD_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("__TEAM_KEY__", systemd_service)
        self.assertIn("__SUPERVISOR_AGENT_ID__", systemd_service)
        self.assertIn("__DB_PATH__", systemd_service)
        self.assertIn("v5-team-__TEAM_KEY__.service", systemd_timer)
        self.assertIn("bot.molt.v5-team-__TEAM_KEY__", launchd)
        self.assertIn("__DB_PATH__", launchd)

    def test_v5_canary_supports_custom_worker_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "team_jobs.db"
            session_root = root / "agents"
            conn = sqlite3.connect(db_path)
            conn.executescript(V4_3_SQL.read_text(encoding="utf-8"))
            conn.execute(
                """
                INSERT INTO jobs (
                    job_ref, title, status, group_peer_id, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("TG-V5-001", "深圳团队任务", "done", "oc_team_sz"),
            )
            conn.execute(
                """
                INSERT INTO job_participants (
                    job_ref, agent_id, account_id, role, status, progress_message_id, final_message_id, summary, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    "TG-V5-001",
                    "ops_market_sz",
                    "ops-bot",
                    "ops",
                    "done",
                    "msg_ops_progress",
                    "msg_ops_final",
                    "ops done",
                ),
            )
            conn.execute(
                """
                INSERT INTO job_participants (
                    job_ref, agent_id, account_id, role, status, progress_message_id, final_message_id, summary, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    "TG-V5-001",
                    "finance_market_sz",
                    "finance-bot",
                    "finance",
                    "done",
                    "msg_fin_progress",
                    "msg_fin_final",
                    "finance done",
                ),
            )
            conn.commit()
            conn.close()

            for agent_id, progress_id, final_id in [
                ("ops_market_sz", "msg_ops_progress", "msg_ops_final"),
                ("finance_market_sz", "msg_fin_progress", "msg_fin_final"),
            ]:
                session_dir = session_root / agent_id / "sessions"
                session_dir.mkdir(parents=True, exist_ok=True)
                (session_dir / f"{agent_id}.jsonl").write_text(
                    f"{progress_id}\n{final_id}\n",
                    encoding="utf-8",
                )

            result = self.run_canary(
                db_path,
                session_root,
                "--job-ref",
                "TG-V5-001",
                "--worker-agents",
                "ops_market_sz,finance_market_sz",
                "--supervisor-agent",
                "supervisor_market_sz",
                "--require-visible-messages",
                "--success-token",
                "V5_TEAM_CANARY_OK",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("V5_TEAM_CANARY_OK", result.stdout)
            self.assertIn("ops_market_sz_progress=msg_ops_progress", result.stdout)
            self.assertIn("finance_market_sz_final=msg_fin_final", result.stdout)

    def test_v5_canary_requires_supervisor_rollup_to_target_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "team_jobs.db"
            session_root = root / "agents"
            conn = sqlite3.connect(db_path)
            conn.executescript(V4_3_SQL.read_text(encoding="utf-8"))
            conn.execute(
                """
                INSERT INTO jobs (
                    job_ref, title, status, group_peer_id, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("TG-V5-002", "深圳团队任务", "done", "oc_team_sz"),
            )
            for agent_id, account_id, role, progress_id, final_id in [
                ("ops_market_sz", "ops-bot", "ops", "msg_ops_progress", "msg_ops_final"),
                ("finance_market_sz", "finance-bot", "finance", "msg_fin_progress", "msg_fin_final"),
            ]:
                conn.execute(
                    """
                    INSERT INTO job_participants (
                        job_ref, agent_id, account_id, role, status, progress_message_id, final_message_id, summary, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """,
                    ("TG-V5-002", agent_id, account_id, role, "done", progress_id, final_id, f"{agent_id} done"),
                )
            conn.commit()
            conn.close()

            for agent_id, progress_id, final_id in [
                ("ops_market_sz", "msg_ops_progress", "msg_ops_final"),
                ("finance_market_sz", "msg_fin_progress", "msg_fin_final"),
            ]:
                session_dir = session_root / agent_id / "sessions"
                session_dir.mkdir(parents=True, exist_ok=True)
                (session_dir / f"{agent_id}.jsonl").write_text(
                    f"{progress_id}\n{final_id}\n",
                    encoding="utf-8",
                )

            supervisor_dir = session_root / "supervisor_market_sz" / "sessions"
            supervisor_dir.mkdir(parents=True, exist_ok=True)
            (supervisor_dir / "supervisor_market_sz.jsonl").write_text(
                'toolCall name="message" target=chat:oc_team_sz jobRef=TG-V5-002 messageId=msg_supervisor_final\n',
                encoding="utf-8",
            )

            result = self.run_canary(
                db_path,
                session_root,
                "--job-ref",
                "TG-V5-002",
                "--worker-agents",
                "ops_market_sz,finance_market_sz",
                "--supervisor-agent",
                "supervisor_market_sz",
                "--require-visible-messages",
                "--require-supervisor-target-chat",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("msg_supervisor_final", result.stdout)


class V5DocumentationTests(unittest.TestCase):
    def test_v5_design_and_plan_docs_exist(self):
        self.assertTrue(V5_DESIGN_DOC.exists())
        self.assertTrue(V5_PLAN_DOC.exists())

        design = V5_DESIGN_DOC.read_text(encoding="utf-8")
        plan = V5_PLAN_DOC.read_text(encoding="utf-8")

        self.assertIn("Team Orchestrator", design)
        self.assertIn("1 个 supervisor", design)
        self.assertIn("teams", plan)

    def test_readme_mentions_v5_team_orchestrator(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("V5", content)
        self.assertIn("Team Orchestrator", content)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", content)
        self.assertIn("oc_7121d87961740dbd72bd8e50e48ba5e3", content)

    def test_skill_mentions_team_orchestrator_and_teams_model(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("Team Orchestrator", content)
        self.assertIn("teams", content)
        self.assertIn("可模板化", content)


class V5TemplateTests(unittest.TestCase):
    def test_v5_input_template_exists_and_mentions_teams(self):
        content = V5_INPUT_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('"teams"', content)
        self.assertIn('"supervisor"', content)
        self.assertIn('"workers"', content)
        self.assertIn('"workflow"', content)
        self.assertIn('oc_f785e73d3c00954d4ccd5d49b63ef919', content)
        self.assertIn('oc_7121d87961740dbd72bd8e50e48ba5e3', content)

    def test_v5_config_snapshot_exists_and_documents_two_teams(self):
        content = V5_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        self.assertIn("V5 Team Orchestrator", content)
        self.assertIn("internal_main", content)
        self.assertIn("external_main", content)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", content)
        self.assertIn("oc_7121d87961740dbd72bd8e50e48ba5e3", content)
        self.assertIn("agent:supervisor_internal_main:main", content)
        self.assertIn("agent:supervisor_external_main:main", content)

    def test_v5_doc_exists_and_keeps_one_supervisor_plus_n_workers_constraint(self):
        content = V5_DOC.read_text(encoding="utf-8")

        self.assertIn("One Team = 1 Supervisor + N Workers", content)
        self.assertIn("teams", content)
        self.assertIn("workflow.stages", content)
        self.assertIn("Codex 真实交付模板", content)
        self.assertIn("aoteman", content)
        self.assertIn("xiaolongxia", content)
        self.assertIn("yiran_yibao", content)

    def test_v5_doc_documents_team_runtime_commands(self):
        content = V5_DOC.read_text(encoding="utf-8")

        self.assertIn("--team-key", content)
        self.assertIn("--supervisor-agent", content)
        self.assertIn("v5-team-watchdog.service", content)
        self.assertIn("v5 runtime manifest", content)


class V5ReadmeAndSkillTests(unittest.TestCase):
    def test_readme_marks_v3_v431_and_v5_as_current_mainlines(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("V3.1", content)
        self.assertIn("V4.3.1", content)
        self.assertIn("V5 Team Orchestrator", content)
        self.assertIn("Codex", content)

    def test_skill_describes_team_unit_over_shared_global_agents(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("每个群", content)
        self.assertIn("1 个 supervisor", content)
        self.assertIn("N 个 worker", content)
        self.assertIn("team unit", content)

    def test_readme_and_skill_list_v5_runtime_artifacts(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        deployment_inputs = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("v5-team-watchdog.service", readme)
        self.assertIn("v5-team-watchdog.plist", readme)
        self.assertIn("v5-team-watchdog.service", skill)
        self.assertIn("v5-team-watchdog.plist", skill)
        self.assertIn("hidden_main_session_key", deployment_inputs)
        self.assertIn("v5_team_runtime", deployment_inputs)
        self.assertIn("runtime manifest", readme)


if __name__ == "__main__":
    unittest.main()
