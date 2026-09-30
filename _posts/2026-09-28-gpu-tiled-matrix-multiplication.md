---
layout: post
title: "分块计算与矩阵乘法"
date: 2026-09-28 01:30:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 矩阵乘法, 分块计算, 共享内存, GPU编程系列]
excerpt: "从逐元素矩阵乘法到共享内存分块，使用完整 CUDA 程序核对边界、浮点结果和性能，并分析数据复用与线程块资源的取舍。"
series: gpu-programming
series_order: 8
---

前一章建立了[性能测量与瓶颈分析]({{ '/posts/gpu-performance-measurement-and-bottleneck-analysis/' | relative_url }})的流程：先明确任务边界和正确性，再比较核函数与包含传输的耗时。本章用矩阵乘法观察另一类工作负载。图像均值滤波每个输出只处理九个邻居；矩阵乘法的每个输出需要一整行与一整列的点积。相邻输出会反复使用同一批输入，因此适合用 tile（分块）解释数据复用。读者需要了解二维线程索引、共享内存与块内同步；运行代码需要 CUDA 编译器和受支持的 NVIDIA GPU。

## 1. 矩阵布局与计算量

设 `A` 为 `M×K`、`B` 为 `K×N`，输出 `C` 为 `M×N`。本章采用 **行优先** `float` 数组，`A[row * K + k]`、`B[k * N + col]` 和 `C[row * N + col]` 分别定位三个元素。第 `(row, col)` 个输出为：

```text
C[row, col] = Σ(k=0..K-1) A[row, k] × B[k, col]
```

例如 `A = [[1, 2, 3], [4, 5, 6]]`、`B = [[7, 8], [9, 10], [11, 12]]`，则 `C = [[58, 64], [139, 154]]`。第一个输出 `58 = 1×7 + 2×9 + 3×11`。这组数可以手算；程序还会检查非整块尺寸，防止只在整齐的方阵上得到正确结果。

朴素实现让一条 GPU 线程计算一个 `C[row, col]`，循环遍历 `K`。全部输出约有 `M×N×K` 次乘加，按一次乘法和一次加法各算一个浮点运算，惯例上写作约 `2MNK` FLOP。它是比较吞吐率的工作量定义，不表示 GPU 必须执行同样数量的独立指令；编译器可能使用融合乘加。

## 2. 输出分块与数据复用

### 朴素读取

在同一个 `k` 上，同一行的多个输出需要同一个 `A[row, k]`，同一列的多个输出需要同一个 `B[k, col]`。朴素源码会从全局地址反复发起读取，但硬件缓存也可能满足部分请求，因此不能把源码读取次数直接等同于 DRAM 流量。

### 共享内存 tile

让一个 `T×T` 线程块负责一块 `T×T` 输出。沿 `K` 方向每次取 `T` 个值：全块协作加载一个 `A` tile 和一个 `B` tile，屏障之后每条线程用共享内存中的一行与一列更新自己的累加值，再通过第二次屏障确保旧 tile 不会在其他线程仍使用时被覆盖。如此循环 `ceil(K/T)` 轮。右侧、底部和末轮 `K` 不足 `T` 的位置填零；无效输出线程仍需参加两次屏障。

```text
一轮 K tile：加载 A 的 T×T 值 + B 的 T×T 值
                       ↓ 全块同步
            计算一块 T×T 输出的部分和
                       ↓ 全块同步
                    进入下一轮
```

