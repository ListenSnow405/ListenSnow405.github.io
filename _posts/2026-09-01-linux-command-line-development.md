---
layout: post
title: "Linux 命令行开发：编译、构建与调试"
date: 2026-09-01 09:10:00 +0800
categories: [学习]
tags: [Linux, C++, CMake, Make, Git]
---

在[上一篇文章]({% post_url 2026-09-01-linux-terminal-common-commands %})中，我们学习了目录、文件、搜索和进程等基础命令。这些能力解决了“如何操作 Linux”的问题，而这篇文章继续解决另一个问题：如何只用终端完成一个代码项目的编译、构建、运行和调试。

本文以一个小型 C++ 项目为主线。即使以后使用 Python、Rust 或其他语言，其中关于目录、环境变量、Git 和排错的思路仍然适用。

## 1. 编译和构建有什么区别

对于 C、C++ 这类编译型语言，一份源代码通常会经历：

```text
源代码 → 预处理 → 编译 → 汇编 → 目标文件 → 链接 → 可执行文件
```

“编译”有时泛指整个过程，严格来说则只是其中一步。“构建”范围更广，它可能包含生成配置、编译多个源文件、链接库、运行测试和打包等任务。

几个常见工具的职责并不相同：

- `gcc`、`g++`：编译并链接 C、C++ 程序；
- `make`：按照 `Makefile` 描述的依赖关系执行构建命令；
- `cmake`：读取 `CMakeLists.txt`，生成构建系统；
- `cmake --build`：调用生成后的底层构建工具完成构建。

因此，`build` 通常不是某个固定的 Linux 命令，而是项目约定的构建目录、脚本名称或构建动作。

## 2. 准备开发环境

先确认工具是否存在：

```bash
command -v g++
command -v make
command -v cmake
command -v gdb
git --version
```

`command -v` 会告诉我们 Shell 实际会执行哪个程序。以 Ubuntu 或 Debian 为例，可以安装常用工具：

```bash
sudo apt update
sudo apt install build-essential cmake gdb git
```

Fedora、Arch Linux 等发行版的软件包名称和安装命令可能不同，应根据发行版文档进行调整。

接下来创建一个练习项目：

```bash
mkdir -p hello-project/src
cd hello-project
```

项目最终会具有下面的结构：

```text
hello-project/
├── CMakeLists.txt
├── Makefile
├── include/
│   └── greet.h
├── src/
│   ├── greet.cpp
│   └── main.cpp
└── build/
```

其中 `build/` 保存生成文件和编译产物，不与源代码混放。

## 3. 直接使用 `g++` 编译

假设 `src/main.cpp` 的内容如下：

```cpp
#include <iostream>

int main() {
    std::cout << "Hello, Linux!\n";
    return 0;
}
```

最简单的编译命令是：

```bash
g++ src/main.cpp -o hello
./hello
```

`-o hello` 指定输出文件名；运行当前目录中的程序时要写 `./hello`，因为当前目录通常不在 `PATH` 中。

实际开发中可以打开更多检查：

```bash
g++ -std=c++17 -Wall -Wextra -pedantic -g src/main.cpp -o hello
```

- `-std=c++17`：使用 C++17 标准；
- `-Wall -Wextra -pedantic`：启用常见警告；
- `-g`：保留调试信息；
- `-O2`：常用的优化级别，通常用于发布构建。

警告往往意味着潜在错误。除非知道原因，不要用关闭警告的选项掩盖它们。

### 分别编译多个源文件

当项目包含多个源文件时，可以先生成目标文件，再进行链接：

```bash
mkdir -p build
g++ -std=c++17 -Wall -Wextra -g -Iinclude -c src/main.cpp -o build/main.o
g++ -std=c++17 -Wall -Wextra -g -Iinclude -c src/greet.cpp -o build/greet.o
g++ build/main.o build/greet.o -o build/hello
./build/hello
```

`-c` 表示只编译、不链接，`-Iinclude` 把 `include/` 加入头文件搜索路径。只修改 `greet.cpp` 时，理论上只需要重新生成 `greet.o`，这就是增量构建的基础。

## 4. 使用 Make 管理构建

每次手工输入完整编译命令很容易出错。Make 会根据文件的更新时间判断哪些目标需要重新生成。

可以在项目根目录编写下面的 `Makefile`：

