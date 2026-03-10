"""Contract tests for the redesigned ingress adapter.

Design reference:
- docs/plans/2026-03-10-v51-control-plane-redesign-design.md
"""

import dataclasses
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


def load_store_module():
    if not STORE_SCRIPT.exists():
        raise AssertionError(f"缺少重构模块: {STORE_SCRIPT}")
    spec = importlib.util.spec_from_file_location(STORE_SCRIPT.stem, STORE_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载模块: {STORE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_ingress_module():
    if not INGRESS_SCRIPT.exists():
        raise AssertionError(f"缺少重构模块: {INGRESS_SCRIPT}")
    spec = importlib.util.spec_from_file_location(INGRESS_SCRIPT.stem, INGRESS_SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"无法加载模块: {INGRESS_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class IngressAdapterContractTests(unittest.TestCase):
    def test_ingress_adapter_exposes_inbound_event_contract(self):
        module = load_ingress_module()

        self.assertTrue(hasattr(module, "InboundEvent"))
        self.assertTrue(dataclasses.is_dataclass(module.InboundEvent))
        self.assertTrue(hasattr(module, "canonicalize_target"))
        self.assertTrue(hasattr(module, "extract_inbound_event"))
        self.assertTrue(hasattr(module, "persist_inbound_event"))
        self.assertTrue(hasattr(module, "claim_inbound_event"))
        self.assertTrue(hasattr(module, "find_unclaimed_inbound_event_for_team"))

    def test_ingress_adapter_canonicalizes_chat_prefixed_group_target(self):
        module = load_ingress_module()

        self.assertEqual(module.canonicalize_target("chat:oc_demo"), "oc_demo")
        self.assertEqual(module.canonicalize_target("oc_demo"), "oc_demo")

    def test_ingress_adapter_extracts_team_scoped_event(self):
        module = load_ingress_module()

        event = module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_123",
            canonical_target_id="chat:oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )

        self.assertEqual(event.team_key, "internal_main")
        self.assertEqual(event.source_message_id, "om_123")
        self.assertEqual(event.canonical_target_id, "oc_demo")
        self.assertEqual(event.request_text, "@奥特曼 帮我做方案")
        self.assertEqual(event.account_id, "aoteman")
        self.assertEqual(event.channel, "feishu")
        self.assertEqual(event.mentioned_agent_id, "supervisor_internal_main")

    def test_ingress_adapter_persists_and_claims_unclaimed_event(self):
        store_module = load_store_module()
        ingress_module = load_ingress_module()

        store = store_module.RuntimeStore(":memory:")
        self.addCleanup(store.close)
        store.initialize()
        event = ingress_module.extract_inbound_event(
            team_key="internal_main",
            source_message_id="om_123",
            canonical_target_id="chat:oc_demo",
            request_text="@奥特曼 帮我做方案",
            requested_by="ou_demo",
            account_id="aoteman",
            mentioned_agent_id="supervisor_internal_main",
        )

        persisted = ingress_module.persist_inbound_event(store, event)
        pending = ingress_module.find_unclaimed_inbound_event_for_team(store, "internal_main")
        claimed = ingress_module.claim_inbound_event(
            store,
            team_key="internal_main",
            source_message_id="om_123",
            job_ref="TG-01TESTCLAIM00000000000000",
        )
        missing = ingress_module.find_unclaimed_inbound_event_for_team(store, "internal_main")

        self.assertTrue(persisted["created"])
        assert pending is not None
        self.assertEqual(pending.source_message_id, "om_123")
        self.assertTrue(claimed["claimed"])
        self.assertIsNone(missing)
