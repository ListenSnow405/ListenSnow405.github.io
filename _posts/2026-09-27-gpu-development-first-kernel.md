---
layout: post
title: "开发环境与首个核函数"
date: 2026-09-27 23:00:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 核函数, GPU编程系列]
excerpt: "检查 CUDA 设备与工具链，编译向量加法核函数，并用 CPU 参考结果区分构建、运行和计算问题。"
series: gpu-programming
series_order: 1
---

本文完成 GPU 编程系列的第一个可运行案例：给定两个等长整数向量，分别用 CPU 循环和 CUDA 核函数计算逐项之和，并检查全部结果。阅读前需要会使用终端、读懂 C++ 数组和循环；建议先阅读[GPU 计算模型与学习路径]({{ '/posts/gpu-computing-roadmap/' | relative_url }})。实际运行需要受当前 CUDA 工具链支持的 NVIDIA GPU、兼容的驱动和主机编译器。没有可用设备时，仍可阅读代码并手算线程下标，但不能把静态阅读当成运行验证。

## 1. 开发环境

### 设备、驱动与工具链

先确认机器有可用于 CUDA 的 NVIDIA GPU，再按操作系统安装驱动、主机编译器和 CUDA Toolkit。Toolkit 提供 `nvcc`、头文件与运行时库；`nvcc` 负责组织 CUDA C++ 的主机端和设备端编译。Windows 需要使用对应 Toolkit 版本支持的 Visual Studio C++ 工具链；Linux 需要对应发行版及受支持的 GCC 工具链。安装步骤和兼容版本会变化，应以 [Windows 安装指南](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/)或 [Linux 安装指南](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)为准，不要照搬另一台机器的版本组合。

安装后在终端检查：

```text
nvidia-smi
nvcc --version
```

Windows 可在 Visual Studio 的 Developer PowerShell 中再运行 `cl`，Linux 可运行 `gcc --version`。`nvidia-smi` 用来查看驱动是否识别设备；其中的“CUDA Version”表示驱动支持的 CUDA 版本上限，**不是**本机已安装的 Toolkit 版本。`nvcc --version` 才用于检查当前终端找到的编译器。能显示版本仍不能证明核函数可运行，最终要编译并执行下面的程序。若命令找不到，先检查安装和终端环境；若版本不兼容，应核对 Toolkit 的发行说明及安装指南，不要盲目更改 PATH 或忽略编译器检查。

### 练习目录与编译

在电脑硬盘中建立空练习目录，例如 `gpu-practice/first-kernel/`，并在其中创建 `vector_add.cu`，将下一节的完整代码原样以 UTF-8 编码保存到该文件。`.cu` 表示文件含 CUDA 设备代码。进入该目录后，Windows 在 Visual Studio 的 Developer PowerShell 中执行：

```powershell
nvcc -Xcompiler /utf-8 vector_add.cu -o vector_add.exe
.\vector_add.exe
```

Linux 在相应发行版的终端中执行：

```bash
nvcc vector_add.cu -o vector_add
./vector_add
```

示例代码含中文注释，Windows 命令中的 `-Xcompiler /utf-8` 将 UTF-8 源码编码选项传给 MSVC；省略它可能导致中文注释被错误解析。若提示找不到 `cl.exe`，应先使用已安装且受 Toolkit 支持的 Visual Studio C++ 开发者终端。编译通过只说明源代码和工具链完成了构建；设备可用性与结果正确性还要分别检查。

## 2. 向量加法案例

### 输入、参考结果与内存位置

令 `a[i] = i`、`b[i] = 2 * i`，长度为 1000，目标为 `c[i] = a[i] + b[i]`。CPU 参考实现通过循环求出每一项，前四项应为 `0、3、6、9`。选整数使本例可以逐项精确比较；浮点运算的比较规则留给后续数值精度专题。

`std::vector` 中的 `a`、`b`、`cpu`、`gpu` 位于主机端。核函数接收的 `d_a`、`d_b`、`d_c` 指向设备端缓冲区。可以把指针先理解为“数据所在位置的地址”：`cudaMalloc` 申请设备空间，`cudaMemcpy` 按方向复制数据，`cudaFree` 释放设备空间。本章只用这些接口完成闭环；传输时机与生命周期会在“设备内存与数据传输”专题中深入讨论。