```makefile
CXX := g++
CXXFLAGS := -std=c++17 -Wall -Wextra -pedantic -g -Iinclude
TARGET := build/hello
OBJECTS := build/main.o build/greet.o

$(TARGET): $(OBJECTS)
	$(CXX) $(OBJECTS) -o $(TARGET)

build/main.o: src/main.cpp include/greet.h
	mkdir -p build
	$(CXX) $(CXXFLAGS) -c src/main.cpp -o build/main.o

build/greet.o: src/greet.cpp include/greet.h
	mkdir -p build
	$(CXX) $(CXXFLAGS) -c src/greet.cpp -o build/greet.o

.PHONY: clean
clean:
	rm -f $(OBJECTS) $(TARGET)
```

> `Makefile` 中每条构建命令前必须是 Tab，而不是若干个空格。

常用操作如下：

```bash
make
make -j4
make clean
```

不带目标的 `make` 会构建第一个目标；`-j4` 最多并行执行四个任务；`make clean` 是这个 `Makefile` 自己定义的清理动作，并不是 Make 内置的固定命令。

手写 Makefile 有助于理解依赖关系，但项目变大、需要跨平台或依赖第三方库时，通常会使用 CMake 等更高层的构建系统。

## 5. 使用 CMake 配置和构建

CMake 自己通常不直接完成编译，而是生成 Makefile、Ninja 文件或 IDE 工程，再驱动相应工具构建。

在项目根目录创建 `CMakeLists.txt`：

```cmake
cmake_minimum_required(VERSION 3.16)
project(hello_project LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(hello
    src/main.cpp
    src/greet.cpp
)

target_include_directories(hello PRIVATE include)
target_compile_options(hello PRIVATE -Wall -Wextra -pedantic)
```

推荐使用源外构建，让生成文件集中在 `build/` 中：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
./build/hello
```

- `-S .`：源代码目录是当前目录；
- `-B build`：把生成文件放入 `build/`；
- `-DCMAKE_BUILD_TYPE=Debug`：生成便于调试的构建配置；
- `cmake --build build`：用统一接口调用实际构建工具；
- `-j`：允许并行构建。

发布前可以创建另一个构建目录，避免与调试配置相互覆盖：

```bash
cmake -S . -B build-release -DCMAKE_BUILD_TYPE=Release
cmake --build build-release -j
```

部分多配置生成器会忽略配置阶段的 `CMAKE_BUILD_TYPE`，此时需要在构建阶段使用 `--config Debug` 或 `--config Release`。

修改 `CMakeLists.txt` 后，再次执行配置命令即可。只修改源代码时，通常直接执行 `cmake --build build`，构建工具会自动处理变化的部分。

### 清理和重新配置

清理编译产物可以运行：

```bash
cmake --build build --target clean
```

如果缓存或生成器配置已经混乱，可以删除明确指定的构建目录后重新配置。先确认它确实是当前项目的构建产物：

```bash
pwd
ls build
rm -ri build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
```

不要在不确定当前位置或变量内容时执行递归删除。

## 6. 运行程序并检查结果

运行程序后，可以查看退出状态：

```bash
./build/hello
echo $?
```

按照约定，`0` 通常表示成功，非零值表示错误。只有紧接着运行 `echo $?`，看到的才是刚才那条命令的退出状态。

命令行参数会放在程序名之后：

```bash
./build/hello Alice
```

如果程序需要输入，可以使用重定向：

```bash
./build/hello < input.txt
./build/hello < input.txt > output.txt
```

测量运行时间可以使用：

```bash
time ./build/hello
```

## 7. 使用 GDB 调试

程序崩溃或结果错误时，先确保使用 `-g` 或 Debug 配置进行构建，然后启动 GDB：

```bash
gdb ./build/hello
```

进入 GDB 后，常用命令有：

```text
break main       在 main 函数处设置断点
run              启动程序
next             执行下一行，不进入函数
step             执行下一行，必要时进入函数
print variable   查看变量
backtrace        查看调用栈，也可以简写为 bt
continue         继续运行
quit             退出 GDB
```

程序带参数时可以使用 `run Alice`，或者启动 GDB 后先执行 `set args Alice`。

### 使用 Sanitizer 查找内存错误

GCC 和 Clang 支持多种运行时检查。下面的 AddressSanitizer 和 UndefinedBehaviorSanitizer 能发现许多越界访问、释放后使用和未定义行为：

```bash
g++ -std=c++17 -Wall -Wextra -g \
  -fsanitize=address,undefined \
  -fno-omit-frame-pointer \
  src/main.cpp -o build/hello-sanitize

