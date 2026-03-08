import json
import importlib.util
import re
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_FILE = REPO_ROOT / "README.md"
SKILL_FILE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/SKILL.md"
TEST_FILE = Path(__file__).resolve()
BUILD_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py"
CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v31_cross_group_canary.py"
V4_3_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py"
V4_3_1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md"
V4_3_1_C1_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md"
V4_3_SQL = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql"
V4_3_1_CONFIG_SNAPSHOT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc"
V4_3_REGISTRY = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py"
V4_3_HYGIENE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py"
V5_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_canary.py"
V5_RECONCILE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py"
V4_3_QUICKSTART_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md"
V5_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-team-orchestrator-design.md"
V5_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-team-orchestrator-implementation.md"
V5_1_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-design.md"
V5_1_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-implementation.md"
V5_INPUT_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-team-orchestrator.json"
V5_FIXED_ROLE_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-fixed-role-multi-group.json"
V5_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md"
V5_CONFIG_SNAPSHOT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc"
V5_1_QUICKSTART_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md"
CUSTOMER_FIRST_USE_CHECKLIST = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md"
CUSTOMER_FIRST_USE_PROMPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md"
CUSTOMER_FIRST_USE_EXAMPLE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md"
LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist"
V5_SYSTEMD_SERVICE_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.service"
V5_SYSTEMD_TIMER_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v5-team-watchdog.timer"
V5_LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v5-team-watchdog.plist"
VERIFICATION_CHECKLIST = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md"
WSL_CONF_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/windows/wsl.conf.example"
WINDOWS_WSL2_NOTES = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md"
MERGE_GAP_ANALYSIS = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/merge-gap-analysis.md"
V4_3_1_STABILITY_PLAN = REPO_ROOT / "docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md"


def legacy_script_names():
    return [
        "build" + "_openclaw_feishu_" + "snippets.py",
        "v4" + "_3_job_registry.py",
        "v4" + "_3_session_hygiene.py",
        "check_" + "v4_3_canary.py",
        "check_" + "v3_dispatch_canary.sh",
    ]


def new_script_paths():
    script_root = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts"
    return [
        script_root / "core_feishu_config_builder.py",
        script_root / "core_job_registry.py",
        script_root / "core_session_hygiene.py",
        script_root / "core_canary_engine.py",
        script_root / "v31_cross_group_canary.py",
        script_root / "v431_single_group_runtime.py",
        script_root / "v431_single_group_hygiene.py",
        script_root / "v431_single_group_canary.py",
        script_root / "v51_team_orchestrator_runtime.py",
        script_root / "v51_team_orchestrator_hygiene.py",
        script_root / "v51_team_orchestrator_canary.py",
        script_root / "v51_team_orchestrator_reconcile.py",
        script_root / "v51_team_orchestrator_deploy.py",
    ]


def active_namespace_docs():
    return [
        README_FILE,
        SKILL_FILE,
        TEST_FILE,
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.service",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v3.1.md",
        V4_3_1_DOC,
        V4_3_1_C1_DOC,
        V5_DOC,
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md",
        CUSTOMER_FIRST_USE_CHECKLIST,
        CUSTOMER_FIRST_USE_PROMPT,
        CUSTOMER_FIRST_USE_EXAMPLE,
        V4_3_QUICKSTART_DOC,
        WINDOWS_WSL2_NOTES,
        REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-design.md",
        REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-implementation.md",
        REPO_ROOT / "docs/plans/2026-03-08-v5-team-orchestrator-implementation.md",
        REPO_ROOT / "docs/plans/2026-03-08-script-namespace-unification-design.md",
        REPO_ROOT / "docs/plans/2026-03-08-script-namespace-unification-implementation.md",
    ]


class ScriptNamespaceContractTests(unittest.TestCase):
    def test_new_script_namespace_files_exist(self):
        missing = [str(path.relative_to(REPO_ROOT)) for path in new_script_paths() if not path.exists()]
        self.assertEqual(missing, [])

    def test_active_docs_and_tests_do_not_reference_legacy_script_names(self):
        violations = []
        for path in active_namespace_docs():
            text = path.read_text(encoding="utf-8")
            for legacy_name in legacy_script_names():
                if legacy_name in text:
                    violations.append(f"{path.relative_to(REPO_ROOT)} -> {legacy_name}")
        self.assertEqual(violations, [])

    def test_version_docs_reference_new_public_entrypoints(self):
        doc_expectations = {
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v3.1.md": [
                "v31_cross_group_canary.py",
            ],
            V4_3_1_DOC: [
                "v431_single_group_runtime.py",
                "v431_single_group_hygiene.py",
                "v431_single_group_canary.py",
            ],
            V4_3_1_C1_DOC: [
                "v431_single_group_runtime.py",
                "v431_single_group_hygiene.py",
                "v431_single_group_canary.py",
            ],
            V5_DOC: [
                "v51_team_orchestrator_runtime.py",
                "v51_team_orchestrator_hygiene.py",
                "v51_team_orchestrator_canary.py",
                "v51_team_orchestrator_reconcile.py",
                "v51_team_orchestrator_deploy.py",
            ],
        }
        missing = []
        for path, expected_tokens in doc_expectations.items():
            text = path.read_text(encoding="utf-8")
            for token in expected_tokens:
                if token not in text:
                    missing.append(f"{path.relative_to(REPO_ROOT)} -> {token}")
        self.assertEqual(missing, [])


def load_build_module():
    spec = importlib.util.spec_from_file_location(BUILD_SCRIPT.stem, BUILD_SCRIPT)
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

    def test_v5_team_input_preserves_identity_and_manifest_description(self):
        data = self.team_input()
        data["teams"][0]["supervisor"]["description"] = "负责深圳团队多专家编排与最终收口"
        data["teams"][0]["supervisor"]["identity"] = {
            "name": "奥特曼总控",
            "theme": "calm orchestrator",
            "emoji": "🧭",
            "avatar": "avatars/supervisor.png",
        }
        data["teams"][0]["workers"][0]["description"] = "负责活动节奏与执行拆解"
        data["teams"][0]["workers"][0]["identity"] = {
            "theme": "growth operator",
            "emoji": "📈",
        }

        patch = self.module.build_plugin_patch(data)
        manifest = self.module.build_v5_runtime_manifest(data)

        self.assertEqual(
            patch["agents"]["list"][0]["identity"],
            {
                "name": "奥特曼总控",
                "theme": "calm orchestrator",
                "emoji": "🧭",
                "avatar": "avatars/supervisor.png",
            },
        )
        self.assertEqual(
            patch["agents"]["list"][1]["identity"],
            {
                "theme": "growth operator",
                "emoji": "📈",
            },
        )
        self.assertEqual(
            manifest["teams"][0]["supervisor"]["description"],
            "负责深圳团队多专家编排与最终收口",
        )
        self.assertEqual(
            manifest["teams"][0]["workers"][0]["description"],
            "负责活动节奏与执行拆解",
        )
        self.assertEqual(
            manifest["teams"][0]["supervisor"]["identity"]["emoji"],
            "🧭",
        )

    def test_v5_team_input_builds_team_runtime_manifest(self):
        manifest = self.module.build_v5_runtime_manifest(self.team_input())

        self.assertEqual(manifest["orchestratorVersion"], "V5.1 Hardening")
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
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["startJob"],
            "start-job-with-workflow",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["nextAction"],
            "get-next-action",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["buildDispatchPayload"],
            "build-dispatch-payload",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["buildVisibleAck"],
            "build-visible-ack",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["buildRollupVisibleMessage"],
            "build-rollup-visible-message",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["recordVisibleMessage"],
            "record-visible-message",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["reconcileScript"],
            "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["reconcileDispatch"],
            "reconcile-dispatch",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["reconcileRollup"],
            "reconcile-rollup",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["controlPlane"]["commands"]["resumeJob"],
            "resume-job",
        )

    def test_v5_team_input_persists_visible_delivery_metadata_for_reconcile(self):
        manifest = self.module.build_v5_runtime_manifest(self.team_input())

        self.assertEqual(
            manifest["teams"][0]["runtime"]["entryAccountId"],
            "marketing-bot",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["entryChannel"],
            "feishu",
        )
        self.assertEqual(
            manifest["teams"][0]["runtime"]["entryTarget"],
            "chat:oc_team_sz",
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

    def test_v5_team_input_rejects_workflow_missing_worker_stage(self):
        data = self.team_input()
        data["teams"][0]["workflow"]["stages"] = [
            {"agentId": "ops_market_sz"},
        ]

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)

    def test_v5_team_input_rejects_duplicate_workflow_stage_agent(self):
        data = self.team_input()
        data["teams"][0]["workflow"]["stages"] = [
            {"agentId": "ops_market_sz"},
            {"agentId": "ops_market_sz"},
        ]

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)


