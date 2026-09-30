---
layout: post
title: "设备内存与数据传输"
date: 2026-09-28 00:20:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 设备内存, 数据传输, GPU编程系列]
excerpt: "以 RGB 图像灰度转换梳理主机与设备缓冲区的生命周期，并分别观察上传、计算和下载的耗时。"
series: gpu-programming
series_order: 3
---

前两章已经能给像素安排线程，但要让核函数得到输入、让 CPU 检查输出，还必须明确数据放在哪里、何时复制、何时释放。本章用一张连续存储的 RGB 图像完成灰度转换，并分别记录上传、核函数执行和下载的主机侧耗时。阅读前应理解[线程组织与数据映射]({{ '/posts/gpu-thread-organization-and-data-mapping/' | relative_url }})中的二维坐标和边界检查；运行示例仍需可用的 CUDA 设备与工具链。

## 1. 主机与设备的数据位置

### 缓冲区与字节数

示例输入是每像素三个通道的 RGB 图像，通道顺序为 `R, G, B`，每个通道占一个字节；输出是每像素一个字节的灰度图。像素按行连续存储，不含文件头、行填充或透明通道。宽 `width`、高 `height` 时，像素数为 `width × height`，输入字节数为 `像素数 × 3`，输出字节数为 `像素数 × 1`。这两个字节数不同，不能把灰度输出按 RGB 输入的长度分配或复制。

本例使用四块不同的缓冲区：

| 名称 | 所在位置 | 内容与生命周期 |
| --- | --- | --- |
| `rgb` | 主机内存 | CPU 准备的 RGB 输入；上传完成前必须保持有效。 |
| `d_rgb` | 设备内存 | `cudaMalloc` 申请；接收输入后供核函数读取。 |
| `d_gray` | 设备内存 | `cudaMalloc` 申请；由核函数写入灰度像素。 |
| `gray` | 主机内存 | 接收下载结果，供 CPU 逐项比较。 |

`std::vector` 管理本例的主机缓冲区，`cudaMalloc` 和 `cudaFree` 管理设备缓冲区。设备指针 `d_rgb`、`d_gray` 保存在主机程序中，用来告诉 CUDA API 和核函数设备内存的位置；本例不在 CPU 上直接解引用它们。CUDA 也提供托管内存等其他方式，但这里使用显式分配和复制，以便看清每个数据移动步骤。[CUDA 运行时内存管理文档](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__MEMORY.html)列出了这些接口的用途。

### 数据流与释放顺序

```text
主机 rgb ── H2D：复制 3 × 像素数个字节 ──> 设备 d_rgb
                                            │
                                     灰度转换核函数
                                            ↓
主机 gray <── D2H：复制 1 × 像素数个字节 ── 设备 d_gray
     │
     └── 与主机 CPU 参考结果逐项比较
```

完整顺序是：准备主机输入与参考结果，申请两块设备内存，上传 RGB，启动核函数并等待完成，下载灰度图，释放设备内存，最后比较结果。`cudaMemcpy(dst, src, bytes, kind)` 的参数顺序是**目标、来源、字节数、方向**。上传使用 `cudaMemcpyHostToDevice`，下载使用 `cudaMemcpyDeviceToHost`。`d_gray` 将被核函数写满有效像素，因此不需要先把主机端的 `gray` 复制到设备。

在本例的默认流中，上传、核函数和下载按依赖顺序执行。核函数启动对主机是异步的，所以启动语句返回时不能认为输出已经写好。程序在核函数之后调用 `cudaDeviceSynchronize()`，确认设备工作完成并检查执行错误，然后才下载结果。下载结束后调用 `cudaFree` 释放 `d_rgb` 与 `d_gray`，最后比较主机上的结果。不能在仍有设备工作需要访问缓冲区时把它当作可重用空间。

## 2. RGB 灰度转换案例

### 输入与参考结果

本章用简单的三通道算术平均定义灰度值：`gray = (R + G + B) / 3`，整数除法舍去余数。计算时先把三个字节提升为 `int`，最大和为 `765`，再转回一个字节。这是便于检查数据流的教学规则，不等同于考虑人眼感知权重或色彩空间转换的标准亮度公式。

第一组图像宽 `3`、高 `2`，六个像素依次为：

| 行 | RGB 像素 | CPU 灰度参考值 |
| --- | --- | --- |
| 0 | `(255,0,0)`、`(0,255,0)`、`(0,0,255)` | `85, 85, 85` |
| 1 | `(0,0,0)`、`(255,255,255)`、`(10,20,30)` | `0, 255, 20` |