./build/hello-sanitize
```

Sanitizer 不是证明程序完全正确的工具，但它比只观察“程序是否崩溃”有效得多。

## 8. 使用 CTest 运行测试

CMake 自带 CTest 接口。可以先在 `CMakeLists.txt` 中添加一个最简单的测试：

```cmake
include(CTest)

if(BUILD_TESTING)
    add_test(NAME hello_runs COMMAND hello)
endif()
```

重新配置并构建后执行：

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build -j
ctest --test-dir build --output-on-failure
```

`--output-on-failure` 会在测试失败时显示输出，适合本地排错和持续集成环境。

## 9. 代码项目中的 Git 工作流

Git 用来记录源代码的历史，而生成的构建产物通常不应提交。初始化仓库前，可以在 `.gitignore` 中加入：

```gitignore
/build/
/build-release/
*.o
```

然后执行：

```bash
git init
git status
git add CMakeLists.txt src include .gitignore
git diff --cached
git commit -m "Add initial CMake project"
```

开发过程中最常用的是：

```bash
git status              # 查看工作区状态
git diff                # 查看尚未暂存的修改
git diff --cached       # 查看准备提交的修改
git log --oneline       # 查看简洁历史
git switch -c feature   # 创建并切换到新分支
```

在 `git add` 和 `git commit` 之前先查看差异，可以避免误提交临时文件、调试代码或敏感信息。

## 10. 搜索、比较与打包

面对真实项目时，下面这些命令很实用：

```bash
rg "TODO" src include
rg --files -g "*.cpp" -g "*.h"
find build -type f -name "*.o"
tree -L 2
diff -u old.cpp new.cpp
```

- `rg`：快速搜索代码或列出文件；
- `find`：按名称、类型等条件查找文件；
- `tree`：展示目录树，部分系统需要单独安装；
- `diff -u`：以统一格式比较两个文件。

项目源码还可以用 `tar` 打包和解压：

```bash
tar -czf hello-project.tar.gz --exclude=build hello-project/
tar -tzf hello-project.tar.gz
tar -xzf hello-project.tar.gz
```

解压来源不明的压缩包之前，先用 `tar -t` 查看其中的路径和内容。

## 11. 环境变量与 `PATH`

程序能够直接通过名字运行，通常是因为它所在的目录列在 `PATH` 环境变量中：

```bash
printf '%s\n' "$PATH"
command -v cmake
```

可以为当前 Shell 临时设置环境变量：

```bash
export APP_MODE=debug
./build/hello
```

也可以只为一条命令设置：

```bash
APP_MODE=debug ./build/hello
```

把工具加入 `PATH` 时，应追加明确的目录，不要用一个全新的值覆盖原有内容：

```bash
export PATH="$PATH:$HOME/tools/bin"
```

Shell 启动文件中的修改会影响之后的终端会话。写入 `~/.bashrc` 或 `~/.zshrc` 前，应理解修改内容，并在修改后重新打开终端或加载对应文件。

## 12. 一套推荐的开发循环

实际写代码时，可以把工作过程收敛为一个稳定循环：

1. 使用 `git status` 确认当前分支和工作区状态；
2. 编辑源代码，并用 `rg` 定位相关定义和调用；
3. 运行 `cmake --build build -j` 增量构建；
4. 运行程序，并检查输出和退出状态；
5. 执行 `ctest --test-dir build --output-on-failure`；
6. 出现崩溃时使用 GDB 或 Sanitizer；
7. 使用 `git diff` 检查修改，再提交一个职责明确的版本。

第一次配置项目时命令会多一些，之后最常执行的往往只是：

```bash
cmake --build build -j && ctest --test-dir build --output-on-failure
```

因为使用了 `&&`，只有构建成功时才会继续运行测试。

## 13. 常用开发命令速查

| 场景 | 命令 |
| --- | --- |
| 检查工具 | `command -v`、`--version` |
| 直接编译 | `gcc`、`g++` |
| Make 构建 | `make`、`make -j`、`make clean` |
| CMake 配置 | `cmake -S . -B build` |
| CMake 构建 | `cmake --build build -j` |
| 运行测试 | `ctest --test-dir build --output-on-failure` |
| 调试与检查 | `gdb`、Sanitizer |
| 搜索与比较 | `rg`、`find`、`diff` |
| 版本控制 | `git status`、`git diff`、`git add`、`git commit` |
| 环境定位 | `command -v`、`env`、`PATH` |

构建工具的命令看起来很多，但核心始终是三件事：描述目标和依赖、只重做发生变化的部分、让构建过程可以稳定复现。理解这三个目标之后，再接触更大的 CMake 项目、第三方依赖和持续集成，也会更容易找到方向。
