"""Contract tests for the redesigned outbox sender.

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
OUTBOX_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_outbox_sender.py"
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


class OutboxSenderContractTests(unittest.TestCase):
    def test_delivery_sender_accepts_nested_result_message_id_shape(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)
        outbox_module = load_module(OUTBOX_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_outbox_nested_ack",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        job = controller.start_job(
            event=event,
            title="outbox nested ack 测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )

        controller.plan_ack(job_ref=job["jobRef"])
        result = outbox_module.deliver_pending_messages(
            store,
            delivery_func=lambda row: {
                "channel": "feishu",
                "result": {"messageId": f"om_nested_{row['messageKind']}"},
            },
            team_key="internal_main",
        )

        self.assertEqual(result["deliveredCount"], 1)
        self.assertEqual(result["results"][0]["deliveryMessageId"], "om_nested_ack")
        self.assertEqual(store.list_pending_outbound_messages(team_key="internal_main"), [])

    def test_ack_is_written_to_outbox_before_delivery(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)
        outbox_module = load_module(OUTBOX_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_outbox_ack",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )
        job = controller.start_job(
            event=event,
            title="outbox ack 测试",
            workflow_agents=("ops_internal_main", "finance_internal_main"),
        )

        controller.plan_ack(job_ref=job["jobRef"])
        pending = store.list_pending_outbound_messages(team_key="internal_main")
        result = outbox_module.deliver_pending_messages(
            store,
            delivery_func=lambda row: {"messageId": f"om_sent_{row['messageKind']}"},
            team_key="internal_main",
        )

        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["messageKind"], "ack")
        self.assertEqual(result["deliveredCount"], 1)
        sent = store.list_pending_outbound_messages(team_key="internal_main")
        self.assertEqual(sent, [])

    def test_duplicate_progress_message_is_deduped_by_outbox_key(self):
        store_module = load_module(STORE_SCRIPT)
        outbox_module = load_module(OUTBOX_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        payload = {
            "jobRef": "TG-01TESTOUTBOX0000000000000A",
            "teamKey": "internal_main",
            "delivery": {"channel": "feishu", "accountId": "ops_bot", "target": "chat:oc_demo"},
            "message": "【运营进度｜TG-01TESTOUTBOX0000000000000A】运营处理中",
        }

        first = outbox_module.enqueue_visible_message(
            store,
            team_key="internal_main",
            job_ref="TG-01TESTOUTBOX0000000000000A",
            message_kind="worker_progress",
            payload=payload,
            stage_index=0,
            agent_id="ops_internal_main",
        )
        second = outbox_module.enqueue_visible_message(
            store,
            team_key="internal_main",
            job_ref="TG-01TESTOUTBOX0000000000000A",
            message_kind="worker_progress",
            payload=payload,
            stage_index=0,
            agent_id="ops_internal_main",
        )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(
            outbox_module.message_dedup_key(
                team_key="internal_main",
                job_ref="TG-01TESTOUTBOX0000000000000A",
                message_kind="worker_progress",
                stage_index=0,
                agent_id="ops_internal_main",
            ),
            "internal_main:TG-01TESTOUTBOX0000000000000A:worker_progress:0:ops_internal_main",
        )

    def test_rollup_message_always_includes_job_ref(self):
        store_module = load_module(STORE_SCRIPT)
        outbox_module = load_module(OUTBOX_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)

        with self.assertRaises(ValueError):
            outbox_module.enqueue_visible_message(
                store,
                team_key="internal_main",
                job_ref="TG-01TESTOUTBOX0000000000000B",
                message_kind="rollup",
                payload={
                    "jobRef": "TG-01TESTOUTBOX0000000000000B",
                    "teamKey": "internal_main",
                    "delivery": {"channel": "feishu", "accountId": "aoteman", "target": "chat:oc_demo"},
                    "message": "【主管最终统一收口】没有编号",
                },
            )

    def test_parallel_stage_only_current_publish_order_callback_is_enqueued(self):
        store_module = load_module(STORE_SCRIPT)
        ingress_module = load_module(INGRESS_SCRIPT)
        controller_module = load_module(CONTROLLER_SCRIPT)
        outbox_module = load_module(OUTBOX_SCRIPT)

        store = store_module.RuntimeStore(":memory:")
        store.initialize()
        self.addCleanup(store.close)
        controller = controller_module.TeamController(store=store)
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_parallel_outbox_001",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 并行方案",
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
            title="parallel ordered publish",
            workflow=workflow,
        )
        controller.plan_ack(job_ref=job["jobRef"])
        outbox_module.deliver_pending_messages(
            store,
            delivery_func=lambda row: {"messageId": f"om_sent_{row['messageKind']}"},
            team_key="internal_main",
        )
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
        self.assertEqual(store.list_pending_outbound_messages(team_key="internal_main"), [])

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

        publishable = controller.collect_publishable_callbacks(job_ref=job["jobRef"])
        self.assertEqual([item["agentId"] for item in publishable], ["ops_internal_main"])

        for callback in publishable:
            payload = callback["payload"]
            outbox_module.enqueue_visible_message(
                store,
                team_key="internal_main",
                job_ref=job["jobRef"],
                message_kind="worker_final",
                payload={
                    "jobRef": job["jobRef"],
                    "teamKey": "internal_main",
                    "delivery": {
                        "channel": "feishu",
                        "accountId": "ops",
                        "target": "chat:oc_demo",
                    },
                    "message": payload["finalDraft"],
                },
                stage_index=callback["stageIndex"],
                agent_id=callback["agentId"],
            )
            controller.mark_callback_published(
                job_ref=job["jobRef"],
                stage_key="analysis",
                agent_id=callback["agentId"],
            )

        pending_after_ops = store.list_pending_outbound_messages(team_key="internal_main")
        self.assertEqual(
            [(row["messageKind"], row["agentId"]) for row in pending_after_ops],
            [("worker_final", "ops_internal_main")],
        )

        publishable_after_ops = controller.collect_publishable_callbacks(job_ref=job["jobRef"])
        self.assertEqual([item["agentId"] for item in publishable_after_ops], ["finance_internal_main"])
