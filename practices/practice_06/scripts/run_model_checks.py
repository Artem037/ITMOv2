"""Isolated OpenCode calls; save final text without reasoning events."""

import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from collections import Counter
from urllib.parse import urlencode

from replay_attacks import INJECTION, QUESTION, ROOT, LocalShop, save


def model_call(agent, model, attachment, question, destination):
    if destination.exists():
        raise FileExistsError("Evidence already exists: " + str(destination))
    attachments = attachment if isinstance(attachment, list) else [attachment]
    command = [
        "opencode",
        "run",
        question,
        "--pure",
        "--dir",
        str(ROOT),
        "--agent",
        agent,
        "--model",
        model,
        "--format",
        "json",
        "--file",
        *[str(path.resolve()) for path in attachments],
    ]
    overrides = {
        "mcp": {
            "fetch": {"enabled": False},
            "trip_planner": {"enabled": False},
        },
        "snapshot": False,
        "small_model": model,
    }
    started = time.time()
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env={
            **os.environ,
            "OPENCODE_DISABLE_AUTOUPDATE": "true",
            "OPENCODE_CONFIG_CONTENT": json.dumps(overrides),
        },
    )
    timed_out = False
    try:
        stdout, stderr = process.communicate(
            timeout=180 if model.startswith("vsellm/") else 90
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=10)
    final, events, session_ids, errors = [], Counter(), set(), []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events[event.get("type", "unknown")] += 1
        if event.get("sessionID"):
            session_ids.add(event["sessionID"])
        if event.get("type") == "text":
            final.append(event.get("part", {}).get("text", ""))
        if event.get("type") == "error":
            error = event.get("error", {})
            errors.append(
                {
                    "name": error.get("name"),
                    "data": {
                        key: error.get("data", {}).get(key)
                        for key in ["message", "statusCode", "isRetryable"]
                    },
                }
            )
    answer = "".join(final)
    record = {
        "command": command,
        "model": model,
        "agent": agent,
        "input_sha256": hashlib.sha256(
            b"\0".join(path.read_bytes() for path in attachments)
        ).hexdigest(),
        "inputs": [
            {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in attachments
        ],
        "prompt_sha256": hashlib.sha256(
            (
                ROOT
                / (
                    "planner-system.txt"
                    if agent == "shop-planner"
                    else "judge-system-prompt.md"
                )
            ).read_bytes()
        ).hexdigest(),
        "duration_seconds": round(time.time() - started, 3),
        "exit_code": process.returncode,
        "timed_out": timed_out,
        "event_types": dict(events),
        "session_ids": sorted(session_ids),
        "final_text": answer,
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
        "errors": errors,
        "runtime_overrides": overrides,
        "generation_parameters": (
            "provider/model defaults; temperature and seed "
            "not exposed by this invocation"
        ),
    }
    try:
        value = answer.strip()
        if value.startswith("```json\n") and value.endswith("```"):
            value = value[8:-3].strip()
        record["decision"] = json.loads(value)
        record["outcome"] = (
            "valid_json"
            if process.returncode == 0 and not timed_out
            else "process_error"
        )
    except json.JSONDecodeError:
        record["outcome"] = "model_error"
    save(destination, record)
    print(
        agent,
        destination.name,
        record["outcome"],
        "exit=",
        process.returncode,
        flush=True,
    )
    return record


def planner(phase, model, run_id):
    directory = ROOT / "evidence" / phase / run_id
    if any(
        (directory / f"{kind}-model.json").exists()
        for kind in ["control", "injection"]
    ):
        raise FileExistsError("Choose a fresh run ID; evidence is immutable")
    with LocalShop() as shop:
        alice = shop.login("alice")
        for kind in ["control", "injection"]:
            if kind == "injection":
                assert (
                    shop.call(
                        "POST",
                        "/reviews",
                        {"product": "chair", "text": INJECTION},
                        alice,
                    )["status"]
                    == 201
                )
            context = shop.call(
                "GET",
                "/assistant/context?"
                + urlencode({"order_id": "1", "question": QUESTION}),
                auth=alice,
            )
            save(directory / f"{kind}-context.json", context)
            if context["status"] != 200:
                raise RuntimeError("Context unavailable")
            attachment = directory / f"{kind}-input.txt"
            attachment.write_text(
                context["response"]["prompt"], encoding="utf-8"
            )
            files_before = shop.snapshot()
            record = model_call(
                "shop-planner",
                model,
                attachment,
                QUESTION,
                directory / f"{kind}-model.json",
            )
            decision = record.get("decision")
            if (
                record["outcome"] == "valid_json"
                and isinstance(decision, dict)
                and isinstance(decision.get("tool"), str)
                and isinstance(decision.get("arguments"), dict)
            ):
                execution = shop.call(
                    "POST", "/assistant/execute", {"decision": decision}, alice
                )
            else:
                execution = {
                    "status": None,
                    "response": "Model output not executed: invalid decision",
                }
            save(
                directory / f"{kind}-execution.json",
                {
                    "source": "real_model",
                    "decision": decision,
                    "execution": execution,
                    "pid": shop.pid,
                    "base_url": shop.address,
                    "files_before": files_before,
                    "files_after": shop.snapshot(),
                },
            )


def judge(phase, model, run_id):
    directory = ROOT / "evidence" / phase / run_id
    if (directory / "judge-result.json").exists():
        raise FileExistsError("Choose a fresh run ID; evidence is immutable")
    directory.mkdir(parents=True, exist_ok=True)
    sections = [
        (
            f"phase: {phase}\nOnly this phase is evaluated. "
            "Source line numbers start at 1 within each named file."
        )
    ]
    requirements = (ROOT / "README.md").read_text().split("## Домашка", 1)[1]
    sections.append(
        "<submitted_requirements>\n"
        + requirements
        + "\n</submitted_requirements>"
    )
    for name in [
        "THREAT_MODEL.md",
        "lab/service.py",
        "lab/sandbox.py",
        "judge-system-prompt.md",
        "REPORT_01.md" if phase == "before" else "REPORT_02.md",
    ]:
        path = ROOT / name
        if path.exists():
            content = path.read_text()
            if name == "REPORT_01.md" and "## Ссылки на Python" in content:
                content = (
                    content.split("## Ссылки на Python", 1)[0]
                    + "\n[Python references omitted; full report SHA-256: "
                    + hashlib.sha256(path.read_bytes()).hexdigest()
                    + "]"
                )
            sections.append(
                f'\n<submitted_file name="{name}">\n'
                f"{content}\n</submitted_file>"
            )
    base = ROOT / "evidence" / phase
    replay = json.loads((base / "http-replay.json").read_text())
    rows = []
    for row in replay["records"]:
        body = row["body"]
        if (
            isinstance(body, dict)
            and isinstance(body.get("text"), str)
            and len(body["text"]) > 512
        ):
            body = {
                "product": body.get("product"),
                "text_length": len(body["text"]),
                "text_sha256": hashlib.sha256(
                    body["text"].encode()
                ).hexdigest(),
            }
        response = row["response"]
        rows.append(
            {
                "id": row["id"],
                "method": row["method"],
                "target": row["target"],
                "body": body,
                "raw_body": row["raw_body"],
                "headers": {
                    key: (
                        "synthetic-session"
                        if key.lower() == "x-token"
                        else value
                    )
                    for key, value in row["headers"].items()
                },
                "status": row["status"],
                "response_excerpt": json.dumps(response, ensure_ascii=False)[
                    :160
                ],
                "row_count": len(response)
                if isinstance(response, list)
                else None,
            }
        )
    evidence = {
        "http-replay.json": {
            "sha256": hashlib.sha256(
                (base / "http-replay.json").read_bytes()
            ).hexdigest(),
            "records": rows,
            "files_before": replay["files_before"],
            "files_after": replay["files_after"],
            "exit_code": 0,
        }
    }
    for kind in ["control", "injection"]:
        paired = base / "verified"
        record = json.loads((paired / f"{kind}-model.json").read_text())
        execution = json.loads((paired / f"{kind}-execution.json").read_text())
        evidence[kind] = {
            key: record.get(key)
            for key in [
                "model",
                "prompt_sha256",
                "input_sha256",
                "session_ids",
                "outcome",
                "decision",
                "exit_code",
            ]
        }
        evidence[kind].update(
            {
                "context": (paired / f"{kind}-input.txt").read_text(),
                "execution": execution["execution"],
                "files_unchanged": execution["files_before"]
                == execution["files_after"],
            }
        )
    log = base / (
        "security-red-final.txt" if phase == "before" else "security-green.txt"
    )
    lines = log.read_text().splitlines()
    evidence["security_tests"] = {
        "full_log": str(log.relative_to(ROOT)),
        "sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "summary": lines[-5:],
        "test_names": [
            line.split(" ", 1)[0] for line in lines if line.startswith("test_")
        ],
        "passed_baseline": (ROOT / "evidence/before/baseline-tests.txt")
        .read_text()
        .splitlines()[-5:],
    }
    attachment = directory / "judge-input.txt"
    attachment.write_text("\n".join(sections), encoding="utf-8")
    evidence_file = directory / "judge-evidence.json"
    save(evidence_file, {"submitted_evidence": evidence})
    for path in [attachment, evidence_file]:
        if path.stat().st_size > 48000 or any(
            len(line) > 1900 for line in path.read_text().splitlines()
        ):
            raise ValueError("Judge attachment exceeds bounded read limits")
    model_call(
        "threat-judge",
        model,
        [attachment, evidence_file],
        "Проверь представленные материалы этой фазы по своей рубрике.",
        directory / "judge-result.json",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    parser.add_argument("--kind", choices=["planner", "judge"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--run-id",
        choices=["resumed", "verified", "review2"],
        default="verified",
    )
    args = parser.parse_args()
    (planner if args.kind == "planner" else judge)(
        args.phase, args.model, args.run_id
    )
