"""Usage accounting fixtures: all Jev HTTP and worker calls stay offline."""

import copy
from email.message import Message
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_router import FakeServer, MODELS, router


class UsageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.store = router.Store(self.root / "state")
        self.policy = {"jev_model": "jev-latest", "request_timeout_seconds": 1,
                       "model_profiles": {"gpt-6-luna": "Routine"},
                       "effort_profiles": {"medium": "Routine", "high": "Complex"}}
        self.request = {"task": "Inspect parser", "cwd": str(self.root)}
        FakeServer.calls = []
        FakeServer.inventory = copy.deepcopy(MODELS)
        FakeServer.turn_error = None
        FakeServer.session_overrides = {}
        FakeServer.catalog_snapshots = []
        FakeServer.catalog_reads = 0
        self.opener = mock.Mock()
        for patcher in [mock.patch.object(router, "AppServer", FakeServer),
                        mock.patch.object(router.urllib.request, "build_opener", return_value=self.opener),
                        mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": "secret-test-api-key"}),
                        mock.patch.object(router.sys, "stderr", io.StringIO())]:
            patcher.start()
            self.addCleanup(patcher.stop)

    def response(self, kind="model", choice="gpt-6-luna", usage=None, headers=None, invalid=False):
        payload = {"model": "jev-latest", "usage": usage,
                   "answers": {kind: {"choice": choice, "confidence": 1,
                                      "probabilities": {choice: 1}}}}
        if invalid:
            payload["answers"] = "secret-response-body"
        response = io.BytesIO(json.dumps(payload).encode())
        response.headers = Message()
        for name, value in (headers or {}).items():
            response.headers[name] = value
        return response

    def start(self, responses):
        self.opener.open.side_effect = responses
        return router.start_task(self.request, self.store, self.policy, route_only=True)

    def test_success_is_saved_before_transport_and_aggregates_across_continue(self):
        responses = [self.response(usage={"input_tokens": 10, "output_tokens": 2},
                                   headers={"X-Request-ID": "req-123"}),
                     self.response("effort", "medium", {"input_tokens": 5, "output_tokens": 1}),
                     self.response("effort", "high", {"input_tokens": 7, "output_tokens": 3})]

        def transport(*args, **kwargs):
            saved = json.loads(next(self.store.directory.glob("*.json")).read_text())
            attempt = saved["jev_attempts"][-1]
            self.assertEqual(attempt["status"], "started")
            self.assertIsNone(attempt["usage"]["input_tokens"])
            self.assertNotIn("secret-test-api-key", json.dumps(saved))
            return responses.pop(0)

        self.opener.open.side_effect = transport
        first = router.start_task(self.request, self.store, self.policy, route_only=True)
        self.assertEqual(first["status"], "routed")
        second = router.continue_task(first["task_id"], "Inspect next case", "Needs reasoning", self.store, self.policy)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(second["model"], first["model"])
        self.assertEqual(self.opener.open.call_count, 3)
        saved = self.store.load(first["task_id"])
        attempts = saved["jev_attempts"]
        self.assertEqual([a["kind"] for a in attempts], ["model", "effort", "effort"])
        self.assertEqual(len({a["call_id"] for a in attempts}), 3)
        self.assertEqual([d["call_id"] for d in saved["decisions"]], [a["call_id"] for a in attempts])
        self.assertTrue(all(a["status"] == "success" and a["duration_seconds"] >= 0 and a["started_at"] for a in attempts))
        self.assertEqual(attempts[0]["request_id"], "req-123")
        usage = router.summary(saved, self.store)["jev_usage"]
        self.assertEqual((usage["known_input_tokens"], usage["known_output_tokens"], usage["known_total_tokens"]), (22, 6, 28))
        self.assertTrue(usage["complete"])
        self.assertEqual(usage["unknown_usage_count"], 0)

    def test_invalid_answer_preserves_usage_and_omits_body_and_headers(self):
        state = self.start([self.response(usage={"input_tokens": 11, "output_tokens": 4},
                            headers={"X-Request-ID": "req-safe", "Set-Cookie": "secret-cookie"}, invalid=True)])
        saved = self.store.load(state["task_id"])
        self.assertEqual(saved["status"], "failed")
        self.assertEqual(saved["jev_attempts"][0]["status"], "invalid_response")
        self.assertEqual(saved["jev_attempts"][0]["response_model"], "jev-latest")
        self.assertEqual(router.usage_summary(saved)["known_total_tokens"], 15)
        self.assertTrue(router.usage_summary(saved)["complete"])
        self.assertFalse(saved["decisions"])
        self.assertEqual(self.opener.open.call_count, 1)
        for secret in ["secret-response-body", "secret-cookie", "secret-test-api-key", "Authorization"]:
            self.assertNotIn(secret, json.dumps(saved))

    def test_http_and_network_errors_keep_unknown_usage_without_retry(self):
        headers = Message()
        headers["X-Request-ID"] = "req-error"
        for error, status in [(router.urllib.error.HTTPError("https://example.invalid", 429, "secret-error", headers, io.BytesIO(b"secret-body")), "http_error"),
                              (router.urllib.error.URLError("secret-network-detail"), "network_error"),
                              (TimeoutError("secret-timeout"), "network_error")]:
            with self.subTest(status=status):
                self.opener.open.reset_mock()
                state = self.start([error])
                saved = self.store.load(state["task_id"])
                attempt = saved["jev_attempts"][0]
                self.assertEqual(attempt["status"], status)
                self.assertEqual(attempt["usage"], {"input_tokens": None, "output_tokens": None})
                usage = router.usage_summary(saved)
                self.assertEqual(usage["unknown_usage_count"], 1)
                self.assertEqual(usage["known_total_tokens"], 0)
                self.assertFalse(usage["complete"])
                self.assertEqual(self.opener.open.call_count, 1)
                self.assertNotIn("secret-", json.dumps(saved))
                if status == "http_error":
                    self.assertEqual(attempt["http_status"], 429)
                    self.assertEqual(attempt["request_id"], "req-error")

    def test_missing_malformed_and_partial_usage_remain_unknown(self):
        for usage in [None, [], "12", {}, {"input_tokens": -1, "output_tokens": True},
                      {"input_tokens": 1.2, "output_tokens": "4"},
                      {"input_tokens": 8}, {"input_tokens": False, "output_tokens": 2}]:
            with self.subTest(usage=usage):
                state = self.start([self.response(usage=usage), self.response("effort", "medium")])
                saved = self.store.load(state["task_id"])
                self.assertEqual(saved["status"], "routed")
                result = router.usage_summary(saved)
                self.assertEqual(result["unknown_usage_count"], 2)
                self.assertFalse(result["complete"])
                expected = 8 if usage == {"input_tokens": 8} else 2 if usage == {"input_tokens": False, "output_tokens": 2} else 0
                self.assertEqual(result["known_total_tokens"], expected)

    def test_zero_tokens_are_known_and_override_adds_no_api_attempt(self):
        zero = {"input_tokens": 0, "output_tokens": 0}
        first = self.start([self.response(usage=zero), self.response("effort", "medium", zero)])
        second = router.continue_task(first["task_id"], "Continue", "Ready", self.store, self.policy, effort="high")
        self.assertEqual(second["status"], "completed")
        self.assertEqual(self.opener.open.call_count, 2)
        self.assertEqual(len(second["jev_attempts"]), 2)
        usage = router.usage_summary(second)
        self.assertTrue(usage["complete"])
        self.assertEqual(usage["known_total_tokens"], 0)
        self.assertEqual(usage["legacy_decisions_without_attempt"], 0)

    def test_legacy_state_status_is_read_only_and_stays_incomplete_after_continue(self):
        zero = {"input_tokens": 0, "output_tokens": 0}
        state = self.start([self.response(usage=zero), self.response("effort", "medium", zero)])
        state.pop("jev_attempts")
        state.pop("jev_usage_history_complete")
        for decision in state["decisions"]:
            decision.pop("call_id")
        state["decisions"].append({"kind": "effort", "choice": "medium", "source": "explicit_override"})
        self.store.save(state)
        path = self.store.path(state["task_id"])
        original = path.read_bytes()
        output = io.StringIO()
        with mock.patch.object(router.sys, "stdout", output):
            self.assertEqual(router.main(["status", "--task", state["task_id"], "--state-dir", str(self.store.directory)]), 0)
        self.assertEqual(path.read_bytes(), original)
        usage = json.loads(output.getvalue())["jev_usage"]
        self.assertEqual(usage["legacy_decisions_without_attempt"], 2)
        self.assertEqual(usage["unknown_usage_count"], 2)
        self.assertFalse(usage["complete"])
        self.opener.open.side_effect = [self.response("effort", "high", {"input_tokens": 9, "output_tokens": 1})]
        second = router.continue_task(state["task_id"], "Continue", "Ready", self.store, self.policy)
        usage = router.usage_summary(second)
        self.assertEqual(second["status"], "completed")
        self.assertEqual(usage["attempt_count"], 1)
        self.assertEqual(usage["known_total_tokens"], 10)
        self.assertFalse(usage["complete"])
        self.assertFalse(usage["history_complete"])

    def test_request_id_allowlist_and_sanitization(self):
        for value in ["secret-test-api-key", "bad request id", "x" * 129, "nonascii-参数"]:
            with self.subTest(value=value):
                state = self.start([self.response(headers={"X-Request-ID": value, "X-Custom-ID": "unapproved"}, invalid=True)])
                self.assertIsNone(state["jev_attempts"][0]["request_id"])
                self.assertNotIn(value, json.dumps(state, ensure_ascii=False))

    def test_response_model_is_sanitized_without_losing_usage(self):
        response = self.response(usage={"input_tokens": 3, "output_tokens": 1}, invalid=True)
        payload = json.loads(response.getvalue())
        payload["model"] = "secret-test-api-key"
        state = self.start([io.BytesIO(json.dumps(payload).encode())])
        self.assertIsNone(state["jev_attempts"][0]["response_model"])
        self.assertEqual(router.usage_summary(state)["known_total_tokens"], 4)
        self.assertNotIn("secret-test-api-key", json.dumps(state))

    def test_preflight_failure_does_not_create_api_attempt(self):
        with mock.patch.dict(os.environ, {"TYPESAFE_API_KEY": ""}):
            state = router.start_task(self.request, self.store, self.policy, route_only=True)
        self.assertEqual(state["status"], "failed")
        self.assertEqual(state["jev_attempts"], [])
        self.opener.open.assert_not_called()

    def test_non_json_response_and_interruption_are_accounted(self):
        for outcome, status in [(io.BytesIO(b"secret-invalid-json"), "invalid_response"),
                                (KeyboardInterrupt(), "interrupted_or_failed")]:
            with self.subTest(status=status):
                state = self.start([outcome])
                saved = self.store.load(state["task_id"])
                self.assertEqual(saved["jev_attempts"][0]["status"], status)
                self.assertFalse(router.usage_summary(saved)["complete"])
                self.assertNotIn("secret-invalid-json", json.dumps(saved))


if __name__ == "__main__":
    unittest.main()
