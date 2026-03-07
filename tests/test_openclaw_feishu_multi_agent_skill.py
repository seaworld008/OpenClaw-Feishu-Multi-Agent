import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_FILE = REPO_ROOT / "README.md"
SKILL_FILE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/SKILL.md"
BUILD_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/build_openclaw_feishu_snippets.py"
CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v3_dispatch_canary.sh"
V4_2_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_2_team_canary.sh"
V4_3_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_3_canary.py"
V4_2_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.2-single-group-team.md"
V4_2_1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.2.1-single-group-team.md"
V4_3_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3-single-group-production.md"
V4_3_1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md"
V4_3_1_C1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md"
V4_3_SQL = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql"
V4_3_REGISTRY = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_job_registry.py"
V4_3_HYGIENE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_session_hygiene.py"
V4_3_QUICKSTART_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md"
LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist"
WSL_CONF_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/windows/wsl.conf.example"
WINDOWS_WSL2_NOTES = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md"


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


class V42CanaryScriptTests(unittest.TestCase):
    def run_script(self, session_files, *extra_args):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            agents_root = root / "agents"
            log_path = root / "openclaw.log"
            log_path.write_text("", encoding="utf-8")

            for rel_path, content in session_files.items():
                target = agents_root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(V4_2_CANARY_SCRIPT),
                    "--session-root",
                    str(agents_root),
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

    def run_script_without_rg(self, session_files, *extra_args):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            agents_root = root / "agents"
            log_path = root / "openclaw.log"
            log_path.write_text("", encoding="utf-8")

            for rel_path, content in session_files.items():
                target = agents_root / rel_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            env = dict(**subprocess.os.environ)
            env["PATH"] = "/usr/bin:/bin"
            result = subprocess.run(
                [
                    "bash",
                    str(V4_2_CANARY_SCRIPT),
                    "--session-root",
                    str(agents_root),
                    "--log",
                    str(log_path),
                    "--start-line",
                    "0",
                    *extra_args,
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            return result

    def test_v42_canary_reports_list_miss_when_send_path_exists(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-001",
                        "sessions_list observed workers",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=ok runId=run-ops",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=ok runId=run-fin",
                        "dispatchEvidence missing on purpose",
                    ]
                ),
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("SEND_PATH_AVAILABLE_BUT_LIST_MISS", result.stdout)

    def test_v42_canary_succeeds_with_worker_session_evidence(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-001",
                        "dispatchEvidence",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=ok runId=run-ops sentAt=2026-03-06T12:00:00Z evidenceSource=session-jsonl",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=ok runId=run-fin sentAt=2026-03-06T12:00:01Z evidenceSource=session-jsonl",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-001 ops task received",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-001 finance task received",
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("TEAM_CANARY_OK", result.stdout)

    def test_v42_canary_reports_timeout_but_worker_delivered(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-001",
                        "sessions_list observed workers",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=timeout",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=timeout",
                        "DISPATCH_INCOMPLETE",
                        "nextAction=warmup_required",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-001 ops task received toSupervisorSummary=ok",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-001 finance task received toSupervisorSummary=ok",
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("TIMEOUT_BUT_WORKER_DELIVERED", result.stdout)

    def test_v42_canary_reports_no_reply_trigger_miss(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "task team-v4-2-001 NO_REPLY",
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP", result.stdout)

    def test_v42_canary_accepts_fire_and_forget_with_worker_evidence(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-001",
                        "dispatchEvidence",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=accepted runId=run-ops sentAt=2026-03-06T12:00:00Z evidenceSource=session-jsonl",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=accepted runId=run-fin sentAt=2026-03-06T12:00:01Z evidenceSource=session-jsonl",
                        "sessions_history verified worker transcript",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-001 ACK toSupervisorSummary=ready",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-001 ACK toSupervisorSummary=ready",
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("TEAM_CANARY_OK", result.stdout)

    def test_v42_canary_falls_back_without_rg(self):
        result = self.run_script_without_rg(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-001",
                        "dispatchEvidence",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=ok runId=run-ops sentAt=2026-03-06T12:00:00Z evidenceSource=session-jsonl",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=ok runId=run-fin sentAt=2026-03-06T12:00:01Z evidenceSource=session-jsonl",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-001 ops task received",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-001 finance task received",
            },
            "--task-id",
            "team-v4-2-001",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("TEAM_CANARY_OK", result.stdout)

    def test_v42_canary_requires_visible_messages_when_enabled(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-015",
                        "dispatchEvidence",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=ok runId=run-ops sentAt=2026-03-06T12:00:00Z evidenceSource=session-jsonl",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=ok runId=run-fin sentAt=2026-03-06T12:00:01Z evidenceSource=session-jsonl",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-015 toSupervisorSummary=ready",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-015 toSupervisorSummary=ready",
            },
            "--task-id",
            "team-v4-2-015",
            "--require-visible-messages",
        )

        self.assertEqual(result.returncode, 3)
        self.assertIn("VISIBLE_MESSAGE_MISSING", result.stdout)

    def test_v42_canary_accepts_visible_messages_when_enabled(self):
        result = self.run_script(
            {
                "supervisor_agent/sessions/s1.jsonl": "\n".join(
                    [
                        "task team-v4-2-015",
                        "dispatchEvidence",
                        "sessions_send target=agent:ops_agent:feishu:group:oc_demo sendStatus=ok runId=run-ops sentAt=2026-03-06T12:00:00Z evidenceSource=session-jsonl",
                        "sessions_send target=agent:finance_agent:feishu:group:oc_demo sendStatus=ok runId=run-fin sentAt=2026-03-06T12:00:01Z evidenceSource=session-jsonl",
                    ]
                ),
                "ops_agent/sessions/o1.jsonl": "team-v4-2-015 toolCall name=\"message\" messageId=om_ops 简短进度已群发",
                "finance_agent/sessions/f1.jsonl": "team-v4-2-015 toolCall name=\"message\" messageId=om_fin 简短进度已群发",
            },
            "--task-id",
            "team-v4-2-015",
            "--require-visible-messages",
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("TEAM_CANARY_OK", result.stdout)


class V42DocumentationContentTests(unittest.TestCase):
    def test_v42_doc_requires_fresh_session_after_prompt_changes(self):
        content = V4_2_DOC.read_text(encoding="utf-8")

        self.assertIn("/reset", content)
        self.assertIn("新 group session 的第一轮", content)
        self.assertIn("不要直接拿旧群会话继续测", content)

    def test_v42_doc_requires_workspace_initialization(self):
        content = V4_2_DOC.read_text(encoding="utf-8")

        self.assertIn("BOOTSTRAP.md", content)
        self.assertIn("IDENTITY.md", content)
        self.assertIn("生产工作区必须完成初始化", content)


    def test_v42_doc_requires_official_session_key_format(self):
        content = V4_2_DOC.read_text(encoding="utf-8")

        self.assertIn("agent:<agentId>:feishu:group:<peerId>", content)
        self.assertIn("禁止使用 `feishu:chat:...`", content)


class V42DocumentationExecutionTests(unittest.TestCase):
    def test_v42_doc_requires_history_check_and_fire_and_forget(self):
        content = V4_2_DOC.read_text(encoding="utf-8")

        self.assertIn("sessions_history", content)
        self.assertIn("timeoutSeconds=0", content)
        self.assertIn("ACK", content)


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

    def test_v42_1_doc_keeps_visible_message_guidance(self):
        content = V4_2_1_DOC.read_text(encoding="utf-8")

        self.assertIn("message 工具", content)
        self.assertIn("worker 显式群发", content)

    def test_v43_doc_describes_internal_jobref_and_queue(self):
        content = V4_3_DOC.read_text(encoding="utf-8")

        self.assertIn("jobRef", content)
        self.assertIn("activeJob", content)
        self.assertIn("queuedJobs", content)
        self.assertIn("SQLite", content)
        self.assertIn("taskId", content)

    def test_v43_doc_requires_one_time_warmup(self):
        content = V4_3_DOC.read_text(encoding="utf-8")

        self.assertIn("WARMUP", content)
        self.assertIn("一次性", content)
        self.assertIn("上线前置", content)

    def test_v43_doc_requires_real_message_ids_before_complete_packet(self):
        content = V4_3_DOC.read_text(encoding="utf-8")

        self.assertIn("两个真实 messageId", content)
        self.assertIn("WORKFLOW_INCOMPLETE", content)
        self.assertIn("COMPLETE_PACKET", content)

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

            import sqlite3

            conn = sqlite3.connect(db_path)
            conn.execute(
                "UPDATE jobs SET created_at = '2026-03-07T00:00:00+00:00', updated_at = '2026-03-07T00:00:00+00:00' WHERE job_ref = 'TG-20260307-001'"
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
            self.assertIn('"jobRef": "TG-20260307-001"', prepared.stdout)

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
                        f"conn=sqlite3.connect({str(db_path)!r}); "
                        "conn.execute(\"UPDATE jobs SET created_at='2026-03-07T00:00:00+00:00', updated_at='2026-03-07T00:00:00+00:00' WHERE job_ref=?\", "
                        f"({first_ref!r},)); "
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

            subprocess.run(
                [
                    "python3",
                    "-c",
                    (
                        "import sqlite3; "
                        f"conn=sqlite3.connect({str(db_path)!r}); "
                        "conn.execute(\"UPDATE jobs SET updated_at='2026-03-07T00:00:00+00:00' WHERE job_ref='TG-20260307-001'\"); "
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

    def test_v42_doc_uses_global_and_agent_level_mention_patterns(self):
        content = V4_2_DOC.read_text(encoding="utf-8")

        self.assertIn("messages.groupChat.mentionPatterns", content)
        self.assertIn("agents.list[].groupChat.mentionPatterns", content)


class V421DocumentationContentTests(unittest.TestCase):
    def test_v421_doc_requires_explicit_worker_message_send(self):
        content = V4_2_1_DOC.read_text(encoding="utf-8")

        self.assertIn("显式调用 `message` 工具", content)
        self.assertIn("messageId", content)
        self.assertIn("群里必须真的看到其他机器人发消息", content)

    def test_v421_doc_records_real_success_evidence(self):
        content = V4_2_1_DOC.read_text(encoding="utf-8")

        self.assertIn("team-v4-2-015", content)
        self.assertIn("om_x100b558f16d170e0c4ac92409ae2e2c", content)
        self.assertIn("om_x100b558f147928a0b214ccb83766041", content)


class V43DocumentationContentTests(unittest.TestCase):
    def test_v43_doc_mentions_auto_jobref_and_queue(self):
        content = V4_3_DOC.read_text(encoding="utf-8")

        self.assertIn("自动生成内部 `jobRef`", content)
        self.assertIn("activeJob", content)
        self.assertIn("queued", content)


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

    def test_v431_c1_doc_exists_and_uses_customer_robot_accounts(self):
        content = V4_3_1_C1_DOC.read_text(encoding="utf-8")

        self.assertIn("V4.3.1-C1.0", content)
        self.assertIn("marketing_bot", content)
        self.assertIn("ecommerce_market_bot", content)
        self.assertIn("finance_bot", content)
        self.assertIn("cli_a926a086e9389cba", content)
        self.assertIn("cli_a926a17fd0b8dcc4", content)
        self.assertIn("cli_a92123297f78dcb0", content)
        self.assertIn("oc_<客户团队群ID待填>", content)

    def test_v431_c1_doc_keeps_three_bot_six_expert_mapping(self):
        content = V4_3_1_C1_DOC.read_text(encoding="utf-8")

        self.assertIn("营销专家 + 文案专家 + 销售专家", content)
        self.assertIn("市场分析专家 + 电商线上运营专家", content)
        self.assertIn("财务专家", content)
        self.assertIn("营销总控已接单", content)
        self.assertIn("电商市场结论", content)


class V431QuickStartAndHygieneTests(unittest.TestCase):
    def run_hygiene(self, home_path, *args):
        result = subprocess.run(
            [
                "python3",
                str(V4_3_HYGIENE_SCRIPT),
                "--home",
                str(home_path),
                "--group-peer-id",
                "oc_demo_group",
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


if __name__ == "__main__":
    unittest.main()
