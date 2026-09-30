---
layout: post
title: "内存访问与共享内存"
date: 2026-09-28 00:30:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 共享内存, 卷积, GPU编程系列]
excerpt: "以 3×3 图像均值滤波比较直接读取与共享内存分块，核对边缘、同步、数据复用和实测耗时。"
series: gpu-programming
series_order: 4
---

[上一章]({{ '/posts/gpu-device-memory-and-data-transfer/' | relative_url }})把灰度图像放到设备上，并区分了上传、计算和下载。本章假设输入已经是连续存储的单通道灰度图，研究核函数**怎样读取**这些数据。我们先写直接读取九邻域的 3×3 均值滤波，再用共享内存让同一线程块内的线程复用输入，最后分别检查结果和测量时间。阅读前需要理解二维线程坐标、`cudaMalloc`、`cudaMemcpy` 与核函数启动；本章代码仍需可用的 CUDA 设备与工具链。

## 1. 九邻域与全局内存访问

### 均值滤波规则

每个输出像素取输入中以它为中心的 3×3 九个位置，求和后除以 9。图像外的位置按 0 处理，这称为**零填充**；即使靠边缘的有效像素，分母仍然是 9。输入和输出都按行优先顺序存放，`(x, y)` 的线性下标是 `y * width + x`。本章使用整数除法，直接版、分块版和 CPU 参考实现的结果可以逐字节比较。

例如，一张 5×5 全零图像只有中央像素为 255。中心周围 3×3 范围内的九个输出都等于 `255 / 9 = 28`，其他输出为 0。另一张只有一个像素且值为 255 的 1×1 图像，输出同样为 28，因为其余八个邻居都在图像外。这两组输入用于检查边缘语义。

### 直接读取

直接核函数为每个有效输出像素循环读取九个输入位置。相邻输出的邻域大量重叠：例如同一行左右相邻的两个输出，各自所需的九个位置中有六个相同。对于没有触及边界的 16×16 输出区域，源码层面最多执行 `16 × 16 × 9 = 2304` 次全局输入读取。GPU 缓存可能让重复读取不必每次都访问显存，所以这个数字**不是**实际显存事务数。

