"""用同一份已核验模型 JSON 测试 TSV/Markdown 转写，保留未修复产物。"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from evaluate_records import ROOT, validator


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs=2, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = validator.checked_json(args.input)
    # 只有结构检查自动执行；调用者必须在此前完成事实核验。
    args.out.mkdir(parents=True, exist_ok=False)
    original = args.input.read_text(encoding="utf-8")
    followup = (ROOT / "prompts/05-02-deliver.txt").read_text(encoding="utf-8")
    prompt = ("以下主 JSON 已由我对照 D5-v1 固定来源逐条核验；本轮确认它为后续交付依据。\n"
              "<checked_json>\n" + original + "\n</checked_json>\n\n" + followup)
    (args.out / "prompt.txt").write_text(prompt, encoding="utf-8", newline="\n")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    summary = {"prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
               "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
               "effort": "low", "repeats": 1, "runs": []}
    for index, model in enumerate(args.models, 1):
        directory = args.out / f"model-{index}"
        workspace = directory / "empty-workspace"
        workspace.mkdir(parents=True)
        raw = directory / "raw-output.txt"
        command = [shutil.which("codex"), "exec", "--ignore-user-config", "--ephemeral",
                   "--skip-git-repo-check", "--sandbox", "read-only", "--model", model,
                   "-c", 'model_reasoning_effort="low"', "-C", str(workspace), "--json",
                   "--output-last-message", str(raw.resolve()), "-"]
        clock = time.perf_counter()
        result = subprocess.run(command, input=prompt, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=env, timeout=300)
        (directory / "events.jsonl").write_text(result.stdout, encoding="utf-8", newline="\n")
        (directory / "stderr.txt").write_text(result.stderr, encoding="utf-8", newline="\n")
        record = {"model_requested": model, "exit_code": result.returncode,
                  "elapsed_seconds": round(time.perf_counter() - clock, 3),
                  "bundle_pass": False, "error": None, "directory": directory.name}
        if raw.exists():
            text = raw.read_text(encoding="utf-8")
            blocks = re.findall(r"```([^\n]*)\n(.*?)\n```", text, re.S)
            record["fenced_blocks"] = len(blocks)
            # 只分离约定代码块，保留真正 TAB 和空值；不修数值、围栏内文本或转义。
            if (len(blocks) == 2 and "records.tsv" in text and "report.md" in text
                    and blocks[0][1].startswith("record_id\t")):
                bundle = directory / "saved-bundle"
                bundle.mkdir()
                (bundle / "records.json").write_text(original, encoding="utf-8", newline="\n")
                (bundle / "records.tsv").write_text(blocks[0][1] + "\n", encoding="utf-8", newline="\n")
                (bundle / "report.md").write_text(blocks[1][1] + "\n", encoding="utf-8", newline="\n")
                try:
                    validator.check_bundle(bundle)
                    record["bundle_pass"] = True
                except (ValueError, OSError) as error:
                    record["error"] = str(error)
            else:
                record["error"] = "expected two named fenced blocks and real TSV tabs"
        summary["runs"].append(record)
        (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)
            + "\n", encoding="utf-8", newline="\n")
        print(f"{model}: bundle_pass={record['bundle_pass']}; error={record['error']}", flush=True)


if __name__ == "__main__":
    main()
