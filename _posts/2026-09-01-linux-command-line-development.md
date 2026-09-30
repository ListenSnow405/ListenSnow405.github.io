---
layout: post
title: "命令行构建与程序调试"
date: 2026-09-01 09:10:00 +0800
categories: [学习]
tags: [C++, CMake, CTest, 调试, 终端实验系列]
excerpt: "建立完整的向量计算项目，核对工具链与构建配置，通过参考结果和 CTest 验证程序，再用独立故障实验学习调试。"
series: terminal-lab
series_order: 3
---

源码修改后，运行成功并不代表运行了新版本；得到数字也不代表结果正确。可靠的开发循环应同时确认工具链、构建配置、二进制路径和结果判据。

本文是系列第三篇，需要能够阅读基本 C++。路径操作见[第一篇]({% post_url 2026-09-01-linux-terminal-common-commands %})，参数和退出码见[第二篇]({% post_url 2026-09-30-shell-execution-and-scripting %})。本文由原 Linux 命令行开发文章重构，文件名和发布地址保持不变。主线采用完整 CMake 项目；性能比较在第六篇展开。

<span id="1-编译和构建有什么区别"></span>

## 1. 编译、链接与构建

C++ 源码经预处理、编译和汇编形成目标文件，链接器把目标文件和库组合成可执行程序。缺头文件常属于预处理问题，语法或类型错误属于编译问题，未定义符号常属于链接问题；运行时找不到动态库则发生在程序加载阶段。

CMake 读取项目配置并生成底层构建系统，`cmake --build` 调用对应构建工具。Make、Ninja、MSBuild 执行依赖规则，编译器仍负责生成机器代码。“build”不是固定的 Linux 命令，也不是某一种编译器。

增量构建依据依赖关系判断哪些目标需要更新。源码比二进制新是线索，不足以证明运行来源；修改了生成脚本、头文件或编译选项时，还需由正确构建系统处理依赖。

<span id="2-准备开发环境"></span>

## 2. 工具链与环境核对

### Windows MSVC 与 Linux GCC

Windows 主线需要 Visual Studio 或 Build Tools 的 C++ 工作负载、Windows SDK 和 CMake。使用安装提供的 **Developer PowerShell**，确认开发环境已经初始化；只把 `cl.exe` 加入 PATH，仍可能缺少头文件与链接库路径。

```powershell
# Windows 本地 · 已初始化 MSVC 的 PowerShell
Get-Command cl, nmake, cmake, ctest
cl
cmake --version
```

Linux 主线需要 GCC、CMake、Make 和可选 GDB：

```bash
# Linux · Bash
command -v g++
command -v cmake
command -v make
command -v gdb
g++ --version
cmake --version
```

工具缺失时按实际发行版或安装器补齐，不默认有管理员权限，不把 Ubuntu 的包名当作所有系统通用。Windows 的 MinGW-w64 是另一条 GCC 路线，生成器、运行库和调试信息不能与 MSVC 路线混用。

### Python 环境入口

后续日志与实验脚本使用 Python 标准库。先确认解释器及依赖位置，再处理安装问题：

```powershell
# Windows 本地 · PowerShell；本系列脚本不需要第三方包
python -c "import sys; print(sys.executable); print(sys.version)"
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip --version
```

```bash
# Linux · Bash；创建虚拟环境依赖发行版提供的 venv 支持
python3 -c 'import sys; print(sys.executable); print(sys.version)'
python3 -m venv .venv
./.venv/bin/python -m pip --version
```

显式调用环境内解释器，不必先激活环境。`python -m pip` 让 pip 归属于该 Python，避免独立 `pip` 指向另一安装；虚拟环境也不是操作系统隔离或 GPU 驱动隔离。

## 3. 完整项目与参考结果

### 起始文件与任务定义

独立阅读时在个人目录创建空的 `terminal-lab`，再创建 `src/`。将下面两份文件用编辑器保存到指定位置，全部构建命令从项目根目录执行。源码、CMake 与后续脚本也集中提供在[配套项目说明]({{ '/assets/examples/terminal-lab/README.md' | relative_url }})中。

