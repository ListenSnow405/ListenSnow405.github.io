---
layout: post
title: "线程组织与数据映射"
date: 2026-09-28 00:00:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 线程组织, 数据映射, GPU编程系列]
excerpt: "从一维下标推导二维线程坐标，用图像阈值处理验证网格配置、行优先存储和非整块边界。"
series: gpu-programming
series_order: 2
---

上一章用一个线程处理向量中的一个元素。本章把同样的分工方式用于二维图像：每个有效线程处理一个像素，先求出行、列，再换算为内存中的线性下标。目标是能为不同宽高配置网格，并确认边缘没有遗漏、重复或越界。阅读前应理解 C++ 数组、循环，以及[第一章的核函数启动与结果检查]({{ '/posts/gpu-development-first-kernel/' | relative_url }})；运行示例仍需可用的 CUDA 设备与工具链。

## 1. 线程层级与一维下标

### 网格、线程块与线程

一次核函数启动会生成一个**网格**（grid）。网格包含多个**线程块**（block），每个块包含多个逻辑**线程**（thread）。启动配置 `kernel<<<grid, block>>>(...)` 中，`grid` 表示各维的块数，`block` 表示每块各维的线程数。核函数内可以读取 `blockIdx`（块在网格中的编号）、`threadIdx`（线程在块中的编号）、`blockDim`（块在各维的大小）和 `gridDim`（网格在各维的大小）。这些编号从 0 开始。

对于一维数据，前一章使用：

```cpp
const int i = blockIdx.x * blockDim.x + threadIdx.x;
if (i < n) {
    output[i] = input[i];
}
```