```text
主机 a、b ──复制到设备──> d_a、d_b
                            │
                      向量加法核函数
                            ↓
主机 gpu  <──复制回主机── d_c
    │
    └──逐项对照主机 cpu
```

### 完整程序

以下代码是一个**完整文件**，不要将各段当作需要依次运行的独立片段。所有 CUDA 调用都检查返回值；核函数启动后分别检查启动错误和执行错误。

```cpp
#include <cuda_runtime.h>

#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <vector>

// 统一检查 CUDA API 的返回值；失败时打印源文件、行号和可读的错误信息。
// 本例直接退出，便于初学时把错误定位到具体调用。
#define CUDA_CHECK(call)                                                    \
    do {                                                                    \
        const cudaError_t error = (call);                                   \
        if (error != cudaSuccess) {                                         \
            std::cerr << "CUDA error at " << __FILE__ << ':' << __LINE__    \
                      << ": " << cudaGetErrorString(error) << '\n';       \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                   \
    } while (false)

__global__ void vector_add(const int* a, const int* b, int* c, int n) {
    // 块号乘以块大小，得到本块的起始下标；再加上线程在块内的下标。
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    // 最后一块可能有多余线程；先检查范围，再读取输入或写入输出。
    if (i < n) {
        c[i] = a[i] + b[i];
    }
}

int main() {
    constexpr int n = 1000;
    constexpr int threads_per_block = 256;
    // 向上取整，确保不足一整块的剩余元素也有线程处理。
    const int blocks = (n + threads_per_block - 1) / threads_per_block;
    const std::size_t bytes = static_cast<std::size_t>(n) * sizeof(int);

    // 主机端准备输入，并用普通 CPU 循环计算逐项对照的参考结果。
    std::vector<int> a(n), b(n), cpu(n), gpu(n);
    for (int i = 0; i < n; ++i) {
        a[i] = i;
        b[i] = 2 * i;
        cpu[i] = a[i] + b[i];
    }

    // 在分配设备内存前，先确认 CUDA 运行时能找到可用设备。
    int device_count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }

    // 三个 d_ 指针分别指向设备上的两个输入缓冲区和一个输出缓冲区。
    int *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_a), bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_b), bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_c), bytes));
    // 只复制两个输入；输出 d_c 将由核函数写入，不必预先从主机复制。
    CUDA_CHECK(cudaMemcpy(d_a, a.data(), bytes, cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, b.data(), bytes, cudaMemcpyHostToDevice));

    // 启动 blocks 个线程块，每块 threads_per_block 个线程。
    vector_add<<<blocks, threads_per_block>>>(d_a, d_b, d_c, n);
    // 启动调用会先返回：分别检查启动配置，并等待设备完成后检查执行错误。
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    // 确认计算完成后，将设备输出复制回主机，供下面的循环逐项检查。
    CUDA_CHECK(cudaMemcpy(gpu.data(), d_c, bytes, cudaMemcpyDeviceToHost));

    // CUDA API 成功不代表算式或下标一定正确，因此仍要与 CPU 结果比较。
    bool matches = true;
    for (int i = 0; i < n; ++i) {
        if (gpu[i] != cpu[i]) {
            std::cerr << "Mismatch at " << i << ": CPU=" << cpu[i]
                      << ", GPU=" << gpu[i] << '\n';
            matches = false;
            break;
        }
    }

    // 正常路径释放本例申请的全部设备缓冲区。
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));

    std::cout << "n=" << n << ", blocks=" << blocks
              << ", threads_per_block=" << threads_per_block
              << ", result=" << (matches ? "PASS" : "FAIL") << '\n';
    return matches ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

这里把错误处理写成简短宏，便于定位失败的调用和行号；若发生错误，示例程序会直接退出。正常路径会显式释放三块设备内存。长期运行的应用应把资源生命周期和错误恢复设计得更完整，不能依赖这个教学宏处理所有情况。

### 核函数与启动配置

`__global__` 标记由设备执行、可从主机启动的核函数。`<<<blocks, threads_per_block>>>` 指定本次启动的网格中有多少线程块、每块安排多少线程。块内线程的 `threadIdx.x` 从 0 开始；`blockIdx.x` 是块号；`blockDim.x` 是块大小。因此 `blockIdx.x * blockDim.x + threadIdx.x` 给每个逻辑线程一个一维下标。每个有效线程只读 `a[i]`、`b[i]` 并写 `c[i]`，无需等待其他线程。

1000 项按每块 256 个线程安排，需要 `(1000 + 256 - 1) / 256 = 4` 块，共启动 1024 个逻辑线程。最后 24 个线程的下标超出输入范围，所以必须在**读取和写入之前**检查 `i < n`。这里的 256 是便于演示的块大小，不是所有设备或任务的最佳配置。下一章会系统解释一维与二维映射及边界。

核函数启动相对于主机是异步的：启动语句返回，不等于设备已经完成计算。`cudaGetLastError()` 检查启动阶段报告的错误；`cudaDeviceSynchronize()` 等待先前设备工作结束并检查执行阶段错误，然后才复制结果。即使这两步都成功，仍可能写错索引或算式，所以最后要与 CPU 的全部 1000 项逐一比较。[CUDA C++ 编程指南的错误处理章节](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html#asynchronous-errors)也区分了启动检查与异步执行检查。

## 3. 运行结果与问题定位

### 预期输出

若编译、执行和逐项验证都成功，应看到：

```text
n=1000, blocks=4, threads_per_block=256, result=PASS
```

`PASS` 只证明这组输入在当前运行环境下与 CPU 参考结果一致，不能证明所有输入都正确，也不能证明 GPU 比 CPU 快。当前程序没有计时；性能比较需要先定义端到端范围、预热和同步，后续专题再处理。

### 故障分类

| 阶段 | 常见现象 | 首先检查 |
| --- | --- | --- |
| 编译 | `nvcc` 或主机编译器未找到、头文件缺失、语法错误 | Toolkit 与受支持的主机编译器、终端环境、`.cu` 文件内容。 |
| 运行 | `cudaGetDeviceCount`、分配、复制、启动或同步返回错误 | 设备和驱动状态、错误所在行及 `cudaGetErrorString` 信息。 |
| 计算 | 程序运行结束但输出 `FAIL` | 首个不匹配下标、索引公式、边界判断和 CPU 参考结果。 |

例如，把 `blocks` 错写成 `n / threads_per_block`，只会启动 3 块，遗漏最后 232 项。CUDA 调用可能全部返回成功，但逐项比较会发现结果不符。这说明“没有运行时错误”和“计算正确”是两种不同的检查。

## 命令速查

| 命令或接口 | 作用 |
| --- | --- |
| `nvidia-smi`、`nvcc --version` | 分别检查设备驱动可见性与当前编译工具链。 |
| `nvcc -Xcompiler /utf-8 vector_add.cu -o vector_add.exe`（Windows）；`nvcc vector_add.cu -o vector_add`（Linux） | 编译含主机与设备代码的完整程序；Windows 同时指定 UTF-8 源码编码。 |
| `cudaMalloc`、`cudaMemcpy`、`cudaFree` | 申请设备空间、复制数据、释放设备空间。 |
| `cudaGetLastError`、`cudaDeviceSynchronize` | 检查启动状态，等待并检查核函数执行。 |

## 实践练习

1. 将 `n` 分别改为 `1`、`256`、`257`，每次重新编译和运行。**验收标准**：三次均为 `PASS`，块数分别为 `1`、`1`、`2`；说明为什么 257 项需要第二个块。
2. 在隔离练习目录中将块数计算暂时改成 `n / threads_per_block`，保持 `n = 1000`，重新编译并观察结果；然后恢复原式。**验收标准**：能指出遗漏的下标范围，并解释为什么这属于计算错误而非必然的 CUDA 运行错误。
3. 画出 `a`、`b`、`gpu` 与 `d_a`、`d_b`、`d_c` 的位置和复制方向。**验收标准**：输入在启动前到达设备，输出在检查前回到主机，三块设备内存均有释放步骤。

## 参考资料

- [NVIDIA CUDA 安装指南：Windows](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/)
- [NVIDIA CUDA 安装指南：Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)
- [NVIDIA CUDA Programming Guide：Intro to CUDA C++](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html)
- [NVIDIA CUDA Programming Guide：Writing SIMT Kernels](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html)

**系列导航**：上一篇 · [GPU 计算模型与学习路径]({{ '/posts/gpu-computing-roadmap/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [线程组织与数据映射]({{ '/posts/gpu-thread-organization-and-data-mapping/' | relative_url }})。
