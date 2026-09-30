---
layout: post
title: "同步、原子操作与归约"
date: 2026-09-28 00:44:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 同步, 原子操作, 归约, GPU编程系列]
excerpt: "以灰度图直方图和像素总和说明共享计数竞争、块内同步、原子更新与分层归约，并用 CPU 结果核验。"
series: gpu-programming
series_order: 5
---

前一章的均值滤波让每条线程写自己的输出位置，线程之间主要共享的是**输入**。本章改为统计灰度图：多个像素可能要增加同一个直方图计数器，所有像素还要合成一个总和。此时必须安排写入顺序和结果合并。我们用同一张单通道图像实现 256 桶直方图与像素值总和，对照 CPU 参考结果，并区分原子操作、块内屏障和分层归约各自解决的问题。阅读前应掌握[内存访问与共享内存]({{ '/posts/gpu-memory-access-and-shared-memory/' | relative_url }})中的线程块和共享内存；运行仍需可用的 CUDA 设备与工具链。

## 1. 统计任务与竞争条件

### 输入与预期结果

每个输入像素是 0 到 255 的无符号字节。直方图 `hist[v]` 记录值为 `v` 的像素个数，因此共有 256 个计数器；总和 `sum` 是所有像素值之和。它们满足两条可检查的关系：

```text
Σ hist[v] = 像素总数
Σ v × hist[v] = sum
```

例如，下面的 4×4 图像每行都是 `0, 0, 1, 255`：

| 灰度值 | 个数 | 对总和的贡献 |
| --- | ---: | ---: |
| 0 | 8 | 0 |
| 1 | 4 | 4 |
| 255 | 4 | 1020 |

因此 `hist[0] = 8`、`hist[1] = 4`、`hist[255] = 4`，其余桶为 0；像素总数为 16，总和为 `1024`。后面的完整程序首先验证这个可手算输入，再验证单像素、非整块和较大图像。

### 同一地址的并发写入

朴素写法 `hist[input[i]] += 1` 包含“读取旧值、加一、写回”三个动作。如果两个线程同时看到旧值 0，它们可能各自写回 1，最后丢失一次计数。这是对同一地址的**写入竞争**；加上 `if (i < n)` 只能防越界，不能防丢失更新。