同一行相邻线程处理相邻的 `x`，通常会访问相邻的输入地址，有利于全局内存访问合并。是否真正合并成多少次事务，取决于硬件、对齐和访问位置；不能只凭源码计数推断带宽。[CUDA 最佳实践指南的全局内存访问章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#coalesced-access-to-global-memory)解释了合并访问和数据复用的区别。

## 2. 共享内存分块

### 输出块与输入块

本例每个线程块有 16×16 个线程，负责最多 16×16 个输出像素。因为滤波半径为 1，这些输出还需要四周各一圈输入：**16×16 输出块对应 18×18 输入块**。外圈常称为 halo；不同线程块各自加载自己的外圈，即使它与邻块重叠。

<figure class="post-figure">
  <img src="{{ '/assets/images/gpu/shared-memory-halo.svg' | relative_url }}" alt="16×16 输出块位于 18×18 输入区域中心，四周有一像素宽的外圈；全块加载输入并同步后才计算输出。" width="560" height="390" loading="lazy" decoding="async">
  <figcaption>图 1：外圈补足 3×3 邻域所需的输入；越出整张图像的位置仍按零填充处理。</figcaption>
</figure>

| 区域 | 尺寸 | 作用 |
| --- | --- | --- |
| 输出块 | `16 × 16 = 256` 个位置 | 每条线程至多写一个有效输出。 |
| 输入块 | `18 × 18 = 324` 个字节 | 16×16 中心加四周一圈，放入块内共享内存。 |
| 输入块边缘 | 超出图像的位置写为 `0` | 与直接版的零填充规则一致。 |

加载时先把线程在块内的二维编号线性化，令 256 条线程共同填满 324 个共享内存位置：前 256 个位置各由一条线程加载，剩余 68 个由前 68 条线程再加载一次。每个共享内存位置只由一个线程写。加载完成后全块执行一次 `__syncthreads()`，确保任何线程读取邻居之前，其他线程对共享内存的写入已经完成。**边缘的无效输出线程也必须先参与加载和同步**，不能在屏障之前提前返回。[CUDA 编程指南的线程块同步说明](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-block-synchronization)明确了这一等待范围。

内区块的代码级全局输入加载从最多 2304 次降为 324 次；随后九邻域从共享内存读取。代价是加载外圈、一次块内同步和每块 324 字节的共享内存。线程用于累加的 `sum` 是线程私有变量，编译器通常尝试把这类变量放在寄存器中；实际寄存器占用仍由编译结果决定。共享内存占用、寄存器数量和同步开销都会影响可同时驻留的线程块，因此“减少全局读取”不保证“运行一定更快”。

## 3. 完整对照程序

### 练习目录与编译

在博客仓库之外建立 `gpu-practice/shared-memory/`，把下面**整个代码块**保存为 UTF-8 编码的 `box_blur.cu`。Windows 在 Visual Studio Developer PowerShell 中进入该目录后执行：

```powershell
nvcc -Xcompiler /utf-8 box_blur.cu -o box_blur.exe
.\box_blur.exe
```

Linux 执行：

```bash
nvcc box_blur.cu -o box_blur
./box_blur
```

程序使用三个独立输入：5×5 的中心亮点、1×1 的边界案例，以及 1003×769 的确定性灰度图。前两组可以手算，第三组用于观察较大输入。每组均先生成 CPU 参考值，再分别运行直接版和共享内存版，下载并检查**全部像素**；仅当较大图像的两种结果都正确时才进入计时。

```cpp
#include <cuda_runtime.h>

#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <vector>

#define CUDA_CHECK(call)                                                    \
    do {                                                                    \
        const cudaError_t error = (call);                                   \
        if (error != cudaSuccess) {                                         \
            std::cerr << "CUDA error at " << __FILE__ << ':' << __LINE__    \
                      << ": " << cudaGetErrorString(error) << '\n';       \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                   \
    } while (false)

constexpr int kBlock = 16;
constexpr int kTile = kBlock + 2; // 每边增加一个输入像素。
using Clock = std::chrono::steady_clock;

// 越界邻居取 0；有效输入按行优先顺序读取。
__device__ unsigned char sample(const unsigned char* input,
                                int x, int y, int width, int height) {
    if (x < 0 || x >= width || y < 0 || y >= height) {
        return 0;
    }
    return input[y * width + x];
}

// 基线：每个有效输出线程直接从全局内存读取九邻域。
__global__ void blur_direct(const unsigned char* input, unsigned char* output,
                            int width, int height) {
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height) {
        return;
    }
    int sum = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        for (int dx = -1; dx <= 1; ++dx) {
            sum += sample(input, x + dx, y + dy, width, height);
        }
    }
    output[y * width + x] = static_cast<unsigned char>(sum / 9);
}

// 分块：全块先协作加载 18×18 的输入，再从共享内存读取九邻域。
__global__ void blur_tiled(const unsigned char* input, unsigned char* output,
                           int width, int height) {
    __shared__ unsigned char tile[kTile * kTile];
    const int local = threadIdx.y * kBlock + threadIdx.x;
    const int x = blockIdx.x * kBlock + threadIdx.x;
    const int y = blockIdx.y * kBlock + threadIdx.y;

    // 256 条线程覆盖 324 个位置；部分线程会再加载一个位置。
    for (int i = local; i < kTile * kTile; i += kBlock * kBlock) {
        const int tile_x = i % kTile;
        const int tile_y = i / kTile;
        const int image_x = blockIdx.x * kBlock + tile_x - 1;
        const int image_y = blockIdx.y * kBlock + tile_y - 1;
        tile[i] = sample(input, image_x, image_y, width, height);
    }
    __syncthreads(); // 所有线程，包括无效输出线程，都要到达此处。

    if (x >= width || y >= height) {
        return; // 屏障之后才可跳过图像外的输出。
    }
    int sum = 0;
    for (int dy = 0; dy < 3; ++dy) {
        for (int dx = 0; dx < 3; ++dx) {
            const int i = (threadIdx.y + dy) * kTile + threadIdx.x + dx;
            sum += tile[i];
        }
    }
    output[y * width + x] = static_cast<unsigned char>(sum / 9);
}

// 两种实现共用启动配置，以便对照相同尺寸和边界。
void launch(bool tiled, const unsigned char* input, unsigned char* output,
            int width, int height, dim3 grid, dim3 block) {
    if (tiled) {
        blur_tiled<<<grid, block>>>(input, output, width, height);
    } else {
        blur_direct<<<grid, block>>>(input, output, width, height);
    }
}

// 先预热，再用 CUDA 事件测多次启动的平均 GPU 时间。
float kernel_ms(bool tiled, const unsigned char* input, unsigned char* output,
                int width, int height, dim3 grid, dim3 block) {
    constexpr int repeats = 100;
    for (int i = 0; i < 3; ++i) {
        launch(tiled, input, output, width, height, grid, block);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));
    for (int i = 0; i < repeats; ++i) {
        launch(tiled, input, output, width, height, grid, block);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    float total_ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&total_ms, start, stop));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    return total_ms / repeats;
}

// 复用已申请的缓冲区，计入上传、启动、等待和下载的主机时间。
double roundtrip_ms(bool tiled, const std::vector<unsigned char>& input,
                    std::vector<unsigned char>& host_output,
                    unsigned char* d_input, unsigned char* d_output,
                    int width, int height, dim3 grid, dim3 block) {
    constexpr int repeats = 20;
    const std::size_t bytes = input.size() * sizeof(unsigned char);
    const auto begin = Clock::now();
    for (int i = 0; i < repeats; ++i) {
        CUDA_CHECK(cudaMemcpy(d_input, input.data(), bytes,
                              cudaMemcpyHostToDevice));
        launch(tiled, d_input, d_output, width, height, grid, block);
        CUDA_CHECK(cudaGetLastError());
        // D2H 在默认流中排在核函数之后；返回时这一轮输出可供主机读取。
        CUDA_CHECK(cudaMemcpy(host_output.data(), d_output, bytes,
                              cudaMemcpyDeviceToHost));
    }
    const auto end = Clock::now();
    return std::chrono::duration<double, std::milli>(end - begin).count()
           / repeats;
}

bool compare(const std::vector<unsigned char>& actual,
             const std::vector<unsigned char>& expected,
             int width, const char* name) {
    for (std::size_t i = 0; i < expected.size(); ++i) {
        if (actual[i] != expected[i]) {
            std::cerr << name << " mismatch at (" << i % width << ", "
                      << i / width << "): CPU=" << static_cast<int>(expected[i])
                      << ", GPU=" << static_cast<int>(actual[i]) << '\n';
            return false;
        }
    }
    return true;
}

bool run_case(const std::vector<unsigned char>& input, int width, int height,
              bool measure) {
    if (width <= 0 || height <= 0) {
        std::cerr << "Image dimensions must be positive.\n";
        return false;
    }
    const std::size_t pixels = static_cast<std::size_t>(width) * height;
    if (input.size() != pixels) {
        std::cerr << "Input size does not match image dimensions.\n";
        return false;
    }
    // CPU 参考实现与两个 GPU 核函数采用同一零填充和整数除法规则。
    std::vector<unsigned char> expected(pixels), direct(pixels), tiled(pixels);
    for (int y = 0; y < height; ++y) {
        for (int x = 0; x < width; ++x) {
            int sum = 0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    const int nx = x + dx, ny = y + dy;
                    if (nx >= 0 && nx < width && ny >= 0 && ny < height) {
                        sum += input[ny * width + nx];
                    }
                }
            }
            expected[y * width + x] = static_cast<unsigned char>(sum / 9);
        }
    }

    unsigned char *d_input = nullptr, *d_direct = nullptr, *d_tiled = nullptr;
    const std::size_t bytes = pixels * sizeof(unsigned char);
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_input), bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_direct), bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_tiled), bytes));
    CUDA_CHECK(cudaMemcpy(d_input, input.data(), bytes, cudaMemcpyHostToDevice));
    const dim3 block(kBlock, kBlock);
    const dim3 grid((width + kBlock - 1) / kBlock,
                    (height + kBlock - 1) / kBlock);

    launch(false, d_input, d_direct, width, height, grid, block);
    CUDA_CHECK(cudaGetLastError());
    launch(true, d_input, d_tiled, width, height, grid, block);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());
    CUDA_CHECK(cudaMemcpy(direct.data(), d_direct, bytes,
                          cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(tiled.data(), d_tiled, bytes,
                          cudaMemcpyDeviceToHost));
    const bool direct_ok = compare(direct, expected, width, "direct");
    const bool tiled_ok = compare(tiled, expected, width, "tiled");
    std::cout << width << 'x' << height
              << ", direct=" << (direct_ok ? "PASS" : "FAIL")
              << ", tiled=" << (tiled_ok ? "PASS" : "FAIL") << '\n';

    // 只对较大且正确的案例计时；输入、尺寸和启动配置相同。
    if (measure && direct_ok && tiled_ok) {
        const float direct_kernel = kernel_ms(false, d_input, d_direct,
                                              width, height, grid, block);
        const float tiled_kernel = kernel_ms(true, d_input, d_tiled,
                                             width, height, grid, block);
        const double direct_total = roundtrip_ms(false, input, direct, d_input,
                                                  d_direct, width, height,
                                                  grid, block);
        const double tiled_total = roundtrip_ms(true, input, tiled, d_input,
                                                 d_tiled, width, height,
                                                 grid, block);
        std::cout << std::fixed << std::setprecision(3)
                  << "kernel ms: direct=" << direct_kernel
                  << ", tiled=" << tiled_kernel << '\n'
                  << "roundtrip ms: direct=" << direct_total
                  << ", tiled=" << tiled_total << '\n';
    }

    CUDA_CHECK(cudaFree(d_input));
    CUDA_CHECK(cudaFree(d_direct));
    CUDA_CHECK(cudaFree(d_tiled));
    return direct_ok && tiled_ok;
}

int main() {
    int device_count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }

    std::vector<unsigned char> impulse(5 * 5, 0);
    impulse[2 * 5 + 2] = 255; // 中央亮点的九个邻域输出应为 28。
    const bool impulse_ok = run_case(impulse, 5, 5, false);
    const bool one_ok = run_case({255}, 1, 1, false);

    constexpr int width = 1003, height = 769;
    const std::size_t pixels = static_cast<std::size_t>(width) * height;
    std::vector<unsigned char> large(pixels);
    for (std::size_t i = 0; i < pixels; ++i) {
        large[i] = static_cast<unsigned char>((i * 37 + 11) % 256);
    }
    const bool large_ok = run_case(large, width, height, true);
    return impulse_ok && one_ok && large_ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

本例为教学代码：尺寸由 `main` 固定在小范围内，通用实现还应检查尺寸乘法、索引范围和设备网格上限。CUDA 调用失败时检查宏会退出进程，正常路径显式释放三块设备内存；长期运行的应用需要覆盖失败路径的资源管理。

### 正确性与测量范围

正确运行时，前三行应显示：

```text
5x5, direct=PASS, tiled=PASS
1x1, direct=PASS, tiled=PASS
1003x769, direct=PASS, tiled=PASS
```

随后会输出两种核函数的平均事件时间，以及两种实现的平均往返时间；数值由实际硬件和运行状态决定。`kernel ms` 对预热后的同一设备缓冲区连续启动 100 次，用 CUDA 事件测整个序列再除以次数，**不含主机与设备之间的传输**；事件区间也可能包含连续启动之间的调度空隙。`roundtrip ms` 重复 20 次“上传 → 核函数 → 下载”，用主机时钟计时后取平均，**不含设备内存分配、CPU 输入生成和结果比对**。本例的主机输入使用普通可分页内存，因此往返时间也包含相应 API 的主机侧开销。

两项指标回答不同问题：共享内存版可能在核函数时间上有收益，往返时间却由传输主导；也可能因为缓存已经有效、外圈加载和同步增加开销，而比直接版更慢。只有在**本机测量结果**支持时，才能说某种实现对当前输入更快。后续性能专题再讨论多轮统计、分析工具和瓶颈定位。

例如，在一台 NVIDIA GeForce RTX 4080 Laptop GPU 上，同一程序连续两次运行记录了以下数值（单位均为毫秒）：

| 运行 | 直接版核函数 | 分块版核函数 | 直接版往返 | 分块版往返 |
| --- | ---: | ---: | ---: | ---: |
| 第一次 | 0.014 | 0.016 | 0.291 | 0.287 |
| 第二次 | 0.014 | 0.021 | 0.477 | 0.501 |

这两次的核函数指标都没有显示分块收益；往返时间的差异方向则发生变化。这些数字受运行状态影响，不能作为不同设备上的预期速度或稳定结论。读者应记录自己的测量值，再判断当前数据规模是否值得使用共享内存。

## 4. 边界、同步与资源

| 情况 | 直接版 | 共享内存版 |
| --- | --- | --- |
| 图像外邻居 | 每次采样检查边界，越界值取 0。 | 加载输入块时把越界位置写成 0。 |
| 右侧或底部多余线程 | 直接返回，不读写输出。 | 先参与输入块加载与屏障，之后才返回。 |
| 相邻输出共享输入 | 源码中重复发起全局读取，缓存可能复用。 | 块内先加载到共享内存，再重复读取共享内存。 |
| 块间共享输入 | 可受硬件缓存影响。 | 外圈由各块分别加载，`__syncthreads()` 不能跨块同步。 |

`__syncthreads()` 是块内屏障，不是整张图像的全局屏障。共享内存也属于一个线程块的资源，不会让相邻块自动共享已经加载的 tile。这个例子只有一次加载和一次屏障；若后续引入多阶段写入，应重新分析每次读写之间的同步条件。资源取舍还包括每块共享内存大小、每线程寄存器和线程块大小，不能只优化源码中的读取次数。

## 规则速查

| 规则 | 本例数值或写法 |
| --- | --- |
| 输出块与输入块 | `16×16` 输出，`18×18` 输入，滤波半径 1。 |
| 直接版内区块全局读取 | 源码最多 `256×9 = 2304` 次。 |
| 分块版内区块全局加载 | 源码最多 `18×18 = 324` 次，含块的外圈。 |
| 共享内存大小 | `324 × sizeof(unsigned char) = 324` 字节/块。 |
| 屏障位置 | 全体线程写完 tile 之后，任何提前返回或邻域读取之前。 |
| 正确性检查 | CPU 参考值与两种 GPU 输出逐像素比较。 |

## 实践练习

1. 将中心亮点从 `(2, 2)` 移到 `(0, 0)`，手算并运行。**验收标准**：只有左上角 2×2 的四个输出为 `28`，其他输出为 0；直接版和分块版均显示 `PASS`。
2. 在隔离练习目录中把共享内存版的边界 `return` 移到 `__syncthreads()` 之前，分析为什么这不安全，然后恢复原状。**验收标准**：能指出同一块内有线程可能无法到达屏障；不把任何一次偶然运行结果当作正确性证明。
3. 在相同设备上记录两种 `kernel ms` 与 `roundtrip ms`。**验收标准**：明确说出各项计时包含和排除的工作，并依据实际数值描述本机结果，不预设分块版一定获胜。

## 参考资料

- [NVIDIA CUDA C++ Best Practices Guide：Coalesced Access to Global Memory](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#coalesced-access-to-global-memory)
- [NVIDIA CUDA C++ Best Practices Guide：Shared Memory](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#shared-memory)
- [NVIDIA CUDA Programming Guide：Thread Block Synchronization](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-block-synchronization)
- [NVIDIA CUDA C++ Best Practices Guide：Timing](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#timing)

**系列导航**：上一篇 · [设备内存与数据传输]({{ '/posts/gpu-device-memory-and-data-transfer/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [同步、原子操作与归约]({{ '/posts/gpu-synchronization-atomics-and-reduction/' | relative_url }})。