若 `n = 10`、每块 4 个线程，则块数向上取整为 `(10 + 4 - 1) / 4 = 3`。三个块提供下标 `0–11`，其中 `10、11` 必须在读写前退出。[导读中的十像素图解]({{ '/posts/gpu-computing-roadmap/' | relative_url }}#线程与像素的对应关系)展示了这一分工。本章的二维写法只是分别对横向和纵向做同样的计算。

### 二维坐标

设线程块大小为 `dim3 block(4, 2)`：每块横向 4 个线程、纵向 2 行，共 `4 × 2 = 8` 个线程。`dim3 grid(2, 3)` 表示横向 2 个块、纵向 3 个块，共 6 个块；它**不是** 2×3 个线程。CUDA 的 `dim3` 可表达一维、二维或三维配置，省略的维度默认为 1。二维线程的全局列、行坐标分别为：

```cpp
const int x = blockIdx.x * blockDim.x + threadIdx.x; // 列
const int y = blockIdx.y * blockDim.y + threadIdx.y; // 行
```

例如，块 `(1, 2)` 内的线程 `(1, 0)` 对应 `(x, y) = (5, 4)`。`x` 与 `y` 是逻辑坐标；它们不要求图像真的以二维数组形式分配。配置的线程总数还须符合设备对单块线程数和各维大小的限制；`4 × 2` 是为手算选择的小配置，不代表合适的性能参数。[CUDA 编程指南的线程层级说明](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-hierarchy)给出了内置变量和维度规则。

## 2. 图像像素与网格映射

### 输入与行优先存储

继续使用导读中的单通道阈值任务：输入像素大于或等于 `128` 时输出 `255`，否则输出 `0`。以宽 `5`、高 `2` 的图像为例，输入和期望输出为：

| 行 `y` | 输入像素（列 `x = 0–4`） | 期望输出 |
| --- | --- | --- |
| 0 | `10, 130, 128, 200, 0` | `0, 255, 255, 255, 0` |
| 1 | `255, 126, 127, 128, 100` | `255, 0, 0, 255, 0` |

程序把像素按**行优先**顺序放进连续的一维缓冲区：先存完第 0 行，再存第 1 行。宽度为 `width` 时，坐标 `(x, y)` 对应 `index = y * width + x`。例如 `(4, 0)` 的下标为 4，`(0, 1)` 的下标为 5。这个乘数是**图像宽度**，不是线程块宽度；若换成带行跨度的图像缓冲区，公式也要相应改变。本章只处理无填充的连续存储。

### 网格尺寸与边界

对于宽 `5`、高 `2`、块大小 `4 × 2` 的图像，横向需要 `ceil(5 / 4) = 2` 个块，纵向需要 `ceil(2 / 2) = 1` 个块，即 `dim3 grid(2, 1)`。整数运算可以写成 `(width + block.x - 1) / block.x` 与 `(height + block.y - 1) / block.y`；这里要求宽高为正。

| 块坐标 | 产生的列 `x` | 产生的行 `y` | 有效像素 |
| --- | --- | --- | --- |
| `(0, 0)` | `0–3` | `0–1` | 前四列，共 8 个 |
| `(1, 0)` | `4–7` | `0–1` | 仅第 4 列，共 2 个 |

两个块共提供 16 个逻辑线程，实际只有 10 个有效像素。第 5–7 列的线程要先检查 `x < width`，再读取或写入。如果高度也不是块高的整数倍，底部的线程还须检查 `y < height`。因此核函数使用 `if (x >= width || y >= height) return;`。检查坐标后才计算并访问 `y * width + x`，可以直接对应图像的有效区域。

## 3. 完整阈值处理程序

### 练习目录与编译

在博客仓库之外建立 `gpu-practice/thread-mapping/` 练习目录，把下方**整个代码块**保存为 UTF-8 编码的 `image_threshold.cu`。沿用第一章已经确认可工作的终端与工具链。进入该目录后，Windows 在 Visual Studio Developer PowerShell 中执行：

```powershell
nvcc -Xcompiler /utf-8 image_threshold.cu -o image_threshold.exe
.\image_threshold.exe
```

Linux 执行：

```bash
nvcc image_threshold.cu -o image_threshold
./image_threshold
```

代码先用普通 CPU 循环计算参考结果，再启动二维 CUDA 核函数，并逐项比较。第一组输入是上表中的 `5 × 2` 图像，检验右边界；第二组是按固定公式生成的 `9 × 5` 图像，横向和纵向都有非整块边界。设备内存接口沿用第一章，分配与传输的生命周期会在下一章集中解释。

```cpp
#include <cuda_runtime.h>

#include <cstddef>
#include <cstdlib>
#include <iostream>
#include <vector>

// 每个 CUDA 调用都检查返回值；出错时显示位置并结束此练习程序。
#define CUDA_CHECK(call)                                                    \
    do {                                                                    \
        const cudaError_t error = (call);                                   \
        if (error != cudaSuccess) {                                         \
            std::cerr << "CUDA error at " << __FILE__ << ':' << __LINE__    \
                      << ": " << cudaGetErrorString(error) << '\n';       \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                   \
    } while (false)

// 一条有效线程处理一个像素；无效线程在访问缓冲区之前退出。
__global__ void threshold_image(const unsigned char* input,
                                unsigned char* output,
                                int width, int height) {
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height) {
        return;
    }

    // 图像按行连续存放，行号乘图像宽度后再加列号。
    const int index = y * width + x;
    output[index] = input[index] >= 128 ? 255 : 0;
}

// 对单组正宽高的输入计算 CPU 参考值，再验证整张 GPU 输出。
bool run_case(const std::vector<unsigned char>& input, int width, int height) {
    const std::size_t count = static_cast<std::size_t>(width) * height;
    const std::size_t bytes = count * sizeof(unsigned char);
    std::vector<unsigned char> expected(count), actual(count);
    for (std::size_t i = 0; i < count; ++i) {
        expected[i] = input[i] >= 128 ? 255 : 0;
    }

    unsigned char *d_input = nullptr, *d_output = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_input), bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_output), bytes));
    CUDA_CHECK(cudaMemcpy(d_input, input.data(), bytes, cudaMemcpyHostToDevice));
    // 未写到的输出保留 127；它与合法结果 0、255 均不同，便于发现遗漏。
    CUDA_CHECK(cudaMemset(d_output, 127, bytes));

    const dim3 block(4, 2); // 小尺寸用于观察映射，不作为性能推荐值。
    const dim3 grid((width + block.x - 1) / block.x,
                    (height + block.y - 1) / block.y);
    threshold_image<<<grid, block>>>(d_input, d_output, width, height);
    CUDA_CHECK(cudaGetLastError());       // 检查启动配置等即时错误。
    CUDA_CHECK(cudaDeviceSynchronize());  // 等待完成并检查执行错误。
    CUDA_CHECK(cudaMemcpy(actual.data(), d_output, bytes,
                          cudaMemcpyDeviceToHost));

    bool matches = true;
    for (std::size_t i = 0; i < count; ++i) {
        if (actual[i] != expected[i]) {
            std::cerr << "Mismatch at (x=" << i % width << ", y=" << i / width
                      << "): CPU=" << static_cast<int>(expected[i])
                      << ", GPU=" << static_cast<int>(actual[i]) << '\n';
            matches = false;
            break;
        }
    }

    // 正常路径释放两块设备缓冲区。
    CUDA_CHECK(cudaFree(d_input));
    CUDA_CHECK(cudaFree(d_output));
    std::cout << width << 'x' << height << ", grid=" << grid.x << 'x' << grid.y
              << ", result=" << (matches ? "PASS" : "FAIL") << '\n';
    return matches;
}

int main() {
    int device_count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }

    // 第一组直接对应正文的 5×2 表格，可手算核对每个像素。
    const std::vector<unsigned char> small = {
        10, 130, 128, 200, 0,
        255, 126, 127, 128, 100
    };
    const bool small_ok = run_case(small, 5, 2);

    // 第二组宽高都不能被块的对应维度整除，检查右侧和底部边界。
    constexpr int width = 9;
    constexpr int height = 5;
    std::vector<unsigned char> irregular(width * height);
    for (int i = 0; i < width * height; ++i) {
        irregular[i] = static_cast<unsigned char>((i * 37 + 10) % 256);
    }
    const bool irregular_ok = run_case(irregular, width, height);
    return small_ok && irregular_ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

这里用 `cudaMemset` 把设备输出预置为 `127`，目的是让未写入的有效像素在比较时显露出来；`127` 不属于阈值函数的合法输出。它不能代替越界检测。CUDA 调用失败时程序会直接退出，正常路径才显式释放内存；生产程序仍需设计完整的资源管理与错误恢复。

### 预期结果与验证

两组尺寸对应的网格分别为 `2 × 1` 和 `3 × 3`。若构建、设备执行和全部像素比较均成功，程序输出应为：

```text
5x2, grid=2x1, result=PASS
9x5, grid=3x3, result=PASS
```

第二组共安排 `3 × 3 × 4 × 2 = 72` 个逻辑线程，其中 45 个对应有效像素。`PASS` 表示这两组输入的 GPU 结果与 CPU 参考值逐项相同，不能推出任意尺寸都正确，也不能据此判断性能。把网格横向块数误写成 `width / block.x`，第一组会漏掉第 4 列；预置值使漏写位置显示为 `127`，比较会报告首个错误坐标。

## 4. 映射规则与常见问题

| 写法或现象 | 原因与检查点 |
| --- | --- |
| `grid.x = width / block.x` | 整数除法向下取整，右侧不足一块的列无人处理；改用向上取整。 |
| 只检查 `x` | 底部多出的线程仍可能访问越界；同时检查 `x` 与 `y`。 |
| 用 `y * blockDim.x + x` 算像素下标 | 块宽不是图像每行的像素数；行优先存储应乘 `width`。 |
| 两个线程写入同一像素 | 检查全局坐标是否同时包含块号与块内编号，再检查线性下标。 |
| `cudaGetLastError()` 成功但结果不符 | 启动成功不保证索引或算式正确；仍需与 CPU 参考结果比较。 |

本章的一维与二维配置都是把逻辑线程映射到数据的办法。选二维网格便于直接表达图像的行列，并不自动提高速度；实际性能还受访存、线程块资源和硬件调度影响。网格也不等于同一时刻并行运行的物理线程数量，不能据此推断设备同时执行了多少个像素。存储访问和性能选择留待后续专题。

## 规则速查

| 目的 | 表达式 |
| --- | --- |
| 一维全局下标 | `blockIdx.x * blockDim.x + threadIdx.x` |
| 二维全局列、行 | `x = blockIdx.x * blockDim.x + threadIdx.x`；`y = blockIdx.y * blockDim.y + threadIdx.y` |
| 二维网格块数 | `grid.x = (width + block.x - 1) / block.x`；`grid.y = (height + block.y - 1) / block.y` |
| 连续行优先像素下标 | `index = y * width + x` |
| 安全读写条件 | `x < width && y < height` |

## 实践练习

1. 在隔离练习目录中将第一组图像改为宽 `5`、高 `3`，为第三行添加五个像素，保持块大小 `4 × 2`。**验收标准**：网格为 `2 × 2`，程序输出 `PASS`；列出 32 个逻辑线程中的 15 个有效坐标，并指出右侧与底部的无效坐标。
2. 将第二组的宽高依次改为 `1 × 1`、`8 × 4`、`9 × 5`，同步生成相应数量的输入像素。**验收标准**：三次均为 `PASS`，网格分别为 `1 × 1`、`2 × 2`、`3 × 3`；解释整块与非整块的差异。
3. 在隔离练习目录中暂时把 `index` 错写成 `y * blockDim.x + x`，观察 CPU 对照报出的首个不匹配位置，再恢复原式。**验收标准**：能说明为什么块宽不能代替图像宽度，并重新运行得到 `PASS`。

## 参考资料

- [NVIDIA CUDA Programming Guide：Intro to CUDA C++](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html)
- [NVIDIA CUDA Programming Guide：Thread Hierarchy](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-hierarchy)
- [NVIDIA CUDA Programming Guide：C/C++ Language Extensions](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/cpp-language-extensions.html)

**系列导航**：上一篇 · [开发环境与首个核函数]({{ '/posts/gpu-development-first-kernel/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [设备内存与数据传输]({{ '/posts/gpu-device-memory-and-data-transfer/' | relative_url }})。
