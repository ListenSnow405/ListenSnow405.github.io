# terminal-lab 配套项目

本目录是“命令行开发与实验实践”六篇文章的完整教学源码。复制到个人练习目录后运行，不在博客源码目录执行故障或清理实验。静态站点会提供这些文件的下载地址；也可从博客仓库中复制本目录。

## 文件与篇目

| 文件 | 用途 |
| --- | --- |
| `src/vector_lab.cpp`、`CMakeLists.txt` | 第三篇的完整 CPU 项目，无外部头文件或数据依赖 |
| `scripts/demo.py`、`run.sh`、`run.ps1` | 第二篇的确定性输出与退出码演示，数值不是测量 |
| `scripts/make_fixtures.py` | 第五篇生成七份教学日志，不是真实性能样本 |
| `scripts/collect.py` | 第五篇检查日志并输出 TSV、JSON、摘要与完整 A/B 关联 |
| `scripts/benchmark.py` | 第六篇保存独立进程预热、A/A、交错 A/B 和基础 metadata |

Python 3 脚本仅依赖标准库。Windows 示例使用 PowerShell 7，Linux 使用 Bash。Bash 文件使用 LF 和无 BOM UTF-8。CMake 最低版本 3.20，C++17 编译器；Windows 主线在已初始化 MSVC 的开发终端执行。GDB 路线在 Windows 另需完整 MinGW-w64 环境。

## 最小验证

从本项目根目录执行。Linux 用 Unix Makefiles 和自己的构建目录，不能复用 Windows 缓存：

```bash
cmake -S . -B build-linux -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build-linux --parallel 2
ctest --test-dir build-linux --output-on-failure
./build-linux/vector_lab 1003 B 2
python3 scripts/make_fixtures.py
python3 scripts/collect.py fixtures results/fixtures
```

Windows MSVC Developer PowerShell：

```powershell
cmake -S . -B build-windows -G 'NMake Makefiles' -DCMAKE_BUILD_TYPE=Release
cmake --build build-windows
ctest --test-dir build-windows --output-on-failure
& ./build-windows/vector_lab.exe 1003 B 2
python scripts/make_fixtures.py
python scripts/collect.py fixtures results/fixtures
```

构建每一步须检查退出码。计算程序 N、版本、REPEAT 依次作为参数，N 为 1..10000000，版本为 A/B，REPEAT 为 1..10000。正确性失败返回 3，非法参数返回 2。日志素材应得到 total 7、ok 3，failed/missing/duplicate/invalid 各 1；普通整理模式返回 0 表示整理完成，`--strict` 在存在异常时返回 2。

## 正式 CPU 样本

使用 Release 产物，Windows 用 `python` 与 `.exe`，Linux 用 `python3` 与本机二进制：

```powershell
python scripts/benchmark.py build-windows/vector_lab.exe --n 1000000 --repeat 10 --pairs 10 --aa-pairs 4 --warmups 2
```

本例产生 32 份日志，随后把实际输出会话路径传给 `collect.py`。输入身份为 formula-v1，计时为 compute-only，每进程输出 REPEAT 轮的平均值；参考检查与 checksum 在计时外。A/A、warmup 与 sample 分开保留；零耗时不计算比值。

自动环境记录并不完整。实验者须补充 CPU、Shell、工具链/配置、资源分配，保存源码、差异和未跟踪源文件。所有失败与超时记录均保留；未提交源码不能仅用提交号代表。日志不覆盖，派生结果允许重新生成。大规模日志需要另行设计流式存储，本例把结构化记录和摘要放入内存。

## 维护与验证边界

文章中完整源码与本目录文件保持一致，修改任一方时同步另一方并重新执行相关验证。`.gitignore` 排除构建、日志、结果和环境快照，不应把它当作任何文件同步工具的过滤规则。

本轮在 Windows PowerShell 7、MSVC 和 MinGW-w64 上验证构建、参考校验、故障检测、日志整理和 CPU 驱动。Linux 原生步骤、远端操作与本篇 GPU profiler 扩展未执行，不以其他平台成功代替。教学日志中的数值不作为性能证据。
