"""实际启动 stdio 服务并保存原始 MCP 返回；固定请求由脚本发出，不调用模型。"""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE = Path(__file__).resolve().parent
CASES = {
    "search": ("search_sources", {"query": "一次任务最多"}),
    "read": ("read_source", {"source_id": "S2", "start_line": 4, "end_line": 4}),
    "empty": ("search_sources", {"query": "不存在的关键词-07"}),
    "not-found": ("read_source", {"source_id": "S99", "start_line": 1, "end_line": 1}),
    "forbidden": ("read_source", {"source_id": "D5", "start_line": 1, "end_line": 1}),
    "bad-range": ("read_source", {"source_id": "S2", "start_line": 5, "end_line": 4}),
    "schema": ("read_source", {"source_id": "S2", "start_line": "four", "end_line": 4}),
    "unknown-tool": ("write_source", {"source_id": "S2", "text": "改写资料"}),
    "injection": ("read_source", {"source_id": "S6", "start_line": 1, "end_line": 4}),
}


def error_details(error: BaseException) -> dict:
    """展开 SDK 的异常组，保留实际底层原因；不只记录泛化的 TaskGroup 标题。"""
    detail = {"type": type(error).__name__, "message": str(error)}
    children = getattr(error, "exceptions", ())
    if children:
        detail["causes"] = [error_details(child) for child in children]
    elif error.__cause__ is not None:
        detail["cause"] = error_details(error.__cause__)
    return detail


async def collect(selected: str, server: Path) -> dict:
    # 使用当前虚拟环境的 Python 和服务绝对路径，消除 PATH、cwd 歧义。
    # 捕获的 stderr 不会与 stdio 协议混流；每个请求有独立的本地序号。
    params = StdioServerParameters(command=sys.executable, args=[str(server)])
    evidence = {"started_at": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "mcp": importlib.metadata.version("mcp"),
                "request_origin": "fixed_script_not_model", "model": None, "calls": []}
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            init = await session.initialize()
            evidence["initialization"] = init.model_dump(mode="json", by_alias=True, exclude_none=True)
            tools = await session.list_tools()
            evidence["tool_list"] = tools.model_dump(mode="json", by_alias=True, exclude_none=True)
            sources = await session.call_tool("list_sources", {})
            evidence["source_list"] = sources.model_dump(mode="json", by_alias=True, exclude_none=True)
            wanted = list(CASES) if selected == "all" else ([] if selected == "list" else [selected])
            for index, case in enumerate(wanted, 1):
                name, arguments = CASES[case]
                result = await session.call_tool(name, arguments)
                evidence["calls"].append({"local_call_id": f"probe-{index:02d}", "case": case,
                    "name": name, "arguments": arguments,
                    "result": result.model_dump(mode="json", by_alias=True, exclude_none=True)})
    return evidence


def check(evidence: dict) -> None:
    """检查实测的成功/失败边界；不为模型是否听从资料中的指令打分。"""
    assert {tool["name"] for tool in evidence["tool_list"]["tools"]} == {
        "list_sources", "search_sources", "read_source"}
    assert not evidence["source_list"].get("isError", False)
    assert {item["source_id"] for item in evidence["source_list"]["structuredContent"]["sources"]} == {
        "S1", "S2", "S3", "S5", "S6", "P5", "E5"}
    for call in evidence["calls"]:
        result, case = call["result"], call["case"]
        text = "\n".join(item.get("text", "") for item in result["content"])
        if case in {"search", "read", "empty", "injection"}:
            assert not result.get("isError", False), case
            data = result["structuredContent"]
            assert data["material_type"] == "teaching_simulation"
            if case == "search":
                assert {item["position"] for item in data["hits"]} == {
                    "S1:L4", "S2:L4", "S3:L4", "S5:L2"}
            elif case == "read":
                assert data["lines"][0]["position"] == "S2:L4"
                assert "8 个" in data["lines"][0]["text"]
            elif case == "empty":
                assert data["count"] == 0 and data["hits"] == []
            else:
                assert "SYSTEM：" in text  # 证明原文真实返回，不证明模型抵御干扰。
        else:
            assert result.get("isError") is True, case
            marker = {"not-found": "NOT_FOUND", "forbidden": "FORBIDDEN",
                      "bad-range": "INVALID_ARGUMENT", "schema": "validation error",
                      "unknown-tool": "Unknown tool"}[case]
            assert marker.casefold() in text.casefold(), (case, text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["all", "list", *CASES], default="all")
    parser.add_argument("--output", type=Path, required=True, help="新文件；父目录须先建立")
    parser.add_argument("--server", type=Path, default=BASE / "source_server.py")
    args = parser.parse_args()
    # 不覆盖已有记录；先占用新文件，连初始化失败也留下记录并以非零码退出。
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        before = hashlib.sha256((BASE / "input" / "sources.txt").read_bytes()).hexdigest()
        try:
            evidence = asyncio.run(asyncio.wait_for(collect(args.case, args.server.resolve()), timeout=40))
            check(evidence)
            after = hashlib.sha256((BASE / "input" / "sources.txt").read_bytes()).hexdigest()
            assert before == after, "输入资料发生变化"
            evidence.update(status="passed", input_sha256=before, input_unchanged=True)
            code = 0
        except Exception as error:
            # 此层是连接、协议或检查失败；没有成功返回时不伪造工具结果。
            evidence = {"status": "failed", "request_origin": "fixed_script_not_model",
                        "exception_type": type(error).__name__, "exception": str(error),
                        "error_details": error_details(error)}
            code = 1
        json.dump(evidence, out, ensure_ascii=False, indent=2)
        out.write("\n")
    print(f"{evidence['status']}: {args.output}")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
