"""Offline JSONL peer for transport tests; it never invokes Codex or a model."""

import json
import sys
import time


def emit(value):
    print(json.dumps(value), flush=True)


for line in sys.stdin:
    request = json.loads(line)
    method = request.get("method")
    request_id = request.get("id")
    if request_id is None:
        continue
    if method == "initialize":
        emit({"id": request_id, "result": {"userAgent": "offline-test"}})
    elif method == "test/echo":
        emit({"id": request_id, "result": request.get("params")})
    elif method == "test/error":
        emit({"id": request_id, "error": {"code": -32000, "message": "fixture failure"}})
    elif method == "test/timeout":
        time.sleep(5)
    elif method == "test/approval":
        emit({"id": "approval-1", "method": "item/commandExecution/requestApproval", "params": {"threadId": "thread-1", "turnId": "turn-1", "itemId": "item-1"}})
        reply = json.loads(sys.stdin.readline())
        if reply.get("result", {}).get("decision") in {"accept", "acceptForSession", "approved", "approved_for_session"}:
            emit({"id": request_id, "result": {"approved": True}})
        else:
            emit({"id": request_id, "error": {"code": -32000, "message": "approval not granted"}})
    elif method == "model/list":
        emit({"id": request_id, "result": {"data": [{"id": "test-luna", "model": "test-luna", "displayName": "Test Luna", "supportedReasoningEfforts": [{"reasoningEffort": "medium", "description": "Routine"}, {"reasoningEffort": "high", "description": "Complex"}], "defaultReasoningEffort": "medium"}], "nextCursor": None}})
    else:
        emit({"id": request_id, "error": {"code": -32601, "message": "unknown fixture method"}})