```text
terminal-lab/
├── CMakeLists.txt
├── src/
│   └── vector_lab.cpp
├── build-windows/        # 稍后生成
└── build-linux/          # 稍后生成
```

输入采用确定性公式 `a[i]=i%251`、`b[i]=i%127`，目标为 `out[i]=3*a[i]+2*b[i]`。A 使用中间数组和两个循环，B 使用一个融合循环。程序接收 `N A|B REPEAT`：N 为元素数，REPEAT 为进程内计算次数，不是独立进程样本数。

参考结果直接由索引公式以 double 计算，与被测循环独立。每轮逐元素检查有限值及绝对误差不超过 `1e-6`；本例整数幅度小，float 可精确表示相关结果。这个阈值不能直接迁移到任意浮点算法。

### 完整源码

保存为 `src/vector_lab.cpp`，无需额外头文件或输入文件：

```cpp
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// 限制练习规模，拒绝负数、尾随字符和超大输入，避免意外耗尽资源。
int positive(const std::string& text, int limit) {
    std::size_t used = 0;
    int value = std::stoi(text, &used);
    if (used != text.size() || value < 1 || value > limit)
        throw std::invalid_argument("argument outside allowed range");
    return value;
}

// A 使用中间数组和两个循环，B 融合循环；数学任务相同。
// 独立函数方便设置断点，具体机器上是否更快由实验决定。
void compute(const std::vector<float>& a, const std::vector<float>& b,
             std::vector<float>& temp, std::vector<float>& out, char variant) {
    if (variant == 'A') {
        for (std::size_t i = 0; i < a.size(); ++i) temp[i] = 3.0f * a[i];
        for (std::size_t i = 0; i < a.size(); ++i) out[i] = temp[i] + 2.0f * b[i];
    } else {
        for (std::size_t i = 0; i < a.size(); ++i) out[i] = 3.0f * a[i] + 2.0f * b[i];
    }
}

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::invalid_argument("usage: vector_lab N A|B REPEAT");
        const int n = positive(argv[1], 10000000);
        const std::string version = argv[2];
        if (version != "A" && version != "B") throw std::invalid_argument("variant must be A or B");
        const int repeat = positive(argv[3], 10000);
        std::vector<float> a(n), b(n), temp(n), out(n);
        for (int i = 0; i < n; ++i) {
            a[i] = static_cast<float>(i % 251);
            b[i] = static_cast<float>(i % 127);
        }

        // 每轮只计 compute，初始化、参考校验、checksum 和输出均在计时外。
        // 每轮读取结果，避免重复调用成为完全不可观察的死代码。
        double total_ms = 0.0, checksum = 0.0;
        bool correct = true;
        for (int r = 0; r < repeat; ++r) {
            const auto start = std::chrono::steady_clock::now();
            compute(a, b, temp, out, version[0]);
            const auto stop = std::chrono::steady_clock::now();
            total_ms += std::chrono::duration<double, std::milli>(stop - start).count();
            for (int i = 0; i < n; ++i) {
                const double ref = 3.0 * (i % 251) + 2.0 * (i % 127);
                correct = correct && std::isfinite(out[i]) && std::abs(out[i] - ref) <= 1e-6;
                checksum += out[i];
            }
        }
        std::cout << "input_id=formula-v1\nn=" << n << "\nvariant=" << version
                  << "\nrepeat=" << repeat << "\nthreads=1\nseed=0\ncorrectness="
                  << (correct ? "pass" : "fail") << "\nmetric=compute_ms\nunit=ms"
                  << "\nscope=compute-only\nvalue=" << std::setprecision(17)
                  << total_ms / repeat << "\nchecksum=" << checksum << '\n';
        return correct ? 0 : 3;
    } catch (const std::exception& e) {
        std::cerr << "# error: " << e.what() << '\n';
        return 2;
    }
}
```

程序只测量 `compute`，分配、初始化、参考校验、checksum 和打印均在计时外。每轮计算后仍读取全部结果，使输出可观察；读取本身会影响下一轮缓存，因此其计时对应本例重复流程，不能宣称是冷缓存测量。A/B 数据与正确性相同，但是否更快取决于编译器和机器。