class CanaryScriptTests(unittest.TestCase):
    def run_script(self, log_content, *extra_args):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / "openclaw.log"
            log_path.write_text(log_content, encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
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
        self.assertIn("v431_single_group_runtime.py", content)
        self.assertIn("StartInterval", content)
        self.assertIn("__TEAM_GROUP_PEER_ID__", content)

    def test_windows_wsl2_notes_prefer_wsl_and_systemd(self):
        content = WINDOWS_WSL2_NOTES.read_text(encoding="utf-8")

        self.assertIn("WSL2", content)
        self.assertIn("systemd=true", content)
        self.assertIn("Windows 原生", content)
        self.assertIn("不推荐", content)

    def test_v5_docs_require_real_message_ids_and_callback_reconcile(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        checklist = VERIFICATION_CHECKLIST.read_text(encoding="utf-8")
        v5_doc = V5_DOC.read_text(encoding="utf-8")
        v5_snapshot = V5_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        self.assertIn("最近的有效 `COMPLETE_PACKET`", readme)
        self.assertIn("pending / placeholder / sent / <pending...>", readme)
        self.assertIn("优先消费最近有效包", skill)
        self.assertIn("status=completed", skill)
        self.assertIn("消费最近有效包", checklist)
        self.assertIn("真实 messageId", checklist)
        self.assertIn("status=completed", v5_doc)
        self.assertIn("pending / placeholder / sent / <pending...>", v5_doc)
        self.assertIn("读取真实 progressMessageId", v5_snapshot)
        self.assertIn("禁止使用 pending/sent/<pending...>/*_placeholder", v5_snapshot)

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

    def test_registry_ready_to_rollup_accepts_v5_team_scoped_worker_ids(self):
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
                "V5 串行任务",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            for agent_id, account_id, role, progress_id, final_id, summary in (
                (
                    "ops_internal_main",
                    "xiaolongxia",
                    "运营执行",
                    "om_ops_progress",
                    "om_ops_final",
                    "运营方案已完成",
                ),
                (
                    "finance_internal_main",
                    "yiran_yibao",
                    "财务执行",
                    "om_fin_progress",
                    "om_fin_final",
                    "财务方案已完成",
                ),
            ):
                completed = self.run_registry(
                    db_path,
                    "mark-worker-complete",
                    "--job-ref",
                    job_ref,
                    "--agent-id",
                    agent_id,
                    "--account-id",
                    account_id,
                    "--role",
                    role,
                    "--progress-message-id",
                    progress_id,
                    "--final-message-id",
                    final_id,
                    "--summary",
                    summary,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            ready = self.run_registry(db_path, "ready-to-rollup", "--job-ref", job_ref)

            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertIn('"ready": true', ready.stdout)
            self.assertIn('"ops_internal_main"', ready.stdout)
            self.assertIn('"finance_internal_main"', ready.stdout)

    def test_registry_ready_to_rollup_waits_for_all_v5_participants(self):
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
                "V5 三专家串行任务",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            for agent_id, account_id, role in (
                ("ops_internal_main", "xiaolongxia", "运营执行"),
                ("finance_internal_main", "yiran_yibao", "财务执行"),
                ("legal_internal_main", "falv", "法务执行"),
            ):
                dispatched = self.run_registry(
                    db_path,
                    "mark-dispatch",
                    "--job-ref",
                    job_ref,
                    "--agent-id",
                    agent_id,
                    "--account-id",
                    account_id,
                    "--role",
                    role,
                    "--dispatch-run-id",
                    f"run-{agent_id}",
                )
                self.assertEqual(dispatched.returncode, 0, dispatched.stderr)

            for agent_id, account_id, role, progress_id, final_id, summary in (
                (
                    "ops_internal_main",
                    "xiaolongxia",
                    "运营执行",
                    "om_ops_progress",
                    "om_ops_final",
                    "运营方案已完成",
                ),
                (
                    "finance_internal_main",
                    "yiran_yibao",
                    "财务执行",
                    "om_fin_progress",
                    "om_fin_final",
                    "财务方案已完成",
                ),
            ):
                completed = self.run_registry(
                    db_path,
                    "mark-worker-complete",
                    "--job-ref",
                    job_ref,
                    "--agent-id",
                    agent_id,
                    "--account-id",
                    account_id,
                    "--role",
                    role,
                    "--progress-message-id",
                    progress_id,
                    "--final-message-id",
                    final_id,
                    "--summary",
                    summary,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)

            ready_before_all = self.run_registry(db_path, "ready-to-rollup", "--job-ref", job_ref)
            self.assertEqual(ready_before_all.returncode, 0, ready_before_all.stderr)
            self.assertIn('"ready": false', ready_before_all.stdout)
            self.assertIn('"legal_internal_main"', ready_before_all.stdout)

            legal_done = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "legal_internal_main",
                "--account-id",
                "falv",
                "--role",
                "法务执行",
                "--progress-message-id",
                "om_legal_progress",
                "--final-message-id",
                "om_legal_final",
                "--summary",
                "法务方案已完成",
            )
            self.assertEqual(legal_done.returncode, 0, legal_done.stderr)

            ready_after_all = self.run_registry(db_path, "ready-to-rollup", "--job-ref", job_ref)
            self.assertEqual(ready_after_all.returncode, 0, ready_after_all.stderr)
            self.assertIn('"ready": true', ready_after_all.stdout)
            self.assertIn('"legal_internal_main"', ready_after_all.stdout)

    def test_registry_start_job_with_workflow_emits_first_dispatch_action(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "V5.1 硬状态机任务",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--orchestrator-version",
                "V5.1 Hardening",
            )

            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn('"orchestratorVersion": "V5.1 Hardening"', started.stdout)
            self.assertIn('"type": "dispatch"', started.stdout)
            self.assertIn('"agentId": "ops_internal_main"', started.stdout)

    def test_registry_get_next_action_advances_only_in_workflow_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "V5.1 串行推进任务",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            dispatch_wrong = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_internal_main",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
            )
            self.assertEqual(dispatch_wrong.returncode, 2, dispatch_wrong.stdout)
            self.assertIn('"status": "workflow_out_of_order"', dispatch_wrong.stdout)

            dispatch_ops = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
            )
            self.assertEqual(dispatch_ops.returncode, 0, dispatch_ops.stderr)
            self.assertIn('"type": "wait_worker"', dispatch_ops.stdout)

            next_after_ops_dispatch = self.run_registry(db_path, "get-next-action", "--job-ref", job_ref)
            self.assertEqual(next_after_ops_dispatch.returncode, 0, next_after_ops_dispatch.stderr)
            self.assertIn('"type": "wait_worker"', next_after_ops_dispatch.stdout)
            self.assertIn('"agentId": "ops_internal_main"', next_after_ops_dispatch.stdout)

            ops_complete = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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
            self.assertEqual(ops_complete.returncode, 0, ops_complete.stderr)
            self.assertIn('"type": "dispatch"', ops_complete.stdout)
            self.assertIn('"agentId": "finance_internal_main"', ops_complete.stdout)

            finance_complete = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_internal_main",
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
            self.assertEqual(finance_complete.returncode, 0, finance_complete.stderr)
            self.assertIn('"type": "rollup"', finance_complete.stdout)

            ready = self.run_registry(db_path, "ready-to-rollup", "--job-ref", job_ref)
            self.assertEqual(ready.returncode, 0, ready.stderr)
            self.assertIn('"ready": true', ready.stdout)
            self.assertIn('"type": "rollup"', ready.stdout)

    def test_registry_init_db_migrates_existing_jobs_table_for_v51_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(V4_3_SQL.read_text(encoding="utf-8"))
            conn.commit()
            conn.close()

            result = self.run_registry(db_path, "init-db")
            self.assertEqual(result.returncode, 0, result.stderr)

            conn = sqlite3.connect(db_path)
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            conn.close()

            self.assertIn("workflow_json", columns)
            self.assertIn("orchestrator_version", columns)
            self.assertIn("current_stage_index", columns)
            self.assertIn("waiting_for_agent_id", columns)
            self.assertIn("next_action", columns)

    def test_registry_init_db_migrates_existing_jobs_table_for_v51_repair_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            conn = sqlite3.connect(db_path)
            conn.executescript(V4_3_SQL.read_text(encoding="utf-8"))
            conn.commit()
            conn.close()

            result = self.run_registry(db_path, "init-db")
            self.assertEqual(result.returncode, 0, result.stderr)

            conn = sqlite3.connect(db_path)
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(jobs)").fetchall()
            }
            conn.close()

            self.assertIn("request_text", columns)
            self.assertIn("entry_account_id", columns)
            self.assertIn("entry_channel", columns)
            self.assertIn("entry_target", columns)
            self.assertIn("entry_delivery_json", columns)
            self.assertIn("hidden_main_session_key", columns)
            self.assertIn("ack_visible_sent", columns)
            self.assertIn("rollup_visible_sent", columns)
            self.assertIn("dispatch_attempt_count", columns)
            self.assertIn("last_control_error", columns)

    def test_registry_start_job_with_workflow_persists_visible_delivery_and_request_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 上下文持久化",
                "--request-text",
                "请给出 3 天促销冲刺方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)

            self.assertEqual(details.returncode, 0, details.stderr)
            self.assertIn('"entryAccountId": "aoteman"', details.stdout)
            self.assertIn('"entryChannel": "feishu"', details.stdout)
            self.assertIn('"entryTarget": "chat:oc_demo"', details.stdout)
            self.assertIn('"hiddenMainSessionKey": "agent:supervisor_internal_main:main"', details.stdout)
            self.assertIn('"participantCount": 2', details.stdout)

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

    def test_watchdog_detects_dispatch_gap_instead_of_reporting_active_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "V5.1 dispatch gap",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
            )
            self.assertEqual(started.returncode, 0, started.stderr)

            watchdog = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
            self.assertNotIn('"status": "active_ok"', watchdog.stdout)
            self.assertIn('"status": "needs_dispatch_reconcile"', watchdog.stdout)

    def test_close_job_done_requires_rollup_visible_message_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "ou_user",
                "--title",
                "V5.1 rollup visibility",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            dispatch_ops = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch_ops.returncode, 0, dispatch_ops.stderr)

            complete_ops = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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
            self.assertEqual(complete_ops.returncode, 0, complete_ops.stderr)

            dispatch_finance = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_internal_main",
                "--account-id",
                "yiran_yibao",
                "--role",
                "财务执行",
                "--dispatch-run-id",
                "run-finance",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch_finance.returncode, 0, dispatch_finance.stderr)

            complete_finance = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "finance_internal_main",
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
            self.assertEqual(complete_finance.returncode, 0, complete_finance.stderr)

            close = self.run_registry(
                db_path,
                "close-job",
                "--job-ref",
                job_ref,
                "--status",
                "done",
            )

            self.assertEqual(close.returncode, 2, close.stdout)
            self.assertIn('"status": "rollup_visible_message_required"', close.stdout)

    def test_registry_build_dispatch_payload_emits_canonical_worker_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 canonical dispatch",
                "--request-text",
                "请给出 3 天促销冲刺方案，包含运营节奏、预算红线和风险预案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            payload = self.run_registry(
                db_path,
                "build-dispatch-payload",
                "--job-ref",
                job_ref,
            )

            self.assertEqual(payload.returncode, 0, payload.stderr)
            self.assertIn(f'"jobRef": "{job_ref}"', payload.stdout)
            self.assertIn('"agentId": "ops_internal_main"', payload.stdout)
            self.assertIn('"groupPeerId": "oc_demo"', payload.stdout)
            self.assertIn('"callbackSessionKey": "agent:supervisor_internal_main:main"', payload.stdout)
            self.assertIn('"mustSend": "progress,final,callback"', payload.stdout)
            self.assertIn('"role": "运营执行"', payload.stdout)
            self.assertIn('"requestText": "请给出 3 天促销冲刺方案，包含运营节奏、预算红线和风险预案。"', payload.stdout)

    def test_registry_build_visible_ack_uses_explicit_feishu_delivery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 ack",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            ack = self.run_registry(db_path, "build-visible-ack", "--job-ref", job_ref)

            self.assertEqual(ack.returncode, 0, ack.stderr)
            self.assertIn('"channel": "feishu"', ack.stdout)
            self.assertIn('"accountId": "aoteman"', ack.stdout)
            self.assertIn('"target": "chat:oc_demo"', ack.stdout)
            self.assertIn(f"【主管已接单｜{job_ref}】", ack.stdout)

    def test_registry_build_rollup_visible_message_requires_completion_packets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 rollup message",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            dispatch = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)

            rolled = self.run_registry(db_path, "build-rollup-visible-message", "--job-ref", job_ref)
            self.assertEqual(rolled.returncode, 2, rolled.stdout)
            self.assertIn('"status": "rollup_not_ready"', rolled.stdout)

            completed = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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
            self.assertEqual(completed.returncode, 0, completed.stderr)

            rolled_ready = self.run_registry(db_path, "build-rollup-visible-message", "--job-ref", job_ref)
            self.assertEqual(rolled_ready.returncode, 0, rolled_ready.stderr)
            self.assertIn(f"【主管最终统一收口｜{job_ref}】", rolled_ready.stdout)
            self.assertIn('"channel": "feishu"', rolled_ready.stdout)

    def test_registry_record_visible_message_updates_ack_and_rollup_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 visible flags",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            ack = self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack",
            )
            self.assertEqual(ack.returncode, 0, ack.stderr)
            self.assertIn('"ackVisibleSent": true', ack.stdout)

            dispatch = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)

            completed = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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
            self.assertEqual(completed.returncode, 0, completed.stderr)

            rollup = self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "rollup",
                "--message-id",
                "om_rollup",
            )
            self.assertEqual(rollup.returncode, 0, rollup.stderr)
            self.assertIn('"rollupVisibleSent": true', rollup.stdout)

    def test_watchdog_detects_missing_rollup_visibility_instead_of_reporting_active_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 rollup gap",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            dispatch = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)

            completed = self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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
            self.assertEqual(completed.returncode, 0, completed.stderr)

            watchdog = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
            self.assertNotIn('"status": "active_ok"', watchdog.stdout)
            self.assertIn('"status": "needs_rollup_reconcile"', watchdog.stdout)

    def test_watchdog_keeps_wait_worker_jobs_active_only_when_dispatch_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--title",
                "V5.1 wait worker",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            watchdog_before = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )
            self.assertIn('"status": "needs_dispatch_reconcile"', watchdog_before.stdout)

            dispatch = self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)

            watchdog_after = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )
            self.assertIn('"status": "active_ok"', watchdog_after.stdout)