例如，第 1 行第 2 列是线性像素下标 `1 × 3 + 2 = 5`，输入通道从 `3 × 5 = 15` 号字节开始，输出写到 `d_gray[5]`。第二组图像宽 `1003`、高 `769`，由固定公式生成，便于观察较大输入的计时结果，并检查非整块边界。两组都用 CPU 循环计算参考结果。

### 练习目录与编译

在博客仓库之外新建 `gpu-practice/device-memory/`，把下面**整个代码块**保存为 UTF-8 编码的 `rgb_to_gray.cu`。进入该目录后，在 Windows 的 Visual Studio Developer PowerShell 中执行：

```powershell
nvcc -Xcompiler /utf-8 rgb_to_gray.cu -o rgb_to_gray.exe
.\rgb_to_gray.exe
```

Linux 终端执行：

```bash
nvcc rgb_to_gray.cu -o rgb_to_gray
./rgb_to_gray
```

代码先计算 CPU 参考结果，再完成一次 GPU 工作流。计时使用主机的 `steady_clock`：H2D 阶段在 `cudaMemcpy` 后同步，核函数阶段在启动后同步，D2H 阶段以拷贝返回为终点。这样各阶段都有明确的完成边界。计时只是帮助观察本次运行的构成，不是稳定的性能基准。

