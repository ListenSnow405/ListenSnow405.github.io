import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("--label", required=True)
parser.add_argument("--fail", action="store_true")
args = parser.parse_args()
# 固定值仅用于演示日志与退出码，绝不能作为性能测量样本。
print("# label: " + args.label)
print("input_id=demo-v1\nn=3\nvariant=demo\nrepeat=1\nthreads=1\nseed=0")
print("correctness=" + ("fail" if args.fail else "pass"))
print("metric=demo_value\nvalue=1.25\nunit=ms\nscope=synthetic")
print("# diagnostic: deterministic demo", file=sys.stderr)
sys.exit(7 if args.fail else 0)
