"""Contract tests for the redesigned OpenClaw adapter boundary.

Design reference:
- docs/plans/2026-03-10-v51-control-plane-redesign-design.md
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
ADAPTER_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_openclaw_adapter.py"
)


def load_module(path: Path):
    if not path.exists():
        raise AssertionError(f"缺少重构模块: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载模块: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class OpenClawAdapterContractTests(unittest.TestCase):
    def test_openclaw_adapter_exposes_narrow_boundary(self):
        module = load_module(ADAPTER_SCRIPT)

        self.assertTrue(hasattr(module, "OpenClawAdapter"))
        self.assertTrue(hasattr(module, "CapturedInboundEvent"))
        self.assertTrue(hasattr(module, "SessionTarget"))
        adapter = module.OpenClawAdapter(openclaw_home=Path("/tmp/fake-openclaw-home"), openclaw_bin="openclaw")
        for method_name in ("capture_inbound_event", "send_message", "invoke_agent", "inspect_or_reset_session"):
            self.assertTrue(hasattr(adapter, method_name), method_name)

    def test_openclaw_adapter_send_message_uses_cli_json_contract(self):
        module = load_module(ADAPTER_SCRIPT)
        adapter = module.OpenClawAdapter(openclaw_home=Path("/tmp/fake-openclaw-home"), openclaw_bin="openclaw")

        completed = module.subprocess.CompletedProcess(
            args=["openclaw"],
            returncode=0,
            stdout='{"messageId":"om_send_001"}\n',
            stderr="",
        )
        with patch.object(module.subprocess, "run", return_value=completed) as mock_run:
            payload = adapter.send_message(
                channel="feishu",
                account_id="aoteman",
                target="chat:oc_demo",
                message="【主管已接单｜TG-01TEST】测试消息",
            )

        self.assertEqual(payload["messageId"], "om_send_001")
        command = mock_run.call_args[0][0]
        self.assertEqual(
            command,
            [
                "openclaw",
                "message",
                "send",
                "--channel",
                "feishu",
                "--account",
                "aoteman",
                "--target",
                "chat:oc_demo",
                "--message",
                "【主管已接单｜TG-01TEST】测试消息",
                "--json",
            ],
        )

    def test_openclaw_adapter_invoke_agent_uses_agent_cli(self):
        module = load_module(ADAPTER_SCRIPT)
        adapter = module.OpenClawAdapter(openclaw_home=Path("/tmp/fake-openclaw-home"), openclaw_bin="openclaw")

        completed = module.subprocess.CompletedProcess(
            args=["openclaw"],
            returncode=0,
            stdout='{"status":"ok","runId":"run_001"}\n',
            stderr="",
        )
        with patch.object(module.subprocess, "run", return_value=completed) as mock_run:
            payload = adapter.invoke_agent(
                agent_id="ops_internal_main",
                message="TASK_DISPATCH|jobRef=TG-01TEST|...",
            )

        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["runId"], "run_001")
        command = mock_run.call_args[0][0]
        self.assertEqual(
            command,
            [
                "openclaw",
                "agent",
                "--agent",
                "ops_internal_main",
                "--message",
                "TASK_DISPATCH|jobRef=TG-01TEST|...",
                "--json",
            ],
        )

    def test_openclaw_adapter_uses_timeout_and_raises_on_hung_cli(self):
        module = load_module(ADAPTER_SCRIPT)
        adapter = module.OpenClawAdapter(
            openclaw_home=Path("/tmp/fake-openclaw-home"),
            openclaw_bin="openclaw",
            timeout_seconds=15,
        )

        with patch.object(
            module.subprocess,
            "run",
            side_effect=module.subprocess.TimeoutExpired(cmd=["openclaw"], timeout=15),
        ) as mock_run:
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                adapter.invoke_agent(
                    agent_id="ops_internal_main",
                    message="TASK_DISPATCH|jobRef=TG-01TEST|...",
                )

        self.assertEqual(mock_run.call_args.kwargs["timeout"], 15)

    def test_openclaw_adapter_capture_inbound_event_reads_group_session(self):
        module = load_module(ADAPTER_SCRIPT)
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            sessions_dir = home / "agents" / "supervisor_internal_main" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_key = "agent:supervisor_internal_main:feishu:group:oc_demo"
            session_id = "sup-group-1"
            transcript_path = sessions_dir / f"{session_id}.jsonl"
            transcript_path.write_text(
                "\n".join(
                    [
                        json.dumps(
                            {
                                "type": "message",
                                "message": {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "text",
                                            "text": "[message_id: om_123]\\nou_demo: @奥特曼 请帮我做活动方案",
                                        }
                                    ],
                                },
                            },
                            ensure_ascii=False,
                        ),
                        json.dumps(
                            {
                                "type": "message",
                                "message": {
                                    "role": "toolResult",
                                    "toolName": "sessions_spawn",
                                    "details": {
                                        "childSessionKey": "agent:supervisor_internal_main:subagent:ops-plan-om_123"
                                    },
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
                            "sessionFile": str(transcript_path),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            adapter = module.OpenClawAdapter(openclaw_home=home, openclaw_bin="openclaw")
            event = adapter.capture_inbound_event(
                agent_id="supervisor_internal_main",
                session_key=session_key,
            )

        self.assertIsNotNone(event)
        self.assertEqual(event.source_message_id, "om_123")
        self.assertEqual(event.requested_by, "ou_demo")
        self.assertEqual(event.request_text, "@奥特曼 请帮我做活动方案")
        self.assertEqual(
            event.supervisor_spawned_session_keys,
            ("agent:supervisor_internal_main:subagent:ops-plan-om_123",),
        )

    def test_openclaw_adapter_inspect_or_reset_session_supports_both_actions(self):
        module = load_module(ADAPTER_SCRIPT)
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            sessions_dir = home / "agents" / "ops_internal_main" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_key = "agent:ops_internal_main:main"
            session_id = "ops-main-1"
            transcript_path = sessions_dir / f"{session_id}.jsonl"
            transcript_path.write_text("hello\n", encoding="utf-8")
            (sessions_dir / "sessions.json").write_text(
                json.dumps(
                    {
                        session_key: {
                            "sessionId": session_id,
                            "sessionFile": str(transcript_path),
                        }
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            adapter = module.OpenClawAdapter(openclaw_home=home, openclaw_bin="openclaw")
            target = module.SessionTarget(agent_id="ops_internal_main", session_key=session_key)
            inspected = adapter.inspect_or_reset_session(targets=[target], action="inspect")
            reset = adapter.inspect_or_reset_session(
                targets=[target],
                action="reset",
                delete_transcripts=True,
            )

            self.assertEqual(inspected[0]["status"], "present")
            self.assertEqual(reset[0]["status"], "removed")
            self.assertFalse(transcript_path.exists())