### 完整 CMake 配置

保存为项目根目录 `CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.20)
project(terminal_lab LANGUAGES CXX)
add_executable(vector_lab src/vector_lab.cpp)
target_compile_features(vector_lab PRIVATE cxx_std_17)
if(MSVC)
  target_compile_options(vector_lab PRIVATE /W4 /utf-8)
else()
  target_compile_options(vector_lab PRIVATE -Wall -Wextra -Wpedantic)
endif()
include(CTest)
if(BUILD_TESTING)
  # 程序逐元素检查参考结果，错误结果返回非零，CTest 据此判失败。
  add_test(NAME vector_A COMMAND vector_lab 1003 A 2)
  add_test(NAME vector_B COMMAND vector_lab 1003 B 2)
  add_test(NAME vector_boundary COMMAND vector_lab 1 B 1)
  add_test(NAME reject_zero COMMAND vector_lab 0 A 1)
  set_tests_properties(reject_zero PROPERTIES WILL_FAIL TRUE)
endif()
```

MSVC 选项不能照抄 GCC 的 `-Wall`、`-fsanitize`。本项目按编译器选择告警选项，使用 target 级设置，不直接覆盖全局编译参数。

<span id="3-直接使用-g-编译"></span>
<span id="分别编译多个源文件"></span>
<span id="4-使用-make-管理构建"></span>

## 4. 直接编译与依赖规则

直接编译是独立路线，适合理解工具链，不与 CMake 构建目录混放：

```bash
# Linux · Bash，项目根目录
mkdir -p build-direct
g++ -std=c++17 -Wall -Wextra -g src/vector_lab.cpp -o build-direct/vector_lab
./build-direct/vector_lab 1003 A 2
```

```powershell
# Windows 本地 · MSVC Developer PowerShell，项目根目录
New-Item -ItemType Directory -Path build-direct -Force
cl /nologo /std:c++17 /EHsc /W4 /utf-8 /Zi src/vector_lab.cpp /Fobuild-direct/vector_lab.obj /Febuild-direct/vector_lab.exe
& ./build-direct/vector_lab.exe 1003 A 2
$programRc = $LASTEXITCODE
```

预期 `correctness=pass`、退出码 0，`checksum` 为所有轮次输出之和。规模为 0、版本不是 A/B 或重复次数非法时，程序输出诊断并返回 2；正常计算但参考验证失败时返回 3。

Make 只用最小规则说明依赖。Linux 中可把下面保存为独立 `Makefile`；**配方行开头必须是真实 Tab**，不是空格：

```make
CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -g
build-make/vector_lab: src/vector_lab.cpp
	mkdir -p build-make
	$(CXX) $(CXXFLAGS) $< -o $@
```

`make` 在源文件更新时重建目标，未变化时通常不再编译。真实多文件项目还需正确追踪头文件依赖；手写这个最小规则不能取代 CMake 已生成的完整依赖关系。

<span id="5-使用-cmake-配置和构建"></span>
<span id="清理和重新配置"></span>

## 5. CMake 配置与增量构建

### 单配置与多配置

本篇 Windows 主线使用 NMake 单配置生成器，Linux 使用 Unix Makefiles。配置和产物放入不同目录，不能在同一缓存目录切换编译器或生成器。

```powershell
# Windows 本地 · MSVC Developer PowerShell，项目根目录
cmake -S . -B build-windows -G 'NMake Makefiles' -DCMAKE_BUILD_TYPE=Debug
if ($LASTEXITCODE -ne 0) { throw '配置失败' }
cmake --build build-windows --verbose
if ($LASTEXITCODE -ne 0) { throw '构建失败' }
ctest --test-dir build-windows --output-on-failure
& ./build-windows/vector_lab.exe 1003 B 2
```

```bash
# Linux · Bash，项目根目录
cmake -S . -B build-linux -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Debug
cmake --build build-linux --parallel 2 --verbose
ctest --test-dir build-linux --output-on-failure
./build-linux/vector_lab 1003 B 2
```

