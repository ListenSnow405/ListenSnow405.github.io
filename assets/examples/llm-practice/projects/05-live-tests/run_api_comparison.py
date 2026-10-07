"""OpenAI Platform Responses API 对照；缺少密钥时不发送请求。"""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from evaluate_records import ROOT, evaluate


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def configured_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key and os.name == "nt":
        # 桌面进程可能早于用户变量设置；只读此命名变量，不输出或修改注册表。
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as environment:
                key = winreg.QueryValueEx(environment, "OPENAI_API_KEY")[0]
        except OSError:
            pass
    return key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs=2, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-output-tokens", type=int, default=5000)
    args = parser.parse_args()
    if not 1 <= args.repeats <= 3:
        parser.error("repeats must be between 1 and 3")
    key = configured_key()
    if not key:
        parser.exit(2, "NOT RUN: OPENAI_API_KEY is absent; no network request sent.\n")
    # 固定官方目的地；不从未知兼容服务推断支持，也不输出密钥或授权头。
    endpoint = "https://api.openai.com/v1/responses"
    args.out.mkdir(parents=True, exist_ok=False)
    prompt_bytes = (ROOT / "prompts/05-01-extract.txt").read_bytes()
    schema = json.loads((ROOT / "projects/05-file-output/records.schema.json").read_text(encoding="utf-8"))
    (args.out / "prompt.txt").write_bytes(prompt_bytes)
    summary = {"transport": "OpenAI Platform Responses API", "endpoint": endpoint,
               "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(), "runs": []}
    for repeat in range(1, args.repeats + 1):
        for mode in ("plain", "schema"):
            for index, model in enumerate(args.models, 1):
                directory = args.out / f"model-{index}-{mode}-{repeat:02}"
                directory.mkdir()
                body = {"model": model, "input": prompt_bytes.decode("utf-8"), "store": False,
                        "max_output_tokens": args.max_output_tokens, "reasoning": {"effort": "low"}}
                if mode == "schema":
                    body["text"] = {"format": {"type": "json_schema", "name": "d5_records",
                                               "strict": True, "schema": schema}}
                save(directory / "request.json", body)
                request = urllib.request.Request(endpoint,
                    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                    method="POST")
                started, clock = datetime.now(timezone.utc).isoformat(), time.perf_counter()
                record = {"model_requested": model, "mode": mode, "repeat": repeat,
                          "started_utc": started, "directory": directory.name}
                try:
                    with urllib.request.urlopen(request, timeout=180) as response:
                        result = json.load(response)
                        record["http_status"] = response.status
                    save(directory / "response.json", result)
                    content = [part for item in result.get("output", []) if item.get("type") == "message"
                               for part in item.get("content", [])]
                    refusals = [part.get("refusal") for part in content if part.get("type") == "refusal"]
                    record.update(model_returned=result.get("model"), status=result.get("status"),
                                  incomplete_details=result.get("incomplete_details"),
                                  refusal=bool(refusals), usage=result.get("usage"))
                    if result.get("status") == "completed" and not refusals:
                        text = "".join(part.get("text", "") for part in content if part.get("type") == "output_text")
                        output = directory / "records.json"
                        # 原文保存，不自动去围栏、补 JSON 或改错值。
                        output.write_text(text, encoding="utf-8", newline="\n")
                        record["grade"] = evaluate(output)
                except urllib.error.HTTPError as error:
                    # 错误消息可能回显密钥片段；只记录 HTTP 状态，不保存鉴权错误正文。
                    record.update(http_status=error.code, error="HTTP error; body omitted")
                except (urllib.error.URLError, TimeoutError, ValueError) as error:
                    record["error"] = type(error).__name__
                record["elapsed_seconds"] = round(time.perf_counter() - clock, 3)
                save(directory / "result.json", record)
                summary["runs"].append(record)
                save(args.out / "summary.json", summary)
                print(f"{model} {mode} #{repeat}: HTTP={record.get('http_status')}; "
                      f"status={record.get('status')}; grade={record.get('grade')}", flush=True)
                if record.get("http_status") in (401, 403, 429):
                    parser.exit(1, "STOP: authentication/access/rate limit requires attention.\n")


if __name__ == "__main__":
    main()
