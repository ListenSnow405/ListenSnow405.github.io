from pathlib import Path

root = Path(__file__).resolve().parents[1] / "fixtures"
root.mkdir(exist_ok=True)
base = """run_id={run}
case_id=vector-small
started_at=2026-09-30T00:00:00+00:00
input_id=formula-v1
n=1003
repeat=2
threads=1
seed=0
variant={variant}
phase=sample
pair={pair}
order=1
correctness=pass
metric=compute_ms
value=1.25e-1
unit=ms
scope=compute-only
exit_code=0
"""
cases = {
    "01-A": base.format(run="r01", variant="A", pair=1),
    "02-B": base.format(run="r02", variant="B", pair=1).replace("1.25e-1", "0.10"),
    "03-failed": base.format(run="r03", variant="A", pair=2).replace("exit_code=0", "exit_code=7"),
    "04-missing": base.format(run="r04", variant="B", pair=2).replace("value=1.25e-1\n", ""),
    "05-duplicate": base.format(run="r05", variant="A", pair=3) + "value=0.2\n",
    "06-invalid": base.format(run="r06", variant="B", pair=3).replace("1.25e-1", "NaN"),
    "07-unmatched": base.format(run="r07", variant="A", pair=4),
}
for name, content in cases.items():
    # 只写本脚本约定的七份教学素材，重复执行会重建这些文件。
    (root / (name + ".log")).write_text(content, encoding="utf-8", newline="\n")
print(f"created {len(cases)} fixtures in {root}")