Linux 每步都应检查退出码，构建失败后不要继续运行旧产物。NMake 不支持这里的并行构建参数，不能机械抄 Linux 命令。

如果选择 Visual Studio 多配置生成器，则是替代路线：配置时通常不通过 `CMAKE_BUILD_TYPE` 决定最终配置，构建用 `--config Debug`，测试用 `ctest -C Debug`，程序常在 `build-vs/Debug/vector_lab.exe`。三者须一致；不能用 Release 构建后去运行另一个目录中的 Debug 程序。

### 缓存与来源记录

`-DNAME=value` 创建或更新 CMake 缓存项，不保证项目一定使用该变量。检查变量名、实际构建目录和项目内部是否覆盖值：

```bash
# 命令同样可在 PowerShell 执行
cmake -LA -N build-linux
cmake --build build-linux --verbose
git rev-parse HEAD
git status --short
git diff HEAD --
git ls-files --others --exclude-standard
```

Windows 路线把上述目录替换为 `build-windows`。有未提交修改时，提交号不足以描述源码，暂存修改和未跟踪源文件都需保存；不在 Git 仓库时如实记录这一状态。配置阶段嵌入的提交号需要重新配置才能更新，也不能单独证明二进制对应完整源码。

只修改源码后运行 `cmake --build` 进行增量构建。缓存确实混乱时优先创建一个新构建目录；若清理旧目录，先核对它只包含生成物。`cmake --build ... --target clean` 也不等于删除整个配置缓存。

<span id="6-运行程序并检查结果"></span>
<span id="8-使用-ctest-运行测试"></span>

## 6. 运行验证与 CTest

CTest 主线有四项测试：A、B、单元素边界和拒绝零规模。前三项通过逐元素校验返回状态；最后一项用 `WILL_FAIL` 表示预期非零，但它不精确限定必须为 2，故仍应独立核对输入诊断。

“进程启动成功”不是正确性测试。下面的独立故障实验只在项目副本中执行，不修改原项目：先复制源码与 CMake 到 `terminal-lab-wrong`，在该副本中把 B 分支的 `2.0f * b[i]` 改成 `2.0f * b[i] + 1.0f`，保留参考公式，再配置和构建副本自己的目录。

预期 A 测试通过，B 与单元素边界测试失败；直接运行 B 返回 3。故障排除后恢复该行，重新构建并确认全部通过。若 CTest 仍全绿，先确认改的是副本、构建的是副本、运行的是副本产物，而不是删除测试以“修复”状态。

编译故障可在另一副本删去某条语句末尾分号。预期构建失败而旧程序可能仍存在，这解释了为什么不能把构建和运行状态混为一谈。链接故障可用声明存在但定义缺失的函数说明；错误属于目标文件与库连接问题，不应靠改 PATH 掩盖。

<span id="7-使用-gdb-调试"></span>
<span id="使用-sanitizer-查找内存错误"></span>

## 7. 调试与内存诊断

### GDB 最小流程

Linux 使用 Debug 程序与 GDB。Windows 如选用完整 MinGW-w64 GCC/GDB 路线，可直接编译带 `-g` 的独立程序，再使用同一套 GDB 操作；不要用这条路线调试 MSVC 生成的程序并承诺同样的源码信息。

```powershell
# Windows 本地 · PowerShell，额外安装 MinGW-w64 GCC 与 GDB
New-Item -ItemType Directory -Path build-gdb -Force
g++ -std=c++17 -g -O0 src/vector_lab.cpp -o build-gdb/vector_lab.exe
gdb --args build-gdb/vector_lab.exe 1003 B 2
```

Linux 对应入口为 `gdb --args build-linux/vector_lab 1003 B 2`。进入 GDB 后使用工具内部命令：

```text
break compute
run
print variant
next
backtrace
continue
quit
```

应停在 `compute` 并看到 variant 为 B。`next` 单步但不进入函数，`step` 可进入调用；`backtrace` 显示调用链。优化可能让变量不可见或源码步进不直观，调试配置应与普通性能配置分开。Windows 的 MinGW GDB 断点和变量查看已实测，MSVC 图形调试器流程未在本例验证。

