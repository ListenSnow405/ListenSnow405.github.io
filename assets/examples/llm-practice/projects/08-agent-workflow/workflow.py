"""D5-v1 本地工作流：读取检查点、导入模型候选、结构核验、待审与本地交付。

只使用标准库，不调用模型、MCP、网络或调度器。故障为读取接口的教学注入。
运行目录只允许单进程操作；文件摘要检查用于发现变化，不是权限或签名机制。
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from validate_output import checked_json, render_report, tsv_rows

BASE = Path(__file__).resolve().parent
SOURCES = ("S1", "S2", "S3", "S5", "P5", "E5")
MAX_ATTEMPTS = 3                 # 每份来源的累计调用上限，重新启动不清零。
VERSION = "08-workflow/1.0"


def digest(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")


def fixed_hashes():
    # 恢复依据包含输入、契约和执行代码；修改任何一项应另开 run_id。
    names = ("sources.txt", "contract.json", "workflow.py", "validate_output.py")
    return {name: digest((BASE / name).read_bytes()) for name in names}


def run_path(run_id):
    # 标识是单个目录名；不允许路径穿越，也不接受 Windows 保留设备名。
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", run_id):
        raise ValueError("run_id 使用小写字母开头的字母、数字与短横线，最长 40 字符")
    if re.fullmatch(r"con|prn|aux|nul|com[1-9]|lpt[1-9]", run_id):
        raise ValueError("run_id 是 Windows 保留名称")
    return BASE / "runs" / run_id


def save_state(folder, state):
    # 状态是可更新索引，产物不覆盖。先落盘再替换，避免普通中断留下半个 JSON。
    # 本例没有目录 fsync 或多机事务，不声称覆盖断电和硬盘损坏。
    temporary = folder / "state.json.tmp"
    with temporary.open("wb") as stream:
        stream.write(json_bytes(state))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, folder / "state.json")


def event(folder, kind, **details):
    record = {"time": datetime.now(timezone.utc).isoformat(), "event": kind, **details}
    with (folder / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")


def remember(folder, state, relative, content):
    """只创建新文件；未登记但已存在的同内容文件可以收编为检查点。

    普通异常若留下部分文件，下次内容比较会拒绝；保留它供检查，不能直接覆盖。
    """
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"已有文件内容不匹配，拒绝覆盖：{relative}")
    else:
        with path.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    state["artifacts"][relative] = digest(content)


@contextmanager
def locked(folder):
    # 排他创建防止两个命令同时改变一个 run_id；不是对其他程序的文件访问控制。
    lock = folder / ".lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        yield
    finally:
        lock.unlink()


def load_checked(folder):
    state = json.loads((folder / "state.json").read_text(encoding="utf-8"))
    if state["workflow_version"] != VERSION or state["fixed_hashes"] != fixed_hashes():
        raise ValueError("输入、契约或执行代码变化；保留旧运行，使用新的 run_id")
    for relative, expected in state["artifacts"].items():
        if digest((folder / relative).read_bytes()) != expected:
            raise ValueError(f"已登记产物变化：{relative}；停止恢复，不自动覆盖")
    return state


def source_blocks():
    text = (BASE / "sources.txt").read_text(encoding="utf-8")
    blocks = {}
    for block in re.split(r"(?=^\[[A-Z][A-Z0-9]*\])", text, flags=re.M):
        match = re.match(r"\[([^]]+)\]", block)
        if match:
            blocks[match[1]] = block.rstrip() + "\n"
    if any(source not in blocks for source in SOURCES):
        raise ValueError("必要来源缺失，不以重复调用补造资料")
    return blocks


def read_step(folder, state, attempts_this_call):
    """每份来源独立计数、独立落盘；只对注入的 TimeoutError 有限重试。"""
    blocks = source_blocks()
    state["status"] = "running"
    state["stage"] = "read"
    for source in SOURCES:
        checkpoint = state["reads"][source]
        if checkpoint["status"] == "done":
            continue
        for _ in range(attempts_this_call):
            if checkpoint["attempts"] >= MAX_ATTEMPTS:
                state.update(status="blocked", reason=f"{source} 累计读取达到 {MAX_ATTEMPTS} 次")
                save_state(folder, state)
                return False
            # 先保存已安排的调用；即使进程随后中断，累计预算也不会回退。
            if checkpoint["attempts"]:
                time.sleep(0.2 * 2 ** (checkpoint["attempts"] - 1))
            checkpoint["attempts"] += 1
            checkpoint["status"] = "running"
            save_state(folder, state)
            event(folder, "read_attempt", source=source, attempt=checkpoint["attempts"])
            try:
                fault = state["fault"]
                if fault == f"{source}:always" or (fault == f"{source}:once" and checkpoint["attempts"] == 1):
                    raise TimeoutError("教学注入：来源读取接口超时；未写入该来源缓存")
                remember(folder, state, f"read/{source}.txt", blocks[source].encode("utf-8"))
                checkpoint["status"] = "done"
                state["reason"] = None
                event(folder, "read_done", source=source)
                save_state(folder, state)
                break
            except TimeoutError as error:
                checkpoint["status"] = "failed"
                state.update(status="blocked" if checkpoint["attempts"] == MAX_ATTEMPTS else "failed",
                             reason=str(error))
                event(folder, "read_failed", source=source, error=str(error))
                save_state(folder, state)
        if checkpoint["status"] != "done":
            return False
    evidence = "\n".join((folder / f"read/{source}.txt").read_text(encoding="utf-8") for source in SOURCES)
    remember(folder, state, "evidence.txt", evidence.encode("utf-8"))
    state.update(status="waiting_input", stage="extract", reason="等待读者保存模型候选")
    save_state(folder, state)
    return True


def bundle_bytes(data):
    stream = io.StringIO(newline="")
    csv.writer(stream, delimiter="\t", lineterminator="\n").writerows(tsv_rows(data))
    return {"records.json": json_bytes(data), "records.tsv": stream.getvalue().encode("utf-8"),
            "report.md": render_report(data).encode("utf-8")}


def review_digest(state):
    # 确认绑定输入版本与三个待审文件，不仅绑定报告文字或 run_id。
    review = {"fixed_hashes": state["fixed_hashes"],
              "preview": {name: value for name, value in state["artifacts"].items()
                          if name.startswith("preview/")}}
    return digest(json_bytes(review))


def advance(folder, state, candidate, attempts_this_call):
    if state["status"] in ("completed", "waiting_review"):
        return
    if state["stage"] == "read" and not read_step(folder, state, attempts_this_call):
        return
    if not candidate:
        return
    # 读者/模型先在 inbox 保存原始候选；脚本只接受本次运行范围内的新版本文件。
    path = (folder / candidate).resolve()
    if not path.is_relative_to((folder / "inbox").resolve()):
        raise ValueError("候选必须位于本次运行的 inbox/；不从参考答案目录读取")
    try:
        data = checked_json(path)
    except (ValueError, OSError) as error:
        state.update(status="blocked", stage="extract", reason=str(error))
        event(folder, "candidate_rejected", candidate=candidate, error=str(error))
        save_state(folder, state)
        return
    # 导入原始文本和规范化主记录；语法、字段、定位存在检查不证明事实语义正确。
    remember(folder, state, "extract/raw.json", path.read_bytes())
    remember(folder, state, "extract/records.json", json_bytes(data))
    verification = {"status": "structure_passed", "records": len(data["records"]),
                    "facts": "pending_human_review", "candidate_sha256": digest(path.read_bytes())}
    remember(folder, state, "verify.json", json_bytes(verification))
    for name, content in bundle_bytes(data).items():
        remember(folder, state, f"preview/{name}", content)
    state.update(status="waiting_review", stage="review", reason="结构通过；等待人工核对证据含义")
    state["review_digest"] = review_digest(state)
    event(folder, "preview_ready", review_digest=state["review_digest"])
    save_state(folder, state)


def approve(folder, state, supplied_digest):
    """这是读者核对后的显式本地确认，不把模型文本或参考答案视为批准。"""
    if state["status"] == "completed":
        if supplied_digest != state.get("review_digest"):
            raise ValueError("确认摘要不匹配")
        return
    if state["status"] != "waiting_review" or supplied_digest != review_digest(state):
        raise ValueError("没有当前待审稿，或确认摘要不匹配")
    # 写入前 load_checked 已复核所有已登记文件；输出仅在 run/output 内。
    for name in ("records.json", "records.tsv", "report.md"):
        remember(folder, state, f"output/{name}", (folder / f"preview/{name}").read_bytes())
    state.update(status="completed", stage="done", reason=None)
    state["approval"] = {"review_digest": supplied_digest, "method": "explicit_local_cli"}
    event(folder, "local_delivery_done", review_digest=supplied_digest)
    save_state(folder, state)


def summary(state):
    result = {key: state[key] for key in ("run_id", "status", "stage", "reason")}
    if "review_digest" in state:
        result["review_digest"] = state["review_digest"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="创建全新运行并读取资料")
    start.add_argument("run_id")
    start.add_argument("--fault", choices=("none", "S3:once", "S3:always"), default="none")
    start.add_argument("--read-attempts", type=int, choices=(1, 2, 3), default=1)
    resume = commands.add_parser("resume", help="复核检查点并继续未完成阶段")
    resume.add_argument("run_id")
    resume.add_argument("--candidate", help="相对本次运行的 inbox 文件路径")
    resume.add_argument("--read-attempts", type=int, choices=(1, 2, 3), default=1)
    decision = commands.add_parser("approve", help="人工核对后确认本次本地交付")
    decision.add_argument("run_id")
    decision.add_argument("--digest", required=True)
    status = commands.add_parser("status", help="只读复核输入、产物与状态")
    status.add_argument("run_id")
    args = parser.parse_args()
    try:
        folder = run_path(args.run_id)
        if args.command == "start":
            # 新 run_id 独占创建，已有目录拒绝；不对已有成果做初始化覆盖。
            folder.mkdir(parents=True, exist_ok=False)
            (folder / "inbox").mkdir()
            state = {"run_id": args.run_id, "workflow_version": VERSION,
                     "fixed_hashes": fixed_hashes(), "fault": args.fault,
                     "status": "running", "stage": "read", "reason": None,
                     "artifacts": {}, "reads": {source: {"status": "pending", "attempts": 0}
                                                  for source in SOURCES}}
            save_state(folder, state)
            event(folder, "run_created", fault=args.fault)
        if args.command == "status":
            summary(load_checked(folder))
            return 0
        with locked(folder):
            state = load_checked(folder)
            if args.command == "approve":
                approve(folder, state, args.digest)
            else:
                advance(folder, state, getattr(args, "candidate", None), args.read_attempts)
            summary(state)
            return 1 if state["status"] in ("failed", "blocked") else 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"STOP: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
