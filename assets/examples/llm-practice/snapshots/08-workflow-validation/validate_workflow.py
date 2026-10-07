"""第八篇程序验收：在独立临时副本运行，不调用模型或修改博客练习输入。

显式使用独立参考 JSON 作为程序测试夹具，不把这些结果统计为模型表现。
--out 指向一个尚不存在的验证记录 JSON；保留临时目录便于复查现场。
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "projects/08-agent-workflow"
REFERENCE = ROOT / "expected/05-output/records.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("验证记录已存在，请另选新文件")
    folder = Path(tempfile.mkdtemp(prefix="llm-08-validation-"))
    project = folder / "08-agent-workflow"
    shutil.copytree(PROJECT, project, ignore=shutil.ignore_patterns("runs", "__pycache__"))
    fixed_before = {path.name: sha(path) for path in project.iterdir() if path.is_file()}
    data = json.loads(REFERENCE.read_text(encoding="utf-8"))
    record = {"system": sys.platform, "python": sys.version.split()[0],
              "project_version": "08-workflow/1.0", "workspace": str(project),
              "fixture": "expected/05-output/records.json; independent program fixture, not model output",
              "commands": [], "checks": [], "model_calls": 0}
    environment = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")

    def command(*arguments, code=0, script="workflow.py"):
        result = subprocess.run([sys.executable, script, *arguments], cwd=project,
                                env=environment, text=True, encoding="utf-8", capture_output=True)
        record["commands"].append({"script": script, "args": list(arguments),
                                   "exit_code": result.returncode, "stdout": result.stdout,
                                   "stderr": result.stderr})
        if result.returncode != code:
            raise AssertionError(f"退出码 {result.returncode} != {code}: {arguments}; {result.stdout}")
        return result

    def state(run):
        return json.loads((project / f"runs/{run}/state.json").read_text(encoding="utf-8"))

    def events(run):
        return [json.loads(line) for line in (project / f"runs/{run}/events.jsonl").read_text(encoding="utf-8").splitlines()]

    def candidate(run, value=data, name="candidate-v1.json"):
        path = project / f"runs/{run}/inbox/{name}"
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
        return "inbox/" + name

    def snapshot(run):
        return {str(path.relative_to(project)): (sha(path), path.stat().st_mtime_ns)
                for path in (project / f"runs/{run}").rglob("*") if path.is_file()}

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        record["checks"].append({"name": name, "passed": True})

    try:
        command("start", "demo-01", "--fault", "S3:once", code=1)
        initial = state("demo-01")
        check("injected read failure stops downstream", initial["status"] == "failed" and
              initial["stage"] == "read" and initial["reads"]["S3"]["attempts"] == 1 and
              not (project / "runs/demo-01/evidence.txt").exists())
        before = {source: (sha(project / f"runs/demo-01/read/{source}.txt"),
                          (project / f"runs/demo-01/read/{source}.txt").stat().st_mtime_ns)
                  for source in ("S1", "S2")}
        command("resume", "demo-01")
        command("status", "demo-01")
        recovered = state("demo-01")
        check("resume reuses S1/S2 bytes and timestamps", all(before[source] ==
              (sha(project / f"runs/demo-01/read/{source}.txt"),
               (project / f"runs/demo-01/read/{source}.txt").stat().st_mtime_ns)
              for source in before))
        check("six sources complete with cumulative counts", recovered["status"] == "waiting_input" and
              all(item["status"] == "done" and item["attempts"] == (2 if source == "S3" else 1)
                  for source, item in recovered["reads"].items()))
        command("resume", "demo-01", "--candidate", candidate("demo-01"))
        check("structural check stops at human review", state("demo-01")["status"] == "waiting_review" and
              not (project / "runs/demo-01/output").exists())
        command("approve", "demo-01", "--digest", "wrong", code=1)
        check("wrong approval digest cannot create output", not (project / "runs/demo-01/output").exists())
        command("approve", "demo-01", "--digest", state("demo-01")["review_digest"])
        command("runs/demo-01/output", script="validate_output.py")
        delivered = json.loads((project / "runs/demo-01/output/records.json").read_text(encoding="utf-8"))
        check("delivered fixture keeps 12 records, conflict, missing and zero", delivered == data and
              len(delivered["records"]) == 12 and state("demo-01")["status"] == "completed")
        stable = snapshot("demo-01")
        command("resume", "demo-01")
        command("approve", "demo-01", "--digest", state("demo-01")["review_digest"])
        command("start", "demo-01", code=1)
        check("repeated commands preserve all run files and timestamps", stable == snapshot("demo-01"))

        command("start", "retry-01", "--fault", "S3:once", "--read-attempts", "2")
        check("finite automatic retry within one invocation", state("retry-01")["status"] == "waiting_input" and
              state("retry-01")["reads"]["S3"]["attempts"] == 2)
        command("start", "stop-01", "--fault", "S3:always", "--read-attempts", "3", code=1)
        event_count = len(events("stop-01"))
        command("resume", "stop-01", code=1)
        check("cumulative cap survives restart with no fourth call", state("stop-01")["status"] == "blocked" and
              state("stop-01")["reads"]["S3"]["attempts"] == 3 and len(events("stop-01")) == event_count)

        command("start", "bad-01")
        bad = json.loads(json.dumps(data))
        bad["records"].pop()
        command("resume", "bad-01", "--candidate", candidate("bad-01", bad), code=1)
        check("incomplete candidate blocks preview and delivery", state("bad-01")["status"] == "blocked" and
              not (project / "runs/bad-01/preview").exists())
        command("resume", "bad-01", "--candidate", candidate("bad-01", name="candidate-v2.json"))
        check("new candidate version recovers structural rejection", state("bad-01")["status"] == "waiting_review" and
              (project / "runs/bad-01/inbox/candidate-v1.json").exists())

        command("start", "semantic-01")
        semantic = json.loads(json.dumps(data))
        semantic["records"][8].update(value="MIT", state="known")
        command("resume", "semantic-01", "--candidate", candidate("semantic-01", semantic))
        check("semantic fault is not falsely claimed as machine verification", state("semantic-01")["status"] == "waiting_review" and
              not (project / "runs/semantic-01/output").exists())

        target = project / "runs/bad-01/preview/report.md"
        original = target.read_bytes()
        target.write_bytes(original + b"changed\n")
        command("approve", "bad-01", "--digest", state("bad-01")["review_digest"], code=1)
        check("changed preview blocks stale approval without overwriting", target.read_bytes() == original + b"changed\n" and
              not (project / "runs/bad-01/output").exists())
        target.write_bytes(original)

        lock = project / "runs/bad-01/.lock"
        lock.write_text("test-lock", encoding="utf-8")
        command("resume", "bad-01", code=1)
        check("exclusive lock remains on conflicting invocation", lock.read_text(encoding="utf-8") == "test-lock")
        lock.unlink()

        source_file = project / "sources.txt"
        source_original = source_file.read_bytes()
        source_file.write_bytes(source_original + b"\nchanged input\n")
        unchanged = snapshot("demo-01")
        command("resume", "demo-01", code=1)
        check("input revision mismatch stops without changing prior run", unchanged == snapshot("demo-01"))
        source_file.write_bytes(source_original)
        command("resume", "demo-01", "--candidate", "../../expected/answer.json")
        # completed 被重复 resume 直接复用；在未完成运行中验证真正的路径限制。
        command("start", "scope-01")
        command("resume", "scope-01", "--candidate", "../../expected/answer.json", code=1)
        check("candidate path cannot escape current inbox", not (project / "runs/scope-01/extract").exists())

        command("start", "partial-01")
        partial_state = (project / "runs/partial-01/state.json").read_bytes()
        candidate_path = candidate("partial-01")
        command("resume", "partial-01", "--candidate", candidate_path)
        (project / "runs/partial-01/state.json").write_bytes(partial_state)
        command("resume", "partial-01", "--candidate", candidate_path)
        check("unregistered identical artifacts can be adopted after interruption", state("partial-01")["status"] == "waiting_review")
        partial_preview = project / "runs/partial-01/preview/report.md"
        (project / "runs/partial-01/state.json").write_bytes(partial_state)
        partial_preview.write_text("partial write\n", encoding="utf-8")
        command("resume", "partial-01", "--candidate", candidate_path, code=1)
        check("unregistered partial artifact is preserved and blocks overwrite", partial_preview.read_text(encoding="utf-8") == "partial write\n" and
              not (project / "runs/partial-01/output").exists())
        check("fixed project files remain unchanged", fixed_before ==
              {path.name: sha(path) for path in project.iterdir() if path.is_file()})
        record["status"] = "passed"
    except Exception as error:
        record.update(status="failed", error=str(error))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "checks": len(record["checks"]),
                      "workspace": str(project), "record": str(args.out.resolve())}, ensure_ascii=False))
    return 0 if record["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
