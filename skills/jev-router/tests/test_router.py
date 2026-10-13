"""Offline behavior tests. Run: python3 -m unittest discover -s tests -v."""

import copy
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "router.py"
SPEC = importlib.util.spec_from_file_location("jev_router_under_test", SCRIPT)
router = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = router
SPEC.loader.exec_module(router)


MODELS = [
    {"model": "gpt-6-luna", "description": "Routine implementation", "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "Routine"}, {"reasoningEffort": "high", "description": "Complex"}]},
    {"model": "other-live-model", "description": "Other available model", "supportedReasoningEfforts": [{"reasoningEffort": "high", "description": "Complex"}]},
]


class FakeServer:
    calls = []
    inventory = MODELS
    turn_error = None
    session_overrides = {}
    catalog_snapshots = []
    catalog_reads = 0

    def __init__(self, cwd, timeout=30):
        self.cwd = str(cwd)
        self.process = type("Process", (), {"pid": os.getpid()})()
        self.on_event = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def list_models(self):
        cls = type(self)
        cls.catalog_reads += 1
        if cls.catalog_snapshots:
            index = min(cls.catalog_reads - 1, len(cls.catalog_snapshots) - 1)
            return copy.deepcopy(cls.catalog_snapshots[index])
        return copy.deepcopy(self.inventory)

    def request(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method in {"thread/start", "thread/resume"}:
            return {
                "thread": {"id": params.get("threadId", "thread-1")},
                "model": params["model"], "cwd": self.cwd,
                "sandbox": {"type": "readOnly"}, "approvalPolicy": "never",
                "approvalsReviewer": "user",
                "reasoningEffort": params.get("config", {}).get("model_reasoning_effort"),
                **self.session_overrides,
            }
        if method == "turn/start":
            index = len([call for call in self.calls if call[0] == "turn/start"])
            return {"turn": {"id": f"turn-{index}", "status": "inProgress"}}
        if method == "turn/interrupt":
            return {}
        raise AssertionError(f"Unexpected RPC method: {method}")

    def wait_turn(self, thread_id, turn_id, timeout):
        if self.turn_error:
            raise self.turn_error
        return {"id": turn_id, "status": "completed", "items": [{"id": "answer-1", "type": "agentMessage", "text": "Checked offline."}]}


class FakeJev:
    choices = []
    calls = []

    def __init__(self, policy, on_attempt=None):
        self.policy = policy

    def choose(self, question, criteria, state):
        self.calls.append((question, copy.deepcopy(criteria), copy.deepcopy(state)))
        choice = self.choices.pop(0)
        if isinstance(choice, Exception):
            raise choice
        return {"choice": choice, "confidence": 0.8, "probabilities": {choice: 0.8}, "jev_model": "jev-latest", "policy_hash": "test-hash"}


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = router.Store(self.root / "state")
        self.policy = {
            "jev_model": "jev-latest",
            "model_profiles": {"gpt-6-luna": "Preferred implementation model", "unavailable-model": "Not actually available"},
            "effort_profiles": {"medium": "Routine", "high": "Complex"},
            "request_timeout_seconds": 1, "turn_timeout_seconds": 1,
        }
        self.request = {"task": "Inspect the parser", "cwd": str(self.root), "context": "Preserve handling of empty input.", "acceptance": ["Report parser boundary behavior"]}
        FakeServer.calls = []
        FakeServer.inventory = copy.deepcopy(MODELS)
        FakeServer.turn_error = None
        FakeServer.session_overrides = {}
        FakeServer.catalog_snapshots = []
        FakeServer.catalog_reads = 0
        FakeJev.calls = []
        FakeJev.choices = ["gpt-6-luna", "medium"]
        patch_server = mock.patch.object(router, "AppServer", FakeServer)
        patch_jev = mock.patch.object(router, "JevClient", FakeJev)
        patch_server.start()
        patch_jev.start()
        self.addCleanup(patch_server.stop)
        self.addCleanup(patch_jev.stop)
        patch_stderr = mock.patch.object(router.sys, "stderr", io.StringIO())
        patch_stderr.start()
        self.addCleanup(patch_stderr.stop)
        patch_catalog_delay = mock.patch.object(router, "CATALOG_RECHECK_DELAY_SECONDS", 0, create=True)
        patch_catalog_delay.start()
        self.addCleanup(patch_catalog_delay.stop)

    def worker_calls(self):
        return [call for call in FakeServer.calls if call[0] in {"thread/start", "thread/resume", "turn/start"}]

    def test_route_only_limits_candidates_to_live_supported_models(self):
        state = router.start_task(self.request, self.store, self.policy, route_only=True)
        self.assertEqual(state["model"], "gpt-6-luna")
        self.assertEqual(state["effort"], "medium")
        self.assertEqual(state["status"], "routed")
        self.assertFalse(self.worker_calls())
        model_criteria = FakeJev.calls[0][1]
        self.assertIn("gpt-6-luna", model_criteria)
        self.assertNotIn("unavailable-model", model_criteria)
        self.assertTrue(set(model_criteria).issubset({model["model"] for model in MODELS}))
        self.assertEqual(self.store.load(state["task_id"])["model"], "gpt-6-luna")

    def test_unsupported_model_is_rejected_before_worker_creation(self):
        FakeJev.choices = ["unavailable-model"]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertIsNotNone(state["error"])
        self.assertFalse(self.worker_calls())

    def test_unavailable_requested_candidate_is_not_sent_to_jev(self):
        self.request["candidate_models"] = ["unavailable-model"]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertFalse(FakeJev.calls)
        self.assertFalse(self.worker_calls())

    def test_effort_candidates_respect_selected_model_capabilities(self):
        self.policy["effort_profiles"]["ultra"] = "Not supported by selected model"
        router.start_task(self.request, self.store, self.policy, route_only=True)
        effort_criteria = FakeJev.calls[1][1]
        self.assertEqual(set(effort_criteria), {"medium", "high"})

    def test_unsupported_effort_is_rejected_before_worker_creation(self):
        FakeJev.choices = ["gpt-6-luna", "ultra"]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertIsNotNone(state["error"])
        self.assertFalse(self.worker_calls())

    def test_jev_error_never_silently_falls_back_to_default(self):
        FakeJev.choices = [router.RouterError("Invalid Jev response")]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertIsNone(state["model"])
        self.assertFalse(self.worker_calls())

    def test_two_turns_preserve_thread_model_and_context_while_effort_changes(self):
        first = router.start_task(self.request, self.store, self.policy)
        FakeJev.choices = ["high"]
        second = router.continue_task(first["task_id"], "Investigate the nested case.", "A complex ambiguity remains.", self.store, self.policy)
        self.assertEqual(second["model"], first["model"])
        self.assertEqual(second["thread_id"], first["thread_id"])
        self.assertEqual(second["effort"], "high")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["request"]["context"], self.request["context"])
        turns = [params for method, params in FakeServer.calls if method == "turn/start"]
        self.assertEqual([turn["threadId"] for turn in turns], ["thread-1", "thread-1"])
        self.assertEqual([turn["model"] for turn in turns], ["gpt-6-luna", "gpt-6-luna"])
        self.assertEqual([turn["effort"] for turn in turns], ["medium", "high"])
        self.assertIn(self.request["context"], json.dumps(turns[0], ensure_ascii=False))
        self.assertIn("Investigate the nested case.", json.dumps(turns[1]))
        self.assertEqual(len([call for call in FakeJev.calls if call[0] == "model"]), 1)
        resumed = [params for method, params in FakeServer.calls if method == "thread/resume"]
        self.assertEqual(resumed[0]["threadId"], first["thread_id"])
        sessions = [params for method, params in FakeServer.calls if method in {"thread/start", "thread/resume"}]
        self.assertTrue(all(params["sandbox"] == "read-only" for params in sessions))
        self.assertTrue(all(params["approvalPolicy"] == "never" for params in sessions))

    def test_explicit_unsupported_effort_cannot_resume_worker(self):
        first = router.start_task(self.request, self.store, self.policy)
        FakeServer.calls = []
        state = router.continue_task(first["task_id"], "Continue", "More analysis", self.store, self.policy, effort="ultra")
        self.assertEqual(state["status"], "failed")
        self.assertFalse(self.worker_calls())

    def test_disappearing_pinned_model_is_not_replaced(self):
        first = router.start_task(self.request, self.store, self.policy)
        FakeServer.calls = []
        FakeServer.inventory = [copy.deepcopy(MODELS[1])]
        FakeServer.catalog_reads = 0
        self.policy["model_profiles"]["other-live-model"] = "Alternative model"
        state = router.continue_task(first["task_id"], "Continue", "More analysis", self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertFalse(self.worker_calls())
        self.assertEqual(self.store.load(first["task_id"])["model"], "gpt-6-luna")
        self.assertEqual(FakeServer.catalog_reads, router.CATALOG_RECHECK_ATTEMPTS + 1)

    def test_delayed_default_policy_model_is_available_before_routing(self):
        self.policy["model_profiles"] = {"gpt-6-luna": "Preferred implementation model"}
        FakeServer.catalog_snapshots = [[copy.deepcopy(MODELS[1])], copy.deepcopy(MODELS)]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["model"], "gpt-6-luna")
        self.assertEqual(FakeServer.catalog_reads, 2)
        self.assertEqual([method for method, _ in FakeServer.calls].count("thread/start"), 1)
        self.assertEqual([method for method, _ in FakeServer.calls].count("turn/start"), 1)
        self.assertEqual(len(FakeJev.calls), 2)

    def test_delayed_explicit_model_is_available_before_routing(self):
        self.request["candidate_models"] = ["gpt-6-luna"]
        FakeServer.catalog_snapshots = [[copy.deepcopy(MODELS[1])], [copy.deepcopy(MODELS[1])], copy.deepcopy(MODELS)]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["model"], "gpt-6-luna")
        self.assertEqual(FakeServer.catalog_reads, 3)
        self.assertEqual([method for method, _ in FakeServer.calls].count("thread/start"), 1)
        self.assertEqual([method for method, _ in FakeServer.calls].count("turn/start"), 1)
        self.assertEqual(len(FakeJev.calls), 2)

    def test_delayed_pinned_model_resumes_same_thread_without_execution_retry(self):
        first = router.start_task(self.request, self.store, self.policy)
        FakeServer.calls = []
        FakeServer.catalog_reads = 0
        FakeServer.catalog_snapshots = [[copy.deepcopy(MODELS[1])], [copy.deepcopy(MODELS[1])], copy.deepcopy(MODELS)]
        FakeJev.calls = []
        FakeJev.choices = ["high"]
        state = router.continue_task(first["task_id"], "Continue the inspection", "Complex case remains", self.store, self.policy)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["model"], first["model"])
        self.assertEqual(state["thread_id"], first["thread_id"])
        self.assertEqual(state["effort"], "high")
        self.assertEqual(FakeServer.catalog_reads, 3)
        self.assertEqual([method for method, _ in FakeServer.calls].count("thread/resume"), 1)
        self.assertEqual([method for method, _ in FakeServer.calls].count("turn/start"), 1)
        self.assertEqual([question for question, _, _ in FakeJev.calls], ["effort"])

    def test_permanently_missing_explicit_model_stops_after_bounded_catalog_reads(self):
        self.request["candidate_models"] = ["gpt-6-luna"]
        FakeServer.inventory = [copy.deepcopy(MODELS[1])]
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "failed")
        self.assertIsNone(state["model"])
        self.assertIsNotNone(state["error"])
        self.assertEqual(FakeServer.catalog_reads, router.CATALOG_RECHECK_ATTEMPTS + 1)
        self.assertFalse(FakeJev.calls)
        self.assertFalse(self.worker_calls())

    def test_routed_task_first_execution_receives_original_context(self):
        first = router.start_task(self.request, self.store, self.policy, route_only=True)
        FakeJev.choices = ["high"]
        state = router.continue_task(first["task_id"], "Proceed with the assigned inspection.", "Ready to execute", self.store, self.policy)
        self.assertEqual(state["status"], "completed")
        params = [params for method, params in FakeServer.calls if method == "turn/start"][0]
        text = params["input"][0]["text"]
        for required in [self.request["task"], self.request["context"], self.request["acceptance"][0], "Proceed with the assigned inspection."]:
            self.assertIn(required, text)

    def test_turn_timeout_persists_unknown_and_refuses_automatic_continue(self):
        FakeServer.turn_error = router.RouterError("Codex App Server timed out.")
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "unknown")
        self.assertEqual(self.store.load(state["task_id"])["status"], "unknown")
        self.assertEqual([method for method, _ in FakeServer.calls].count("turn/interrupt"), 1)
        FakeServer.calls = []
        with self.assertRaises(router.RouterError):
            router.continue_task(state["task_id"], "Retry", "Timeout", self.store, self.policy)
        self.assertFalse(self.worker_calls())

    def test_approval_request_persists_blocked_state(self):
        FakeServer.turn_error = router.BlockedError("Worker requires approval")
        state = router.start_task(self.request, self.store, self.policy)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(self.store.load(state["task_id"])["status"], "blocked")

    def test_session_model_or_permissions_mismatch_stops_before_turn(self):
        for overrides in [{"model": "other-live-model"}, {"approvalPolicy": "on-request"}, {"sandbox": {"type": "dangerFullAccess"}}, {"sandbox": {"type": "readOnly", "networkAccess": True}}]:
            with self.subTest(overrides=overrides):
                FakeServer.session_overrides = overrides
                FakeServer.calls = []
                FakeJev.choices = ["gpt-6-luna", "medium"]
                state = router.start_task(self.request, self.store, self.policy)
                self.assertEqual(state["status"], "failed")
                self.assertFalse([call for call in FakeServer.calls if call[0] == "turn/start"])


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = router.Store(self.temp.name)
        self.task_id = str(uuid.uuid4())
        self.state = {"task_id": self.task_id, "request": {"task": "Inspect", "sandbox": "read-only"}, "model": "gpt-6-luna", "status": "routed"}

    def test_lock_excludes_second_router_and_releases_after_exit(self):
        other = router.Store(self.temp.name)
        with self.store.lock(self.task_id):
            with self.assertRaises(router.RouterError):
                with other.lock(self.task_id):
                    self.fail("Concurrent ownership must not be possible")
        with other.lock(self.task_id):
            pass

    def test_failed_atomic_replace_preserves_previous_state_and_cleans_temp(self):
        self.store.save(self.state)
        old_bytes = self.store.path(self.task_id).read_bytes()
        updated = {**self.state, "status": "completed"}
        with mock.patch.object(router.os, "replace", side_effect=OSError("Simulated interrupted commit")):
            with self.assertRaises(OSError):
                self.store.save(updated)
        self.assertEqual(self.store.path(self.task_id).read_bytes(), old_bytes)
        self.assertEqual(list(Path(self.temp.name).glob(".state-*")), [])

    def test_saved_model_and_permissions_cannot_be_replaced(self):
        self.store.save(self.state)
        for replacement in [{**self.state, "model": "other-live-model"}, {**self.state, "request": {"task": "Inspect", "sandbox": "workspace-write"}}]:
            with self.subTest(replacement=replacement):
                with self.assertRaises(router.RouterError):
                    self.store.save(replacement)
        self.assertEqual(self.store.load(self.task_id)["model"], "gpt-6-luna")
        self.assertEqual(self.store.load(self.task_id)["request"]["sandbox"], "read-only")

    def test_task_id_cannot_escape_state_directory(self):
        for task_id in ["../../outside", "", "/tmp/state"]:
            with self.subTest(task_id=task_id):
                with self.assertRaises(router.RouterError):
                    self.store.load(task_id)


class JevTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "offline-test-key"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.policy = {"jev_model": "jev-latest", "request_timeout_seconds": 1}
        self.criteria = {"gpt-6-luna": "Routine implementation", "other-live-model": "Complex reasoning"}
        self.payload = {"model": "jev-latest", "answers": {"model": {"choice": "gpt-6-luna", "confidence": 0.8, "probabilities": {"gpt-6-luna": 0.8, "other-live-model": 0.2}}}}

    def choose_with_payload(self, payload):
        opener = mock.Mock()
        opener.open.return_value = io.BytesIO(json.dumps(payload).encode())
        with mock.patch.object(router.urllib.request, "build_opener", return_value=opener):
            result = router.JevClient(self.policy).choose("model", self.criteria, {"task": "Inspect"})
        return result, opener

    def test_valid_structured_choice_and_request(self):
        result, opener = self.choose_with_payload(self.payload)
        self.assertEqual(result["choice"], "gpt-6-luna")
        self.assertEqual(result["confidence"], 0.8)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.typesafe.ai/v1/systemone")
        sent = json.loads(request.data)
        self.assertEqual(sent["questions"]["model"]["criteria"], self.criteria)
        self.assertEqual(json.loads(sent["state"]), {"task": "Inspect"})

    def test_malformed_or_unsupported_jev_response_is_rejected(self):
        invalid = [{}, {"model": "jev-latest", "answers": []}]
        for field, value in [("choice", "unavailable"), ("confidence", True), ("confidence", float("nan")), ("confidence", 1.2), ("probabilities", {}), ("probabilities", {"unavailable": 0.7}), ("probabilities", {"other-live-model": 1.0}), ("probabilities", {"gpt-6-luna": 0.8, "other-live-model": 0.8}), ("probabilities", {"gpt-6-luna": 0.0, "other-live-model": 0.0})]:
            payload = copy.deepcopy(self.payload)
            payload["answers"]["model"][field] = value
            invalid.append(payload)
        for payload in invalid:
            with self.subTest(payload=payload):
                with self.assertRaises(router.RouterError):
                    self.choose_with_payload(payload)

    def test_network_error_is_not_replaced_by_an_invented_choice(self):
        opener = mock.Mock()
        opener.open.side_effect = router.urllib.error.URLError("offline failure")
        with mock.patch.object(router.urllib.request, "build_opener", return_value=opener):
            with self.assertRaises(router.RouterError):
                router.JevClient(self.policy).choose("model", {"gpt-6-luna": "Routine"}, {})


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        fixture = Path(__file__).with_name("fake_app_server.py")
        actual_popen = subprocess.Popen

        def fake_popen(_command, *args, **kwargs):
            return actual_popen([sys.executable, str(fixture)], *args, **kwargs)

        patcher = mock.patch.object(router.subprocess, "Popen", side_effect=fake_popen)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_jsonl_round_trip_and_live_inventory(self):
        with router.AppServer(self.temp.name, timeout=1) as server:
            self.assertEqual(server.request("test/echo", {"unicode": "参数", "value": 42}), {"unicode": "参数", "value": 42})
            self.assertEqual(server.list_models()[0]["model"], "test-luna")

    def test_rpc_error_is_reported(self):
        with router.AppServer(self.temp.name, timeout=1) as server:
            with self.assertRaises(router.RouterError):
                server.request("test/error", {})

    def test_timeout_is_bounded_and_reported(self):
        with router.AppServer(self.temp.name, timeout=0.1) as server:
            with self.assertRaises(router.RouterError):
                server.request("test/timeout", {})

    def test_approval_request_is_never_automatically_accepted(self):
        with router.AppServer(self.temp.name, timeout=0.2) as server:
            with self.assertRaises(router.RouterError):
                server.request("test/approval", {})


if __name__ == "__main__":
    unittest.main()
