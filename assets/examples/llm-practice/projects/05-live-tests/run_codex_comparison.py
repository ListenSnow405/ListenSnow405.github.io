"""独立 Codex 调用的受控输出测试；不等同于 Platform Responses API。"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from evaluate_records import ROOT, evaluate


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs=2, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--effort", default="low")
    args = parser.parse_args()
    if args.repeats < 1 or args.repeats > 3:
        parser.error("repeats must be between 1 and 3")
    codex = shutil.which("codex")
    if not codex:
        parser.error("codex not found")
    args.out.mkdir(parents=True, exist_ok=False)
    prompt_bytes = (ROOT / "prompts/05-01-extract.txt").read_bytes()
    prompt = prompt_bytes.decode("utf-8")
    schema = ROOT / "projects/05-file-output/records.schema.json"
    (args.out / "prompt.txt").write_bytes(prompt_bytes)
    (args.out / "records.schema.json").write_bytes(schema.read_bytes())
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    summary = {"transport": "Codex CLI / existing login", "platform_api_tested": False,
               "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
               "schema_sha256": hashlib.sha256(schema.read_bytes()).hexdigest(),
               "effort": args.effort, "repeats": args.repeats,
               "cli_version": subprocess.run([codex, "--version"], capture_output=True,
                   text=True, encoding="utf-8", env=env).stdout.strip(), "runs": []}
    # 按重复、模式、模型交错执行，原始产物不修复、不加围栏清理。
    for repeat in range(1, args.repeats + 1):
        for mode in ("plain", "schema"):
            for index, model in enumerate(args.models, 1):
                run_dir = args.out / f"model-{index}-{mode}-{repeat:02}"
                workspace = run_dir / "empty-workspace"
                workspace.mkdir(parents=True)
                output = run_dir / "records.json"
                command = [codex, "exec", "--ignore-user-config", "--ephemeral",
                           "--skip-git-repo-check", "--sandbox", "read-only", "--model", model,
                           "-c", f'model_reasoning_effort="{args.effort}"', "-C", str(workspace),
                           "--json", "--output-last-message", str(output.resolve())]
                if mode == "schema":
                    command.extend(["--output-schema", str(schema.resolve())])
                command.append("-")
                started = datetime.now(timezone.utc).isoformat()
                clock = time.perf_counter()
                result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                        encoding="utf-8", errors="replace", env=env, timeout=300)
                duration = round(time.perf_counter() - clock, 3)
                (run_dir / "events.jsonl").write_text(result.stdout, encoding="utf-8", newline="\n")
                (run_dir / "stderr.txt").write_text(result.stderr, encoding="utf-8", newline="\n")
                events = []
                for line in result.stdout.splitlines():
                    try:
                        events.append(json.loads(line))
                    except ValueError:
                        pass
                items = [event.get("item", {}).get("type") for event in events
                         if event.get("type") == "item.completed"]
                tools = [item for item in items if item not in (None, "agent_message", "reasoning")]
                usage = next((event.get("usage") for event in events
                              if event.get("type") == "turn.completed"), None)
                grade = evaluate(output) if output.exists() else {"error": "no final output"}
                metadata = {"model_requested": model, "mode": mode, "repeat": repeat,
                            "started_utc": started, "elapsed_seconds": duration,
                            "exit_code": result.returncode, "tool_items": tools, "usage": usage,
                            "grade": grade, "directory": run_dir.name,
                            "backend_snapshot": "not exposed by CLI events"}
                write_json(run_dir / "result.json", metadata)
                summary["runs"].append(metadata)
                write_json(args.out / "summary.json", summary)
                print(f"{model} {mode} #{repeat}: exit={result.returncode}; "
                      f"contract={grade.get('contract_pass')}; facts={grade.get('fact_matches')}/12; "
                      f"refs={grade.get('reference_coverage')}/12; tool_items={len(tools)}", flush=True)
                # 避免把有工具读取的结果算作仅使用固定 Prompt 的独立试验。
                if tools:
                    print("Run excluded from clean comparison: unexpected tool usage.", flush=True)


if __name__ == "__main__":
    main()
