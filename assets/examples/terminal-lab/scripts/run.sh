#!/usr/bin/env bash
set -u
# 固定从项目根执行，调用者的当前目录不影响日志位置。
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd) || exit 1
cd -- "$root" || exit 1
if (( $# < 1 )); then printf 'usage: bash scripts/run.sh LABEL [--fail]\n' >&2; exit 2; fi
command -v python3 >/dev/null || exit 127
mkdir -p logs || exit 1
run_id="demo-$(date -u +%Y%m%dT%H%M%S)-$$-$RANDOM"
log="logs/$run_id.log"
# noclobber 阻止同名覆盖；时间、PID 和随机后缀降低碰撞概率。
(set -C; : > "$log") || exit 1
{
  printf 'run_id=%s\ncase_id=demo-v1\n' "$run_id"
  printf 'started_at=%s\nphase=sample\npair=1\norder=1\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >> "$log" || exit 1
python3 scripts/demo.py --label "$1" "${@:2}" >> "$log" 2>&1
program_rc=$?
# 先保存实验退出码；日志写入失败也必须成为脚本失败。
printf 'exit_code=%s\n' "$program_rc" >> "$log" || exit 1
cat -- "$log" || exit 1
exit "$program_rc"
