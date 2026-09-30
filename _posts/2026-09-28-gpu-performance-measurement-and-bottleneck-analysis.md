---
layout: post
title: "性能测量与瓶颈分析"
date: 2026-09-28 01:20:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 性能分析, 性能测量, Roofline, GPU编程系列]
excerpt: "以均值滤波和图像统计程序建立可复现的测量基线，区分核函数、传输与启动开销，并用带宽、占用率和 Roofline 提出可检验的瓶颈假设。"
series: gpu-programming
series_order: 7
---

[内存访问与共享内存]({{ '/posts/gpu-memory-access-and-shared-memory/' | relative_url }})比较了均值滤波的直接版与分块版；[同步、原子操作与归约]({{ '/posts/gpu-synchronization-atomics-and-reduction/' | relative_url }})比较了两种直方图，并计算每块像素部分和。它们已有正确性检查和初步计时，但“某个数字更小”尚不足以确定瓶颈。本章沿用这两份程序，建立测量边界、重复实验、提出假设、用分析工具核查，再判断优化是否改善完整任务。阅读前需要理解核函数、数据传输和归约；运行案例需要 CUDA 设备与编译工具链。

## 1. 测量范围与计时方法

### 计时边界

同一程序有不同范围的计时。先约定输入和输出是什么，再决定哪一项代表用户实际等待的任务。

| 指标 | 本系列对应代码 | 包含的工作 | 主要用途 |
| --- | --- | --- | --- |
| 核函数阶段 | `box_blur` 的 `kernel ms` | 已驻留设备的输入上，连续启动同一种滤波核函数；CUDA 事件记录区间 | 比较两种滤波核函数在同一输入上的表现 |
| 设备统计阶段 | `histogram_reduction` 的 `step ms` | 每轮清零直方图，再启动一种统计核函数；CUDA 事件记录区间 | 比较直方图方案，不能当作单独核函数时间 |
| 往返流程 | 两程序的 `roundtrip ms` | 复用已申请缓冲区，逐轮上传、启动、下载；直方图另含清零；主机时钟计时 | 判断包含传输和主机调用后，方案是否仍有收益 |
| 完整统计任务 | 本章补充的 `complete ... ms` | 上传、清零、直方图、归约、下载两种结果、主机合并 | 比较同时交付直方图与总和的任务 |

这些是**教学程序定义的任务边界**。它们都不含图像读取、设备内存申请、CPU 参考结果和最终比对；第五章原有的两项直方图计时不含部分和归约及主机合并，本章补充的完整统计计时则包含它们。因此，若真实应用每张图都要重新申请缓冲区或输出统计文件，仍须另设覆盖这些步骤的端到端计时。不能用“往返时间减核函数时间”精确得到传输时间：两次实验的启动、缓存、同步与主机侧开销不同。