class V51ReconcileTests(unittest.TestCase):
    def run_registry(self, db_path, *args):
        return subprocess.run(
            ["python3", str(V4_3_REGISTRY), "--db", str(db_path), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def run_reconcile(self, manifest_path, team_key, openclaw_home, openclaw_bin, *args):
        return subprocess.run(
            [
                "python3",
                str(V5_RECONCILE_SCRIPT),
                "--manifest",
                str(manifest_path),
                "--team-key",
                team_key,
                "--openclaw-home",
                str(openclaw_home),
                "--openclaw-bin",
                str(openclaw_bin),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def write_manifest(self, manifest_path, db_path, group_peer_id="oc_demo"):
        manifest = {
            "orchestratorVersion": "V5.1 Hardening",
            "teams": [
                {
                    "teamKey": "internal_main",
                    "displayName": "内部生产群",
                    "group": {
                        "peerId": group_peer_id,
                        "entryAccountId": "aoteman",
                        "requireMention": True,
                    },
                    "supervisor": {
                        "agentId": "supervisor_internal_main",
                        "accountId": "aoteman",
                        "hiddenMainSessionKey": "agent:supervisor_internal_main:main",
                    },
                    "workers": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                            "groupSessionKey": f"agent:ops_internal_main:feishu:group:{group_peer_id}",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                            "groupSessionKey": f"agent:finance_internal_main:feishu:group:{group_peer_id}",
                        },
                    ],
                    "workflow": {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    "runtime": {
                        "dbPath": str(db_path),
                        "hiddenMainSessionKey": "agent:supervisor_internal_main:main",
                        "entryAccountId": "aoteman",
                        "entryChannel": "feishu",
                        "entryTarget": f"chat:{group_peer_id}",
                        "controlPlane": {
                            "registryScript": str(V4_3_REGISTRY),
                            "commands": {
                                "startJob": "start-job-with-workflow",
                                "nextAction": "get-next-action",
                                "buildDispatchPayload": "build-dispatch-payload",
                                "buildVisibleAck": "build-visible-ack",
                                "buildRollupContext": "build-rollup-context",
                                "buildRollupVisibleMessage": "build-rollup-visible-message",
                                "recordVisibleMessage": "record-visible-message",
                                "readyToRollup": "ready-to-rollup",
                            },
                        },
                        "sessionKeys": {
                            "supervisorGroup": f"agent:supervisor_internal_main:feishu:group:{group_peer_id}",
                            "supervisorMain": "agent:supervisor_internal_main:main",
                            "workers": [
                                f"agent:ops_internal_main:feishu:group:{group_peer_id}",
                                f"agent:finance_internal_main:feishu:group:{group_peer_id}",
                            ],
                        },
                    },
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    def write_supervisor_transcript(self, openclaw_home, body, message_id="om_demo"):
        sessions_dir = openclaw_home / "agents" / "supervisor_internal_main" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = "session-supervisor-group"
        session_key = "agent:supervisor_internal_main:feishu:group:oc_demo"
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        user_text = (
            "Conversation info (untrusted metadata):\n"
            "```json\n"
            "{\n"
            f"  \"message_id\": \"{message_id}\",\n"
            "  \"sender_id\": \"ou_demo_user\",\n"
            "  \"conversation_label\": \"oc_demo\",\n"
            "  \"sender\": \"SeaWorld\",\n"
            "  \"timestamp\": \"Sun 2026-03-08 23:00 GMT+8\",\n"
            "  \"group_subject\": \"oc_demo\",\n"
            "  \"is_group_chat\": true,\n"
            "  \"was_mentioned\": true\n"
            "}\n"
            "```\n\n"
            "Sender (untrusted metadata):\n"
            "```json\n"
            "{\n"
            "  \"label\": \"SeaWorld (ou_demo_user)\",\n"
            "  \"id\": \"ou_demo_user\",\n"
            "  \"name\": \"SeaWorld\"\n"
            "}\n"
            "```\n\n"
            f"[message_id: {message_id}]\n"
            f"SeaWorld: {body}"
        )
        transcript_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "message",
                            "id": "msg-user",
                            "timestamp": "2026-03-08T15:00:07.499Z",
                            "message": {
                                "role": "user",
                                "content": [{"type": "text", "text": user_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "msg-assistant",
                            "timestamp": "2026-03-08T15:00:10.667Z",
                            "message": {
                                "role": "assistant",
                                "content": [{"type": "text", "text": "NO_REPLY"}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (sessions_dir / "sessions.json").write_text(
            json.dumps(
                {
                    session_key: {
                        "sessionId": session_id,
                        "updatedAt": 1772982010667,
                        "sessionFile": str(transcript_path),
                        "deliveryContext": {
                            "channel": "feishu",
                            "to": "chat:oc_demo",
                            "accountId": "aoteman",
                        },
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def write_worker_main_no_reply_transcript(self, openclaw_home, agent_id, job_ref, group_peer_id="oc_demo"):
        sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = f"{agent_id}-main-1"
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        dispatch_text = (
            f"[Sun 2026-03-08 23:58 GMT+8] TASK_DISPATCH|jobRef={job_ref}|from=supervisor_internal_main|"
            f"to={agent_id}|title=测试任务|request=请输出完整方案|"
            f"callbackSessionKey=agent:supervisor_internal_main:main|mustSend=progress,final,callback|"
            f"channel=feishu|accountId=xiaolongxia|target=chat:{group_peer_id}|groupPeerId={group_peer_id}"
        )
        transcript_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-user",
                            "timestamp": "2026-03-08T15:58:10.127Z",
                            "message": {
                                "role": "user",
                                "content": [{"type": "text", "text": dispatch_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-assistant",
                            "timestamp": "2026-03-08T15:58:15.271Z",
                            "message": {
                                "role": "assistant",
                                "content": [{"type": "text", "text": "NO_REPLY"}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (sessions_dir / "sessions.json").write_text(
            json.dumps(
                {
                    f"agent:{agent_id}:main": {
                        "sessionId": session_id,
                        "updatedAt": 1772985495284,
                        "sessionFile": str(transcript_path),
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def write_worker_main_completed_transcript(
        self,
        openclaw_home,
        agent_id,
        job_ref,
        *,
        group_peer_id="oc_demo",
        callback_session_key="agent:supervisor_internal_main:main",
        progress_message_id="om_progress_real",
        final_message_id="om_final_real",
    ):
        sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = f"{agent_id}-main-complete"
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        dispatch_text = (
            f"[Sun 2026-03-08 23:58 GMT+8] TASK_DISPATCH|jobRef={job_ref}|from=supervisor_internal_main|"
            f"to={agent_id}|title=测试任务|request=请输出完整方案|"
            f"callbackSessionKey={callback_session_key}|mustSend=progress,final,callback|"
            f"channel=feishu|accountId=xiaolongxia|target=chat:{group_peer_id}|groupPeerId={group_peer_id}"
        )
        transcript_path.write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-user",
                            "timestamp": "2026-03-08T15:58:10.127Z",
                            "message": {
                                "role": "user",
                                "content": [{"type": "text", "text": dispatch_text}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-tool-result-progress",
                            "timestamp": "2026-03-08T15:58:14.000Z",
                            "message": {
                                "role": "toolResult",
                                "toolName": "message",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(
                                            {
                                                "channel": "feishu",
                                                "result": {
                                                    "messageId": progress_message_id,
                                                    "chatId": group_peer_id,
                                                },
                                            },
                                            ensure_ascii=False,
                                        ),
                                    }
                                ],
                                "details": {
                                    "channel": "feishu",
                                    "result": {
                                        "messageId": progress_message_id,
                                        "chatId": group_peer_id,
                                    },
                                },
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-tool-result-final",
                            "timestamp": "2026-03-08T15:58:18.000Z",
                            "message": {
                                "role": "toolResult",
                                "toolName": "message",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(
                                            {
                                                "channel": "feishu",
                                                "result": {
                                                    "messageId": final_message_id,
                                                    "chatId": group_peer_id,
                                                },
                                            },
                                            ensure_ascii=False,
                                        ),
                                    }
                                ],
                                "details": {
                                    "channel": "feishu",
                                    "result": {
                                        "messageId": final_message_id,
                                        "chatId": group_peer_id,
                                    },
                                },
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-assistant",
                            "timestamp": "2026-03-08T15:58:19.000Z",
                            "message": {
                                "role": "assistant",
                                "content": [{"type": "text", "text": "NO_REPLY"}],
                            },
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (sessions_dir / "sessions.json").write_text(
            json.dumps(
                {
                    f"agent:{agent_id}:main": {
                        "sessionId": session_id,
                        "updatedAt": 1772985499284,
                        "sessionFile": str(transcript_path),
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def write_supervisor_main_packet_no_reply_transcript(self, openclaw_home, packet_text):
        self.write_supervisor_main_turns(
            openclaw_home,
            [
                (packet_text, "NO_REPLY"),
            ],
        )

    def write_supervisor_main_turns(self, openclaw_home, turns):
        sessions_dir = openclaw_home / "agents" / "supervisor_internal_main" / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = "session-supervisor-main"
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        lines = []
        for idx, (user_text, assistant_text) in enumerate(turns, start=1):
            lines.append(
                json.dumps(
                    {
                        "type": "message",
                        "id": f"main-user-{idx}",
                        "timestamp": f"2026-03-08T16:03:{25 + idx:02d}.651Z",
                        "message": {
                            "role": "user",
                            "content": [{"type": "text", "text": user_text}],
                        },
                    },
                    ensure_ascii=False,
                )
            )
            lines.append(
                json.dumps(
                    {
                        "type": "message",
                        "id": f"main-assistant-{idx}",
                        "timestamp": f"2026-03-08T16:03:{26 + idx:02d}.620Z",
                        "message": {
                            "role": "assistant",
                            "content": [{"type": "text", "text": assistant_text}],
                        },
                    },
                    ensure_ascii=False,
                )
            )
        transcript_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        sessions_path = sessions_dir / "sessions.json"
        current = {}
        if sessions_path.exists():
            current = json.loads(sessions_path.read_text(encoding="utf-8"))
        current["agent:supervisor_internal_main:main"] = {
            "sessionId": session_id,
            "updatedAt": 1772985809620,
            "sessionFile": str(transcript_path),
        }
        sessions_path.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def make_fake_openclaw(self, path, log_path):
        script = f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

log_path = Path({str(log_path)!r})
args = sys.argv[1:]
with log_path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(args, ensure_ascii=False) + "\\n")

if args[:2] == ["message", "send"]:
    message = args[args.index("--message") + 1]
    message_id = "om_ack_reconcile" if "主管已接单" in message else "om_rollup_reconcile"
    print(json.dumps({{"messageId": message_id, "payload": {{"messageId": message_id}}}}, ensure_ascii=False))
elif args[:1] == ["agent"]:
    agent_id = args[args.index("--agent") + 1]
    print(json.dumps({{"runId": f"run-{{agent_id}}", "status": "ok", "result": {{"payloads": []}}}}, ensure_ascii=False))
else:
    print(json.dumps({{"status": "ok"}}))
"""
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)

    def make_retrying_fake_openclaw(self, path, log_path, openclaw_home):
        script = f"""#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

log_path = Path({str(log_path)!r})
openclaw_home = Path({str(openclaw_home)!r})
counter_path = Path(str(log_path) + ".counter")
args = sys.argv[1:]
with log_path.open("a", encoding="utf-8") as fh:
    fh.write(json.dumps(args, ensure_ascii=False) + "\\n")

def write_jsonl(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")

def write_worker_bare_no_reply(agent_id, message):
    job_ref = re.search(r"jobRef=([^|]+)", message).group(1)
    sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_id = f"{{agent_id}}-dispatch-attempt"
    transcript_path = sessions_dir / f"{{session_id}}.jsonl"
    write_jsonl(
        transcript_path,
        [
            json.dumps(
                {{
                    "type": "message",
                    "id": "worker-user",
                    "message": {{
                        "role": "user",
                        "content": [{{"type": "text", "text": message}}],
                    }},
                }},
                ensure_ascii=False,
            ),
            json.dumps(
                {{
                    "type": "message",
                    "id": "worker-assistant",
                    "message": {{
                        "role": "assistant",
                        "content": [{{"type": "text", "text": "NO_REPLY"}}],
                    }},
                }},
                ensure_ascii=False,
            ),
        ],
    )
    (sessions_dir / "sessions.json").write_text(
        json.dumps(
            {{
                f"agent:{{agent_id}}:main": {{
                    "sessionId": session_id,
                    "updatedAt": 1772985495284,
                    "sessionFile": str(transcript_path),
                }}
            }},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return job_ref

def write_supervisor_complete_packet(job_ref, agent_id):
    sessions_dir = openclaw_home / "agents" / "supervisor_internal_main" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_id = "session-supervisor-main"
    transcript_path = sessions_dir / f"{{session_id}}.jsonl"
    packet = (
        f"[Mon 2026-03-09 00:03 GMT+8] "
        f"COMPLETE_PACKET|jobRef={{job_ref}}|from={{agent_id}}|status=completed|"
        "progressMessageId=om_progress_real|finalMessageId=om_final_real|"
        "summary=已完成阶段并可继续流程。"
    )
    write_jsonl(
        transcript_path,
        [
            json.dumps(
                {{
                    "type": "message",
                    "id": "main-user-1",
                    "message": {{
                        "role": "user",
                        "content": [{{"type": "text", "text": packet}}],
                    }},
                }},
                ensure_ascii=False,
            ),
            json.dumps(
                {{
                    "type": "message",
                    "id": "main-assistant-1",
                    "message": {{
                        "role": "assistant",
                        "content": [{{"type": "text", "text": "NO_REPLY"}}],
                    }},
                }},
                ensure_ascii=False,
            ),
        ],
    )
    sessions_path = sessions_dir / "sessions.json"
    current = {{}}
    if sessions_path.exists():
        current = json.loads(sessions_path.read_text(encoding="utf-8"))
    current["agent:supervisor_internal_main:main"] = {{
        "sessionId": session_id,
        "updatedAt": 1772985809620,
        "sessionFile": str(transcript_path),
    }}
    sessions_path.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

if args[:2] == ["message", "send"]:
    message = args[args.index("--message") + 1]
    if "主管已接单" in message:
        message_id = "om_ack_reconcile"
    elif "主管最终统一收口" in message:
        message_id = "om_rollup_reconcile"
    else:
        message_id = "om_message_reconcile"
    print(json.dumps({{"messageId": message_id, "payload": {{"messageId": message_id}}}}, ensure_ascii=False))
elif args[:1] == ["agent"]:
    agent_id = args[args.index("--agent") + 1]
    message = args[args.index("--message") + 1]
    count = int(counter_path.read_text(encoding="utf-8")) if counter_path.exists() else 0
    count += 1
    counter_path.write_text(str(count), encoding="utf-8")
    job_ref = write_worker_bare_no_reply(agent_id, message)
    if count >= 2:
        write_supervisor_complete_packet(job_ref, agent_id)
    print(json.dumps({{"runId": f"run-{{agent_id}}-{{count}}", "status": "ok", "result": {{"payloads": []}}}}, ensure_ascii=False))
else:
    print(json.dumps({{"status": "ok"}}))
"""
        path.write_text(script, encoding="utf-8")
        path.chmod(0o755)

    def test_resume_job_creates_job_from_no_reply_transcript_and_dispatches_first_worker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.write_supervisor_transcript(
                openclaw_home,
                "请为我们做一个 3 天限时促销冲刺方案，必须给出运营节奏、预算红线和风险预案。",
                message_id="om_entry_001",
            )
            self.make_fake_openclaw(fake_openclaw, fake_log)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "dispatch_reconciled"', result.stdout)
            self.assertIn('"jobStarted": true', result.stdout)
            self.assertIn('"ackVisibleSent": true', result.stdout)
            self.assertIn('"agentId": "ops_internal_main"', result.stdout)

            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")
            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn('"sourceMessageId": "om_entry_001"', self.run_registry(db_path, "get-job", "--job-ref", active.stdout.split('"jobRef": "')[1].split('"', 1)[0]).stdout)
            self.assertIn('"ackVisibleSent": true', active.stdout)
            self.assertIn('"nextAction": {', active.stdout)
            self.assertIn('"type": "wait_worker"', active.stdout)

            calls = fake_log.read_text(encoding="utf-8")
            self.assertIn("message", calls)
            self.assertIn("主管已接单", calls)
            self.assertIn("agent", calls)
            self.assertIn("ops_internal_main", calls)
            self.assertIn("TASK_DISPATCH|", calls)

    def test_resume_job_clears_waiting_worker_main_session_before_dispatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.write_supervisor_transcript(
                openclaw_home,
                "请输出完整运营与财务执行方案。",
                message_id="om_entry_worker_reset",
            )
            worker_sessions_dir = openclaw_home / "agents" / "ops_internal_main" / "sessions"
            worker_sessions_dir.mkdir(parents=True, exist_ok=True)
            worker_main_transcript = worker_sessions_dir / "ops-main-1.jsonl"
            worker_main_transcript.write_text("stale worker main transcript", encoding="utf-8")
            worker_group_transcript = worker_sessions_dir / "ops-group-1.jsonl"
            worker_group_transcript.write_text("worker group transcript should remain", encoding="utf-8")
            (worker_sessions_dir / "sessions.json").write_text(
                json.dumps(
                    {
                        "agent:ops_internal_main:main": {
                            "sessionId": "ops-main-1",
                            "sessionFile": str(worker_main_transcript),
                        },
                        "agent:ops_internal_main:feishu:group:oc_demo": {
                            "sessionId": "ops-group-1",
                            "sessionFile": str(worker_group_transcript),
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.make_fake_openclaw(fake_openclaw, fake_log)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            sessions_payload = json.loads((worker_sessions_dir / "sessions.json").read_text(encoding="utf-8"))
            self.assertNotIn("agent:ops_internal_main:main", sessions_payload)
            self.assertIn("agent:ops_internal_main:feishu:group:oc_demo", sessions_payload)
            self.assertFalse(worker_main_transcript.exists())
            self.assertTrue(worker_group_transcript.exists())

    def test_resume_job_redispatches_when_worker_main_latest_turn_is_no_reply(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_retry_seed",
                "--title",
                "worker no reply retry",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_worker_main_no_reply_transcript(openclaw_home, "ops_internal_main", job_ref)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "dispatch_reconciled"', result.stdout)
            self.assertIn('"jobStarted": false', result.stdout)
            self.assertIn('"workerMainSessionReset"', result.stdout)
            calls = fake_log.read_text(encoding="utf-8")
            self.assertGreaterEqual(calls.count("TASK_DISPATCH|"), 1)
            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM job_events WHERE job_ref = ? AND event_type = 'worker_dispatched'",
                    (job_ref,),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(count, 2)

    def test_resume_job_retries_worker_no_reply_within_same_run_until_callback_arrives(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_retrying_fake_openclaw(fake_openclaw, fake_log, openclaw_home)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_worker_retry_loop",
                "--title",
                "worker no reply loop recovery",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_worker_main_no_reply_transcript(openclaw_home, "ops_internal_main", job_ref)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "rollup_reconciled"', result.stdout)
            calls = fake_log.read_text(encoding="utf-8")
            self.assertGreaterEqual(calls.count('"agent"'), 2)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"status": "done"', job.stdout)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)

    def test_resume_job_consumes_hidden_main_completion_packet_and_dispatches_next_stage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_hidden_main_valid",
                "--title",
                "hidden main callback retry",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_supervisor_main_packet_no_reply_transcript(
                openclaw_home,
                (
                    f"[Mon 2026-03-09 00:03 GMT+8] "
                    f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                    "progressMessageId=om_progress_real|finalMessageId=om_final_real|"
                    "summary=已完成运营阶段并可进入财务校验。"
                ),
            )

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "dispatch_reconciled"', result.stdout)
            self.assertIn('"agentId": "finance_internal_main"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"ops_internal_main": {', job.stdout)
            self.assertIn('"status": "done"', job.stdout)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)
            self.assertIn('"waitingForAgentId": "finance_internal_main"', job.stdout)
            self.assertIn('"type": "wait_worker"', job.stdout)
            calls = fake_log.read_text(encoding="utf-8")
            self.assertIn("finance_internal_main", calls)
            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM job_events WHERE job_ref = ? AND event_type = 'worker_completed'",
                    (job_ref,),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(count, 1)

    def test_resume_job_redispatches_when_hidden_main_completion_packet_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_hidden_main_invalid",
                "--title",
                "hidden main invalid callback retry",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_supervisor_main_packet_no_reply_transcript(
                openclaw_home,
                (
                    f"[Mon 2026-03-09 00:03 GMT+8] "
                    f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=failed|"
                    "progressMessageId=pending|finalMessageId=pending|summary=processing"
                ),
            )
            self.write_worker_main_no_reply_transcript(openclaw_home, "ops_internal_main", job_ref)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "dispatch_reconciled"', result.stdout)
            self.assertIn('"agentId": "ops_internal_main"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertNotIn('"status": "done"', job.stdout)
            self.assertIn('"waitingForAgentId": "ops_internal_main"', job.stdout)
            calls = fake_log.read_text(encoding="utf-8")
            self.assertIn("ops_internal_main", calls)
            conn = sqlite3.connect(db_path)
            try:
                count = conn.execute(
                    "SELECT COUNT(*) FROM job_events WHERE job_ref = ? AND event_type = 'worker_completed'",
                    (job_ref,),
                ).fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(count, 0)

    def test_resume_job_prefers_latest_valid_hidden_main_completion_packet_even_if_newer_packet_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_hidden_main_mixed",
                "--title",
                "hidden main mixed callbacks",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_supervisor_main_turns(
                openclaw_home,
                [
                    (
                        (
                            f"[Mon 2026-03-09 00:03 GMT+8] "
                            f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                            "progressMessageId=om_progress_real|finalMessageId=om_final_real|"
                            "summary=已完成运营阶段并可进入财务校验。"
                        ),
                        "[[reply_to_current]] 收到，但没有写入 registry。",
                    ),
                    (
                        (
                            f"[Mon 2026-03-09 00:04 GMT+8] "
                            f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                            "progressMessageId=<pending_from_tool_1>|"
                            "finalMessageId=msg_final_placeholder|summary=processing"
                        ),
                        "ANNOUNCE_SKIP",
                    ),
                ],
            )

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"agentId": "finance_internal_main"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)
            self.assertIn('"waitingForAgentId": "finance_internal_main"', job.stdout)

    def test_resume_job_rejects_placeholder_like_message_ids_in_hidden_main_completion_packet(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_hidden_main_placeholder",
                "--title",
                "hidden main placeholder callback",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_supervisor_main_turns(
                openclaw_home,
                [
                    (
                        (
                            f"[Mon 2026-03-09 00:03 GMT+8] "
                            f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                            "progressMessageId=om_progress_real|finalMessageId=om_final_real|"
                            "summary=已完成运营阶段并可进入财务校验。"
                        ),
                        "NO_REPLY",
                    ),
                    (
                        (
                            f"[Mon 2026-03-09 00:04 GMT+8] "
                            f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                            "progressMessageId=<pending_from_tool_1>|"
                            "finalMessageId=msg_final_placeholder|"
                            "summary=已完成运营阶段并可进入财务校验。"
                        ),
                        "NO_REPLY",
                    ),
                ],
            )

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"agentId": "finance_internal_main"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)

    def test_resume_job_recovers_real_message_ids_from_worker_transcript_when_hidden_main_packet_is_placeholder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_hidden_main_transcript_recovery",
                "--title",
                "hidden main transcript recovery",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [
                            {"agentId": "ops_internal_main"},
                            {"agentId": "finance_internal_main"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops-existing",
                "--dispatch-status",
                "accepted",
            )
            self.write_worker_main_completed_transcript(openclaw_home, "ops_internal_main", job_ref)
            self.write_supervisor_main_turns(
                openclaw_home,
                [
                    (
                        (
                            f"[Mon 2026-03-09 00:03 GMT+8] "
                            f"COMPLETE_PACKET|jobRef={job_ref}|from=ops_internal_main|status=completed|"
                            "progressMessageId=<pending_from_tool_1>|"
                            "finalMessageId=msg_final_placeholder|"
                            "summary=已完成运营阶段并可进入财务校验。"
                        ),
                        "NO_REPLY",
                    ),
                ],
            )

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"agentId": "finance_internal_main"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)
            self.assertIn('"waitingForAgentId": "finance_internal_main"', job.stdout)

    def test_resume_job_ignores_warmup_no_reply_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.write_supervisor_transcript(openclaw_home, "WARMUP", message_id="om_warmup")
            self.make_fake_openclaw(fake_openclaw, fake_log)

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "resume-job",
                "--stale-seconds",
                "180",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "no_pending_inbound_message"', result.stdout)
            active = self.run_registry(db_path, "get-active", "--group-peer-id", "oc_demo")
            self.assertIn('"active": null', active.stdout)
            self.assertFalse(fake_log.exists() and fake_log.read_text(encoding="utf-8").strip())

    def test_reconcile_rollup_sends_visible_message_and_closes_job(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            db_path = tmp_path / "team_jobs.db"
            manifest_path = tmp_path / "manifest.json"
            openclaw_home = tmp_path / "openclaw-home"
            fake_openclaw = tmp_path / "openclaw"
            fake_log = tmp_path / "openclaw.log"

            self.run_registry(db_path, "init-db")
            self.write_manifest(manifest_path, db_path)
            self.make_fake_openclaw(fake_openclaw, fake_log)

            started = self.run_registry(
                db_path,
                "start-job-with-workflow",
                "--group-peer-id",
                "oc_demo",
                "--requested-by",
                "SeaWorld",
                "--source-message-id",
                "om_rollup_entry",
                "--title",
                "V5.1 rollup reconcile",
                "--request-text",
                "请生成完整方案。",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "ack",
                "--message-id",
                "om_ack_existing",
            )
            self.run_registry(
                db_path,
                "mark-dispatch",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )
            self.run_registry(
                db_path,
                "mark-worker-complete",
                "--job-ref",
                job_ref,
                "--agent-id",
                "ops_internal_main",
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

            result = self.run_reconcile(
                manifest_path,
                "internal_main",
                openclaw_home,
                fake_openclaw,
                "reconcile-rollup",
                "--job-ref",
                job_ref,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('"status": "rollup_reconciled"', result.stdout)
            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"status": "done"', details.stdout)
            self.assertIn('"rollupVisibleSent": true', details.stdout)
            calls = fake_log.read_text(encoding="utf-8")
            self.assertIn("主管最终统一收口", calls)


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
        self.assertIn("v431_single_group_hygiene.py", content)
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

        self.assertIn("v431_single_group_hygiene.py", content)
        self.assertIn("WARMUP", content)
        self.assertIn("v431_single_group_canary.py", content)
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
                            f"agent:{agent_id}:main": {
                                "sessionId": f"{session_id}-main",
                                "sessionFile": str(session_dir / f"{session_id}-main.jsonl"),
                            },
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
                (session_dir / f"{session_id}-main.jsonl").write_text("worker main transcript", encoding="utf-8")

            result = self.run_hygiene(home, "--include-workers", "--delete-transcripts", "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["includeWorkers"], True)
            statuses = [item["status"] for item in payload["results"] if item["agentId"] in {"ops_agent", "finance_agent"}]
            self.assertTrue(all(status == "would_remove" for status in statuses))
            self.assertTrue((home / "agents" / "ops_agent" / "sessions" / "ops-1.jsonl").exists())
            self.assertTrue((home / "agents" / "ops_agent" / "sessions" / "ops-1-main.jsonl").exists())
            self.assertTrue((home / "agents" / "finance_agent" / "sessions" / "fin-1.jsonl").exists())
            self.assertTrue((home / "agents" / "finance_agent" / "sessions" / "fin-1-main.jsonl").exists())
            worker_keys = {(item["agentId"], item["sessionKey"]) for item in payload["results"]}
            self.assertIn(("ops_agent", "agent:ops_agent:main"), worker_keys)
            self.assertIn(("finance_agent", "agent:finance_agent:main"), worker_keys)

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
                str(V5_CANARY_SCRIPT),
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
        self.assertIn("__RECONCILE_SCRIPT__", systemd_service)
        self.assertIn("__MANIFEST_PATH__", systemd_service)
        self.assertIn("v5-team-__TEAM_KEY__.service", systemd_timer)
        self.assertIn("bot.molt.v5-team-__TEAM_KEY__", launchd)
        self.assertIn("__RECONCILE_SCRIPT__", launchd)
        self.assertIn("__MANIFEST_PATH__", launchd)
        self.assertIn("__OPENCLAW_HOME__", launchd)

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


class V51DocumentationTests(unittest.TestCase):
    def test_v51_design_and_plan_docs_exist(self):
        self.assertTrue(V5_1_DESIGN_DOC.exists())
        self.assertTrue(V5_1_PLAN_DOC.exists())

        design = V5_1_DESIGN_DOC.read_text(encoding="utf-8")
        plan = V5_1_PLAN_DOC.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", design)
        self.assertIn("Deterministic Orchestrator", design)
        self.assertIn("LLM 负责内容，代码负责流程", design)
        self.assertIn("start-job-with-workflow", plan)
        self.assertIn("get-next-action", plan)

    def test_v5_docs_and_templates_reference_v51_hardening_control_plane(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V5_DOC.read_text(encoding="utf-8")
        v5_input = V5_INPUT_TEMPLATE.read_text(encoding="utf-8")
        v5_snapshot = V5_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        for content in (readme, skill, v5_doc, v5_input, v5_snapshot):
            self.assertIn("V5.1 Hardening", content)
            self.assertIn("start-job-with-workflow", content)
            self.assertIn("get-next-action", content)
            self.assertIn("build-dispatch-payload", content)
            self.assertIn("build-visible-ack", content)
            self.assertIn("record-visible-message", content)
            self.assertIn("v51_team_orchestrator_reconcile.py", content)
            self.assertIn("resume-job", content)

    def test_v5_skill_documents_supervisor_no_reply_hygiene_repair(self):
        skill = SKILL_FILE.read_text(encoding="utf-8")
        checklist = VERIFICATION_CHECKLIST.read_text(encoding="utf-8")

        self.assertIn("主管群 session", skill)
        self.assertIn("裸 NO_REPLY", skill)
        self.assertIn("v51_team_orchestrator_hygiene.py", skill)
        self.assertIn("v51_team_orchestrator_reconcile.py", skill)
        self.assertIn("hygiene", checklist)


class V5TemplateTests(unittest.TestCase):
    def test_v5_input_template_exists_and_mentions_teams(self):
        content = V5_INPUT_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('"teams"', content)
        self.assertIn('"supervisor"', content)
        self.assertIn('"workers"', content)
        self.assertIn('"description"', content)
        self.assertIn('"identity"', content)
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
        self.assertIn("description", content)
        self.assertIn("identity", content)
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
        self.assertIn("v51_team_orchestrator_reconcile.py", content)
        self.assertIn("resume-job", content)

    def test_v5_fixed_role_template_exists_and_documents_role_combinations(self):
        content = V5_FIXED_ROLE_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('"accounts"', content)
        self.assertIn('"teams"', content)
        self.assertIn('"accountId": "aoteman"', content)
        self.assertIn('"accountId": "xiaolongxia"', content)
        self.assertIn('"accountId": "yiran_yibao"', content)
        self.assertIn('"roleKey": "supervisor"', content)
        self.assertIn('"roleKey": "ops"', content)
        self.assertIn('"roleKey": "finance"', content)
        self.assertIn('"teamKey": "full_team_demo"', content)
        self.assertIn('"teamKey": "ops_only_demo"', content)
        self.assertIn('"teamKey": "finance_only_demo"', content)
        self.assertIn('"entryAccountId": "aoteman"', content)

    def test_v5_fixed_role_standard_is_documented_in_readme_skill_and_v5_doc(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V5_DOC.read_text(encoding="utf-8")
        deployment_inputs = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml"
        ).read_text(encoding="utf-8")

        for content in (readme, skill, v5_doc):
            self.assertIn("bot 复用，role 固定", content)
            self.assertIn("同一个 bot 可以跨很多群复用", content)
            self.assertIn("每个群的角色组合可以不同", content)
            self.assertIn("input-template-v5-fixed-role-multi-group.json", content)

        self.assertIn("recommended_v5_fixed_role_accounts", deployment_inputs)
        self.assertIn('supervisor: "aoteman"', deployment_inputs)
        self.assertIn('ops: "xiaolongxia"', deployment_inputs)
        self.assertIn('finance: "yiran_yibao"', deployment_inputs)


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
        self.assertIn("v51_team_orchestrator_reconcile.py", readme)
        self.assertIn("v51_team_orchestrator_reconcile.py", skill)
        self.assertIn("hidden_main_session_key", deployment_inputs)
        self.assertIn("v5_team_runtime", deployment_inputs)
        self.assertIn("runtime manifest", readme)

    def test_readme_includes_bilingual_default_expert_catalog_with_30_experts(self):
        content = README_FILE.read_text(encoding="utf-8")

        match = re.search(
            r"## 默认专家库 / Default Expert Catalog\n(?P<section>.*?)(?:\n## |\Z)",
            content,
            flags=re.S,
        )
        self.assertIsNotNone(match)
        section = match.group("section")

        for heading in (
            "### 管理与协调 / Management & Orchestration",
            "### 增长与营销 / Growth & Marketing",
            "### 销售与商务 / Sales & Business",
            "### 财务与风控 / Finance & Risk",
            "### 产品与项目 / Product & Delivery",
            "### 运营与履约 / Operations & Fulfillment",
            "### 客户成功与服务 / Customer Success & Service",
            "### 数据与分析 / Data & Analytics",
            "### 人力与组织 / HR & Organization",
            "### 法务与合规 / Legal & Compliance",
        ):
            self.assertIn(heading, section)

        expert_lines = [
            line for line in section.splitlines()
            if line.strip().startswith("- `") and "`：" in line
        ]
        self.assertEqual(len(expert_lines), 30)

        for expert_name in (
            "TeamOrchestrator",
            "GrowthStrategist",
            "SalesCloser",
            "FinancialController",
            "ProductLead",
            "FulfillmentManager",
            "CustomerSuccessLead",
            "DataAnalyst",
            "TalentPartner",
            "ComplianceCounsel",
        ):
            self.assertIn(f"`{expert_name}`", section)

    def test_customer_first_use_docs_exist_and_are_linked_in_readme(self):
        for path in (
            V5_1_QUICKSTART_DOC,
            CUSTOMER_FIRST_USE_CHECKLIST,
            CUSTOMER_FIRST_USE_PROMPT,
            CUSTOMER_FIRST_USE_EXAMPLE,
        ):
            self.assertTrue(path.exists(), path.name)

        readme = README_FILE.read_text(encoding="utf-8")
        self.assertIn("V5.1-新机器快速启动-SOP.md", readme)
        self.assertIn("客户首次使用信息清单.md", readme)
        self.assertIn("客户首次使用-Codex提示词.md", readme)
        self.assertIn("客户首次使用真实案例.md", readme)

    def test_customer_first_use_docs_cover_collection_prompt_and_real_case(self):
        quickstart = V5_1_QUICKSTART_DOC.read_text(encoding="utf-8")
        checklist = CUSTOMER_FIRST_USE_CHECKLIST.read_text(encoding="utf-8")
        prompt = CUSTOMER_FIRST_USE_PROMPT.read_text(encoding="utf-8")
        example = CUSTOMER_FIRST_USE_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("V5 Team Orchestrator / V5.1 Hardening", quickstart)
        self.assertIn("curl -fsSL https://openclaw.ai/install.sh | bash", quickstart)
        self.assertIn("openclaw onboard --install-daemon", quickstart)
        self.assertIn("openclaw plugins install @openclaw/feishu", quickstart)
        self.assertIn("customer-v51-prod-input.json", quickstart)
        self.assertIn("v51_team_orchestrator_hygiene.py", quickstart)
        self.assertIn("v51_team_orchestrator_reconcile.py", quickstart)
        self.assertIn("主管最终统一收口", quickstart)

        self.assertIn("必须先收集", checklist)
        self.assertIn("appId", checklist)
        self.assertIn("appSecret", checklist)
        self.assertIn("peerId", checklist)
        self.assertIn("accountId 是我们自己定义的键名", checklist)
        self.assertIn("填写到", checklist)
        self.assertIn("input-template-v5-fixed-role-multi-group.json", checklist)

        self.assertIn("请使用 openclaw-feishu-multi-agent-deploy skill", prompt)
        self.assertIn("先备份", prompt)
        self.assertIn("openclaw config validate", prompt)
        self.assertIn("openclaw gateway restart", prompt)
        self.assertIn("一次配置 1 个群或多个群", prompt)

        self.assertIn("internal_main", example)
        self.assertIn("external_main", example)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", example)
        self.assertIn("oc_7121d87961740dbd72bd8e50e48ba5e3", example)
        self.assertIn("aoteman", example)
        self.assertIn("xiaolongxia", example)
        self.assertIn("yiran_yibao", example)
        self.assertIn("把下面这些真实值替换成客户自己的值", example)


if __name__ == "__main__":
    unittest.main()
