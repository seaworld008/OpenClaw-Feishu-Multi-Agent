import json
import importlib.util
import re
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTER_SKILL_ROOT = REPO_ROOT.parent
README_FILE = REPO_ROOT / "README.md"
CHANGELOG_FILE = REPO_ROOT / "CHANGELOG.md"
VERSION_FILE = REPO_ROOT / "VERSION"
SKILL_FILE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/SKILL.md"
ROOT_SKILL_FILE = OUTER_SKILL_ROOT / "SKILL.md"
ROOT_CODEX_PROMPT = OUTER_SKILL_ROOT / "references/codex-prompt-templates.md"
ROOT_NOTES_FILE = OUTER_SKILL_ROOT / "references/openclaw-feishu-multi-agent-notes.md"
ROOT_PREREQUISITES_FILE = OUTER_SKILL_ROOT / "references/prerequisites-checklist.md"
ROOT_ROLLOUT_PLAYBOOK = OUTER_SKILL_ROOT / "references/rollout-and-upgrade-playbook.md"
ROOT_VERIFICATION_TEMPLATE = OUTER_SKILL_ROOT / "templates/verification-checklist.md"
ROOT_LEGACY_BUILD_SCRIPT = OUTER_SKILL_ROOT / ("scripts/" + "build" + "_openclaw_feishu_" + "snippets.py")
INNER_NOTES_FILE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/openclaw-feishu-multi-agent-notes.md"
TEST_FILE = Path(__file__).resolve()
BUILD_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py"
JOB_REGISTRY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py"
SESSION_HYGIENE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py"
V51_RUNTIME_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py"
V51_CANARY_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_canary.py"
V51_RECONCILE_SCRIPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_reconcile.py"
V51_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-design.md"
V51_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-08-v5-1-hardening-implementation.md"
ROLE_CATALOG_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-09-role-catalog-canonicalization-design.md"
ROLE_CATALOG_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-09-role-catalog-canonicalization-implementation.md"
PRUNING_DESIGN_DOC = REPO_ROOT / "docs/plans/2026-03-09-skill-mainline-pruning-design.md"
PRUNING_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-09-skill-mainline-pruning-implementation.md"
ROOT_ALIGNMENT_PLAN_DOC = REPO_ROOT / "docs/plans/2026-03-09-root-skill-mainline-alignment.md"
V51_INPUT_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-team-orchestrator.json"
V51_FIXED_ROLE_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-fixed-role-multi-group.json"
V51_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md"
V51_CONFIG_SNAPSHOT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc"
V51_QUICKSTART_DOC = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md"
CUSTOMER_FIRST_USE_CHECKLIST = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md"
CUSTOMER_FIRST_USE_PROMPT = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md"
CUSTOMER_FIRST_USE_EXAMPLE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md"
SOURCE_CROSS_VALIDATION_20260305 = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-05.md"
V51_SYSTEMD_SERVICE_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v51-team-watchdog.service"
V51_SYSTEMD_TIMER_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v51-team-watchdog.timer"
V51_LAUNCHD_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v51-team-watchdog.plist"
VERIFICATION_CHECKLIST = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md"
WSL_CONF_TEMPLATE = REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/windows/wsl.conf.example"

REMOVED_V4_ASSETS = [
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-legacy-chat-feishu.json",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-07-v4-3-1.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-07-platforms.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.service",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.timer",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/v4-3-job-registry.example.sql",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py",
    REPO_ROOT / "docs/plans/2026-03-07-v4-3-1-cross-platform-compatibility.md",
    REPO_ROOT / "docs/plans/2026-03-07-v4-3-1-single-group-production-stability.md",
    REPO_ROOT / "docs/plans/2026-03-07-v4-3-1-solidify-success.md",
    REPO_ROOT / "docs/plans/2026-03-08-script-namespace-unification-design.md",
    REPO_ROOT / "docs/plans/2026-03-08-script-namespace-unification-implementation.md",
    REPO_ROOT / "docs/plans/2026-03-08-default-expert-catalog-design.md",
    REPO_ROOT / "docs/plans/2026-03-08-default-expert-catalog-implementation.md",
    REPO_ROOT / "docs/plans/2026-03-08-v5-fixed-role-multi-group-design.md",
    REPO_ROOT / "docs/plans/2026-03-08-v5-fixed-role-multi-group-implementation.md",
    REPO_ROOT / "docs/plans/2026-03-08-客户首次使用交付包设计.md",
    REPO_ROOT / "docs/plans/2026-03-08-客户首次使用交付包实施计划.md",
]

REMOVED_V3_ASSETS = [
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v3.1.md",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template.json",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/input-template-plugin.json",
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/v31_cross_group_canary.py",
]

REMOVED_ROOT_LEGACY_ASSETS = [
    OUTER_SKILL_ROOT / "references/input-template-legacy-chat-feishu.json",
]


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
        INNER_NOTES_FILE,
        BUILD_SCRIPT,
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md",
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v51-team-orchestrator.example.jsonc",
        V51_DOC,
        REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md",
        CUSTOMER_FIRST_USE_CHECKLIST,
        CUSTOMER_FIRST_USE_PROMPT,
        CUSTOMER_FIRST_USE_EXAMPLE,
        V51_DESIGN_DOC,
        V51_PLAN_DOC,
        PRUNING_DESIGN_DOC,
        PRUNING_PLAN_DOC,
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
            V51_DOC: [
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


def load_registry_module():
    spec = importlib.util.spec_from_file_location(JOB_REGISTRY_SCRIPT.stem, JOB_REGISTRY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_root_bridge_build_module():
    spec = importlib.util.spec_from_file_location(ROOT_LEGACY_BUILD_SCRIPT.stem, ROOT_LEGACY_BUILD_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


WORKFLOW_PARTICIPANT_DEFAULTS = {
    "ops_internal_main": {
        "accountId": "xiaolongxia",
        "role": "运营执行",
        "visibleLabel": "运营",
    },
    "finance_internal_main": {
        "accountId": "yiran_yibao",
        "role": "财务执行",
        "visibleLabel": "财务",
    },
    "legal_internal_main": {
        "accountId": "falv",
        "role": "法务执行",
        "visibleLabel": "法务",
    },
}


def workflow_payload_json(*agent_ids):
    return json.dumps(
        {
            "mode": "serial",
            "stages": [{"agentId": agent_id} for agent_id in agent_ids],
        },
        ensure_ascii=False,
    )


def workflow_participants_json(*participants):
    normalized = []
    for participant in participants:
        if isinstance(participant, str):
            agent_id = participant
            normalized.append(
                {
                    "agentId": agent_id,
                    **WORKFLOW_PARTICIPANT_DEFAULTS[agent_id],
                }
            )
            continue

        item = dict(participant)
        agent_id = str(item["agentId"])
        defaults = WORKFLOW_PARTICIPANT_DEFAULTS.get(agent_id, {})
        normalized.append(
            {
                "agentId": agent_id,
                **defaults,
                **item,
            }
        )
    return json.dumps(normalized, ensure_ascii=False)


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

    def minimal_v51_input(self):
        return {
            "mode": "plugin",
            "accounts": [
                {
                    "accountId": "main",
                    "appId": "cli_xxx",
                    "appSecret": "secret",
                    "encryptKey": "",
                    "verificationToken": "",
                },
                {
                    "accountId": "ops",
                    "appId": "cli_ops",
                    "appSecret": "secret_ops",
                },
            ],
            "teams": [
                {
                    "teamKey": "demo_team",
                    "group": {
                        "peerId": "oc_group_sales",
                        "entryAccountId": "main",
                        "requireMention": True,
                    },
                    "supervisor": {
                        "agentId": "supervisor_demo_team",
                        "accountId": "main",
                        "role": "主管总控",
                        "visibleLabel": "主管",
                        "systemPrompt": "supervisor prompt",
                    },
                    "workers": [
                        {
                            "agentId": "ops_demo_team",
                            "accountId": "ops",
                            "role": "运营专家",
                            "visibleLabel": "运营",
                            "visibility": "visible",
                            "systemPrompt": "ops prompt",
                        }
                    ],
                    "workflow": {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_demo_team"}],
                    },
                }
            ],
        }

    def test_legacy_routes_input_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "only accepts accounts \\+ roleCatalog \\+ teams"):
            self.module.build_plugin_patch(self.base_input())

    def test_string_agents_do_not_override_generated_team_agents(self):
        data = self.minimal_v51_input()
        data["agents"] = ["sales_agent", "ops_agent"]

        patch = self.module.build_plugin_patch(data)

        self.assertEqual(
            [agent["id"] for agent in patch["agents"]["list"]],
            ["supervisor_demo_team", "ops_demo_team"],
        )

    def test_agent_objects_are_rejected_for_v51_inputs(self):
        data = self.minimal_v51_input()
        data["agents"] = [
            {"id": "sales_agent", "systemPrompt": "sales prompt"},
            {"id": "ops_agent", "systemPrompt": "ops prompt"},
        ]

        with self.assertRaisesRegex(ValueError, "must not provide agents.list"):
            self.module.build_plugin_patch(data)

    def test_blank_encrypt_fields_are_omitted(self):
        data = self.minimal_v51_input()

        patch = self.module.build_plugin_patch(data)
        account_cfg = patch["channels"]["feishu"]["accounts"]["main"]

        self.assertEqual(account_cfg["appId"], "cli_xxx")
        self.assertEqual(account_cfg["appSecret"], "secret")
        self.assertNotIn("encryptKey", account_cfg)
        self.assertNotIn("verificationToken", account_cfg)

    def test_v51_inline_team_input_requires_explicit_visible_label(self):
        data = self.minimal_v51_input()
        data["teams"][0]["workers"][0].pop("visibleLabel")

        with self.assertRaisesRegex(ValueError, "visibleLabel is required"):
            self.module.build_plugin_patch(data)

    def test_builder_source_does_not_keep_legacy_route_validation_helpers(self):
        content = BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("def route_sort_key(", content)
        self.assertNotIn("def validate_routes(", content)


class RootBridgeBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_root_bridge_build_module()

    def test_rewrite_bridge_args_rejects_removed_legacy_input_alias(self):
        with self.assertRaisesRegex(ValueError, "Legacy input alias removed"):
            self.module.rewrite_bridge_args(
                ["--input", "references/input-template.json", "--out", "/tmp/custom-out"]
            )

    def test_rewrite_bridge_args_requires_explicit_input_template(self):
        with self.assertRaisesRegex(ValueError, "Explicit --input is required"):
            self.module.rewrite_bridge_args([])

    def test_rewrite_bridge_args_rejects_removed_plugin_alias(self):
        with self.assertRaisesRegex(ValueError, "Legacy input alias removed"):
            self.module.rewrite_bridge_args(
                ["--input", "references/input-template-plugin.json", "--out", "/tmp/custom-out"]
            )

    def test_rewrite_bridge_args_rejects_removed_legacy_chat_feishu_alias(self):
        with self.assertRaisesRegex(ValueError, "Legacy input alias removed"):
            self.module.rewrite_bridge_args(
                ["--input", "references/input-template-legacy-chat-feishu.json", "--out", "/tmp/custom-out"]
            )

    def test_rewrite_bridge_args_preserves_explicit_custom_paths(self):
        rewritten = self.module.rewrite_bridge_args(
            ["--input", "/tmp/custom-input.json", "--out", "/tmp/custom-out"]
        )

        self.assertEqual(
            rewritten,
            ["--input", "/tmp/custom-input.json", "--out", "/tmp/custom-out"],
        )

    def test_root_bridge_source_does_not_keep_default_input_injection(self):
        content = ROOT_LEGACY_BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("DEFAULT_INPUT_TEMPLATE", content)
        self.assertNotIn('args.extend([option, str(preferred_value)])', content)

    def test_root_bridge_script_rejects_removed_legacy_input_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT_LEGACY_BUILD_SCRIPT),
                    "--input",
                    "references/input-template.json",
                    "--out",
                    tmpdir,
                ],
                cwd=OUTER_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Legacy input alias removed", result.stderr or result.stdout)

    def test_root_bridge_script_rejects_removed_plugin_alias(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT_LEGACY_BUILD_SCRIPT),
                    "--input",
                    "references/input-template-plugin.json",
                    "--out",
                    tmpdir,
                ],
                cwd=OUTER_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Legacy input alias removed", result.stderr or result.stdout)

    def test_root_bridge_script_requires_explicit_input_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT_LEGACY_BUILD_SCRIPT),
                    "--out",
                    tmpdir,
                ],
                cwd=OUTER_SKILL_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Explicit --input is required", result.stderr or result.stdout)