CUDA 核函数启动通常不会让主机等待执行完成。用主机时钟只包住 `kernel<<<...>>>` 会量到提交调用的时间，不能当作设备执行时间。若用主机时钟量完整任务，应在停止计时前等待所需 GPU 工作完成；本系列的同步 `cudaMemcpy` 下载保证默认流中前面的核函数结果可读。CUDA 事件应在与被测工作相同的流中记录，并在读取经过时间前同步结束事件。事件区间可能包含连续启动之间的调度空隙，因而这里称为“核函数阶段”，不把它解释成每次核函数的纯指令执行时间。[CUDA C++ 最佳实践指南的计时章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#timing)说明了主机计时、异步执行和 CUDA 事件各自的边界。

### 可比性条件

先运行正确性检查，再测量。固定设备、输入尺寸与分布、编译选项、线程块配置和计时范围；预热使初次上下文建立与加载不混入稳态样本。同一程序运行多轮，记录各轮原值和中位数，同时观察波动，不能只保留最快一次。若两方案轮流运行，交换先后次序再测，以排查频率、温度和系统负载随时间变化的影响。记录 GPU 型号、驱动与 CUDA 版本、是否接电以及其他 GPU 工作负载；这些条件决定结果能否复现。[CUDA C++ 最佳实践指南的应用分析章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#application-profiling)强调使用具有代表性的工作负载。

## 2. 均值滤波的基线

### 复现实验

建立练习目录，把[第四章完整代码]({{ '/posts/gpu-memory-access-and-shared-memory/' | relative_url }})保存为 `box_blur.cu`。该程序依次检查 5×5、1×1 和 1003×769 输入，只对最后一组计时。Windows 在 Visual Studio Developer PowerShell 中执行以下命令；Linux 去掉 `-Xcompiler /utf-8`，并将程序路径改为 `./box_blur`。

```powershell
nvcc -Xcompiler /utf-8 -O2 box_blur.cu -o box_blur.exe
1..5 | ForEach-Object { .\box_blur.exe }
```

每轮先核对三行 `direct=PASS, tiled=PASS`，再抄录两组 `kernel ms` 和 `roundtrip ms`。源码在计时前进行了预热，并在相同设备缓冲区上测量；五次**进程运行**是外层重复，不要误认为程序内部 100 次启动已经证明了跨运行稳定性。编译选项要对两种方案相同。

下面是一次 NVIDIA GeForce RTX 4080 Laptop GPU、驱动 595.79、CUDA 13.1、`-O2` 的五轮记录的中位数，单位为毫秒；它只是本机示例，不是其他设备的预期值。

| 1003×769 图像 | 直接版 | 分块版 | 观察 |
| --- | ---: | ---: | --- |
| `kernel ms` | 0.017 | 0.022 | 这五轮的中位数未显示分块版收益 |
| `roundtrip ms` | 0.355 | 0.319 | 方向与核函数阶段不同，需交换运行顺序并检查传输与主机开销 |

单轮的直接版核函数为 0.014～0.019 ms，分块版为 0.016～0.027 ms。原程序总是先测直接版，后测分块版；往返时间的反向排序可能混有顺序或系统状态影响，不能据此声称分块版让整个任务稳定变快。第四章的源码层面，直接版每个有效输出最多读取九个邻域值；分块版每块先装入带边缘的 18×18 输入块，再进行共享内存读取和一次屏障。缓存可能已复用直接版的读取，而分块加载、边界处理和同步也有代价。**源码读取次数不是实际 DRAM 字节数**，需要进一步观察缓存与访存计数器。

### 有效带宽的解释

对 1003×769 的八位单通道图，`N = 771307`。无论哪种实现，至少要读取输入并写出输出；按每像素各 1 字节计算，逻辑数据量为 `2N = 1542614` 字节。若用直接版的 0.017 ms 作分母，可得约 `90.7 GB/s`。这是按**最少逻辑数据量**计算的工作吞吐率，既不代表实测 DRAM 带宽，也未计入额外邻域读取、缓存命中、事务放大或写回流量。若把源码中的九次读取简单相加，也同样不能当作 DRAM 流量。只有明确字节计数的定义，才有意义地比较两次“带宽”。[CUDA C++ 最佳实践指南的有效带宽章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#effective-bandwidth-calculation)给出了按读写字节数和时间计算的基本方法。

## 3. 图像统计与归约的阶段划分

第五章的直方图程序已经比较“全局原子更新”与“块内聚合”，并用 `reduce_blocks` 输出各块部分和，但当前 `step ms` **只测清零和直方图**，没有测归约。先在仓库外保存[第五章完整代码]({{ '/posts/gpu-synchronization-atomics-and-reduction/' | relative_url }})为 `histogram_reduction.cu`，编译运行：

```powershell
nvcc -Xcompiler /utf-8 -O2 histogram_reduction.cu -o histogram_reduction.exe
1..5 | ForEach-Object { .\histogram_reduction.exe }
```

Linux 使用 `nvcc -O2 histogram_reduction.cu -o histogram_reduction` 和 `./histogram_reduction`。确认每组 `global=PASS, block=PASS, sum=PASS` 后才解释计时；大输入分别是 262145 个相同像素和 1003×769 个混合像素。

为单独测量部分和核函数，可在第五章代码的 `run_case` 函数之前加入下面的辅助函数，并在 `run_case` 原有 `if (measure && global_ok && block_ok && sum_ok)` 分支中，打印其他计时之前，加入 `std::cout << "  reduction ms: " << reduction_kernel_ms(d_input, d_partial, n, blocks) << '\n';`。这是对**原代码的连续修改**，无需更改 `reduce_blocks`；每次启动都覆盖相同的部分和输出。

```cpp
float reduction_kernel_ms(const unsigned char* d_input,
                          unsigned int* d_partial, int n, int blocks) {
    constexpr int repeats = 100;
    for (int i = 0; i < 3; ++i) {
        reduce_blocks<<<blocks, kThreads>>>(d_input, d_partial, n);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    cudaEvent_t start, stop;
    CUDA_CHECK(cudaEventCreate(&start));
    CUDA_CHECK(cudaEventCreate(&stop));
    CUDA_CHECK(cudaEventRecord(start));
    for (int i = 0; i < repeats; ++i) {
        reduce_blocks<<<blocks, kThreads>>>(d_input, d_partial, n);
    }
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaEventRecord(stop));
    CUDA_CHECK(cudaEventSynchronize(stop));
    float elapsed_ms = 0.0f;
    CUDA_CHECK(cudaEventElapsedTime(&elapsed_ms, start, stop));
    CUDA_CHECK(cudaEventDestroy(start));
    CUDA_CHECK(cudaEventDestroy(stop));
    return elapsed_ms / repeats;
}
```

此值是预热后连续启动的**归约核函数阶段**时间；CPU 合并部分和、设备到主机下载及输入上传仍在范围外。不能把它直接加到先前的 `roundtrip ms` 上充当完整统计时间，因为两种测试的运行状态和边界不同。

原版程序在同一设备上的五轮中位数如下。相同像素时，块内聚合显著减少对**同一个全局桶**的竞争；混合像素时仍有收益，但幅度不同。表中数字只覆盖直方图，不覆盖新增的归约计时。

| 输入 | 全局版 `step ms` | 块内版 `step ms` | 全局版往返 | 块内版往返 |
| --- | ---: | ---: | ---: | ---: |
| 262145 个相同像素 | 0.232 | 0.014 | 0.353 | 0.137 |
| 1003×769 混合像素 | 0.144 | 0.029 | 0.325 | 0.226 |

对归约核函数还应记录部分和数组长度 `blocks = ceil(n/256)`、输入字节数和核函数时间。它每个有效像素至少读 1 字节，每块写 4 字节部分和；共享内存中的中间加法不等于设备 DRAM 读写。观察输入规模改变时的核函数时间，再判断启动开销与实际工作量哪一部分更值得分析。

### 完整统计任务的计时

如果应用同时需要直方图与像素总和，测量范围应覆盖两种输出。下面的代码仍以第五章完整程序为基础：在头文件区增加 `#include <algorithm>`；把两个辅助函数放在 `check_histogram` 之后、`run_case` 之前。每次计时从上传输入开始，经过清零、直方图核函数、归约核函数、两次下载和 CPU 合并部分和，到得到最终总和为止。缓冲区分配、CPU 参考计算和正确性检查不在计时内。

```cpp
double complete_once_ms(bool block_local,
                        const std::vector<unsigned char>& input,
                        std::vector<unsigned int>& host_hist,
                        std::vector<unsigned int>& host_partial,
                        unsigned char* d_input, unsigned int* d_hist,
                        unsigned int* d_partial, int n, int blocks,
                        std::uint64_t& result_sum) {
    const std::size_t hist_bytes = kBins * sizeof(unsigned int);
    const std::size_t partial_bytes = host_partial.size() * sizeof(unsigned int);
    const auto begin = Clock::now();
    CUDA_CHECK(cudaMemcpy(d_input, input.data(), input.size(),
                          cudaMemcpyHostToDevice));
    CUDA_CHECK(cudaMemset(d_hist, 0, hist_bytes));
    launch_histogram(block_local, d_input, d_hist, n, blocks);
    CUDA_CHECK(cudaGetLastError());
    reduce_blocks<<<blocks, kThreads>>>(d_input, d_partial, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaMemcpy(host_hist.data(), d_hist, hist_bytes,
                          cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaMemcpy(host_partial.data(), d_partial, partial_bytes,
                          cudaMemcpyDeviceToHost));
    result_sum = 0;
    for (unsigned int part : host_partial) result_sum += part;
    return std::chrono::duration<double, std::milli>(Clock::now() - begin)
        .count();
}

bool measure_complete(bool block_local,
                      const std::vector<unsigned char>& input,
                      const std::vector<unsigned int>& expected,
                      std::uint64_t expected_sum,
                      std::vector<unsigned int>& host_hist,
                      std::vector<unsigned int>& host_partial,
                      unsigned char* d_input, unsigned int* d_hist,
                      unsigned int* d_partial, int n, int blocks) {
    std::vector<double> samples;
    for (int round = -2; round < 5; ++round) {
        std::uint64_t result_sum = 0;
        const double ms = complete_once_ms(
            block_local, input, host_hist, host_partial,
            d_input, d_hist, d_partial, n, blocks, result_sum);
        const char* label = block_local ? "complete block" : "complete global";
        if (!check_histogram(host_hist, expected, expected_sum,
                             input.size(), label) || result_sum != expected_sum) {
            std::cerr << label << " sum=" << result_sum
                      << ", expected=" << expected_sum << '\n';
            return false;
        }
        if (round >= 0) samples.push_back(ms);
    }
    std::cout << (block_local ? "  complete block ms: "
                              : "  complete global ms: ");
    for (double ms : samples) std::cout << std::fixed
                                        << std::setprecision(3) << ms << ' ';
    std::sort(samples.begin(), samples.end());
    std::cout << "| median=" << samples[2] << '\n';
    return true;
}
```

在 `run_case` 的 `if (measure && global_ok && block_ok && sum_ok)` 分支之前声明 `bool complete_ok = true;`；在该分支原有计时和输出之后、分支结束之前加入以下调用，并把函数末尾的返回条件改为 `return global_ok && block_ok && sum_ok && complete_ok;`。两种方案只替换直方图核函数，归约、下载和主机合并路径相同。

```cpp
        complete_ok = measure_complete(
            false, input, expected, expected_sum, global, partial,
            d_input, d_global, d_partial, n, blocks);
        if (complete_ok) {
            complete_ok = measure_complete(
                true, input, expected, expected_sum, block, partial,
                d_input, d_block, d_partial, n, blocks);
        }
```

每次正式运行会分别打印两种完整任务的五个原值和中位数。这里的两个结果按“全局版后块内版”的固定顺序测量；小于波动范围的差别须交换顺序并跨进程复测。不能把这两个值与原版的 `step ms` 或 `roundtrip ms` 相减，来推算归约或 CPU 合并的准确耗时。若真实应用还要读取图像文件、反复分配缓冲区或输出统计文件，仍须据该应用另定更外层的计时范围。

在 NVIDIA GeForce RTX 4080 Laptop GPU、驱动 595.79、CUDA 13.1、`-O2` 下，把上述修改合入第五章程序并独立运行五次。每次先预热两轮，再对每种方案记录五个完整任务样本；所有运行的直方图逐桶比较与总和检查均通过。下表列出每次进程内的五轮中位数，以及这五个中位数的中位数，单位为毫秒：

| 输入与方案 | 运行 1 | 运行 2 | 运行 3 | 运行 4 | 运行 5 | 中位数 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 262145 个相同像素，全局版 | 0.338 | 0.297 | 0.299 | 0.350 | 0.334 | 0.334 |
| 262145 个相同像素，块内版 | 0.143 | 0.110 | 0.107 | 0.143 | 0.146 | 0.143 |
| 1003×769 混合像素，全局版 | 0.328 | 0.292 | 0.291 | 0.294 | 0.283 | 0.292 |
| 1003×769 混合像素，块内版 | 0.203 | 0.200 | 0.204 | 0.212 | 0.197 | 0.203 |

这次实验中块内版在两组完整统计任务上均较快；相同像素时差异更大，与全局同桶原子竞争的解释一致。这里没有分别计量两次传输、归约和主机合并的独立耗时，也没有采到核函数内部的性能计数器，因此不能仅凭此表断言每一段的瓶颈。表中的进程内原始五轮值由程序打印，复现实验应连同设备状态一起保存；固定测量顺序仍是限制。

## 4. 瓶颈证据与分析工具

### 从时间线到核函数

先用主机计时确定真实任务，再用系统时间线看上传、核函数、下载及主机 API 调用的先后关系。若安装了 Nsight Systems，可以对**仓库外的可执行程序**运行 `nsys profile --trace=cuda --sample=none --cpuctxsw=none -o box_blur_trace ./box_blur`（Windows 将路径换成 `.\box_blur.exe`）。查看 CUDA API 行与 GPU 行：传输是否占较长时间、启动之间是否有空隙、是否在无意中串行等待。时间线用于定位范围，不把分析器下的运行时间当作普通运行的性能基线。[Nsight Systems 用户指南的 CUDA Trace](https://docs.nvidia.com/nsight-systems/UserGuide/#cuda-trace)说明了这些轨道和命令行采集方法。

确定值得分析的核函数后，用 Nsight Compute 只采集目标实例，核对报告中的函数名、网格尺寸与输入尺寸，避免把 1×1 边界案例当作大图。先看 `Speed Of Light`、`Memory Workload Analysis`、`Launch Statistics` 和 `Occupancy`；需要时再查看 Roofline。工具可能需要额外的驱动支持或性能计数器权限，无法采集时记录失败原因，继续保留主机与事件基线。Nsight Compute 会按指标重放核函数，并可能改变缓存状态、时钟与并发方式；分析器的时间不应直接与普通运行的事件时间混算。[Nsight Compute Profiling Guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)解释了这些指标与采集开销。

| 初步现象 | 下一项证据 | 可检验的改动 |
| --- | --- | --- |
| 往返远大于核函数阶段 | 时间线中的上传、下载和 API 间隙；数据是否可长期留在设备 | 把多步图像处理放在一次上传和下载之间，再测完整流程 |
| 大量极短核函数，GPU 轨道有间隙 | 启动次数、主机提交时间和核函数时长 | 合并可合并的工作或增加单次批量，并检查结果是否仍正确 |
| 访存单元接近其实际带宽上限 | 缓存层级的流量与利用率、访问合并情况 | 调整数据布局或复用，再核查 DRAM 流量和任务时间 |
| 算术单元持续忙碌 | 运算类型、吞吐和实际算术强度 | 减少重复计算或选用适当算法、精度；先验证误差 |
| 带宽与算术吞吐都不高 | 原子竞争、依赖、同步、分支或工作量不足的指标 | 用相同输入做单变量实验，逐一排除假设 |

占用率是活跃 warp 相对硬件可容纳 warp 的比例。`Occupancy` 报告的理论上限受寄存器、共享内存、块大小等限制；实际占用率还受工作规模和不均衡影响。低占用率可提示延迟隐藏不足，**高占用率本身不是优化目标**，也不能单独证明访存或计算瓶颈。改变块大小或共享内存用量后，应一起比较资源占用、核函数时间和完整任务时间。[Nsight Compute 的 Occupancy 说明](https://docs.nvidia.com/nsight-compute/ProfilingGuide/#occupancy)给出了该指标的定义与限制。

### Roofline 的适用范围

Roofline 把计算吞吐与算术强度关联起来：`算术强度 = 浮点运算次数 / 对应内存层级传输字节数`，上界可概括为 `min(峰值浮点吞吐, 该层级带宽 × 算术强度)`。必须说明浮点精度和内存层级。第六章的 `float` 分块求和，在只计输入加法和读入的粗略模型中，约为一次加法对应四字节输入，算术强度约 `0.25 FLOP/B`；部分和写出、缓存和其他指令会改变实际位置。它可用来提出“内存流量可能限制求和”的假设，随后仍要看实测数据。

本章的八位均值滤波主要是整数加法与除法，直方图的关键操作是原子更新。不能把它们的整数操作硬算成浮点 FLOP，再以浮点 Roofline 判定瓶颈；对这两个案例，访存、原子竞争与启动成本的证据更直接。Roofline 也不表示落在斜线一侧的程序就一定只受单一资源限制。[Nsight Compute Roofline Charts](https://docs.nvidia.com/nsight-compute/ProfilingGuide/#roofline-charts)说明了图中运算量、流量、峰值边界与实测点的关系。

## 5. 结果记录与常见问题

| 现象 | 检查顺序 |
| --- | --- |
| 核函数变快，完整任务未变快 | 核对端到端范围；查看传输、下载、CPU 工作和启动次数。 |
| 多轮结果忽快忽慢 | 保留原始样本；检查设备负载、运行顺序、温度和电源状态，增加轮数。 |
| 很短的核函数接近计时分辨能力 | 用连续多次启动取平均，并报告范围；不要把小数后三位的差异解释过度。 |
| `step ms` 被当成直方图核函数时间 | 记住它还包含每轮 `cudaMemset`；单独分析核函数时改变计时区间。 |
| 报告显示较高占用率但仍很慢 | 结合原子、访存、指令和完整任务证据；不能仅凭占用率判断。 |
| Nsight 时间与事件时间不同 | 检查分析器的核函数重放、缓存、时钟和并发设置；以常规运行结果检验优化。 |

记录表至少包括：设备及软件版本、输入尺寸与分布、编译选项、预热次数、内外层重复次数、计时范围、每轮原值、中位数、正确性结果、改动前后唯一变化，以及下一项待验证的假设。若新实现结果不符合[数值精度与正确性]({{ '/posts/gpu-numerical-precision-and-correctness/' | relative_url }})中的比较规则，速度数字不能作为有效优化结果。

## 规则速查

| 问题 | 对应测量 |
| --- | --- |
| 单个算子在设备上是否更快 | 相同输入与启动配置下的事件计时，加多轮波动记录。 |
| 用户等待的任务是否更快 | 覆盖真实输入、传输、计算、等待和输出的主机计时。 |
| 时间消耗在哪一阶段 | 系统时间线与明确的任务边界。 |
| 核函数内部可能受什么限制 | 内存流量、算术吞吐、原子竞争、资源用量和占用率等联合证据。 |
| 改动是否有效 | 正确性通过、条件可比、完整任务与目标阶段均有记录。 |

## 实践练习

1. 用第四章程序各运行至少五轮，保存三组 `PASS` 和四项时间的原始记录。**验收标准**：给出核函数与往返时间的中位数，写明各自范围；交换直接版与分块版的测量顺序后，重新判断排序是否稳定。
2. 用第五章程序比较相同像素与混合像素两组输入，再加入本章的 `reduction_kernel_ms`。**验收标准**：两组均通过逐桶和总和检查；报告 `step ms`、往返及归约核函数时间，并指出归约不在原有两项直方图计时之内。
3. 为实际图像批处理定义包含所需输出的端到端范围，提出一次只改变一个因素的优化实验。**验收标准**：记录改动前后正确性、原始时间及中位数；依据时间线或计数器证据说明目标瓶颈。没有分析器时，明确标出哪些瓶颈判断仍是假设。

## 参考资料

- [NVIDIA CUDA C++ Best Practices Guide：Application Profiling 与 Performance Metrics](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [NVIDIA Nsight Systems User Guide：CUDA Trace](https://docs.nvidia.com/nsight-systems/UserGuide/#cuda-trace)
- [NVIDIA Nsight Compute Profiling Guide：Occupancy、Memory Workload Analysis 与 Roofline](https://docs.nvidia.com/nsight-compute/ProfilingGuide/)
- [NVIDIA CUDA Runtime API：Event Management](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__EVENT.html)

**系列导航**：上一篇 · [数值精度与正确性]({{ '/posts/gpu-numerical-precision-and-correctness/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [分块计算与矩阵乘法]({{ '/posts/gpu-tiled-matrix-multiplication/' | relative_url }})。