`atomicAdd(&hist[input[i]], 1u)` 把一个计数器上的读—改—写作为原子更新。它保证同一桶的增加不会相互覆盖，但**不是全线程屏障**，也不负责让其他地址上的普通写入自动按期望顺序可见。直方图缓冲区仍须在核函数开始前清零；本例使用默认流中的 `cudaMemset`，随后才启动统计核函数。[CUDA C++ 语言扩展的原子操作章节](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/cpp-language-extensions.html#legacy-atomic-functions)说明了 `atomicAdd` 可操作全局或共享内存中的计数器，以及它的原子性范围。

## 2. 两级直方图与分层求和

### 全局计数与块内计数

最直接的 GPU 直方图让每个有效线程对全局内存中的一个桶执行一次 `atomicAdd`。当很多像素具有相同灰度值时，大量线程竞争同一个桶。另一种实现让每个块先维护自己的 256 桶共享内存直方图，块内像素用原子操作更新本块的桶，最后每个非零桶只向全局直方图合并一次。不同块之间仍通过全局 `atomicAdd` 安全合并。

```text
直接版：像素 ──每像素一次全局 atomicAdd──> 全局 hist[256]

分块版：像素 ──块内 atomicAdd──> 本块 local[256]
                                   │ 块内屏障
                                   └──非零桶的全局 atomicAdd──> 全局 hist[256]
```

一个 256 线程块最多处理 256 个像素。如果这些像素全是 7，直接版对 `hist[7]` 发起 256 次全局原子更新；分块版先在共享内存的 `local[7]` 中累计，再向 `hist[7]` 发起一次全局更新。若像素分散在很多桶，分块版的初始化、屏障和合并也有代价，不能预设一定更快。

分块版使用两次 `__syncthreads()`：第一次在各线程把共享内存桶清零后，保证任何线程计数前初始化已完成；第二次在各线程完成块内计数后，保证合并线程读到完整的桶值。最后一块中下标越界的线程也要参与这两次屏障，只跳过像素更新。屏障只覆盖**当前线程块**；它不能让一个块等待所有其他块结束。[CUDA 编程指南的线程块同步说明](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-block-synchronization)给出了这一范围。

### 树形归约

像素总和不必让每个线程争用同一个全局计数器。本例的求和核函数让每个线程把一个像素值放进共享内存；最后一块的无效线程放入 0。随后按跨度 `128, 64, …, 1` 两两相加，每轮之后让全块同步。每个块最终写出一个部分和，主机下载这些部分和后用 64 位整数相加，得到整张图像的总和。

每块最多有 256 个字节值，部分和最大为 `256 × 255 = 65280`，可放入 32 位无符号整数；主机累加采用 `std::uint64_t`，避免多块求和时沿用过窄的类型。对于本章固定输入，直方图计数使用 32 位无符号整数也足够。若通用程序可能处理超过计数类型上限的像素，还必须重新设计计数类型和容量检查。这个求和是“块内归约 → 主机合并”的两级流程，并未在一个普通核函数内部设置跨块屏障。

## 3. 完整统计程序

### 练习目录与编译

在博客仓库之外建立 `gpu-practice/histogram-reduction/`，将下面**整个代码块**保存为 UTF-8 编码的 `histogram_reduction.cu`。Windows 在 Visual Studio Developer PowerShell 中进入该目录后执行：

```powershell
nvcc -Xcompiler /utf-8 histogram_reduction.cu -o histogram_reduction.exe
.\histogram_reduction.exe
```

Linux 终端执行：

```bash
nvcc histogram_reduction.cu -o histogram_reduction
./histogram_reduction
```

完整运行包含 4×4 手算图、单像素图、全部为 7 的大输入和确定性生成的混合灰度图。`--check-only` 模式只运行小图、单像素和跨越线程块边界的 257 像素图，便于使用检查工具。所有案例先在 CPU 上计算参考直方图与总和，再逐桶比较两种 GPU 直方图，并验证块部分和；只有正确的较大案例才计时。

```cpp
#include <cuda_runtime.h>

#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <vector>
#include <chrono>

#define CUDA_CHECK(call)                                                    \
    do {                                                                    \
        const cudaError_t error = (call);                                   \
        if (error != cudaSuccess) {                                         \
            std::cerr << "CUDA error at " << __FILE__ << ':' << __LINE__    \
                      << ": " << cudaGetErrorString(error) << '\n';       \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                   \
    } while (false)

constexpr int kThreads = 256;
constexpr int kBins = 256;
using Clock = std::chrono::steady_clock;

// 基线：每个有效像素直接原子更新设备全局直方图。
__global__ void histogram_global(const unsigned char* input,
                                  unsigned int* histogram, int n) {
    const int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) {
        atomicAdd(&histogram[input[i]], 1u);
    }
}

// 每块先形成私有直方图，再把非零桶安全合并到全局直方图。
__global__ void histogram_block(const unsigned char* input,
                                 unsigned int* histogram, int n) {
    __shared__ unsigned int local[kBins];
    const int lane = threadIdx.x;
    const int i = blockIdx.x * blockDim.x + lane;

    local[lane] = 0;      // 256 条线程各清零一个桶。
    __syncthreads();     // 任何计数开始前，所有桶都已清零。
    if (i < n) {
        atomicAdd(&local[input[i]], 1u);
    }
    __syncthreads();     // 合并前等待本块的全部像素更新。
    if (local[lane] != 0) {
        atomicAdd(&histogram[lane], local[lane]);
    }
}

// 每块输出一个部分和；越界线程贡献 0，仍参与所有屏障。
__global__ void reduce_blocks(const unsigned char* input,
                               unsigned int* partial, int n) {
    __shared__ unsigned int values[kThreads];
    const int lane = threadIdx.x;
    const int i = blockIdx.x * blockDim.x + lane;
    values[lane] = i < n ? static_cast<unsigned int>(input[i]) : 0u;
    __syncthreads();
    for (int stride = kThreads / 2; stride > 0; stride /= 2) {
        if (lane < stride) {
            values[lane] += values[lane + stride];
        }
        __syncthreads(); // 下一轮必须看到本轮的写入。
    }
    if (lane == 0) {
        partial[blockIdx.x] = values[0];
    }
}

void launch_histogram(bool block_local, const unsigned char* input,
                      unsigned int* histogram, int n, int blocks) {
    if (block_local) {
        histogram_block<<<blocks, kThreads>>>(input, histogram, n);
    } else {
        histogram_global<<<blocks, kThreads>>>(input, histogram, n);
    }
}

// CUDA 事件测“清零 + 直方图核函数”的平均设备时间，不含传输。
float histogram_step_ms(bool block_local, const unsigned char* d_input,
                        unsigned int* d_hist, int n, int blocks) {
    constexpr int repeats = 20;
    const std::size_t hist_bytes = kBins * sizeof(unsigned int);
    for (int i = 0; i < 2; ++i) {
        CUDA_CHECK(cudaMemset(d_hist, 0, hist_bytes));
        launch_histogram(block_local, d_input, d_hist, n, blocks);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));
    for (int i = 0; i < repeats; ++i) {
        CUDA_CHECK(cudaMemset(d_hist, 0, hist_bytes));
        launch_histogram(block_local, d_input, d_hist, n, blocks);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    float elapsed = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&elapsed, start, stop));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    return elapsed / repeats;
}

// 主机计时覆盖上传、清零、统计、下载；设备缓冲区已事先申请。
double histogram_roundtrip_ms(bool block_local,
                              const std::vector<unsigned char>& input,
                              std::vector<unsigned int>& host_hist,
                              unsigned char* d_input, unsigned int* d_hist,
                              int n, int blocks) {
    constexpr int repeats = 10;
    const std::size_t hist_bytes = kBins * sizeof(unsigned int);
    const auto begin = Clock::now();
    for (int i = 0; i < repeats; ++i) {
        CUDA_CHECK(cudaMemcpy(d_input, input.data(), input.size(),
                              cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemset(d_hist, 0, hist_bytes));
        launch_histogram(block_local, d_input, d_hist, n, blocks);
        CUDA_CHECK(cudaGetLastError());
        // 默认流中下载排在统计之后；返回时这一轮结果可读。
        CUDA_CHECK(cudaMemcpy(host_hist.data(), d_hist, hist_bytes,
                              cudaMemcpyDeviceToHost));
    }
    const auto end = Clock::now();
    return std::chrono::duration<double, std::milli>(end - begin).count()
           / repeats;
}

bool check_histogram(const std::vector<unsigned int>& actual,
                     const std::vector<unsigned int>& expected,
                     std::uint64_t expected_sum, std::size_t pixels,
                     const char* name) {
    std::uint64_t count = 0, weighted_sum = 0;
    bool matches = true;
    for (int value = 0; value < kBins; ++value) {
        if (actual[value] != expected[value]) {
            std::cerr << name << " bin " << value << ": CPU="
                      << expected[value] << ", GPU=" << actual[value] << '\n';
            matches = false;
            break;
        }
        count += actual[value];
        weighted_sum += static_cast<std::uint64_t>(value) * actual[value];
    }
    if (matches && (count != pixels || weighted_sum != expected_sum)) {
        std::cerr << name << " histogram invariant failed.\n";
        matches = false;
    }
    return matches;
}

bool run_case(const std::vector<unsigned char>& input, const char* name,
              bool measure) {
    if (input.empty() || input.size() > 1000000) {
        std::cerr << "This lesson supports 1 to 1,000,000 pixels.\n";
        return false;
    }
    const int n = static_cast<int>(input.size());
    const int blocks = (n + kThreads - 1) / kThreads;
    const std::size_t hist_bytes = kBins * sizeof(unsigned int);
    const std::size_t partial_bytes = static_cast<std::size_t>(blocks)
                                      * sizeof(unsigned int);

    // CPU 参考值；用 64 位整数累加总和。
    std::vector<unsigned int> expected(kBins, 0);
    std::uint64_t expected_sum = 0;
    for (unsigned char value : input) {
        ++expected[value];
        expected_sum += value;
    }

    unsigned char* d_input = nullptr;
    unsigned int *d_global = nullptr, *d_block = nullptr, *d_partial = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_input), input.size()));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_global), hist_bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_block), hist_bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_partial), partial_bytes));
    CUDA_CHECK(cudaMemcpy(d_input, input.data(), input.size(),
                          cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemset(d_global, 0, hist_bytes));
    CUDA_CHECK(cudaMemset(d_block, 0, hist_bytes));
    launch_histogram(false, d_input, d_global, n, blocks);
    CUDA_CHECK(cudaGetLastError());
    launch_histogram(true, d_input, d_block, n, blocks);
    CUDA_CHECK(cudaGetLastError());
    reduce_blocks<<<blocks, kThreads>>>(d_input, d_partial, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    std::vector<unsigned int> global(kBins), block(kBins), partial(blocks);
    CUDA_CHECK(cudaMemcpy(global.data(), d_global, hist_bytes,
                          cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(block.data(), d_block, hist_bytes,
                          cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(partial.data(), d_partial, partial_bytes,
                          cudaMemcpyDeviceToHost));
    const bool global_ok = check_histogram(global, expected, expected_sum,
                                            input.size(), "global");
    const bool block_ok = check_histogram(block, expected, expected_sum,
                                           input.size(), "block");
    std::uint64_t reduced_sum = 0;
    for (unsigned int part : partial) {
        reduced_sum += part;
    }
    const bool sum_ok = reduced_sum == expected_sum;
    if (!sum_ok) {
        std::cerr << "sum: CPU=" << expected_sum
                  << ", GPU partials=" << reduced_sum << '\n';
    }
    std::cout << name << ": global=" << (global_ok ? "PASS" : "FAIL")
              << ", block=" << (block_ok ? "PASS" : "FAIL")
              << ", sum=" << (sum_ok ? "PASS" : "FAIL")
              << ", value=" << reduced_sum << '\n';

    if (measure && global_ok && block_ok && sum_ok) {
        const float global_step = histogram_step_ms(false, d_input, d_global,
                                                     n, blocks);
        const float block_step = histogram_step_ms(true, d_input, d_block,
                                                    n, blocks);
        const double global_trip = histogram_roundtrip_ms(
            false, input, global, d_input, d_global, n, blocks);
        const double block_trip = histogram_roundtrip_ms(
            true, input, block, d_input, d_block, n, blocks);
        std::cout << std::fixed << std::setprecision(3)
                  << "  step ms: global=" << global_step
                  << ", block=" << block_step << '\n'
                  << "  roundtrip ms: global=" << global_trip
                  << ", block=" << block_trip << '\n';
    }

    // 正常路径释放全部设备缓冲区。
    CUDA_CHECK(cudaFree(d_input));
    CUDA_CHECK(cudaFree(d_global));
    CUDA_CHECK(cudaFree(d_block));
    CUDA_CHECK(cudaFree(d_partial));
    return global_ok && block_ok && sum_ok;
}

int main(int argc, char** argv) {
    bool check_only = false;
    if (argc == 2 && std::strcmp(argv[1], "--check-only") == 0) {
        check_only = true;
    } else if (argc != 1) {
        std::cerr << "Usage: histogram_reduction [--check-only]\n";
        return EXIT_FAILURE;
    }
    int device_count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }

    const std::vector<unsigned char> small = {
        0, 0, 1, 255, 0, 0, 1, 255,
        0, 0, 1, 255, 0, 0, 1, 255
    };
    const bool small_ok = run_case(small, "4x4", false);
    const bool one_ok = run_case({255}, "1 pixel", false);
    if (check_only) {
        std::vector<unsigned char> edge(257, 7);
        const bool edge_ok = run_case(edge, "257 pixels", false);
        return small_ok && one_ok && edge_ok ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    std::vector<unsigned char> skewed(262145, 7);
    const bool skewed_ok = run_case(skewed, "262145 equal pixels", true);
    constexpr int width = 1003, height = 769;
    std::vector<unsigned char> mixed(width * height);
    for (std::size_t i = 0; i < mixed.size(); ++i) {
        mixed[i] = static_cast<unsigned char>((i * 37 + 11) % 256);
    }
    const bool mixed_ok = run_case(mixed, "1003x769 mixed pixels", true);
    return small_ok && one_ok && skewed_ok && mixed_ok
           ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

教学程序把输入限制在 100 万像素以内，使设备端的 `int` 下标、32 位桶计数和每块部分和都有明确范围。正常路径显式释放四块设备内存；CUDA 调用失败时检查宏直接退出进程，长期运行的程序需要覆盖失败路径的资源管理。`cudaMemset` 必须在相应直方图核函数之前执行；若未清零，多次运行会把旧计数继续累加。

### 预期输出与测量范围

不带参数运行时，首先应看到四组 `global=PASS, block=PASS, sum=PASS`。其中 4×4 案例的 `value` 应为 1024；`257 pixels` 只在 `--check-only` 模式出现，其 `value` 应为 `257 × 7 = 1799`，并会产生两个线程块。程序只有在逐桶和总和检查通过后才打印大输入的计时结果；具体毫秒数随设备和负载变化。

`step ms` 使用 CUDA 事件测连续 20 次“清零 + 直方图核函数”的平均设备时间，不含上传和下载；事件区间可能包含连续启动之间的调度空隙。`roundtrip ms` 用主机时钟测连续 10 次“上传 → 清零 → 统计 → 下载”的平均耗时，复用已经申请的设备缓冲区。两者都不包含求和归约、CPU 参考计算和结果比较。前者检查直方图计算阶段的变化，后者检查这一个直方图任务包含传输后的变化；不能把其中任一数字当作整个图像应用的端到端时间。

对于全部为 7 的输入，分块版大幅减少对**全局** `hist[7]` 的原子更新次数，但块内仍有同一桶的竞争。混合分布的输入可能呈现不同结果。一次在 NVIDIA GeForce RTX 4080 Laptop GPU 上的运行记录了以下平均值（单位：毫秒）：

| 输入 | 全局版 `step` | 分块版 `step` | 全局版往返 | 分块版往返 |
| --- | ---: | ---: | ---: | ---: |
| 262145 个相同像素 | 0.307 | 0.018 | 0.408 | 0.183 |
| 1003×769 混合像素 | 0.152 | 0.028 | 0.388 | 0.303 |

这次运行中分块版在两组输入的统计阶段和含传输流程中均较快，但收益幅度不同。这些数值受设备和负载影响，不能把原子更新次数直接换算成加速倍数，也不能作为稳定的跨设备结论；完整的性能诊断留到后续专题。

## 4. 正确性检查与常见问题

| 现象 | 原因与检查 |
| --- | --- |
| 某个桶少于 CPU 结果 | 检查是否误用普通 `+=`、是否遗漏最后一个不完整线程块，或是否未合并某块的本地桶。 |
| 第二次统计的桶数翻倍 | 检查每次核函数启动前是否重新清零对应的设备直方图。 |
| 分块版偶发错误 | 检查共享桶初始化和合并前的两次屏障，确认无效像素线程没有提前返回。 |
| 部分和正确但总和错误 | 检查末块的无效线程是否填 0、每轮归约是否同步、主机合并是否使用足够宽的类型。 |
| 直方图正确但统计和不符 | 核对 `Σ hist[v]` 和 `Σ v × hist[v]`；检查参考结果、输入长度和求和路径。 |

对难以定位的错误，可在练习目录中用 CUDA Toolkit 自带的 Compute Sanitizer 运行小尺寸模式：

```bash
compute-sanitizer --tool memcheck ./histogram_reduction --check-only
compute-sanitizer --tool racecheck ./histogram_reduction --check-only
compute-sanitizer --tool synccheck ./histogram_reduction --check-only
```

Windows 将可执行文件路径改为 `.\histogram_reduction.exe`。`memcheck` 用于查找越界或未对齐的设备内存访问；`racecheck` 重点报告共享内存读写危害，**不能代替**对所有全局内存竞争的分析；`synccheck` 检查同步原语的错误用法。先运行 `memcheck`，再结合 CPU 参考值和其他工具报告检查逻辑；工具无报错也不保证所有输入都正确。[NVIDIA Compute Sanitizer 手册](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html)列出了各工具的检测范围。

## 规则速查

| 需求 | 本例做法 |
| --- | --- |
| 同一桶并发增加 | 用 `atomicAdd`，避免普通读—改—写丢失更新。 |
| 块内共享桶初始化完成 | 清零后全块执行 `__syncthreads()`。 |
| 块内计数完成后合并 | 更新后再执行 `__syncthreads()`。 |
| 最后一个不完整块 | 无效线程不读输入，但仍参与所有屏障与求和中的零填充。 |
| 多块总和合并 | 每块写一个部分和，主机以 64 位整数累加。 |
| 结果验证 | 逐桶比较，检查总桶数、加权和与归约总和。 |

## 实践练习

1. 把 4×4 示例改为每行 `0, 1, 1, 255`，先手算再运行。**验收标准**：`hist[0]=4`、`hist[1]=8`、`hist[255]=4`，总和为 `1028`；两种直方图和归约都显示 `PASS`。
2. 使用 `--check-only` 执行程序，再分别运行 `memcheck`、`racecheck` 和 `synccheck`。**验收标准**：三组输入都显示 `PASS`；能说出三个检查工具各自覆盖的错误类型与限制。若环境没有 Compute Sanitizer，应如实记录未完成的工具验证。
3. 记录同一设备上“全部为 7”和“混合灰度”两组的 `step ms` 与 `roundtrip ms`。**验收标准**：根据本机数据说明块内聚合是否有收益，并区分统计阶段与含传输流程，不预设两种分布的结论相同。

## 参考资料

- [NVIDIA CUDA Programming Guide：Thread Block Synchronization](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-block-synchronization)
- [NVIDIA CUDA Programming Guide：Atomics](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#atomics)
- [NVIDIA CUDA C++ Language Extensions：Legacy Atomic Functions](https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/cpp-language-extensions.html#legacy-atomic-functions)
- [NVIDIA Compute Sanitizer](https://docs.nvidia.com/compute-sanitizer/ComputeSanitizer/index.html)

**系列导航**：上一篇 · [内存访问与共享内存]({{ '/posts/gpu-memory-access-and-shared-memory/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [数值精度与正确性]({{ '/posts/gpu-numerical-precision-and-correctness/' | relative_url }})。