class BuildSnippetV51Tests(unittest.TestCase):
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
                        "visibleLabel": "主管",
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
                            "visibleLabel": "运营",
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
                            "visibleLabel": "财务",
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

    def team_input_with_role_catalog(self):
        return {
            "mode": "plugin",
            "connectionMode": "websocket",
            "defaultAccount": "aoteman",
            "messages": {
                "groupChat": {
                    "mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"],
                }
            },
            "accounts": [
                {
                    "accountId": "aoteman",
                    "appId": "cli_supervisor",
                    "appSecret": "secret_supervisor",
                },
                {
                    "accountId": "xiaolongxia",
                    "appId": "cli_ops",
                    "appSecret": "secret_ops",
                },
                {
                    "accountId": "yiran_yibao",
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
            "roleCatalog": {
                "supervisor_default": {
                    "kind": "supervisor",
                    "accountId": "aoteman",
                    "name": "奥特曼",
                    "role": "主管总控",
                    "visibleLabel": "主管",
                    "description": "负责任务受理、拆解、调度与统一收口。",
                    "responsibility": "接单、拆解、调度、统一收口",
                    "identity": {
                        "name": "奥特曼总控",
                        "theme": "steady orchestrator",
                        "emoji": "🧭",
                    },
                    "mentionPatterns": ["@奥特曼", "奥特曼", "主管机器人"],
                    "systemPrompt": "catalog supervisor prompt",
                },
                "ops_default": {
                    "kind": "worker",
                    "accountId": "xiaolongxia",
                    "name": "小龙虾找妈妈",
                    "role": "运营专家",
                    "visibleLabel": "运营",
                    "description": "负责活动打法、节奏设计和执行推进。",
                    "responsibility": "活动打法、节奏、执行动作",
                    "identity": {
                        "theme": "growth operator",
                        "emoji": "📈",
                    },
                    "visibility": "visible",
                    "systemPrompt": "catalog ops prompt",
                },
                "finance_default": {
                    "kind": "worker",
                    "accountId": "yiran_yibao",
                    "name": "易燃易爆",
                    "role": "财务专家",
                    "visibleLabel": "财务",
                    "description": "负责预算、毛利、ROI 与风险控制。",
                    "responsibility": "预算、毛利、ROI 与风险",
                    "identity": {
                        "theme": "financial controller",
                        "emoji": "💹",
                    },
                    "visibility": "visible",
                    "systemPrompt": "catalog finance prompt",
                },
            },
            "teams": [
                {
                    "teamKey": "market_sz",
                    "displayName": "深圳团队",
                    "group": {
                        "peerId": "oc_team_sz",
                        "entryAccountId": "aoteman",
                        "requireMention": True,
                    },
                    "supervisor": {
                        "profileId": "supervisor_default",
                        "agentId": "supervisor_market_sz",
                    },
                    "workers": [
                        {
                            "profileId": "ops_default",
                            "agentId": "ops_market_sz",
                        },
                        {
                            "profileId": "finance_default",
                            "agentId": "finance_market_sz",
                            "visibleLabel": "财审",
                            "systemPrompt": "team finance override prompt",
                            "identity": {
                                "theme": "client-facing finance",
                            },
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

    def test_v51_team_input_generates_team_scoped_agents_and_bindings(self):
        patch = self.module.build_plugin_patch(self.team_input())

        agents = patch["agents"]["list"]
        bindings = patch["bindings"]

        self.assertEqual([agent["id"] for agent in agents], ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"])
        self.assertEqual([binding["agentId"] for binding in bindings], ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"])
        self.assertTrue(all(binding["match"]["peer"]["id"] == "oc_team_sz" for binding in bindings))
        self.assertEqual(agents[0]["workspace"], "~/.openclaw/teams/market_sz/workspaces/supervisor")
        self.assertEqual(agents[1]["workspace"], "~/.openclaw/teams/market_sz/workspaces/ops")
        self.assertEqual(agents[2]["workspace"], "~/.openclaw/teams/market_sz/workspaces/finance")

    def test_v51_team_input_generates_group_prompts_per_account(self):
        patch = self.module.build_plugin_patch(self.team_input())
        accounts = patch["channels"]["feishu"]["accounts"]

        self.assertEqual(accounts["marketing-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "supervisor prompt")
        self.assertEqual(accounts["ops-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "ops prompt")
        self.assertEqual(accounts["finance-bot"]["groups"]["oc_team_sz"]["systemPrompt"], "finance prompt")

    def test_v51_team_input_builds_agent_to_agent_allowlist_from_generated_agents(self):
        patch = self.module.build_plugin_patch(self.team_input())

        self.assertEqual(
            patch["tools"]["agentToAgent"]["allow"],
            ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"],
        )

    def test_v51_team_input_generates_group_require_mention_and_messages_defaults(self):
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

    def test_v51_team_input_preserves_identity_and_manifest_description(self):
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
        manifest = self.module.build_v51_runtime_manifest(data)

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

    def test_v51_team_input_builds_team_runtime_manifest(self):
        manifest = self.module.build_v51_runtime_manifest(self.team_input())

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

    def test_v51_team_input_supports_role_catalog_profiles_and_overrides(self):
        patch = self.module.build_plugin_patch(self.team_input_with_role_catalog())
        manifest = self.module.build_v51_runtime_manifest(self.team_input_with_role_catalog())

        agents = patch["agents"]["list"]
        self.assertEqual([agent["id"] for agent in agents], ["supervisor_market_sz", "ops_market_sz", "finance_market_sz"])
        self.assertEqual(agents[0]["name"], "奥特曼")
        self.assertEqual(agents[1]["name"], "小龙虾找妈妈")
        self.assertEqual(agents[2]["name"], "易燃易爆")
        self.assertEqual(
            patch["channels"]["feishu"]["accounts"]["aoteman"]["groups"]["oc_team_sz"]["systemPrompt"],
            "catalog supervisor prompt",
        )
        self.assertEqual(
            patch["channels"]["feishu"]["accounts"]["xiaolongxia"]["groups"]["oc_team_sz"]["systemPrompt"],
            "catalog ops prompt",
        )
        self.assertEqual(
            patch["channels"]["feishu"]["accounts"]["yiran_yibao"]["groups"]["oc_team_sz"]["systemPrompt"],
            "team finance override prompt",
        )
        self.assertEqual(manifest["teams"][0]["supervisor"]["profileId"], "supervisor_default")
        self.assertEqual(manifest["teams"][0]["supervisor"]["visibleLabel"], "主管")
        self.assertEqual(manifest["teams"][0]["workers"][0]["profileId"], "ops_default")
        self.assertEqual(manifest["teams"][0]["workers"][0]["visibleLabel"], "运营")
        self.assertEqual(manifest["teams"][0]["workers"][1]["profileId"], "finance_default")
        self.assertEqual(manifest["teams"][0]["workers"][1]["visibleLabel"], "财审")
        self.assertEqual(
            manifest["teams"][0]["workers"][1]["identity"],
            {
                "theme": "client-facing finance",
                "emoji": "💹",
            },
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

    def test_v51_team_input_persists_visible_delivery_metadata_for_reconcile(self):
        manifest = self.module.build_v51_runtime_manifest(self.team_input())

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

    def test_v51_team_input_rejects_duplicate_team_keys(self):
        data = self.team_input()
        data["teams"].append(dict(data["teams"][0]))

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)

    def test_v51_role_catalog_profiles_require_explicit_visible_label(self):
        data = self.team_input_with_role_catalog()
        data["roleCatalog"]["ops_default"].pop("visibleLabel")

        with self.assertRaisesRegex(ValueError, "visibleLabel is required"):
            self.module.build_plugin_patch(data)

    def test_v51_team_input_rejects_invalid_team_key(self):
        data = self.team_input()
        data["teams"][0]["teamKey"] = "市场一组"

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)

    def test_v51_team_input_rejects_workflow_missing_worker_stage(self):
        data = self.team_input()
        data["teams"][0]["workflow"]["stages"] = [
            {"agentId": "ops_market_sz"},
        ]

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)

    def test_v51_team_input_rejects_duplicate_workflow_stage_agent(self):
        data = self.team_input()
        data["teams"][0]["workflow"]["stages"] = [
            {"agentId": "ops_market_sz"},
            {"agentId": "ops_market_sz"},
        ]

        with self.assertRaises(ValueError):
            self.module.build_plugin_patch(data)


class DocumentationConsistencyTests(unittest.TestCase):
    def test_root_skill_redirects_to_current_mainline_and_hides_legacy_routes(self):
        root_skill = ROOT_SKILL_FILE.read_text(encoding="utf-8")
        root_prompt = ROOT_CODEX_PROMPT.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", root_skill)
        self.assertIn("openclaw-feishu-multi-agent-deploy", root_skill)
        self.assertIn("codex-prompt-templates-v51-team-orchestrator.md", root_skill)
        self.assertNotIn("V3.1", root_skill)
        self.assertNotIn("chat-feishu", root_skill)
        self.assertNotIn("build" + "_openclaw_feishu_" + "snippets.py", root_skill)
        self.assertNotIn("input-template-legacy-chat-feishu.json", root_skill)

        self.assertIn("V5.1 Hardening", root_prompt)
        self.assertIn("openclaw-feishu-multi-agent-deploy", root_prompt)
        self.assertIn("codex-prompt-templates-v51-team-orchestrator.md", root_prompt)
        self.assertNotIn("V3.1", root_prompt)
        self.assertNotIn("chat-feishu", root_prompt)
        self.assertNotIn("build" + "_openclaw_feishu_" + "snippets.py", root_prompt)

    def test_root_notes_mark_legacy_input_as_historical_only(self):
        root_notes = ROOT_NOTES_FILE.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", root_notes)
        self.assertIn("历史兼容", root_notes)
        self.assertIn("input-template-v51-fixed-role-multi-group.json", root_notes)
        self.assertNotIn("V3.1", root_notes)
        self.assertNotIn("chat-feishu", root_notes)
        self.assertNotIn("老项目兼容：\n  - `references/input-template-legacy-chat-feishu.json`", root_notes)

    def test_inner_required_notes_use_v51_fixed_role_template_as_current_default(self):
        inner_notes = INNER_NOTES_FILE.read_text(encoding="utf-8")

        self.assertIn("input-template-v51-fixed-role-multi-group.json", inner_notes)
        self.assertNotIn("V3.1", inner_notes)
        self.assertNotIn("新项目优先使用：\n  - `references/input-template.json`（官方插件默认）", inner_notes)
        self.assertNotIn("新项目优先使用：\n  - `references/input-template-plugin.json`（插件多账号完整示例）", inner_notes)

    def test_root_checklists_are_bridge_docs_to_current_mainline(self):
        for path in (ROOT_PREREQUISITES_FILE, ROOT_ROLLOUT_PLAYBOOK, ROOT_VERIFICATION_TEMPLATE):
            content = path.read_text(encoding="utf-8")
            self.assertIn("V5.1 Hardening", content, str(path))
            self.assertIn("openclaw-feishu-multi-agent-deploy", content, str(path))
            self.assertIn("桥接", content, str(path))
            self.assertNotIn("V3.1", content, str(path))

    def test_root_legacy_builder_script_redirects_to_inner_builder(self):
        content = ROOT_LEGACY_BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("core_feishu_config_builder.py", content)
        self.assertIn("input-template-v51-fixed-role-multi-group.json", content)
        self.assertNotIn("chat-feishu", content)
        self.assertNotIn("LEGACY_CHANNEL", content)
        self.assertNotIn("--input references/input-template.json", content)

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

    def test_readme_keeps_only_v51_mainline(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", content)
        self.assertNotIn("V3.1", content)
        self.assertNotIn("V4.3.1", content)
        self.assertNotIn("C1.0", content)
        self.assertNotIn("V4.2.1", content)
        self.assertNotIn("V4.2", content)
        self.assertNotIn("V4.1", content)
        self.assertNotIn("V4：单群高级", content)

    def test_removed_v4_assets_do_not_exist(self):
        existing = [str(path.relative_to(REPO_ROOT)) for path in REMOVED_V4_ASSETS if path.exists()]
        self.assertEqual(existing, [])

    def test_removed_v3_assets_do_not_exist(self):
        existing = [str(path.relative_to(REPO_ROOT)) for path in REMOVED_V3_ASSETS if path.exists()]
        self.assertEqual(existing, [])

    def test_removed_root_legacy_assets_do_not_exist(self):
        existing = [str(path.relative_to(OUTER_SKILL_ROOT)) for path in REMOVED_ROOT_LEGACY_ASSETS if path.exists()]
        self.assertEqual(existing, [])

    def test_readme_and_skill_do_not_advertise_legacy_chat_feishu_route(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")

        self.assertNotIn("chat-feishu", readme)
        self.assertNotIn("chat-feishu", skill)

    def test_pruning_design_docs_exist(self):
        self.assertTrue(PRUNING_DESIGN_DOC.exists())
        self.assertTrue(PRUNING_PLAN_DOC.exists())

        design = PRUNING_DESIGN_DOC.read_text(encoding="utf-8")
        plan = PRUNING_PLAN_DOC.read_text(encoding="utf-8")
        root_alignment = ROOT_ALIGNMENT_PLAN_DOC.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", design)
        self.assertIn("V4.3.1", design)
        self.assertNotIn("V3.1", design)
        self.assertIn("只保留 `V5.1 Hardening`", plan)
        self.assertIn("README.md", plan)
        self.assertIn("tests/test_openclaw_feishu_multi_agent_skill.py", plan)
        self.assertNotIn("V3.1", plan)
        self.assertNotIn("V3.1", root_alignment)

    def test_current_mainline_assets_do_not_use_legacy_version_labels(self):
        checks = [
            (V51_DESIGN_DOC, ["V5 team unit"]),
            (ROLE_CATALOG_PLAN_DOC, ["normalize_v5_teams", "build_v5_plugin_patch", "build_v5_runtime_manifest"]),
        ]
        v51_repair_plan = REPO_ROOT / "docs/plans/2026-03-08-v5-1-production-stability-repair.md"
        if v51_repair_plan.exists():
            checks.append((v51_repair_plan, ["test_v5_"]))
        checks.append((V51_PLAN_DOC, ["test_v5_"]))
        ack_design = REPO_ROOT / "docs/plans/2026-03-09-ack-role-summary-design.md"
        if ack_design.exists():
            checks.append((ack_design, ["V5 job"]))

        violations = []
        for path, banned_tokens in checks:
            text = path.read_text(encoding="utf-8")
            for token in banned_tokens:
                if token in text:
                    violations.append(f"{path.relative_to(REPO_ROOT)} -> {token}")

        test_text = TEST_FILE.read_text(encoding="utf-8")
        obsolete_test_defs = re.findall(r"^\s*def\s+([A-Za-z0-9_]*_v5_[A-Za-z0-9_]*)\(", test_text, flags=re.M)
        for name in obsolete_test_defs:
            violations.append(f"tests/test_openclaw_feishu_multi_agent_skill.py -> {name}")
        obsolete_titles = re.findall(r'--title",\n\s*"V5 [^"]+"', test_text)
        for title in obsolete_titles:
            violations.append(f"tests/test_openclaw_feishu_multi_agent_skill.py -> {title.strip()}")

        self.assertEqual(violations, [])

    def test_v51_docs_require_real_message_ids_and_callback_reconcile(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        checklist = VERIFICATION_CHECKLIST.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")
        v5_snapshot = V51_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

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


class RuntimeRegistryTests(unittest.TestCase):
    def run_registry(self, db_path, *args):
        result = subprocess.run(
            [
                "python3",
                str(JOB_REGISTRY_SCRIPT),
                "--db",
                str(db_path),
                *args,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return result

    def start_v51_job(
        self,
        db_path,
        *,
        title,
        workflow_agents,
        requested_by="SeaWorld",
        group_peer_id="oc_demo",
        supervisor_visible_label="主管",
        participants=None,
        extra_args=(),
    ):
        return self.run_registry(
            db_path,
            "start-job-with-workflow",
            "--group-peer-id",
            group_peer_id,
            "--requested-by",
            requested_by,
            "--title",
            title,
            *extra_args,
            "--supervisor-visible-label",
            supervisor_visible_label,
            "--workflow-json",
            workflow_payload_json(*workflow_agents),
            "--participants-json",
            workflow_participants_json(*(participants or workflow_agents)),
        )

    def clear_workflow_visible_snapshots(self, db_path, job_ref, *, clear_supervisor=False, clear_agents=()):
        conn = sqlite3.connect(db_path)
        try:
            if clear_supervisor:
                conn.execute("UPDATE jobs SET supervisor_visible_label = '' WHERE job_ref = ?", (job_ref,))
            for agent_id in clear_agents:
                conn.execute(
                    "UPDATE job_participants SET visible_label = '' WHERE job_ref = ? AND agent_id = ?",
                    (job_ref, agent_id),
                )
            conn.commit()
        finally:
            conn.close()

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
                "--visible-label",
                "运营",
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
                "--visible-label",
                "财务",
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

    def test_registry_ready_to_rollup_accepts_v51_team_scoped_worker_ids(self):
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
                "V5.1 串行任务",
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
                    "--visible-label",
                    "运营" if "ops" in agent_id else "财务" if "finance" in agent_id else "法务",
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

    def test_registry_ready_to_rollup_waits_for_all_v51_participants(self):
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
                "V5.1 三专家串行任务",
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
                    "--visible-label",
                    "运营" if "ops" in agent_id else "财务" if "finance" in agent_id else "法务",
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 硬状态机任务",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--orchestrator-version",
                    "V5.1 Hardening",
                ),
            )

            self.assertEqual(started.returncode, 0, started.stderr)
            self.assertIn('"orchestratorVersion": "V5.1 Hardening"', started.stdout)
            self.assertIn('"type": "dispatch"', started.stdout)
            self.assertIn('"agentId": "ops_internal_main"', started.stdout)

    def test_registry_get_next_action_advances_only_in_workflow_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 串行推进任务",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
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
            conn.executescript(load_registry_module().SCHEMA)
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
            conn.executescript(load_registry_module().SCHEMA)
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 上下文持久化",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
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
                "--visible-label",
                "财务",
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
                "SELECT account_id, role, visible_label FROM job_participants WHERE job_ref = ? AND agent_id = ?",
                (job_ref, "finance_agent"),
            ).fetchone()
            conn.close()

            self.assertEqual(dispatched.returncode, 0, dispatched.stderr)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn('"agentId": "finance_agent"', completed.stdout)
            self.assertEqual(row[0], "yiran_yibao")
            self.assertEqual(row[1], "财务执行")
            self.assertEqual(row[2], "财务")

    def test_registry_mark_dispatch_requires_explicit_visible_label_without_existing_snapshot(self):
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
                "ops_agent",
                "--account-id",
                "xiaolongxia",
                "--role",
                "运营执行",
                "--dispatch-run-id",
                "run-ops",
                "--dispatch-status",
                "accepted",
            )

            self.assertEqual(dispatched.returncode, 2, dispatched.stdout)
            self.assertIn('"status": "invalid_visible_label"', dispatched.stdout)
            self.assertIn("participant visibleLabel snapshot is required", dispatched.stdout)

    def test_registry_mark_worker_complete_requires_existing_snapshot_or_explicit_identity(self):
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

            self.assertEqual(completed.returncode, 2, completed.stdout)
            self.assertIn('"status": "participant_identity_missing"', completed.stdout)
            self.assertIn("accountId and role are required", completed.stdout)

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
                "--visible-label",
                "运营",
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 dispatch gap",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--hidden-main-session-key",
                    "agent:supervisor_internal_main:main",
                ),
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

    def test_watchdog_surfaces_invalid_visible_label_before_dispatch_reconcile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot watchdog",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            watchdog = self.run_registry(
                db_path,
                "watchdog-tick",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(watchdog.returncode, 0, watchdog.stderr)
            self.assertIn('"status": "invalid_visible_label"', watchdog.stdout)
            self.assertIn("workflow participant visibleLabel snapshot is required: ops_internal_main", watchdog.stdout)
            self.assertNotIn('"status": "needs_dispatch_reconcile"', watchdog.stdout)

    def test_begin_turn_surfaces_invalid_visible_label_in_recover_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot begin turn",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            begin_turn = self.run_registry(
                db_path,
                "begin-turn",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(begin_turn.returncode, 0, begin_turn.stderr)
            self.assertIn('"status": "invalid_visible_label"', begin_turn.stdout)
            self.assertIn("workflow participant visibleLabel snapshot is required: ops_internal_main", begin_turn.stdout)
            self.assertNotIn('"status": "needs_dispatch_reconcile"', begin_turn.stdout)

    def test_begin_turn_active_payload_surfaces_invalid_visible_label_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot active payload",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            begin_turn = self.run_registry(
                db_path,
                "begin-turn",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(begin_turn.returncode, 0, begin_turn.stderr)
            self.assertIn('"snapshotStatus": "invalid_visible_label"', begin_turn.stdout)
            self.assertIn('"snapshotError": "workflow participant visibleLabel snapshot is required: ops_internal_main"', begin_turn.stdout)

    def test_get_active_surfaces_invalid_visible_label_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot get active",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            active = self.run_registry(
                db_path,
                "get-active",
                "--group-peer-id",
                "oc_demo",
            )

            self.assertEqual(active.returncode, 0, active.stderr)
            self.assertIn('"status": "invalid_visible_label"', active.stdout)
            self.assertIn('"snapshotStatus": "invalid_visible_label"', active.stdout)
            self.assertIn("workflow participant visibleLabel snapshot is required: ops_internal_main", active.stdout)

    def test_get_job_surfaces_invalid_visible_label_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot get job",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            job = self.run_registry(
                db_path,
                "get-job",
                "--job-ref",
                job_ref,
            )

            self.assertEqual(job.returncode, 0, job.stderr)
            self.assertIn('"status": "invalid_visible_label"', job.stdout)
            self.assertIn('"snapshotStatus": "invalid_visible_label"', job.stdout)
            self.assertIn("workflow participant visibleLabel snapshot is required: ops_internal_main", job.stdout)

    def test_recover_stale_surfaces_invalid_visible_label_before_dispatch_reconcile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 invalid snapshot recover stale",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]
            self.clear_workflow_visible_snapshots(
                db_path,
                job_ref,
                clear_agents=("ops_internal_main",),
            )

            recover = self.run_registry(
                db_path,
                "recover-stale",
                "--group-peer-id",
                "oc_demo",
                "--stale-seconds",
                "999999",
            )

            self.assertEqual(recover.returncode, 0, recover.stderr)
            self.assertIn('"status": "invalid_visible_label"', recover.stdout)
            self.assertIn("workflow participant visibleLabel snapshot is required: ops_internal_main", recover.stdout)
            self.assertNotIn('"status": "needs_dispatch_reconcile"', recover.stdout)

    def test_close_job_done_requires_rollup_visible_message_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 rollup visibility",
                requested_by="ou_user",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 canonical dispatch",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--request-text",
                    "请给出 3 天促销冲刺方案，包含运营节奏、预算红线和风险预案。",
                    "--entry-account-id",
                    "aoteman",
                    "--entry-channel",
                    "feishu",
                    "--entry-target",
                    "chat:oc_demo",
                    "--hidden-main-session-key",
                    "agent:supervisor_internal_main:main",
                ),
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
            self.assertIn(f'"progressTitle": "【运营进度｜{job_ref}】"', payload.stdout)
            self.assertIn(f'"finalTitle": "【运营结论｜{job_ref}】"', payload.stdout)
            self.assertIn('"callbackMustInclude": "summary,details,risks,actionItems"', payload.stdout)
            self.assertIn('"role": "运营执行"', payload.stdout)
            self.assertIn('"requestText": "请给出 3 天促销冲刺方案，包含运营节奏、预算红线和风险预案。"', payload.stdout)
            self.assertIn(f"progressTitle=【运营进度｜{job_ref}】", payload.stdout)
            self.assertIn(f"finalTitle=【运营结论｜{job_ref}】", payload.stdout)

    def test_registry_build_visible_ack_uses_explicit_feishu_delivery(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 ack",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--entry-account-id",
                    "aoteman",
                    "--entry-channel",
                    "feishu",
                    "--entry-target",
                    "chat:oc_demo",
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
            self.assertIn("任务已受理，正分配给运营处理，请稍候查看进度。", ack.stdout)

    def test_start_job_with_workflow_rejects_missing_participant_visible_labels(self):
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
                "V5.1 participant visible label required",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--supervisor-visible-label",
                "主管",
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
                            "accountId": "ops-bot",
                            "role": "运营专家",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "finance-bot",
                            "role": "财务专家",
                            "visibleLabel": "财审",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 2, started.stderr)
            self.assertIn('"status": "invalid_workflow"', started.stdout)
            self.assertIn("participants_json[0].visibleLabel is required", started.stdout)

    def test_start_job_with_workflow_rejects_missing_participants_json(self):
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
                "V5.1 participants required",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--supervisor-visible-label",
                "主管",
                "--workflow-json",
                json.dumps(
                    {
                        "mode": "serial",
                        "stages": [{"agentId": "ops_internal_main"}],
                    },
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 2, started.stderr)
            self.assertIn('"status": "invalid_workflow"', started.stdout)
            self.assertIn("participants_json is required", started.stdout)

    def test_start_job_with_workflow_rejects_missing_supervisor_visible_label(self):
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
                "V5.1 supervisor visible label required",
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
                "--participants-json",
                json.dumps(
                    [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "ops-bot",
                            "role": "运营专家",
                            "visibleLabel": "运营",
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 2, started.stderr)
            self.assertIn('"status": "invalid_workflow"', started.stdout)
            self.assertIn("supervisor_visible_label is required", started.stdout)

    def test_registry_visible_messages_use_persisted_visible_label_snapshots(self):
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
                "V5.1 visible label snapshots",
                "--entry-account-id",
                "aoteman",
                "--entry-channel",
                "feishu",
                "--entry-target",
                "chat:oc_demo",
                "--hidden-main-session-key",
                "agent:supervisor_internal_main:main",
                "--supervisor-visible-label",
                "总控台",
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
                            "role": "运营专家",
                            "visibleLabel": "增长",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务专家",
                            "visibleLabel": "财审",
                        },
                    ],
                    ensure_ascii=False,
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertEqual(details.returncode, 0, details.stderr)
            self.assertIn('"supervisorVisibleLabel": "总控台"', details.stdout)
            self.assertIn('"visibleLabel": "增长"', details.stdout)
            self.assertIn('"visibleLabel": "财审"', details.stdout)

            dispatch = self.run_registry(
                db_path,
                "build-dispatch-payload",
                "--job-ref",
                job_ref,
            )
            self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
            self.assertIn(f'"progressTitle": "【增长进度｜{job_ref}】"', dispatch.stdout)
            self.assertIn(f'"finalTitle": "【增长结论｜{job_ref}】"', dispatch.stdout)

            ack = self.run_registry(db_path, "build-visible-ack", "--job-ref", job_ref)
            self.assertEqual(ack.returncode, 0, ack.stderr)
            self.assertIn(f"【总控台已接单｜{job_ref}】", ack.stdout)
            self.assertIn("正分配给增长和财审处理", ack.stdout)

            for agent_id, account_id, role, visible_label in (
                ("ops_internal_main", "xiaolongxia", "运营专家", "增长"),
                ("finance_internal_main", "yiran_yibao", "财务专家", "财审"),
            ):
                dispatch_result = self.run_registry(
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
                    "--visible-label",
                    visible_label,
                    "--dispatch-run-id",
                    f"run-{agent_id}",
                    "--dispatch-status",
                    "accepted",
                )
                self.assertEqual(dispatch_result.returncode, 0, dispatch_result.stderr)
                complete = self.run_registry(
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
                    "--visible-label",
                    visible_label,
                    "--progress-message-id",
                    f"om_{agent_id}_progress",
                    "--final-message-id",
                    f"om_{agent_id}_final",
                    "--summary",
                    f"{visible_label}方案已完成",
                    "--final-visible-text",
                    f"【{visible_label}结论｜{job_ref}】\n完整{visible_label}方案。",
                )
                self.assertEqual(complete.returncode, 0, complete.stderr)

            rollup = self.run_registry(db_path, "build-rollup-visible-message", "--job-ref", job_ref)
            self.assertEqual(rollup.returncode, 0, rollup.stderr)
            self.assertIn(f"【总控台最终统一收口｜{job_ref}】", rollup.stdout)
            self.assertIn("二、增长终案方案", rollup.stdout)
            self.assertIn("三、财审终案方案", rollup.stdout)

    def test_registry_build_rollup_visible_message_requires_completion_packets(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 rollup message",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--entry-account-id",
                    "aoteman",
                    "--entry-channel",
                    "feishu",
                    "--entry-target",
                    "chat:oc_demo",
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

    def test_registry_build_rollup_visible_message_renders_structured_supervisor_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 structured rollup",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--request-text",
                    "请产出完整的 3 天促销冲刺执行方案。",
                    "--entry-account-id",
                    "aoteman",
                    "--entry-channel",
                    "feishu",
                    "--entry-target",
                    "chat:oc_demo",
                ),
            )
            self.assertEqual(started.returncode, 0, started.stderr)
            job_ref = started.stdout.split('"jobRef": "')[1].split('"', 1)[0]

            for agent_id, account_id, role in (
                ("ops_internal_main", "xiaolongxia", "运营执行"),
                ("finance_internal_main", "yiran_yibao", "财务执行"),
            ):
                dispatch = self.run_registry(
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
                    "--dispatch-status",
                    "accepted",
                )
                self.assertEqual(dispatch.returncode, 0, dispatch.stderr)
                complete = self.run_registry(
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
                    f"om_{agent_id}_progress",
                    "--final-message-id",
                    f"om_{agent_id}_final",
                    "--summary",
                    "该角色已完成完整方案并可直接执行。",
                    "--details",
                    "活动今晚完成物料锁版，明早 10 点准时开跑。",
                    "--risks",
                    "若 CPA 超过红线必须立刻降预算并切换素材。",
                    "--action-items",
                    "锁定物料、校验链路、召开战前会。",
                    "--final-visible-text",
                    (
                        f"【{role}结论｜{job_ref}】\n"
                        "一、目标与约束\n"
                        "3天100单，预算不超10000，毛利率不低于35%。\n"
                        "二、执行步骤\n"
                        "今晚锁版物料，明早10点开跑，中午复盘，晚高峰二次冲刺。\n"
                        "三、关键红线\n"
                        "任何动作不得击穿预算和毛利红线。"
                    ),
                )
                self.assertEqual(complete.returncode, 0, complete.stderr)

            rolled_ready = self.run_registry(db_path, "build-rollup-visible-message", "--job-ref", job_ref)
            self.assertEqual(rolled_ready.returncode, 0, rolled_ready.stderr)
            self.assertIn(f"【主管最终统一收口｜{job_ref}】", rolled_ready.stdout)
            self.assertIn("任务主题：V5.1 structured rollup", rolled_ready.stdout)
            self.assertIn("一、主管统一终案", rolled_ready.stdout)
            self.assertIn("二、运营终案方案", rolled_ready.stdout)
            self.assertIn("三、财务终案方案", rolled_ready.stdout)
            self.assertIn("四、联合风险与红线", rolled_ready.stdout)
            self.assertIn("五、明日三件事", rolled_ready.stdout)
            self.assertIn("一、目标与约束", rolled_ready.stdout)
            self.assertIn("二、执行步骤", rolled_ready.stdout)
            self.assertIn("今晚锁版物料，明早10点开跑，中午复盘，晚高峰二次冲刺。", rolled_ready.stdout)
            self.assertIn("三、关键红线", rolled_ready.stdout)
            self.assertIn("锁定物料、校验链路、召开战前会。", rolled_ready.stdout)
            self.assertNotIn("ops_internal_main:", rolled_ready.stdout)

    def test_registry_record_visible_message_updates_ack_and_rollup_flags(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"

            self.run_registry(db_path, "init-db")
            started = self.start_v51_job(
                db_path,
                title="V5.1 visible flags",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--entry-account-id",
                    "aoteman",
                    "--entry-channel",
                    "feishu",
                    "--entry-target",
                    "chat:oc_demo",
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 rollup gap",
                workflow_agents=("ops_internal_main",),
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
            started = self.start_v51_job(
                db_path,
                title="V5.1 wait worker",
                workflow_agents=("ops_internal_main",),
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
            ["python3", str(JOB_REGISTRY_SCRIPT), "--db", str(db_path), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def start_v51_job(
        self,
        db_path,
        *,
        title,
        workflow_agents,
        requested_by="SeaWorld",
        group_peer_id="oc_demo",
        supervisor_visible_label="主管",
        participants=None,
        extra_args=(),
    ):
        return self.run_registry(
            db_path,
            "start-job-with-workflow",
            "--group-peer-id",
            group_peer_id,
            "--requested-by",
            requested_by,
            "--title",
            title,
            *extra_args,
            "--supervisor-visible-label",
            supervisor_visible_label,
            "--workflow-json",
            workflow_payload_json(*workflow_agents),
            "--participants-json",
            workflow_participants_json(*(participants or workflow_agents)),
        )

    def run_reconcile(self, manifest_path, team_key, openclaw_home, openclaw_bin, *args):
        return subprocess.run(
            [
                "python3",
                str(V51_RECONCILE_SCRIPT),
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
                        "visibleLabel": "主管",
                        "hiddenMainSessionKey": "agent:supervisor_internal_main:main",
                    },
                    "workers": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                            "visibleLabel": "运营",
                            "groupSessionKey": f"agent:ops_internal_main:feishu:group:{group_peer_id}",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                            "visibleLabel": "财务",
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
                            "registryScript": str(JOB_REGISTRY_SCRIPT),
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

    def write_worker_main_completed_transcript_with_callback_toolcall(
        self,
        openclaw_home,
        agent_id,
        job_ref,
        *,
        group_peer_id="oc_demo",
        callback_session_key="agent:supervisor_internal_main:main",
        progress_message_id="om_progress_real",
        final_message_id="om_final_real",
        callback_progress_message_id="progressMessageId_pending",
        callback_final_message_id="finalMessageId_pending",
    ):
        sessions_dir = openclaw_home / "agents" / agent_id / "sessions"
        sessions_dir.mkdir(parents=True, exist_ok=True)
        session_id = f"{agent_id}-main-complete-with-callback"
        transcript_path = sessions_dir / f"{session_id}.jsonl"
        dispatch_text = (
            f"[Sun 2026-03-08 23:58 GMT+8] TASK_DISPATCH|jobRef={job_ref}|from=supervisor_internal_main|"
            f"to={agent_id}|title=测试任务|request=请输出完整方案|"
            f"callbackSessionKey={callback_session_key}|mustSend=progress,final,callback|"
            f"progressTitle=【运营进度｜{job_ref}】|finalTitle=【运营结论｜{job_ref}】|"
            f"callbackMustInclude=summary,details,risks,actionItems|"
            f"channel=feishu|accountId=xiaolongxia|target=chat:{group_peer_id}|groupPeerId={group_peer_id}"
        )
        callback_text = (
            f"COMPLETE_PACKET|jobRef={job_ref}|from={agent_id}|status=completed|"
            f"progressMessageId={callback_progress_message_id}|"
            f"finalMessageId={callback_final_message_id}|"
            "summary=已完成运营阶段并可进入财务校验。|"
            "details=已输出完整运营方案与执行节奏。|"
            "risks=需继续校验预算与毛利红线。|"
            "actionItems=1) 进入财务校验；2) 汇总红线；3) 准备统一收口。"
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
                            "id": "worker-assistant-tools",
                            "timestamp": "2026-03-08T15:58:12.000Z",
                            "message": {
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "toolCall",
                                        "id": "call-progress",
                                        "name": "message",
                                        "arguments": {
                                            "action": "send",
                                            "channel": "feishu",
                                            "accountId": "xiaolongxia",
                                            "target": f"chat:{group_peer_id}",
                                            "message": f"【运营进度｜{job_ref}】\\n已进入执行阶段。",
                                        },
                                    },
                                    {
                                        "type": "toolCall",
                                        "id": "call-final",
                                        "name": "message",
                                        "arguments": {
                                            "action": "send",
                                            "channel": "feishu",
                                            "accountId": "xiaolongxia",
                                            "target": f"chat:{group_peer_id}",
                                            "message": f"【运营结论｜{job_ref}】\\n已输出完整运营方案。",
                                        },
                                    },
                                    {
                                        "type": "toolCall",
                                        "id": "call-callback",
                                        "name": "sessions_send",
                                        "arguments": {
                                            "sessionKey": callback_session_key,
                                            "message": callback_text,
                                        },
                                    },
                                ],
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
                                "toolCallId": "call-progress",
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
                                "toolCallId": "call-final",
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
                            "id": "worker-tool-result-callback",
                            "timestamp": "2026-03-08T15:58:19.000Z",
                            "message": {
                                "role": "toolResult",
                                "toolName": "sessions_send",
                                "toolCallId": "call-callback",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(
                                            {
                                                "runId": "run-callback",
                                                "status": "ok",
                                                "sessionKey": callback_session_key,
                                                "delivery": {"status": "pending", "mode": "announce"},
                                            },
                                            ensure_ascii=False,
                                        ),
                                    }
                                ],
                                "details": {
                                    "runId": "run-callback",
                                    "status": "ok",
                                    "sessionKey": callback_session_key,
                                    "delivery": {"status": "pending", "mode": "announce"},
                                },
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "type": "message",
                            "id": "worker-assistant-final",
                            "timestamp": "2026-03-08T15:58:20.000Z",
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

            started = self.start_v51_job(
                db_path,
                title="worker no reply retry",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--source-message-id",
                    "om_retry_seed",
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

            started = self.start_v51_job(
                db_path,
                title="worker no reply loop recovery",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--source-message-id",
                    "om_worker_retry_loop",
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

            started = self.start_v51_job(
                db_path,
                title="hidden main callback retry",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--source-message-id",
                    "om_hidden_main_valid",
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

            started = self.start_v51_job(
                db_path,
                title="hidden main invalid callback retry",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--source-message-id",
                    "om_hidden_main_invalid",
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

            started = self.start_v51_job(
                db_path,
                title="hidden main mixed callbacks",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--source-message-id",
                    "om_hidden_main_mixed",
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

            started = self.start_v51_job(
                db_path,
                title="hidden main placeholder callback",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--source-message-id",
                    "om_hidden_main_placeholder",
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

            started = self.start_v51_job(
                db_path,
                title="hidden main transcript recovery",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--source-message-id",
                    "om_hidden_main_transcript_recovery",
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

    def test_resume_job_promotes_worker_transcript_callback_before_hidden_main_delivery(self):
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

            started = self.start_v51_job(
                db_path,
                title="worker transcript callback only",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
                extra_args=(
                    "--source-message-id",
                    "om_worker_transcript_only",
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
            self.write_worker_main_completed_transcript_with_callback_toolcall(
                openclaw_home,
                "ops_internal_main",
                job_ref,
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
            self.assertIn('"status": "worker_transcript_callback_promoted"', result.stdout)
            job = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"progressMessageId": "om_progress_real"', job.stdout)
            self.assertIn('"finalMessageId": "om_final_real"', job.stdout)
            self.assertIn('"finalVisibleText": "【运营结论｜', job.stdout)
            self.assertIn('已输出完整运营方案。', job.stdout)
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

            started = self.start_v51_job(
                db_path,
                title="V5.1 rollup reconcile",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--source-message-id",
                    "om_rollup_entry",
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

    def test_reconcile_rollup_does_not_resend_when_rollup_already_recorded(self):
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

            started = self.start_v51_job(
                db_path,
                title="V5.1 existing rollup",
                workflow_agents=("ops_internal_main",),
                extra_args=(
                    "--source-message-id",
                    "om_rollup_existing",
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
            self.run_registry(
                db_path,
                "record-visible-message",
                "--job-ref",
                job_ref,
                "--kind",
                "rollup",
                "--message-id",
                "om_rollup_existing",
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
            self.assertIn('"status": "rollup_already_recorded"', result.stdout)
            details = self.run_registry(db_path, "get-job", "--job-ref", job_ref)
            self.assertIn('"status": "done"', details.stdout)
            if fake_log.exists():
                self.assertNotIn("主管最终统一收口", fake_log.read_text(encoding="utf-8"))


class SessionHygieneTests(unittest.TestCase):
    def run_hygiene(self, home_path, *args, group_peer_id="oc_demo_group"):
        result = subprocess.run(
            [
                "python3",
                str(SESSION_HYGIENE_SCRIPT),
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

    def test_deployment_inputs_document_runtime_hygiene(self):
        content = (REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml").read_text(encoding="utf-8")

        self.assertIn("runtime_hygiene", content)
        self.assertIn("roleCatalog", content)
        self.assertIn("workflow.stages", content)
        self.assertIn("v51_team_orchestrator_hygiene.py", content)

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


class V51RuntimeArtifactsTests(unittest.TestCase):
    def run_canary(self, db_path, session_root, *args):
        return subprocess.run(
            [
                "python3",
                str(V51_CANARY_SCRIPT),
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

    def test_v51_watchdog_templates_use_team_placeholders(self):
        systemd_service = V51_SYSTEMD_SERVICE_TEMPLATE.read_text(encoding="utf-8")
        systemd_timer = V51_SYSTEMD_TIMER_TEMPLATE.read_text(encoding="utf-8")
        launchd = V51_LAUNCHD_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn("__TEAM_KEY__", systemd_service)
        self.assertIn("__SUPERVISOR_AGENT_ID__", systemd_service)
        self.assertIn("__RECONCILE_SCRIPT__", systemd_service)
        self.assertIn("__MANIFEST_PATH__", systemd_service)
        self.assertIn("v51-team-__TEAM_KEY__.service", systemd_timer)
        self.assertIn("bot.molt.v51-team-__TEAM_KEY__", launchd)
        self.assertIn("__RECONCILE_SCRIPT__", launchd)
        self.assertIn("__MANIFEST_PATH__", launchd)
        self.assertIn("__OPENCLAW_HOME__", launchd)

    def test_v51_canary_supports_custom_worker_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "team_jobs.db"
            session_root = root / "agents"
            conn = sqlite3.connect(db_path)
            conn.executescript(load_registry_module().SCHEMA)
            conn.execute(
                """
                INSERT INTO jobs (
                    job_ref, title, status, group_peer_id, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("TG-V51-001", "深圳团队任务", "done", "oc_team_sz"),
            )
            conn.execute(
                """
                INSERT INTO job_participants (
                    job_ref, agent_id, account_id, role, status, progress_message_id, final_message_id, summary, completed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    "TG-V51-001",
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
                    "TG-V51-001",
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
                "TG-V51-001",
                "--worker-agents",
                "ops_market_sz,finance_market_sz",
                "--supervisor-agent",
                "supervisor_market_sz",
                "--require-visible-messages",
                "--success-token",
                "V51_TEAM_CANARY_OK",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("V51_TEAM_CANARY_OK", result.stdout)
            self.assertIn("ops_market_sz_progress=msg_ops_progress", result.stdout)
            self.assertIn("finance_market_sz_final=msg_fin_final", result.stdout)

    def test_v51_canary_requires_supervisor_rollup_to_target_group(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            db_path = root / "team_jobs.db"
            session_root = root / "agents"
            conn = sqlite3.connect(db_path)
            conn.executescript(load_registry_module().SCHEMA)
            conn.execute(
                """
                INSERT INTO jobs (
                    job_ref, title, status, group_peer_id, created_at, updated_at, closed_at
                ) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), datetime('now'))
                """,
                ("TG-V51-002", "深圳团队任务", "done", "oc_team_sz"),
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
                    ("TG-V51-002", agent_id, account_id, role, "done", progress_id, final_id, f"{agent_id} done"),
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
                'toolCall name="message" target=chat:oc_team_sz jobRef=TG-V51-002 messageId=msg_supervisor_final\n',
                encoding="utf-8",
            )

            result = self.run_canary(
                db_path,
                session_root,
                "--job-ref",
                "TG-V51-002",
                "--worker-agents",
                "ops_market_sz,finance_market_sz",
                "--supervisor-agent",
                "supervisor_market_sz",
                "--require-visible-messages",
                "--require-supervisor-target-chat",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("msg_supervisor_final", result.stdout)


class V51DocumentationTests(unittest.TestCase):
    def test_v51_design_and_plan_docs_exist(self):
        self.assertTrue(V51_DESIGN_DOC.exists())
        self.assertTrue(V51_PLAN_DOC.exists())
        self.assertTrue(ROLE_CATALOG_DESIGN_DOC.exists())
        self.assertTrue(ROLE_CATALOG_PLAN_DOC.exists())

        design = V51_DESIGN_DOC.read_text(encoding="utf-8")
        plan = V51_PLAN_DOC.read_text(encoding="utf-8")
        role_catalog_design = ROLE_CATALOG_DESIGN_DOC.read_text(encoding="utf-8")
        role_catalog_plan = ROLE_CATALOG_PLAN_DOC.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", design)
        self.assertIn("Deterministic Orchestrator", design)
        self.assertIn("LLM 负责内容，代码负责流程", design)
        self.assertIn("start-job-with-workflow", plan)
        self.assertIn("get-next-action", plan)
        self.assertIn("roleCatalog", role_catalog_design)
        self.assertIn("visibleLabel", role_catalog_design)
        self.assertIn("profileId", role_catalog_plan)

    def test_v51_docs_and_templates_reference_v51_hardening_control_plane(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")
        v5_input = V51_INPUT_TEMPLATE.read_text(encoding="utf-8")
        v5_snapshot = V51_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        for content in (readme, skill, v5_doc, v5_input, v5_snapshot):
            self.assertIn("V5.1 Hardening", content)
            self.assertIn("start-job-with-workflow", content)
            self.assertIn("get-next-action", content)
            self.assertIn("build-dispatch-payload", content)
            self.assertIn("build-visible-ack", content)
            self.assertIn("record-visible-message", content)
            self.assertIn("v51_team_orchestrator_reconcile.py", content)
            self.assertIn("resume-job", content)

    def test_v51_skill_documents_supervisor_no_reply_hygiene_repair(self):
        skill = SKILL_FILE.read_text(encoding="utf-8")
        checklist = VERIFICATION_CHECKLIST.read_text(encoding="utf-8")

        self.assertIn("主管群 session", skill)
        self.assertIn("裸 NO_REPLY", skill)
        self.assertIn("v51_team_orchestrator_hygiene.py", skill)
        self.assertIn("v51_team_orchestrator_reconcile.py", skill)
        self.assertIn("hygiene", checklist)

    def test_v51_docs_require_canonical_worker_titles_and_single_structured_rollup(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")
        v5_snapshot = V51_CONFIG_SNAPSHOT.read_text(encoding="utf-8")
        checklist = VERIFICATION_CHECKLIST.read_text(encoding="utf-8")

        self.assertIn("progressTitle=【角色进度｜TG-xxxx】", readme)
        self.assertIn("finalTitle=【角色结论｜TG-xxxx】", readme)
        self.assertIn("同一 `jobRef` 的 `【主管最终统一收口｜TG-xxxx】` 只允许出现一次", readme)
        self.assertIn("完整 `finalVisibleText` 终案正文", readme)

        self.assertIn("progressTitle/finalTitle", skill)
        self.assertIn("同一 `jobRef` 若出现两次 `【主管最终统一收口】`", skill)
        self.assertIn("完整 `finalVisibleText` 正文", skill)

        self.assertIn("progressTitle/finalTitle/callbackMustInclude", v5_doc)
        self.assertIn("summary=...|details=...|risks=...|actionItems=...", v5_doc)
        self.assertIn("联合风险与红线", v5_doc)
        self.assertIn("明日三件事", v5_doc)
        self.assertIn("只允许出现一次", v5_doc)
        self.assertIn("完整 `finalVisibleText` 终案正文", v5_doc)

        self.assertIn("progressTitle/finalTitle/callbackMustInclude", v5_snapshot)
        self.assertIn("【运营进度｜TG-xxxx】", v5_snapshot)
        self.assertIn("【财务结论｜TG-xxxx】", v5_snapshot)
        self.assertIn("完整 finalVisibleText 终案正文", v5_snapshot)

        self.assertIn("worker 的两条群内可见消息都带固定标题", checklist)
        self.assertIn("同一 `jobRef` 在群里只出现 1 次 `【主管最终统一收口｜TG-xxxx】`", checklist)
        self.assertIn("完整 `finalVisibleText` 终案正文", checklist)

    def test_v51_docs_document_role_catalog_as_canonical_schema(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")
        v5_input = V51_INPUT_TEMPLATE.read_text(encoding="utf-8")
        v5_fixed_role = V51_FIXED_ROLE_TEMPLATE.read_text(encoding="utf-8")
        v5_snapshot = V51_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        self.assertIn("roleCatalog", readme)
        self.assertIn("profileId", readme)
        self.assertIn("visibleLabel", readme)

        self.assertIn("roleCatalog", skill)
        self.assertIn("profileId", skill)
        self.assertIn("visibleLabel", skill)

        self.assertIn("roleCatalog", v5_doc)
        self.assertIn("profileId", v5_doc)
        self.assertIn("visibleLabel", v5_doc)

        self.assertIn('"roleCatalog"', v5_input)
        self.assertIn('"profileId"', v5_input)
        self.assertIn('"visibleLabel"', v5_input)

        self.assertIn('"roleCatalog"', v5_fixed_role)
        self.assertIn('"profileId"', v5_fixed_role)
        self.assertIn('"visibleLabel"', v5_fixed_role)

        self.assertIn('"roleCatalog"', v5_snapshot)
        self.assertIn('"profileId"', v5_snapshot)
        self.assertIn('"visibleLabel"', v5_snapshot)

    def test_v51_canonical_schema_examples_include_accounts(self):
        readme = README_FILE.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")

        self.assertRegex(readme, r"canonical schema 最小示意：[\s\S]*?\"accounts\"")
        self.assertRegex(v5_doc, r"### canonical schema[\s\S]*?\"accounts\"")

    def test_v51_mainline_docs_name_accounts_as_part_of_unified_entry_schema(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        prompt = CUSTOMER_FIRST_USE_PROMPT.read_text(encoding="utf-8")
        example = CUSTOMER_FIRST_USE_EXAMPLE.read_text(encoding="utf-8")
        checklist = CUSTOMER_FIRST_USE_CHECKLIST.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")

        self.assertIn("accounts + roleCatalog + teams(profileId + override)", readme)
        self.assertIn("accounts + roleCatalog + teams(profileId + override)", skill)
        self.assertIn("accounts + roleCatalog + teams(profileId + override)", prompt)
        self.assertIn("accounts + roleCatalog + teams(profileId + override)", example)
        self.assertIn("accounts + roleCatalog + teams(profileId + override)", checklist)
        self.assertIn("accounts + roleCatalog + teams(profileId + override)", v5_doc)

        self.assertNotIn("主线 schema 固定按 `roleCatalog + teams(profileId + override)` 组织", skill)
        self.assertNotIn("主线 schema 统一使用 `roleCatalog + teams(profileId + override)`", prompt)
        self.assertNotIn("主线 schema 必须按 roleCatalog + teams(profileId + override) 解析。", prompt)
        self.assertNotIn("canonical schema：`roleCatalog + teams(profileId + override)`", example)
        self.assertNotIn("当前主线输入采用 `roleCatalog + teams(profileId + override)`。", example)
        self.assertNotIn("canonical schema：`roleCatalog + teams(profileId + override)`", checklist)

    def test_source_cross_validation_20260305_uses_bindings_for_v51_mainline(self):
        content = SOURCE_CROSS_VALIDATION_20260305.read_text(encoding="utf-8")

        self.assertIn("当前 `V5.1 Hardening` 主线统一入口是 `accounts + roleCatalog + teams`", content)
        self.assertIn("最终由 builder 派生 `bindings`", content)
        self.assertNotIn("并在 routes 中显式写 `accountId`", content)


class V51TemplateTests(unittest.TestCase):
    def test_v51_input_template_exists_and_mentions_teams(self):
        content = V51_INPUT_TEMPLATE.read_text(encoding="utf-8")

        self.assertIn('"teams"', content)
        self.assertIn('"supervisor"', content)
        self.assertIn('"workers"', content)
        self.assertIn('"description"', content)
        self.assertIn('"identity"', content)
        self.assertIn('"workflow"', content)
        self.assertIn('oc_f785e73d3c00954d4ccd5d49b63ef919', content)
        self.assertIn('oc_7121d87961740dbd72bd8e50e48ba5e3', content)

    def test_v51_config_snapshot_exists_and_documents_two_teams(self):
        content = V51_CONFIG_SNAPSHOT.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", content)
        self.assertIn("internal_main", content)
        self.assertIn("external_main", content)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", content)
        self.assertIn("oc_7121d87961740dbd72bd8e50e48ba5e3", content)
        self.assertIn("agent:supervisor_internal_main:main", content)
        self.assertIn("agent:supervisor_external_main:main", content)

    def test_v51_doc_exists_and_keeps_one_supervisor_plus_n_workers_constraint(self):
        content = V51_DOC.read_text(encoding="utf-8")

        self.assertIn("One Team = 1 Supervisor + N Workers", content)
        self.assertIn("teams", content)
        self.assertIn("workflow.stages", content)
        self.assertIn("description", content)
        self.assertIn("identity", content)
        self.assertIn("Codex 真实交付模板", content)
        self.assertIn("aoteman", content)
        self.assertIn("xiaolongxia", content)
        self.assertIn("yiran_yibao", content)

    def test_v51_doc_documents_team_runtime_commands(self):
        content = V51_DOC.read_text(encoding="utf-8")

        self.assertIn("--team-key", content)
        self.assertIn("--supervisor-agent", content)
        self.assertIn("v51-team-watchdog.service", content)
        self.assertIn("v51 runtime manifest", content)
        self.assertIn("v51_team_orchestrator_reconcile.py", content)
        self.assertIn("resume-job", content)

    def test_v51_fixed_role_template_exists_and_documents_role_combinations(self):
        content = V51_FIXED_ROLE_TEMPLATE.read_text(encoding="utf-8")

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

    def test_v51_fixed_role_standard_is_documented_in_readme_skill_and_v51_doc(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        v5_doc = V51_DOC.read_text(encoding="utf-8")
        deployment_inputs = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml"
        ).read_text(encoding="utf-8")

        for content in (readme, skill, v5_doc):
            self.assertIn("bot 复用，role 固定", content)
            self.assertIn("同一个 bot 可以跨很多群复用", content)
            self.assertIn("每个群的角色组合可以不同", content)
            self.assertIn("input-template-v51-fixed-role-multi-group.json", content)

        self.assertIn("recommended_v51_fixed_role_accounts", deployment_inputs)
        self.assertIn('supervisor: "aoteman"', deployment_inputs)
        self.assertIn('ops: "xiaolongxia"', deployment_inputs)
        self.assertIn('finance: "yiran_yibao"', deployment_inputs)


class V51ReadmeAndSkillTests(unittest.TestCase):
    def test_readme_marks_v51_as_current_mainline(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", content)
        self.assertNotIn("V3.1", content)
        self.assertNotIn("V4.3.1", content)
        self.assertIn("Codex", content)

    def test_skill_describes_team_unit_over_shared_global_agents(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("每个群", content)
        self.assertIn("1 个 supervisor", content)
        self.assertIn("N 个 worker", content)
        self.assertIn("team unit", content)

    def test_skill_uses_v51_fixed_role_template_as_default_v51_input_example(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("--input references/input-template-v51-fixed-role-multi-group.json", content)

    def test_builder_usage_example_uses_v51_fixed_role_template(self):
        content = BUILD_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("--input references/input-template-v51-fixed-role-multi-group.json", content)

    def test_readme_and_skill_list_v51_runtime_artifacts(self):
        readme = README_FILE.read_text(encoding="utf-8")
        skill = SKILL_FILE.read_text(encoding="utf-8")
        deployment_inputs = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("v51-team-watchdog.service", readme)
        self.assertIn("v51-team-watchdog.plist", readme)
        self.assertIn("v51-team-watchdog.service", skill)
        self.assertIn("v51-team-watchdog.plist", skill)
        self.assertIn("v51_team_orchestrator_reconcile.py", readme)
        self.assertIn("v51_team_orchestrator_reconcile.py", skill)
        self.assertIn("hidden_main_session_key", deployment_inputs)
        self.assertIn("v51_team_runtime", deployment_inputs)
        self.assertIn("runtime manifest", readme)

    def test_readme_codex_task_uses_v51_team_schema_instead_of_legacy_routes(self):
        readme = README_FILE.read_text(encoding="utf-8")
        marker = "### 2) 重启后直接发这个标准任务（V5.1 群内多 Agent 可扩展版）"
        self.assertIn(marker, readme)
        prompt_section = readme.split(marker, 1)[1]
        prompt = prompt_section.split("```text\n", 1)[1].split("\n```", 1)[0]

        self.assertIn("V5.1 Hardening", prompt)
        self.assertIn("roleCatalog:", prompt)
        self.assertIn("teams:", prompt)
        self.assertIn("internal_main", prompt)
        self.assertIn("external_main", prompt)
        self.assertIn("v51 runtime manifest", prompt)
        self.assertNotIn("accountMappings:", prompt)
        self.assertNotIn("routes:", prompt)
        self.assertNotIn('agents: ["sales_agent", "ops_agent", "finance_agent"]', prompt)

    def test_readme_collection_guidance_uses_unified_team_entry(self):
        readme = README_FILE.read_text(encoding="utf-8")
        start = "## 飞书与 OpenClaw 信息采集（你现在最容易卡的点）"
        end = "## 使用 Codex 的实战案例（安装到上线）"
        self.assertIn(start, readme)
        self.assertIn(end, readme)
        section = readme.split(start, 1)[1].split(end, 1)[0]

        self.assertIn("internal_main", section)
        self.assertIn("external_main", section)
        self.assertIn("roleCatalog", section)
        self.assertIn("teams[]", section)
        self.assertIn("`bindings` 是", section)
        self.assertIn("派生结果", section)
        self.assertNotIn("sales_agent", section)
        self.assertNotIn("ops_agent", section)
        self.assertNotIn("finance_agent", section)
        self.assertNotIn("routes:", section)

    def test_skill_prefers_unified_entry_over_route_templates(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("roleCatalog", content)
        self.assertIn("teams", content)
        self.assertIn("`bindings` 是", content)
        self.assertIn("派生结果", content)
        self.assertNotIn("确认 `agents`、`accounts`、`routes` 完整", content)
        self.assertNotIn("templates/openclaw-single-bot-route.example.jsonc", content)
        self.assertNotIn("templates/openclaw-multi-bot-route.example.jsonc", content)

    def test_readme_version_matches_version_file_and_current_release_date(self):
        readme = README_FILE.read_text(encoding="utf-8")
        changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
        version = VERSION_FILE.read_text(encoding="utf-8").strip()

        self.assertIn(f"`v{version}`（2026-03-09）", readme)
        self.assertIn("当前最新稳定版：`V5.1 Hardening`", readme)
        self.assertIn(f"## [{version}] - 2026-03-09", changelog)

    def test_skill_marks_single_bot_and_multi_bot_as_topology_background_only(self):
        content = SKILL_FILE.read_text(encoding="utf-8")

        self.assertIn("部署拓扑背景（不是第二套配置入口）", content)
        self.assertIn("主线配置入口仍然是 `accounts + roleCatalog + teams`", content)
        self.assertIn("不应让用户手写另一套 `routes` 入口", content)

    def test_deployment_inputs_template_uses_unified_entry_input_not_manual_routing(self):
        content = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml"
        ).read_text(encoding="utf-8")

        self.assertIn("accounts:", content)
        self.assertIn("roleCatalog:", content)
        self.assertIn("teams:", content)
        self.assertIn("workflow:", content)
        self.assertNotIn("\nrouting:\n", content)
        self.assertNotIn("\n  bindings:\n", content)
        self.assertNotIn("account_profiles:", content)

    def test_prerequisites_checklist_requests_unified_entry_materials(self):
        content = (
            REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/references/prerequisites-checklist.md"
        ).read_text(encoding="utf-8")

        self.assertIn("统一入口素材", content)
        self.assertIn("accounts", content)
        self.assertIn("roleCatalog", content)
        self.assertIn("teams", content)
        self.assertIn("workflow.stages", content)
        self.assertNotIn("## 4. 路由素材", content)
        self.assertNotIn("路由表（哪个 accountId + 哪个群/私聊 → 哪个 agent）", content)

    def test_skill_required_reading_prefers_stable_docs_over_time_snapshot(self):
        content = SKILL_FILE.read_text(encoding="utf-8")
        marker = "## 必读资源（按顺序）"
        self.assertIn(marker, content)
        section = content.split(marker, 1)[1].split("## 交付模式", 1)[0]

        self.assertIn("references/rollout-and-upgrade-playbook.md", section)
        self.assertNotIn("references/source-cross-validation-2026-03-04.md", section)

    def test_readme_cross_validation_docs_are_archived_not_best_practice_sources(self):
        content = README_FILE.read_text(encoding="utf-8")

        self.assertIn("历史交叉验证归档", content)
        self.assertNotIn("当前保留的最佳实践来源", content)

    def test_skill_reusable_files_do_not_mix_cross_validation_into_runbooks(self):
        content = SKILL_FILE.read_text(encoding="utf-8")
        marker = "- 运行手册："
        self.assertIn(marker, content)
        section = content.split(marker, 1)[1].split("- `templates/systemd/v51-team-watchdog.service`", 1)[0]

        self.assertIn("references/rollout-and-upgrade-playbook.md", section)
        self.assertIn("references/codex-prompt-templates-v51-team-orchestrator.md", section)
        self.assertNotIn("references/source-cross-validation-2026-03-04.md", section)
        self.assertNotIn("references/source-cross-validation-2026-03-05.md", section)

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
            V51_QUICKSTART_DOC,
            CUSTOMER_FIRST_USE_CHECKLIST,
            CUSTOMER_FIRST_USE_PROMPT,
            CUSTOMER_FIRST_USE_EXAMPLE,
        ):
            self.assertTrue(path.exists(), path.name)

        readme = README_FILE.read_text(encoding="utf-8")
        self.assertIn(
            "skills/openclaw-feishu-multi-agent-deploy/references/V5.1-新机器快速启动-SOP.md",
            readme,
        )
        self.assertIn(
            "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用信息清单.md",
            readme,
        )
        self.assertIn(
            "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用-Codex提示词.md",
            readme,
        )
        self.assertIn(
            "skills/openclaw-feishu-multi-agent-deploy/references/客户首次使用真实案例.md",
            readme,
        )
        self.assertNotIn(
            "产品手册：`references/codex-prompt-templates-v51-team-orchestrator.md`",
            readme,
        )
        self.assertNotIn(
            "收集清单：`references/客户首次使用信息清单.md`",
            readme,
        )

    def test_customer_first_use_docs_cover_collection_prompt_and_real_case(self):
        quickstart = V51_QUICKSTART_DOC.read_text(encoding="utf-8")
        checklist = CUSTOMER_FIRST_USE_CHECKLIST.read_text(encoding="utf-8")
        prompt = CUSTOMER_FIRST_USE_PROMPT.read_text(encoding="utf-8")
        example = CUSTOMER_FIRST_USE_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("V5.1 Hardening", quickstart)
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
        self.assertIn("input-template-v51-fixed-role-multi-group.json", checklist)

        self.assertIn("请使用 openclaw-feishu-multi-agent-deploy skill", prompt)
        self.assertIn("先备份", prompt)
        self.assertIn("openclaw config validate", prompt)
        self.assertIn("openclaw gateway restart", prompt)
        self.assertIn("一次配置 1 个群或多个群", prompt)

        self.assertIn("roleCatalog", quickstart)
        self.assertIn("profileId", quickstart)
        self.assertIn('"roleCatalog"', example)
        self.assertIn('"profileId"', example)

        self.assertIn("internal_main", example)
        self.assertIn("external_main", example)
        self.assertIn("oc_f785e73d3c00954d4ccd5d49b63ef919", example)
        self.assertIn("oc_7121d87961740dbd72bd8e50e48ba5e3", example)
        self.assertIn("aoteman", example)
        self.assertIn("xiaolongxia", example)
        self.assertIn("yiran_yibao", example)
        self.assertIn("把下面这些真实值替换成客户自己的值", example)

    def test_readme_mainline_navigation_links_resolve_to_inner_docs(self):
        readme = README_FILE.read_text(encoding="utf-8")

        expected_links = (
            "skills/openclaw-feishu-multi-agent-deploy/references/prerequisites-checklist.md",
            "skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml",
            "skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v51-team-orchestrator.md",
            "skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md",
            "skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md",
            "skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-04.md",
            "skills/openclaw-feishu-multi-agent-deploy/references/source-cross-validation-2026-03-05.md",
        )
        for path in expected_links:
            self.assertIn(path, readme)
            self.assertTrue((REPO_ROOT / path).exists(), path)

        self.assertNotIn("1. `references/prerequisites-checklist.md`", readme)
        self.assertNotIn("2. `templates/deployment-inputs.example.yaml`", readme)
        self.assertNotIn("3. `references/codex-prompt-templates-v51-team-orchestrator.md`", readme)
        self.assertNotIn("4. `templates/verification-checklist.md`", readme)
        self.assertNotIn("5. `references/rollout-and-upgrade-playbook.md`", readme)
        self.assertNotIn(
            "| `V5.1 Hardening` | 多群模板化主线 | 多个群并行、每群独立 team unit、可复制到 2/10 个团队 | `references/codex-prompt-templates-v51-team-orchestrator.md` |",
            readme,
        )

    def test_v51_product_docs_cover_unified_entry_and_expansion_scenarios(self):
        readme = README_FILE.read_text(encoding="utf-8")
        v51_doc = V51_DOC.read_text(encoding="utf-8")
        prompt = CUSTOMER_FIRST_USE_PROMPT.read_text(encoding="utf-8")
        example = CUSTOMER_FIRST_USE_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("如果只看一个文件", readme)
        self.assertIn("你将得到什么效果", v51_doc)
        self.assertIn("统一入口配置", v51_doc)
        self.assertIn("实现原理", v51_doc)
        self.assertIn("新增一个群", v51_doc)
        self.assertIn("新增一个机器人账号", v51_doc)
        self.assertIn("给现有群增加一个 worker", v51_doc)
        self.assertIn("从现有群移除一个 worker", v51_doc)
        self.assertIn("下线一个群", v51_doc)

        self.assertIn("新增一个群", prompt)
        self.assertIn("新增一个机器人账号", prompt)
        self.assertIn("给现有群增加一个 worker", prompt)
        self.assertIn("从现有群移除一个 worker", prompt)
        self.assertIn("下线一个群", prompt)

        self.assertIn("supervisor_internal_default", example)
        self.assertIn("ops_default", example)
        self.assertIn("finance_default", example)


if __name__ == "__main__":
    unittest.main()
