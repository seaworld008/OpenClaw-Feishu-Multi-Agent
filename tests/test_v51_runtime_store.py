"""Contract tests for the redesigned runtime store.

Design reference:
- docs/plans/2026-03-10-v51-control-plane-redesign-design.md
"""

import importlib.util
import sqlite3
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STORE_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_runtime_store.py"
)
JOB_REGISTRY_SCRIPT = (
    REPO_ROOT / "skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py"
)


def load_store_module():
    if not STORE_SCRIPT.exists():
        raise AssertionError(f"缺少重构模块: {STORE_SCRIPT}")
    spec = importlib.util.spec_from_file_location(STORE_SCRIPT.stem, STORE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载模块: {STORE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_registry_module():
    spec = importlib.util.spec_from_file_location(JOB_REGISTRY_SCRIPT.stem, JOB_REGISTRY_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载模块: {JOB_REGISTRY_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeStoreContractTests(unittest.TestCase):
    def test_runtime_store_module_exposes_team_first_api(self):
        module = load_store_module()

        self.assertTrue(hasattr(module, "RuntimeStore"))
        store = module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        for method_name in (
            "initialize",
            "record_inbound_event",
            "enqueue_outbound_message",
            "acquire_controller_lock",
        ):
            self.assertTrue(hasattr(store, method_name), method_name)

    def test_runtime_store_records_inbound_events_idempotently_per_team(self):
        module = load_store_module()
        store = module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        store.initialize()

        first = store.record_inbound_event(
            team_key="internal_main",
            source_message_id="om_same",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 第一条",
            requested_by="ou_demo",
        )
        second = store.record_inbound_event(
            team_key="internal_main",
            source_message_id="om_same",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 第一条重复",
            requested_by="ou_demo",
        )
        third = store.record_inbound_event(
            team_key="external_main",
            source_message_id="om_same",
            canonical_target_id="oc_demo",
            request_text="@奥特曼 跨 team",
            requested_by="ou_demo",
        )

        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertTrue(third["created"])

    def test_runtime_store_controller_lock_is_scoped_by_team_key(self):
        module = load_store_module()
        store = module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        store.initialize()

        self.assertTrue(
            store.acquire_controller_lock(
                team_key="internal_main",
                owner="test-owner-a",
                ttl_seconds=30,
            )
        )

    def test_registry_init_db_bootstraps_runtime_store_schema(self):
        registry = load_registry_module()
        conn = sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory = sqlite3.Row

        registry.init_db(conn)

        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        self.assertTrue(
            {"inbound_events", "outbound_messages", "stage_callbacks", "controller_locks"}.issubset(tables)
        )

    def test_runtime_store_bootstraps_parallel_publish_gate_schema_and_api(self):
        module = load_store_module()
        store = module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        store.initialize()

        tables = {
            row["name"]
            for row in store.connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        }
        self.assertIn("publish_gates", tables)
        for method_name in (
            "create_publish_gate",
            "get_publish_gate",
            "advance_publish_gate",
        ):
            self.assertTrue(hasattr(store, method_name), method_name)

    def test_runtime_store_tracks_publish_order_and_cursor_for_parallel_stage(self):
        module = load_store_module()
        store = module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        store.initialize()

        gate = store.create_publish_gate(
            job_ref="TG_parallel_001",
            stage_key="analysis",
            mode="parallel",
            publish_order=["ops_internal_main", "finance_internal_main", "legal_internal_main"],
        )
        self.assertEqual(gate["publishCursor"], 0)
        self.assertEqual(gate["stageStatus"], "pending")

        advanced = store.advance_publish_gate(
            job_ref="TG_parallel_001",
            stage_key="analysis",
            published_agent_id="ops_internal_main",
        )
        self.assertEqual(advanced["publishCursor"], 1)
        self.assertEqual(advanced["nextAgentId"], "finance_internal_main")