对完整的内部 tile，一轮约做 `2T³` FLOP，只从源码层面加载 `2T²` 个 `float`，即 `8T²` 字节；暂不计最终输出写入时，理想化算术强度为 `T/4 FLOP/B`。`T=8` 得 `2 FLOP/B`，`T=16` 得 `4 FLOP/B`。朴素实现若把每次源码读取都算作独立流量，大 `K` 时约为 `0.25 FLOP/B`。这些值用于理解复用关系；缓存、边界、写回与内存事务会改变实际 DRAM 算术强度。[NVIDIA CUDA C++ 最佳实践指南的矩阵乘法章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#shared-memory-in-matrix-multiplication-c-ab)也以共享内存减少重复全局读取，但其示例尺寸和硬件结果不能直接套用于本例。

资源也随 tile 改变：本例两个 `float` 共享数组合计需要 `2T²×4` 字节，因此 8×8 为 512 字节、16×16 为 2048 字节；每块线程数分别为 64 与 256。较大的 tile 增加块内复用，也改变寄存器用量、块数、同步与占用率。具体哪种更快，必须在目标设备上测量。

## 3. 完整对照程序

### 练习目录与编译

在博客仓库之外建立 `gpu-practice/matmul/`，把下面整个代码块保存为 UTF-8 编码的 `tiled_matmul.cu`。Windows 在 Visual Studio Developer PowerShell 中进入该目录后运行：

```powershell
nvcc -std=c++17 -O2 -Xcompiler /utf-8 tiled_matmul.cu -o tiled_matmul.exe
.\tiled_matmul.exe
```

Linux 使用 `nvcc -std=c++17 -O2 tiled_matmul.cu -o tiled_matmul` 和 `./tiled_matmul`。程序比较三个**替代实现**：朴素版、8×8 分块版和 16×16 分块版；它们不会把结果串联起来。前两组小输入检查形状和边界，后两组测量性能。所有缓冲区在计时前申请，CPU 参考值和逐元素检查不计入计时。

```cpp
#include <cuda_runtime.h>

#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <vector>

#define CUDA_CHECK(call)                                                   \
    do {                                                                   \
        cudaError_t status = (call);                                       \
        if (status != cudaSuccess) {                                       \
            std::cerr << #call << ": " << cudaGetErrorString(status)       \
                      << '\n';                                             \
            std::exit(EXIT_FAILURE);                                      \
        }                                                                  \
    } while (false)

using Clock = std::chrono::steady_clock;
enum class Kind { naive, tile8, tile16 };

const char* label(Kind kind) {
    switch (kind) {
        case Kind::naive: return "naive";
        case Kind::tile8: return "tile8";
        case Kind::tile16: return "tile16";
    }
    return "unknown";
}

__global__ void matmul_naive(const float* a, const float* b, float* c,
                             int m, int n, int k_size) {
    const int col = blockIdx.x * blockDim.x + threadIdx.x;
    const int row = blockIdx.y * blockDim.y + threadIdx.y;
    if (row >= m || col >= n) return;

    float sum = 0.0f;
    for (int k = 0; k < k_size; ++k) {
        sum += a[row * k_size + k] * b[k * n + col];
    }
    c[row * n + col] = sum;
}

template <int T>
__global__ void matmul_tiled(const float* a, const float* b, float* c,
                             int m, int n, int k_size) {
    __shared__ float a_tile[T][T];
    __shared__ float b_tile[T][T];
    const int tx = threadIdx.x, ty = threadIdx.y;
    const int col = blockIdx.x * T + tx;
    const int row = blockIdx.y * T + ty;
    float sum = 0.0f;

    for (int base = 0; base < k_size; base += T) {
        const int a_k = base + tx;
        const int b_k = base + ty;
        a_tile[ty][tx] = (row < m && a_k < k_size)
                             ? a[row * k_size + a_k] : 0.0f;
        b_tile[ty][tx] = (b_k < k_size && col < n)
                             ? b[b_k * n + col] : 0.0f;
        __syncthreads();

        #pragma unroll
        for (int k = 0; k < T; ++k) {
            sum += a_tile[ty][k] * b_tile[k][tx];
        }
        __syncthreads();
    }
    if (row < m && col < n) c[row * n + col] = sum;
}

void launch(Kind kind, const float* a, const float* b, float* c,
            int m, int n, int k_size) {
    switch (kind) {
        case Kind::naive: {
            dim3 block(16, 16), grid((n + 15) / 16, (m + 15) / 16);
            matmul_naive<<<grid, block>>>(a, b, c, m, n, k_size);
            break;
        }
        case Kind::tile8: {
            dim3 block(8, 8), grid((n + 7) / 8, (m + 7) / 8);
            matmul_tiled<8><<<grid, block>>>(a, b, c, m, n, k_size);
            break;
        }
        case Kind::tile16: {
            dim3 block(16, 16), grid((n + 15) / 16, (m + 15) / 16);
            matmul_tiled<16><<<grid, block>>>(a, b, c, m, n, k_size);
            break;
        }
    }
}

float kernel_ms(Kind kind, const float* a, const float* b, float* c,
                int m, int n, int k_size) {
    constexpr int repeats = 50;
    for (int i = 0; i < 3; ++i) launch(kind, a, b, c, m, n, k_size);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));
    for (int i = 0; i < repeats; ++i) launch(kind, a, b, c, m, n, k_size);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    float elapsed = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&elapsed, start, stop));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    return elapsed / repeats;
}

double roundtrip_ms(Kind kind, const std::vector<float>& a,
                    const std::vector<float>& b, std::vector<float>& output,
                    float* d_a, float* d_b, float* d_c,
                    int m, int n, int k_size) {
    constexpr int repeats = 10;
    const std::size_t a_bytes = a.size() * sizeof(float);
    const std::size_t b_bytes = b.size() * sizeof(float);
    const std::size_t c_bytes = output.size() * sizeof(float);
    auto once = [&] {
        CUDA_CHECK(cudaMemcpy(d_a, a.data(), a_bytes, cudaMemcpyHostToDevice));
        CUDA_CHECK(cudaMemcpy(d_b, b.data(), b_bytes, cudaMemcpyHostToDevice));
        launch(kind, d_a, d_b, d_c, m, n, k_size);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaMemcpy(output.data(), d_c, c_bytes,
                              cudaMemcpyDeviceToHost));
    };
    once(); // 往返预热，不计入下面的平均值。
    const auto begin = Clock::now();
    for (int i = 0; i < repeats; ++i) once();
    const auto end = Clock::now();
    return std::chrono::duration<double, std::milli>(end - begin).count()
           / repeats;
}

bool check(const std::vector<float>& actual,
           const std::vector<double>& reference, int n, Kind kind) {
    double max_error = 0.0;
    for (std::size_t i = 0; i < actual.size(); ++i) {
        const double got = static_cast<double>(actual[i]);
        const double expected = reference[i];
        if (!std::isfinite(got)) {
            std::cerr << label(kind) << " non-finite at ("
                      << i / n << ", " << i % n << ")\n";
            return false;
        }
        const double error = std::fabs(got - expected);
        if (error > max_error) max_error = error;
        if (error > 1e-4 + 1e-5 * std::fabs(expected)) {
            std::cerr << label(kind) << " mismatch at ("
                      << i / n << ", " << i % n << "): GPU=" << got
                      << ", CPU=" << expected << "\n";
            return false;
        }
    }
    std::cout << "  " << label(kind) << "=PASS, max error="
              << max_error << '\n';
    return true;
}

struct Problem { int m, k, n; bool measure; };

bool run_case(Problem p) {
    const std::size_t a_count = static_cast<std::size_t>(p.m) * p.k;
    const std::size_t b_count = static_cast<std::size_t>(p.k) * p.n;
    const std::size_t c_count = static_cast<std::size_t>(p.m) * p.n;
    std::vector<float> a(a_count), b(b_count), output(c_count);
    std::vector<double> reference(c_count);
    for (std::size_t i = 0; i < a_count; ++i)
        a[i] = static_cast<float>(static_cast<int>((i * 17) % 13) - 6) / 8.0f;
    for (std::size_t i = 0; i < b_count; ++i)
        b[i] = static_cast<float>(static_cast<int>((i * 29) % 11) - 5) / 8.0f;

    for (int row = 0; row < p.m; ++row) {
        for (int col = 0; col < p.n; ++col) {
            double sum = 0.0;
            for (int k = 0; k < p.k; ++k)
                sum += static_cast<double>(a[row * p.k + k]) *
                       static_cast<double>(b[k * p.n + col]);
            reference[row * p.n + col] = sum;
        }
    }

    float *d_a = nullptr, *d_b = nullptr, *d_c = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_a), a_count * sizeof(float)));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_b), b_count * sizeof(float)));
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_c), c_count * sizeof(float)));
    CUDA_CHECK(cudaMemcpy(d_a, a.data(), a_count * sizeof(float),
                          cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemcpy(d_b, b.data(), b_count * sizeof(float),
                          cudaMemcpyHostToDevice));

    std::cout << p.m << 'x' << p.k << " * " << p.k << 'x' << p.n << '\n';
    const Kind kinds[] = {Kind::naive, Kind::tile8, Kind::tile16};
    bool ok = true;
    for (Kind kind : kinds) {
        launch(kind, d_a, d_b, d_c, p.m, p.n, p.k);
        CUDA_CHECK(cudaGetLastError());
        CUDA_CHECK(cudaMemcpy(output.data(), d_c, c_count * sizeof(float),
                              cudaMemcpyDeviceToHost));
        ok = check(output, reference, p.n, kind) && ok;
    }
    if (p.measure && ok) {
        for (Kind kind : kinds) {
            const float device = kernel_ms(kind, d_a, d_b, d_c,
                                           p.m, p.n, p.k);
            const double trip = roundtrip_ms(kind, a, b, output,
                                             d_a, d_b, d_c, p.m, p.n, p.k);
            ok = check(output, reference, p.n, kind) && ok;
            const double gflops = 2.0 * p.m * p.n * p.k /
                                  (device * 1e6);
            std::cout << std::fixed << std::setprecision(3)
                      << "  " << label(kind) << ": kernel=" << device
                      << " ms, roundtrip=" << trip
                      << " ms, estimated=" << gflops << " GFLOP/s\n";
        }
    }
    CUDA_CHECK(cudaFree(d_a));
    CUDA_CHECK(cudaFree(d_b));
    CUDA_CHECK(cudaFree(d_c));
    return ok;
}

int main() {
    int count = 0;
    CUDA_CHECK(cudaGetDeviceCount(&count));
    if (count == 0) {
        std::cerr << "No CUDA device is available.\n";
        return EXIT_FAILURE;
    }
    cudaDeviceProp device;
    CUDA_CHECK(cudaGetDeviceProperties(&device, 0));
    std::cout << "GPU: " << device.name << '\n';
    const Problem cases[] = {
        {3, 5, 4, false}, {17, 19, 23, false},
        {257, 129, 193, true}, {512, 512, 512, true}
    };
    bool ok = true;
    for (Problem p : cases) ok = run_case(p) && ok;
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

固定测试尺寸使 `int` 索引、网格维度和分配乘法都处于小范围；将此程序改为任意输入尺寸时，需要检查乘法溢出、设备网格与线程块限制以及可用内存。教学代码在正常路径释放三块设备缓冲区，CUDA 调用失败时由检查宏退出；长期运行的程序应为失败路径安排资源回收。输入包含可由二进制精确表示的八分之一倍数，CPU 用 `double` 形成较高精度参考。这里使用 `1e-4 + 1e-5×|参考值|` 的容差并报告最大误差；改用更长的 `K`、其他输入分布或混合精度时，需要按[数值精度与正确性]({{ '/posts/gpu-numerical-precision-and-correctness/' | relative_url }})重新设定误差预算。

### 结果与测量边界

每个尺寸都应显示三行 `PASS`，其中 `3×5 * 5×4` 和 `17×19 * 19×23` 检查部分 tile 的零填充。`kernel` 是同一批已在设备上的矩阵连续启动 50 次的 CUDA 事件平均时间；`roundtrip` 是预热后 10 次“上传 A、上传 B → 核函数 → 下载 C”的主机平均时间，复用已分配缓冲区。两者均不含 CPU 参考计算、初次分配和正确性比较，不能相减得到精确传输时间。`estimated GFLOP/s` 只用约 `2MNK` 除以核函数阶段时间，是此算子的估计有效吞吐率，不代表设备的理论峰值。

在 NVIDIA GeForce RTX 4080 Laptop GPU、驱动 595.79、CUDA 13.1 和 `-O2` 下，同一程序运行五次，所得中位数如下（毫秒）。每轮三种实现均通过逐元素检查。这只是一台设备、一次测试时段的记录；具体排序应以实际运行数据为准。

| 尺寸 `M×K · K×N` | 实现 | 核函数 ms | 往返 ms |
| --- | --- | ---: | ---: |
| 257×129 · 129×193 | 朴素 | 0.017 | 0.137 |
| 257×129 · 129×193 | tile8 | 0.018 | 0.143 |
| 257×129 · 129×193 | tile16 | 0.016 | 0.139 |
| 512×512 · 512×512 | 朴素 | 0.230 | 0.690 |
| 512×512 · 512×512 | tile8 | 0.236 | 0.697 |
| 512×512 · 512×512 | tile16 | 0.179 | 0.637 |

这次 512 方阵实验中，tile16 的核函数中位数低于朴素版，往返时间也有所下降；tile8 的中位数则未显示收益。较小矩阵的几项差距接近毫秒小数点后三位，不宜过度解释。程序固定按朴素、tile8、tile16 的顺序测量；若要确认差距，仍应交换顺序、保留各轮原始值，并在同一设备上再次复测。tile 的加载和两次屏障可能抵消复用收益，寄存器、线程块数量和缓存表现也会影响结果；这些具体原因需要分析器证据。

## 4. 资源分析与专用矩阵计算

若某个分块版本变慢，先查看它的核函数和往返时间，再检查 Nsight Compute 的 `Launch Statistics`、`Occupancy`、`Memory Workload Analysis` 和 `Speed Of Light`。将报告中的线程块、共享内存、寄存器、实际内存流量与本章源码的 `2T²×4` 字节对照。这个公式只算两个共享数组，不能预测寄存器数量或实际占用率；缓存命中也可能让朴素版避免很多 DRAM 访问。分析器的重放和缓存设置会改变运行条件，最终收益仍以正常运行的正确性和计时为准。[Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)解释了各项报告与采集限制。

矩阵乘法在适用的 NVIDIA 设备上还能使用专用矩阵计算硬件。实际应用通常先评估 cuBLAS 或 cuBLASLt：确定输入布局、维度、类型、计算精度与输出，再调用矩阵乘法接口，核对结果并测量完整流程。Tensor Core 路径能否被选择、是否带来收益，取决于设备能力、数据类型、尺寸、对齐和库算法；TF32、FP16、BF16 等模式也会改变输入精度或累加行为，不能与本章的普通 FP32 核函数只按速度比较。[cuBLAS 文档](https://docs.nvidia.com/cuda/cublas/)列出了矩阵乘法接口、计算类型与 Tensor Core 使用条件。本章不实现这些库接口；需要时应单独建立对应的正确性与性能基线。

## 5. 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 仅右侧、底部或最后一轮结果错误 | 核对 `row < M`、`col < N`、`base + tx/ty < K` 和零填充。 |
| 分块版偶发错误或停滞 | 确认所有线程都到达两次 `__syncthreads()`；不要在屏障前按输出越界提前返回。 |
| 结果整体像转置 | 核对行优先下标 `A[row*K+k]`、`B[k*N+col]`、`C[row*N+col]`；与列优先库接口交互时明确布局。 |
| `PASS` 但时间波动很大 | 保留原始样本，检查预热、运行顺序、其他 GPU 工作和时钟状态。 |
| tile16 比 tile8 慢 | 联合检查线程块规模、寄存器、共享内存、占用率和实际时间，不仅比较理想化 FLOP/B。 |
| 与 CPU 的小数末位不同 | 记录实际误差与容差，考虑融合乘加及运算顺序；不能只用逐位相同判断正确性。 |

## 规则速查

| 内容 | 本例约定 |
| --- | --- |
| 形状 | `A(M×K) × B(K×N) = C(M×N)` |
| 存储 | 三个矩阵均为行优先 `float` |
| 线程映射 | 一条线程计算一个输出，块覆盖一个输出 tile |
| 分块轮数 | `ceil(K/T)`，末轮无效输入填零 |
| 块内同步 | 加载后同步，使用完本轮 tile 再同步 |
| 共享内存 | 两个 `T×T` 的 `float` 数组，共 `8T²` 字节/块 |
| 理想化复用 | 完整内部 tile 的输入强度约 `T/4 FLOP/B`，不等于实测 DRAM 强度 |

## 实践练习

1. 将小案例改为文首的 `2×3 · 3×2` 整数矩阵：把 `cases` 中的第一项改为 `{2, 3, 2, false}`，在 `run_case` 的两个输入生成循环之后分别令 `a={1,2,3,4,5,6}`、`b={7,8,9,10,11,12}`，使 CPU 和 GPU 使用同一输入。**验收标准**：手算与程序结果均为 `[[58, 64], [139, 154]]`；能够解释末轮和边界位置的零填充。
2. 在相同设备上对两组大输入至少运行五轮。**验收标准**：三种实现都通过逐元素检查，报告每轮原值、核函数与往返时间的中位数，并按实测结果说明 tile8 与 tile16 的资源取舍。
3. 增加一个 `M=255, K=257, N=129` 的独立案例。**验收标准**：三种实现均通过检查；指出最后一个 K tile 中哪些加载被置零，以及哪些线程虽然不写 C 仍必须参加屏障。

## 参考资料

- [NVIDIA CUDA C++ Best Practices Guide：Shared Memory in Matrix Multiplication](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#shared-memory-in-matrix-multiplication-c-ab)
- [NVIDIA CUDA Programming Guide：Thread Block Synchronization](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/writing-cuda-kernels.html#thread-block-synchronization)
- [NVIDIA Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)
- [NVIDIA cuBLAS Documentation](https://docs.nvidia.com/cuda/cublas/)

**系列导航**：上一篇 · [性能测量与瓶颈分析]({{ '/posts/gpu-performance-measurement-and-bottleneck-analysis/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [异步执行与批处理流水线]({{ '/posts/gpu-asynchronous-execution-and-batch-pipeline/' | relative_url }})。
