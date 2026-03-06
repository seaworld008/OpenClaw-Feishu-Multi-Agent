import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/build_openclaw_feishu_snippets.py"
CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v3_dispatch_canary.sh"
V4_2_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_2_team_canary.sh"


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


if __name__ == "__main__":
    unittest.main()
