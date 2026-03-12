"""Contract tests for the redesigned worker callback sink.

Design reference:
- docs/plans/2026-03-10-v51-control-plane-redesign-design.md
"""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STORE_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_runtime_store.py"
)
INGRESS_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_ingress_adapter.py"
)
CONTROLLER_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_team_controller.py"
)
CALLBACK_SINK_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_worker_callback_sink.py"
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


class WorkerCallbackSinkContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store_module = load_module(STORE_SCRIPT)
        self.ingress_module = load_module(INGRESS_SCRIPT)
        self.controller_module = load_module(CONTROLLER_SCRIPT)

    def create_running_job(self):
        store = self.store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = self.controller_module.TeamController(store=store)
        event = self.ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_sink_001",
            canonical_target_id="oc_internal",
            request_text="@奥特曼 请出一版活动方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        job = controller.start_job(
            event=event,
            title="structured callback sink 测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )
        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])
        return store, controller, job

    def test_callback_sink_accepts_structured_payload(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        store, _controller, job = self.create_running_job()

        callback = sink_module.StructuredWorkerCallback(
            job_ref=job["jobRef"],
            team_key="internal_main",
            stage_index=0,
            agent_id="ops_internal_main",
            progress_draft=f"【运营进度｜{job['jobRef']}】已完成活动节奏和渠道拆解。",
            final_draft=f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
            final_visible_text=f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
            progress_message_id="",
            final_message_id="",
            summary="运营方案已完成。",
            details="完成渠道、节奏、文案和排期设计。",
            risks="社群转化率可能低于预期。",
            action_items="1) 进入财务测算；2) 核预算；3) 等待主管统一收口。",
        )

        accepted = sink_module.ingest_callback(store=store, callback=callback)
        replay = sink_module.ingest_callback(store=store, callback=callback)

        self.assertEqual(accepted["status"], "accepted")
        self.assertEqual(replay["status"], "duplicate")
        callbacks = store.list_stage_callbacks(job_ref=job["jobRef"])
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(callbacks[0]["payload"]["finalVisibleText"], callback.final_visible_text)

    def test_callback_sink_accepts_progress_only_payload_without_advancing_stage(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        store, _controller, job = self.create_running_job()

        callback = sink_module.StructuredWorkerCallback(
            job_ref=job["jobRef"],
            team_key="internal_main",
            stage_index=0,
            agent_id="ops_internal_main",
            progress_draft=f"【运营进度｜{job['jobRef']}】已开始拆解活动节奏。",
            final_draft="",
            final_visible_text="",
            progress_message_id="",
            final_message_id="",
            summary="",
            details="",
            risks="",
            action_items="",
        )

        accepted = sink_module.ingest_callback(store=store, callback=callback)
        self.assertEqual(accepted["status"], "progress_recorded")
        callbacks = store.list_stage_callbacks(job_ref=job["jobRef"])
        self.assertEqual(callbacks, [])
        row = store.connection.execute(
            "select current_stage_index, waiting_for_agent_id, next_action from jobs where job_ref = ?",
            (job["jobRef"],),
        ).fetchone()
        self.assertEqual(row[0], 0)
        self.assertEqual(row[1], "ops_internal_main")
        self.assertEqual(row[2], "wait_worker")
        participant = store.connection.execute(
            "select progress_message_id, final_message_id from job_participants where job_ref = ? and agent_id = ?",
            (job["jobRef"], "ops_internal_main"),
        ).fetchone()
        self.assertEqual(participant[0], "")
        self.assertEqual(participant[1], "")

    def test_callback_sink_rejects_cross_role_final_text(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        store, _controller, job = self.create_running_job()

        callback = sink_module.StructuredWorkerCallback(
            job_ref=job["jobRef"],
            team_key="internal_main",
            stage_index=0,
            agent_id="ops_internal_main",
            progress_draft=f"【运营进度｜{job['jobRef']}】运营处理中。",
            final_draft=f"【财务结论｜{job['jobRef']}】这是越权输出。",
            final_visible_text=f"【财务结论｜{job['jobRef']}】这是越权输出。",
            progress_message_id="",
            final_message_id="",
            summary="越权测试。",
            details="越权测试。",
            risks="越权测试。",
            action_items="越权测试。",
        )

        with self.assertRaises(ValueError):
            sink_module.ingest_callback(store=store, callback=callback)

    def test_callback_sink_rejects_worker_subagent_sessions_for_job_scope(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        store, _controller, job = self.create_running_job()

        callback = sink_module.StructuredWorkerCallback(
            job_ref=job["jobRef"],
            team_key="internal_main",
            stage_index=0,
            agent_id="ops_internal_main",
            progress_draft=f"【运营进度｜{job['jobRef']}】运营处理中。",
            final_draft=f"【运营结论｜{job['jobRef']}】完成运营方案。",
            final_visible_text=f"【运营结论｜{job['jobRef']}】完成运营方案。",
            progress_message_id="",
            final_message_id="",
            summary="运营方案已完成。",
            details="完成活动节奏与渠道设计。",
            risks="社群转化仍需观察。",
            action_items="1) 进入财务测算；2) 等待统一收口。",
        )

        with self.assertRaises(ValueError):
            sink_module.ingest_callback(
                store=store,
                callback=callback,
                subagent_sessions=[{"sessionKey": f"agent:ops_internal_main:subagent:{job['jobRef']}"}],
            )

    def test_callback_sink_rejects_placeholder_message_ids(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        store, _controller, job = self.create_running_job()

        callback = sink_module.StructuredWorkerCallback(
            job_ref=job["jobRef"],
            team_key="internal_main",
            stage_index=0,
            agent_id="ops_internal_main",
            progress_draft=f"【运营进度｜{job['jobRef']}】运营处理中。",
            final_draft=f"【运营结论｜{job['jobRef']}】完成运营方案。",
            final_visible_text=f"【运营结论｜{job['jobRef']}】完成运营方案。",
            progress_message_id="<pending_from_tool_1>",
            final_message_id="msg_final_placeholder",
            summary="运营方案已完成。",
            details="完成活动节奏与渠道设计。",
            risks="社群转化仍需观察。",
            action_items="1) 进入财务测算；2) 等待统一收口。",
        )

        with self.assertRaises(ValueError):
            sink_module.ingest_callback(store=store, callback=callback)

    def test_callback_sink_cli_accepts_single_payload_argument(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            store = self.store_module.RuntimeStore(str(db_path))
            store.initialize()
            self.addCleanup(store.close)
            controller = self.controller_module.TeamController(store=store)
            event = self.ingress_module.extract_inbound_event(
                team_key="internal_main",
                source_message_id="om_sink_cli_001",
                canonical_target_id="oc_internal",
                request_text="@奥特曼 请出一版活动方案",
                requested_by="ou_demo",
                account_id="aoteman",
                mentioned_agent_id="supervisor_internal_main",
            )
            job = controller.start_job(
                event=event,
                title="structured callback sink CLI 测试",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            controller.plan_ack(job_ref=job["jobRef"])
            controller.dispatch_next_stage(job_ref=job["jobRef"])

            payload = {
                "progressDraft": f"【运营进度｜{job['jobRef']}】已完成活动节奏和渠道拆解。",
                "finalDraft": f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
                "finalVisibleText": f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
                "progressMessageId": "",
                "finalMessageId": "",
                "summary": "运营方案已完成。",
                "details": "完成渠道、节奏、文案和排期设计。",
                "risks": "社群转化率可能低于预期。",
                "actionItems": "1) 进入财务测算；2) 核预算；3) 等待主管统一收口。",
            }

            exit_code = sink_module.main(
                [
                    "ingest",
                    "--db",
                    str(db_path),
                    "--job-ref",
                    job["jobRef"],
                    "--team-key",
                    "internal_main",
                    "--stage-index",
                    "0",
                    "--agent-id",
                    "ops_internal_main",
                    "--payload",
                    json.dumps(payload, ensure_ascii=False),
                ]
            )

            self.assertEqual(exit_code, 0)
            callbacks = store.list_stage_callbacks(job_ref=job["jobRef"])
            self.assertEqual(len(callbacks), 1)
            self.assertEqual(callbacks[0]["payload"]["finalDraft"], payload["finalDraft"])

    def test_callback_sink_cli_serializes_array_fields_as_json_strings(self):
        sink_module = load_module(CALLBACK_SINK_SCRIPT)
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "team_jobs.db"
            store = self.store_module.RuntimeStore(str(db_path))
            store.initialize()
            self.addCleanup(store.close)
            controller = self.controller_module.TeamController(store=store)
            event = self.ingress_module.extract_inbound_event(
                team_key="internal_main",
                source_message_id="om_sink_cli_002",
                canonical_target_id="oc_internal",
                request_text="@奥特曼 请出一版活动方案",
                requested_by="ou_demo",
                account_id="aoteman",
                mentioned_agent_id="supervisor_internal_main",
            )
            job = controller.start_job(
                event=event,
                title="structured callback sink array 测试",
                workflow_agents=("ops_internal_main", "finance_internal_main"),
            )
            controller.plan_ack(job_ref=job["jobRef"])
            controller.dispatch_next_stage(job_ref=job["jobRef"])

            payload = {
                "progressDraft": f"【运营进度｜{job['jobRef']}】已完成活动节奏和渠道拆解。",
                "finalDraft": f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
                "finalVisibleText": f"【运营结论｜{job['jobRef']}】建议先用社群预热，再推短视频转化。",
                "summary": "运营方案已完成。",
                "details": ["完成渠道设计。", "完成排期设计。"],
                "risks": ["社群转化率可能低于预期。", "投放成本可能波动。"],
                "actionItems": ["进入财务测算。", "核预算。", "等待主管统一收口。"],
            }

            exit_code = sink_module.main(
                [
                    "ingest",
                    "--db",
                    str(db_path),
                    "--job-ref",
                    job["jobRef"],
                    "--team-key",
                    "internal_main",
                    "--stage-index",
                    "0",
                    "--agent-id",
                    "ops_internal_main",
                    "--payload",
                    json.dumps(payload, ensure_ascii=False),
                ]
            )

            self.assertEqual(exit_code, 0)
            callbacks = store.list_stage_callbacks(job_ref=job["jobRef"])
            self.assertEqual(len(callbacks), 1)
            self.assertEqual(callbacks[0]["payload"]["details"], "[\"完成渠道设计。\", \"完成排期设计。\"]")
            self.assertEqual(callbacks[0]["payload"]["risks"], "[\"社群转化率可能低于预期。\", \"投放成本可能波动。\"]")
            self.assertEqual(
                callbacks[0]["payload"]["actionItems"],
                "[\"进入财务测算。\", \"核预算。\", \"等待主管统一收口。\"]",
            )