### Sanitizer 独立实验

内存故障使用独立 `bad_memory.cpp`，不要把故意越界加入正常项目：

```cpp
int main() {
    int* values = new int[4]{};
    volatile int outside = values[4]; // 故意越界：合法索引为 0..3。
    delete[] values;
    return outside;
}
```

Linux GCC/Clang 支持相应 Sanitizer 的环境可执行：

```bash
g++ -g -O1 -fsanitize=address,undefined -fno-omit-frame-pointer bad_memory.cpp -o bad_memory
./bad_memory
```

MSVC 采用自己的 ASan 选项，需安装对应运行库，使用独立输出目录：

```powershell
cl /nologo /EHsc /Zi /fsanitize=address bad_memory.cpp /Febad_memory.exe
& ./bad_memory.exe
```

MSVC ASan 与 `/RTC`、增量链接等存在兼容限制，不能把 Linux 的 UBSan 支持直接等同到 MSVC。本例 MSVC ASan 故意越界检查已实测；Linux Sanitizer 未执行。诊断未报错不证明程序完全正确，带检查产物也不进入普通性能比较。

<span id="13-常用开发命令速查"></span>

## 8. 常见问题与命令速查

| 症状 | 检查与判断依据 | 处理 |
| --- | --- | --- |
| `cl` 存在但缺头文件 | 开发环境及 SDK 路径 | 使用安装提供的开发终端 |
| 修改后输出不变 | 构建退出码、配置和绝对程序路径 | 重建正确目录，记录二进制哈希 |
| CMake 的 `-D` 无效 | 缓存项、拼写及项目读取位置 | 检查实际缓存和构建命令 |
| 程序输出错误但测试通过 | 测试是否检查参考结果 | 将正确性失败转为非零状态 |
| 加载动态库失败 | 依赖架构、搜索路径及运行库 | 核对对应工具链的运行环境 |

| 阶段 | 入口 |
| --- | --- |
| 核对 | `Get-Command` / `command -v`、工具版本 |
| 配置 | `cmake -S . -B ...` |
| 构建 | `cmake --build ... --verbose` |
| 测试 | `ctest --test-dir ... --output-on-failure` |
| 调试 | `gdb --args ...`、`break`、`print`、`backtrace` |
| Python | `python -m venv`、环境内的 `python -m pip` |

<span id="12-一套推荐的开发循环"></span>

## 9. 实践练习

验收包括：正确项目四项测试通过；N=0 的直接运行返回 2；错误副本的 B 返回 3 且 CTest 发现错误；只修改源码后完成增量构建；记录编译器、配置、完整程序路径与代码状态。Windows MSVC 和 MinGW 构建均已实测，Linux 构建未执行，不能把 GCC 在 Windows 的成功称为 Linux 验证。

<span id="9-代码项目中的-git-工作流"></span>
<span id="10-搜索比较与打包"></span>
<span id="11-环境变量与-path"></span>

## 10. 旧章节入口与参考资料

原文环境变量移至[第二篇]({% post_url 2026-09-30-shell-execution-and-scripting %})，普通文件检索见[第一篇]({% post_url 2026-09-01-linux-terminal-common-commands %})，打包同步见[第四篇]({% post_url 2026-09-30-remote-development-and-task-management %})。Git 版本记录的完整规则见[Git 基本原理与学习路径]({% post_url 2026-09-16-git-learning-roadmap %})。

- [CMake 命令行手册](https://cmake.org/cmake/help/latest/manual/cmake.1.html)。
- [CTest 手册](https://cmake.org/cmake/help/latest/manual/ctest.1.html)。
- [GNU Make 手册](https://www.gnu.org/software/make/manual/make.html)。
- [GDB 单步与继续执行](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Continuing-and-Stepping.html)。
- [Microsoft AddressSanitizer](https://learn.microsoft.com/en-us/cpp/sanitizers/asan?view=msvc-170)。

上一篇：[Shell 执行与脚本基础]({% post_url 2026-09-30-shell-execution-and-scripting %}) · 下一篇：[远程开发与任务管理]({% post_url 2026-09-30-remote-development-and-task-management %})。
