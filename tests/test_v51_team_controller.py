"""Contract tests for the redesigned team controller.

Design reference:
- docs/plans/2026-03-10-v51-control-plane-redesign-design.md
"""

import importlib.util
import sys
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


class TeamControllerContractTests(unittest.TestCase):
    def test_team_controller_exposes_single_writer_api(self):
        module = load_module(CONTROLLER_SCRIPT)

        self.assertTrue(hasattr(module, "TeamController"))
        controller = module.TeamController(store=None)
        for method_name in (
            "start_job",
            "plan_ack",
            "dispatch_next_stage",
            "accept_worker_callback",
            "plan_rollup",
        ):
            self.assertTrue(hasattr(controller, method_name), method_name)

    def test_team_controller_routes_visible_messages_through_outbox(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_123",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )

        job = controller.start_job(
            event=event,
            title="统一控制面测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )
        ack = controller.plan_ack(job_ref=job["jobRef"])

        self.assertEqual(job["nextAction"], "dispatch")
        self.assertEqual(ack["deliveryMode"], "outbox")
        self.assertEqual(ack["messageKind"], "ack")
        self.assertEqual(ack["teamKey"], "internal_main")

    def test_team_controller_is_single_writer_for_state_and_rejects_cross_role_callback(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_124",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        job = controller.start_job(
            event=event,
            title="单写状态机测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )

        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])

        with self.assertRaises(Exception):
            controller.dispatch_next_stage(job_ref=job["jobRef"])

        with self.assertRaises(ValueError):
            controller.accept_worker_callback(
                job_ref=job["jobRef"],
                agent_id="ops_internal_main",
                progress_text=f"【运营进度｜{job['jobRef']}】运营处理中",
                final_text=f"【财务结论｜{job['jobRef']}】这是越权内容",
                summary="越权测试",
                details="越权测试",
                risks="越权测试",
                action_items="越权测试",
            )

    def test_team_controller_only_allows_one_next_action_transition(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_125",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )

        job = controller.start_job(
            event=event,
            title="单动作推进测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )
        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])

        with self.assertRaises(RuntimeError):
            controller.plan_ack(job_ref=job["jobRef"])

    def test_team_controller_blocks_rollup_until_required_callbacks_exist(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_126",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        job = controller.start_job(
            event=event,
            title="收口前置校验测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )

        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])

        with self.assertRaises(RuntimeError):
            controller.plan_rollup(job_ref=job["jobRef"])

    def test_team_controller_parallel_stage_creates_publish_gate_and_dispatches_all_agents(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_parallel_001",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        workflow = {
            "stages": [
                {
                    "stageKey": "analysis",
                    "mode": "parallel",
                    "agents": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "ops",
                            "role": "运营",
                            "visibleLabel": "运营",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "finance",
                            "role": "财务",
                            "visibleLabel": "财务",
                        },
                    ],
                    "publishOrder": ["ops_internal_main", "finance_internal_main"],
                }
            ]
        }

        job = controller.start_job(
            event=event,
            title="并行 stage 测试",
            workflow=workflow,
        )
        controller.plan_ack(job_ref=job["jobRef"])
        dispatch = controller.dispatch_next_stage(job_ref=job["jobRef"])

        self.assertEqual(dispatch["mode"], "parallel")
        self.assertEqual(dispatch["nextAction"], "wait_worker")
        self.assertEqual([item["agentId"] for item in dispatch["dispatches"]], ["ops_internal_main", "finance_internal_main"])

        gate = store.get_publish_gate(job_ref=job["jobRef"], stage_key="analysis")
        self.assertIsNotNone(gate)
        self.assertEqual(gate["stageStatus"], "running")
        self.assertEqual(gate["publishCursor"], 0)
        self.assertEqual(gate["nextAgentId"], "ops_internal_main")

    def test_team_controller_parallel_stage_publishes_in_order_after_callbacks(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_parallel_002",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        workflow = {
            "stages": [
                {
                    "stageKey": "analysis",
                    "mode": "parallel",
                    "agents": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "ops",
                            "role": "运营",
                            "visibleLabel": "运营",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "finance",
                            "role": "财务",
                            "visibleLabel": "财务",
                        },
                    ],
                    "publishOrder": ["ops_internal_main", "finance_internal_main"],
                }
            ]
        }

        job = controller.start_job(
            event=event,
            title="并行顺序发布测试",
            workflow=workflow,
        )
        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])

        finance = controller.accept_worker_callback(
            job_ref=job["jobRef"],
            agent_id="finance_internal_main",
            progress_text=f"【财务进度｜{job['jobRef']}】财务处理中",
            final_text=f"【财务结论｜{job['jobRef']}】财务结论",
            summary="财务已完成",
            details="财务细项",
            risks="财务风险",
            action_items="财务动作",
        )
        self.assertEqual(finance["nextAction"], "wait_worker")
        self.assertEqual(controller.collect_publishable_callbacks(job_ref=job["jobRef"]), [])

        ops = controller.accept_worker_callback(
            job_ref=job["jobRef"],
            agent_id="ops_internal_main",
            progress_text=f"【运营进度｜{job['jobRef']}】运营处理中",
            final_text=f"【运营结论｜{job['jobRef']}】运营结论",
            summary="运营已完成",
            details="运营细项",
            risks="运营风险",
            action_items="运营动作",
        )
        self.assertEqual(ops["nextAction"], "publish")
        ready = controller.collect_publishable_callbacks(job_ref=job["jobRef"])
        self.assertEqual([item["agentId"] for item in ready], ["ops_internal_main"])

        published = controller.mark_callback_published(
            job_ref=job["jobRef"],
            stage_key="analysis",
            agent_id="ops_internal_main",
        )
        self.assertEqual(published["publishCursor"], 1)
        self.assertEqual(published["nextAgentId"], "finance_internal_main")

        ready_after_ops = controller.collect_publishable_callbacks(job_ref=job["jobRef"])
        self.assertEqual([item["agentId"] for item in ready_after_ops], ["finance_internal_main"])

    def test_team_controller_parallel_stage_enqueues_only_current_publish_order_into_outbox(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_parallel_003",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        workflow = {
            "stages": [
                {
                    "stageKey": "analysis",
                    "mode": "parallel",
                    "agents": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "ops",
                            "role": "运营",
                            "visibleLabel": "运营",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "finance",
                            "role": "财务",
                            "visibleLabel": "财务",
                        },
                    ],
                    "publishOrder": ["ops_internal_main", "finance_internal_main"],
                }
            ]
        }

        job = controller.start_job(
            event=event,
            title="parallel publish outbox 测试",
            workflow=workflow,
        )
        controller.plan_ack(job_ref=job["jobRef"])
        controller.dispatch_next_stage(job_ref=job["jobRef"])
        controller.accept_worker_callback(
            job_ref=job["jobRef"],
            agent_id="finance_internal_main",
            progress_text=f"【财务进度｜{job['jobRef']}】财务处理中",
            final_text=f"【财务结论｜{job['jobRef']}】财务结论",
            summary="财务已完成",
            details="财务细项",
            risks="财务风险",
            action_items="财务动作",
        )
        controller.accept_worker_callback(
            job_ref=job["jobRef"],
            agent_id="ops_internal_main",
            progress_text=f"【运营进度｜{job['jobRef']}】运营处理中",
            final_text=f"【运营结论｜{job['jobRef']}】运营结论",
            summary="运营已完成",
            details="运营细项",
            risks="运营风险",
            action_items="运营动作",
        )

        enqueued = controller.enqueue_publishable_callbacks(job_ref=job["jobRef"])
        self.assertEqual([item["agentId"] for item in enqueued], ["ops_internal_main", "ops_internal_main"])
        pending = store.list_pending_outbound_messages(team_key="internal_main")
        worker_pending = [
            (row["messageKind"], row["agentId"])
            for row in pending
            if row["messageKind"] in {"worker_progress", "worker_final"}
        ]
        self.assertEqual(
            worker_pending,
            [("worker_progress", "ops_internal_main"), ("worker_final", "ops_internal_main")],
        )

    def test_team_controller_parallel_stage_preserves_worker_metadata_from_workflow_definition(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_parallel_004",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 请并行分析运营和财务方案。",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        workflow = {
            "stages": [
                {
                    "stageKey": "analysis",
                    "mode": "parallel",
                    "agents": [
                        {
                            "agentId": "ops_internal_main",
                            "accountId": "xiaolongxia",
                            "role": "运营执行",
                            "visibleLabel": "运营",
                        },
                        {
                            "agentId": "finance_internal_main",
                            "accountId": "yiran_yibao",
                            "role": "财务执行",
                            "visibleLabel": "财务",
                        },
                    ],
                    "publishOrder": ["ops_internal_main", "finance_internal_main"],
                }
            ]
        }

        job = controller.start_job(
            event=event,
            title="parallel metadata preserve",
            workflow=workflow,
            workflow_agents=tuple(workflow["stages"][0]["agents"]),
        )
        controller.plan_ack(job_ref=job["jobRef"])
        dispatch = controller.dispatch_next_stage(job_ref=job["jobRef"])

        by_agent = {item["agentId"]: item for item in dispatch["dispatches"]}
        self.assertEqual(by_agent["ops_internal_main"]["accountId"], "xiaolongxia")
        self.assertEqual(by_agent["finance_internal_main"]["accountId"], "yiran_yibao")
        self.assertEqual(by_agent["ops_internal_main"]["scopeLabel"], "运营")
        self.assertEqual(by_agent["finance_internal_main"]["scopeLabel"], "财务")