```cpp
#include <cuda_runtime.h>

#include <chrono>
#include <cstddef>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <vector>

// 失败时标出 CUDA 调用所在行；此教学程序直接结束进程。
#define CUDA_CHECK(call)                                                    \
    do {                                                                    \
        const cudaError_t error = (call);                                   \
        if (error != cudaSuccess) {                                         \
            std::cerr << "CUDA error at " << __FILE__ << ':' << __LINE__    \
                      << ": " << cudaGetErrorString(error) << '\n';       \
            std::exit(EXIT_FAILURE);                                       \
        }                                                                   \
    } while (false)

using Clock = std::chrono::steady_clock;

double milliseconds(Clock::time_point begin, Clock::time_point end) {
    return std::chrono::duration<double, std::milli>(end - begin).count();
}

// 输入每像素三个连续字节，输出每像素一个字节。
__global__ void rgb_to_gray(const unsigned char* rgb, unsigned char* gray,
                            int width, int height) {
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height) {
        return; // 边缘多出的线程不访问任何缓冲区。
    }

    const int pixel = y * width + x;
    const int rgb_offset = 3 * pixel;
    const int sum = static_cast<int>(rgb[rgb_offset]) +
                    static_cast<int>(rgb[rgb_offset + 1]) +
                    static_cast<int>(rgb[rgb_offset + 2]);
    gray[pixel] = static_cast<unsigned char>(sum / 3);
}

bool run_case(const std::vector<unsigned char>& rgb, int width, int height) {
    // 本例只接受正宽高且输入恰好含三个通道的紧密排列图像。
    if (width <= 0 || height <= 0) {
        std::cerr << "Image dimensions must be positive.\n";
        return false;
    }
    const std::size_t pixels = static_cast<std::size_t>(width) * height;
    const std::size_t input_bytes = pixels * 3 * sizeof(unsigned char);
    const std::size_t output_bytes = pixels * sizeof(unsigned char);
    if (rgb.size() != pixels * 3) {
        std::cerr << "RGB input size does not match image dimensions.\n";
        return false;
    }

    // CPU 参考计算不计入下面的 GPU 工作流时间。
    std::vector<unsigned char> expected(pixels), gray(pixels);
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        const std::size_t offset = 3 * pixel;
        const int sum = static_cast<int>(rgb[offset]) +
                        static_cast<int>(rgb[offset + 1]) +
                        static_cast<int>(rgb[offset + 2]);
        expected[pixel] = static_cast<unsigned char>(sum / 3);
    }

    // 分别申请输入与输出设备内存；字节数不能混用。
    unsigned char *d_rgb = nullptr, *d_gray = nullptr;
    const auto total_begin = Clock::now();
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_rgb), input_bytes));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_gray), output_bytes));

    // H2D：将主机 RGB 输入上传，并等待最终设备传输完成。
    const auto h2d_begin = Clock::now();
    CUDA_CHECK(cudaMemcpy(d_rgb, rgb.data(), input_bytes,
                          cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaDeviceSynchronize());
    const auto h2d_end = Clock::now();

    // 使用上一章的二维映射；所有有效像素各写一次 d_gray。
    const dim3 block(16, 16);
    const dim3 grid((width + block.x - 1) / block.x,
                    (height + block.y - 1) / block.y);
    const auto kernel_begin = Clock::now();
    rgb_to_gray<<<grid, block>>>(d_rgb, d_gray, width, height);
    CUDA_CHECK(cudaGetLastError());       // 检查启动错误。
    CUDA_CHECK(cudaDeviceSynchronize());  // 等待核函数完成并检查执行错误。
    const auto kernel_end = Clock::now();

    // D2H：核函数已完成，将灰度输出下载到主机以便验证。
    const auto d2h_begin = Clock::now();
    CUDA_CHECK(cudaMemcpy(gray.data(), d_gray, output_bytes,
                          cudaMemcpyDeviceToHost));
    const auto d2h_end = Clock::now();

    // 正常路径按申请对象逐一释放，释放后不再使用设备指针。
    CUDA_CHECK(cudaFree(d_rgb));
    CUDA_CHECK(cudaFree(d_gray));
    const auto total_end = Clock::now();

    bool matches = true;
    for (std::size_t pixel = 0; pixel < pixels; ++pixel) {
        if (gray[pixel] != expected[pixel]) {
            std::cerr << "Mismatch at (x=" << pixel % width
                      << ", y=" << pixel / width
                      << "): CPU=" << static_cast<int>(expected[pixel])
                      << ", GPU=" << static_cast<int>(gray[pixel]) << '\n';
            matches = false;
            break;
        }
    }

    std::cout << width << 'x' << height << ", grid=" << grid.x << 'x' << grid.y
              << ", result=" << (matches ? "PASS" : "FAIL") << '\n';
    std::cout << std::fixed << std::setprecision(3)
              << "H2D=" << milliseconds(h2d_begin, h2d_end) << " ms, "
              << "kernel+wait=" << milliseconds(kernel_begin, kernel_end)
              << " ms, D2H=" << milliseconds(d2h_begin, d2h_end)
              << " ms, total=" << milliseconds(total_begin, total_end)
              << " ms\n";
    return matches;
}

int main() {
    int device_count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&device_count));
    if (device_count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }

    // 六个像素的顺序与正文表格一致，可手算出 85,85,85,0,255,20。
    const std::vector<unsigned char> small = {
        255, 0, 0,     0, 255, 0,     0, 0, 255,
        0, 0, 0,       255, 255, 255, 10, 20, 30
    };
    const bool small_ok = run_case(small, 3, 2);

    // 较大图像使用确定性数据；仅改变规模，不改变灰度规则。
    constexpr int width = 1003;
    constexpr int height = 769;
    const std::size_t pixels = static_cast<std::size_t>(width) * height;
    std::vector<unsigned char> large(pixels * 3);
    for (std::size_t i = 0; i < pixels; ++i) {
        large[3 * i] = static_cast<unsigned char>((i * 17 + 3) % 256);
        large[3 * i + 1] = static_cast<unsigned char>((i * 29 + 7) % 256);
        large[3 * i + 2] = static_cast<unsigned char>((i * 43 + 11) % 256);
    }
    const bool large_ok = run_case(large, width, height);
    return small_ok && large_ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

这个程序使用的 `std::vector` 属于普通主机内存。根据 [CUDA 运行时的同步行为说明](https://docs.nvidia.com/cuda/cuda-runtime-api/api-sync-behavior.html)，从可分页主机内存上传时，`cudaMemcpy` 返回可能只表示数据已复制到中转缓冲区，设备端 DMA 尚未结束；因此 H2D 计时段后又调用了 `cudaDeviceSynchronize()`。从设备下载到主机时，`cudaMemcpy` 在拷贝完成后返回。核函数计时段包含启动、错误检查和主机等待，**不是纯设备内核时间**。[CUDA 最佳实践指南的计时章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#timing)进一步介绍 CPU 计时与 CUDA 事件计时的区别。

示例的 `total` 从设备分配前开始，到设备释放后结束，包含分配、上传、核函数、下载和释放，不包含 CPU 输入生成、CPU 参考计算与结果比较。因此 `total` 不等于屏幕所列三个阶段的简单相加。程序只演示文中的两组尺寸；通用图像处理接口还须检查大小乘法、索引范围与设备网格上限。CUDA API 出错时，教学宏直接结束进程；需要在同一进程中恢复错误并继续处理下一张图像的应用，应使用能覆盖失败路径的资源管理方式。

### 预期输出与解释

若结果正确，首先应看到两组 `PASS`，对应网格分别为 `1 × 1` 与 `63 × 49`：

```text
3x2, grid=1x1, result=PASS
H2D=... ms, kernel+wait=... ms, D2H=... ms, total=... ms
1003x769, grid=63x49, result=PASS
H2D=... ms, kernel+wait=... ms, D2H=... ms, total=... ms
```

省略号表示由本机实际输出的数值，不是固定预期。小图像的各段时间主要反映调用与等待开销；即使大图像也只有一次运行，还可能受到首次初始化、系统负载和计时分辨率影响。这里先学会区分阶段与范围，不根据一次数字断言 GPU 比 CPU 快，也不把 `kernel+wait` 当作设备纯计算耗时。正式性能比较会在“性能测量与瓶颈分析”专题中加入预热、重复运行和相应设备侧指标。

## 3. 生命周期与常见问题

| 现象或写法 | 检查要点 |
| --- | --- |
| 上传只复制 `pixels` 个字节 | RGB 输入实际占 `3 × pixels` 字节；余下通道未上传。 |
| 下载复制 `input_bytes` | 灰度输出仅占 `pixels` 字节；按 RGB 长度下载会超出输出缓冲区。 |
| 把 `d_rgb` 当主机数组读取 | 本例的设备指针只传给 CUDA API 和核函数；CPU 检查应使用下载后的 `gray`。 |
| 启动后立即读取 `gray` | 核函数结果还在设备端；须等待计算完成并下载。 |
| `cudaMemcpy` 成功但结果不一致 | 继续检查字节数、通道次序、下标、灰度公式及 CPU 参考实现。 |
| 循环处理多张图像却持续重新分配 | 在尺寸和生命周期允许时考虑复用设备缓冲区；先保证大小、同步和正确性，再测收益。 |

如果下一步核函数仍使用灰度结果，可以让它继续读取 `d_gray`，不必在每一步之间往返主机。这样减少传输的做法要以实际数据依赖和测量结果为依据。本章只运行一次灰度核函数；多阶段流水线与异步拷贝会在后续专题讨论。

## 接口速查

| 接口或表达式 | 本例作用 |
| --- | --- |
| `cudaMalloc(reinterpret_cast<void**>(&ptr), bytes)` | 申请设备输入或输出缓冲区，参数大小按字节计算。 |
| `cudaMemcpy(dst, src, bytes, cudaMemcpyHostToDevice)` | 将主机 RGB 输入上传到设备。 |
| `cudaMemcpy(dst, src, bytes, cudaMemcpyDeviceToHost)` | 将设备灰度输出下载到主机。 |
| `cudaDeviceSynchronize()` | 等待先前设备工作完成；本例用于明确上传和核函数的计时终点。 |
| `cudaFree(ptr)` | 不再使用设备缓冲区后释放其空间。 |

## 实践练习

1. 为宽 `3`、高 `2` 的例子画出四块缓冲区和两次复制的方向，标明字节数。**验收标准**：`rgb` 与 `d_rgb` 各为 `18` 字节，`d_gray` 与 `gray` 各为 `6` 字节；上传和下载方向均正确。
2. 将小图像的最后一个像素改为 `(0, 30, 60)`，重新编译运行。**验收标准**：手算该像素的灰度值为 `30`，逐项比较通过，两组案例仍显示 `PASS`。
3. 在隔离练习目录中分别运行小图像和大图像，记录 `H2D`、`kernel+wait`、`D2H`、`total`。**验收标准**：能说明 `total` 的起止位置、未包含的 CPU 工作，以及为何三段数字不能代表完整程序或稳定性能。

## 参考资料

- [NVIDIA CUDA Runtime API：Memory Management](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__MEMORY.html)
- [NVIDIA CUDA Runtime API：API Synchronization Behavior](https://docs.nvidia.com/cuda/cuda-runtime-api/api-sync-behavior.html)
- [NVIDIA CUDA Programming Guide：Synchronizing CPU and GPU](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html#synchronizing-cpu-and-gpu)
- [NVIDIA CUDA C++ Best Practices Guide：Timing](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#timing)

**系列导航**：上一篇 · [线程组织与数据映射]({{ '/posts/gpu-thread-organization-and-data-mapping/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [内存访问与共享内存]({{ '/posts/gpu-memory-access-and-shared-memory/' | relative_url }})。
