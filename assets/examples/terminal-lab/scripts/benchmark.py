import argparse
import hashlib
import json
import platform
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("executable", type=Path)
parser.add_argument("--n", type=int, default=1000000)
parser.add_argument("--repeat", type=int, default=10)
parser.add_argument("--pairs", type=int, default=10)
parser.add_argument("--aa-pairs", type=int, default=4)
parser.add_argument("--warmups", type=int, default=2)
parser.add_argument("--timeout", type=float, default=60)
args = parser.parse_args()
if not (1 <= args.n <= 10000000 and 1 <= args.repeat <= 10000 and
        1 <= args.pairs <= 1000 and 1 <= args.aa_pairs <= 1000 and
        0 <= args.warmups <= 100 and args.timeout > 0):
    parser.error("invalid experiment bounds")
exe = args.executable.resolve(strict=True)
root = Path(__file__).resolve().parents[1]
session = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
log_dir = root / "logs" / session
log_dir.mkdir(parents=True, exist_ok=False)
meta_dir = root / "metadata" / session
meta_dir.mkdir(parents=True, exist_ok=False)

def git_output(*arguments):
    # 错误也保留，不把不在仓库中的项目伪装成干净提交。
    result = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    return {"exit_code": result.returncode, "output": result.stdout, "error": result.stderr}

try:
    git = {"head": git_output("rev-parse", "HEAD"),
           "status": git_output("status", "--porcelain=v1"),
           "diff": git_output("diff", "HEAD", "--"),
           "untracked": git_output("ls-files", "--others", "--exclude-standard")}
except FileNotFoundError:
    git = {"error": "git executable unavailable"}
metadata = {"session": session, "hostname": platform.node(), "platform": platform.platform(),
            "python": sys.version, "executable": str(exe),
            "binary_sha256": hashlib.sha256(exe.read_bytes()).hexdigest(),
            "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
            "git": git,
            "limits": "补充 CPU 型号、编译器/配置、Shell、资源分配和源码快照；自动记录并不完整。"}
(meta_dir / "environment.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
case_id = f"formula-v1-n{args.n}-r{args.repeat}-t1"
order = 0
failed = False

def run(variant, phase, pair):
    global order, failed
    order += 1
    run_id = session + "-" + f"{order:04d}"
    command = [str(exe), str(args.n), variant, str(args.repeat)]
    header = f"run_id={run_id}\ncase_id={case_id}\nstarted_at={datetime.now(timezone.utc).isoformat()}\nphase={phase}\npair={pair}\norder={order}\n"
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                errors="strict", timeout=args.timeout, check=False)
        body, code = result.stdout, result.returncode
        body += "".join("# stderr: " + line + "\n" for line in result.stderr.splitlines())
    except subprocess.TimeoutExpired:
        body, code = "# error: timeout; no complete result\n", 124
    with (log_dir / (run_id + ".log")).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(header + body + f"exit_code={code}\n")
    failed = failed or code != 0
    print(f"{order}: {phase} {variant} exit={code}")

for pair in range(1, args.warmups + 1):
    for variant in ("A", "B"):
        run(variant, "warmup", pair)
for pair in range(1, args.aa_pairs + 1):
    # 两次都是 A，通过 order 保留先后；第五篇只按 sample 做 A/B 关联。
    run("A", "aa", pair)
    run("A", "aa", pair)
for pair in range(1, args.pairs + 1):
    for variant in (("A", "B") if pair % 2 else ("B", "A")):
        run(variant, "sample", pair)
print(f"log_dir={log_dir}\nmetadata_dir={meta_dir}")
raise SystemExit(1 if failed else 0)
