---
layout: post
title: "异步执行与批处理流水线"
date: 2026-09-28 01:40:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 异步执行, CUDA Stream, CUDA Event, 批处理, GPU编程系列]
excerpt: "用图像均值滤波的完整批处理程序比较单流串行与双缓冲流水线，说明流、事件、页锁定内存和端到端吞吐量的关系。"
series: gpu-programming
series_order: 9
---

前一章用[分块计算与矩阵乘法]({{ '/posts/gpu-tiled-matrix-multiplication/' | relative_url }})讨论了单个算子的内部数据复用。实际图像任务往往连续处理多帧，每帧都要经历主机到设备传输、核函数计算、设备到主机传输。本章用逐帧的 3×3 均值滤波比较两种**替代调度方案**：单流串行队列与双缓冲流水线。目标是保证每帧结果正确，再判断整批吞吐量是否改善。读者需要了解设备内存、核函数启动和基本计时；运行示例需要 CUDA 编译器及受支持的 NVIDIA GPU。

## 1. 批处理任务与执行顺序

设一批共有 `F` 张互不依赖的单通道图像，每张宽 `W`、高 `H`，输入和输出都是行优先的 `unsigned char` 数组。均值滤波把当前位置及其八邻域的整数和除以 9，边界坐标钳位到最近的合法像素；CPU 参考程序与 GPU 核函数使用同一规则。第四章的均值滤波采用**图像外取 0**，本章改用**最近像素钳位**；两章是不同的边界契约，不能直接逐像素比较结果。这样选择是为了让第十章的库接口与自定义核函数沿用同一个规则。本章的比较对象仅是同一规则下的两种调度方案。每帧经历三步：上传 `H`、滤波 `K`、下载 `D`。

```text
单流串行：H0 → K0 → D0 → H1 → K1 → D1 → …
双缓冲：  第 0 槽处理帧 0、2、4、…
          第 1 槽处理帧 1、3、5、…
          每帧仍须满足 H_i → K_i → D_i
```

CUDA 核函数启动和 `cudaMemcpyAsync` 通常先把工作提交给设备，然后主机继续执行；函数返回不等于输出已可读取。**stream（流）**是设备工作队列：同一流内的操作按提交顺序执行，不同流中的独立操作才有机会交错或重叠。**event（事件）**记录流执行到某个位置的完成状态，另一条流可以等待它建立依赖。跨流没有自动保证“上传完再计算”，也不能仅凭不同的流就断言发生了重叠。[CUDA Programming Guide 的异步执行章节](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/asynchronous-execution.html)说明了提交、同步与并发的区别。

主机缓冲区必须在异步传输结束前保持有效：上传期间不能改写对应输入，下载期间不能读取或复用对应输出。本例一次性准备整批独立的输入、输出缓冲区，最终等待所有工作完成后再检查结果。`cudaMallocHost` 申请页锁定（pinned）主机内存，使主机与设备间的 `cudaMemcpyAsync` 具备异步传输和重叠的必要条件；它仍不保证设备一定能让拷贝与计算并行。页锁定内存是有限资源，不宜为无限长的视频流预留全部帧；生产程序应让主机缓冲区也按完成事件循环复用。[最佳实践指南的传输章节](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#asynchronous-and-overlapping-transfers-with-computation)还指出设备的拷贝引擎能力会影响实际重叠。

## 2. 双缓冲依赖关系

每个槽拥有设备输入、设备输出、上传流 `upload`、计算流 `work`，以及两个不用于计时的事件 `ready`、`done`。对第 `i` 帧选择 `slot = i % 2`，按以下顺序提交命令：

| 提交步骤 | 所在线程或流 | 作用 |
| --- | --- | --- |
| 第三帧起，`upload` 等待旧 `done` | 设备上的跨流依赖 | 旧帧下载结束后，才覆盖该槽的设备输入。 |
| 上传输入并记录 `ready` | `upload` 流 | 输入已到达设备，允许核函数读取。 |
| `work` 等待 `ready`，执行滤波 | `work` 流 | 确保计算不早于对应上传。 |
| 下载输出并记录 `done` | `work` 流 | 下载不早于计算；下一次使用同槽时等待它。 |

<figure class="post-figure">
  <img src="{{ '/assets/images/gpu/double-buffer-dependencies.svg' | relative_url }}" alt="槽零按 H0、K0、D0、H2 的依赖顺序运行，槽一按 H1、K1、D1、H3 的依赖顺序运行；箭头不表示两个槽一定重叠。" width="560" height="290" loading="lazy" decoding="async">
  <figcaption>图 1：<code>ready</code> 保证上传先于计算，<code>done</code> 保证同槽的下一帧等待下载完成；箭头只表示依赖。</figcaption>
</figure>

箭头表示必须满足的依赖，不表示两个槽一定同时运行。事件可以在后续帧中重复记录：`cudaStreamWaitEvent` 在调用时引用该事件**当时最近一次记录**的工作，后来重新记录事件不会改变已提交的等待。[CUDA Runtime API 的事件说明](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__EVENT.html)明确规定了这一点。本例两个槽各自复用事件；最终同步两个 `work` 流，也覆盖了它们等待的上传工作。若直接在每次提交后调用 `cudaDeviceSynchronize()`，主机就会逐帧等待，流水线无法形成。

## 3. 完整批处理程序

### 练习目录与编译

在博客仓库之外建立 `gpu-practice/batch-pipeline/`，把下面整个代码块保存为 UTF-8 编码的 `batch_pipeline.cu`。Windows 在 Visual Studio Developer PowerShell 中进入该目录后执行：

```powershell
nvcc -std=c++17 -O2 -Xcompiler /utf-8 batch_pipeline.cu -o batch_pipeline.exe
.\batch_pipeline.exe
```

Linux 使用 `nvcc -std=c++17 -O2 batch_pipeline.cu -o batch_pipeline` 和 `./batch_pipeline`。示例为每帧准备不同输入，使用相同核函数与已申请的缓冲区比较两种方案。计时前完成内存分配、输入生成、CPU 参考计算和预热；五轮交替改变两种方案的测量先后，逐轮核对全部输出。修改 `WIDTH`、`HEIGHT` 或 `FRAMES` 前应先估算页锁定内存和设备内存占用。

```cpp
#include <cuda_runtime.h>

#include <algorithm>
#include <chrono>
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

constexpr int WIDTH = 2051, HEIGHT = 1027, FRAMES = 16, SLOTS = 2;
constexpr std::size_t PIXELS = std::size_t(WIDTH) * HEIGHT;
constexpr std::size_t TOTAL = PIXELS * FRAMES;
using Clock = std::chrono::steady_clock;

__global__ void mean3x3(const unsigned char* input,
                        unsigned char* output, int width, int height) {
    int x = blockIdx.x * blockDim.x + threadIdx.x;
    int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height) return;
    int sum = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        int yy = min(max(y + dy, 0), height - 1);
        for (int dx = -1; dx <= 1; ++dx) {
            int xx = min(max(x + dx, 0), width - 1);
            sum += input[yy * width + xx];
        }
    }
    output[y * width + x] = static_cast<unsigned char>(sum / 9);
}

struct Slot {
    unsigned char *d_input = nullptr, *d_output = nullptr;
    cudaStream_t upload = nullptr, work = nullptr;
    cudaEvent_t ready = nullptr, done = nullptr;
};

void launch(Slot& slot) {
    dim3 block(16, 16);
    dim3 grid((WIDTH + 15) / 16, (HEIGHT + 15) / 16);
    mean3x3<<<grid, block, 0, slot.work>>>(
        slot.d_input, slot.d_output, WIDTH, HEIGHT);
    CUDA_CHECK(cudaGetLastError());
}

double run_serial(Slot& slot, const unsigned char* input,
                  unsigned char* output) {
    auto start = Clock::now();
    for (int i = 0; i < FRAMES; ++i) {
        auto* src = input + std::size_t(i) * PIXELS;
        auto* dst = output + std::size_t(i) * PIXELS;
        CUDA_CHECK(cudaMemcpyAsync(slot.d_input, src, PIXELS,
                                  cudaMemcpyHostToDevice, slot.work));
        launch(slot);
        CUDA_CHECK(cudaMemcpyAsync(dst, slot.d_output, PIXELS,
                                  cudaMemcpyDeviceToHost, slot.work));
    }
    CUDA_CHECK(cudaStreamSynchronize(slot.work));
    return std::chrono::duration<double, std::milli>(
        Clock::now() - start).count();
}

double run_pipeline(Slot (&slots)[SLOTS], const unsigned char* input,
                    unsigned char* output) {
    auto start = Clock::now();
    for (int i = 0; i < FRAMES; ++i) {
        Slot& slot = slots[i % SLOTS];
        auto* src = input + std::size_t(i) * PIXELS;
        auto* dst = output + std::size_t(i) * PIXELS;
        if (i >= SLOTS)
            CUDA_CHECK(cudaStreamWaitEvent(slot.upload, slot.done, 0));
        CUDA_CHECK(cudaMemcpyAsync(slot.d_input, src, PIXELS,
                                  cudaMemcpyHostToDevice, slot.upload));
        CUDA_CHECK(cudaEventRecord(slot.ready, slot.upload));
        CUDA_CHECK(cudaStreamWaitEvent(slot.work, slot.ready, 0));
        launch(slot);
        CUDA_CHECK(cudaMemcpyAsync(dst, slot.d_output, PIXELS,
                                  cudaMemcpyDeviceToHost, slot.work));
        CUDA_CHECK(cudaEventRecord(slot.done, slot.work));
    }
    for (Slot& slot : slots)
        CUDA_CHECK(cudaStreamSynchronize(slot.work));
    return std::chrono::duration<double, std::milli>(
        Clock::now() - start).count();
}

void make_reference(const unsigned char* input,
                    std::vector<unsigned char>& reference) {
    for (int frame = 0; frame < FRAMES; ++frame) {
        const unsigned char* src = input + std::size_t(frame) * PIXELS;
        unsigned char* dst = reference.data() + std::size_t(frame) * PIXELS;
        for (int y = 0; y < HEIGHT; ++y) {
            for (int x = 0; x < WIDTH; ++x) {
                int sum = 0;
                for (int dy = -1; dy <= 1; ++dy) {
                    int yy = std::min(std::max(y + dy, 0), HEIGHT - 1);
                    for (int dx = -1; dx <= 1; ++dx) {
                        int xx = std::min(std::max(x + dx, 0), WIDTH - 1);
                        sum += src[yy * WIDTH + xx];
                    }
                }
                dst[y * WIDTH + x] = static_cast<unsigned char>(sum / 9);
            }
        }
    }
}

bool check(const char* name, const unsigned char* output,
           const std::vector<unsigned char>& reference) {
    for (std::size_t i = 0; i < TOTAL; ++i) {
        if (output[i] != reference[i]) {
            std::cerr << name << " FAIL frame=" << i / PIXELS
                      << " pixel=" << i % PIXELS << " got=" << int(output[i])
                      << " expected=" << int(reference[i]) << '\n';
            return false;
        }
    }
    std::cout << name << " PASS\n";
    return true;
}

double median(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return values[values.size() / 2];  // 本例固定运行五轮
}

int main() {
    cudaDeviceProp device{};
    CUDA_CHECK(cudaGetDeviceProperties(&device, 0));
    std::cout << "GPU: " << device.name
              << ", asyncEngineCount=" << device.asyncEngineCount << '\n';

    unsigned char *input = nullptr, *output = nullptr;
    CUDA_CHECK(cudaMallocHost(reinterpret_cast<void**>(&input), TOTAL));
    CUDA_CHECK(cudaMallocHost(reinterpret_cast<void**>(&output), TOTAL));
    for (std::size_t i = 0; i < TOTAL; ++i)
        input[i] = static_cast<unsigned char>((i * 37 + i / PIXELS * 11) % 251);
    std::vector<unsigned char> reference(TOTAL);
    make_reference(input, reference);

    Slot slots[SLOTS];
    for (Slot& slot : slots) {
        CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&slot.d_input), PIXELS));
        CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&slot.d_output), PIXELS));
        CUDA_CHECK(cudaStreamCreateWithFlags(&slot.upload,
                                             cudaStreamNonBlocking));
        CUDA_CHECK(cudaStreamCreateWithFlags(&slot.work,
                                             cudaStreamNonBlocking));
        CUDA_CHECK(cudaEventCreateWithFlags(&slot.ready,
                                            cudaEventDisableTiming));
        CUDA_CHECK(cudaEventCreateWithFlags(&slot.done,
                                            cudaEventDisableTiming));
    }

    run_serial(slots[0], input, output);
    if (!check("serial warmup", output, reference)) return EXIT_FAILURE;
    run_pipeline(slots, input, output);
    if (!check("pipeline warmup", output, reference)) return EXIT_FAILURE;

    std::vector<double> serial_ms, pipeline_ms;
    for (int round = 0; round < 5; ++round) {
        if (round % 2 == 0) {
            serial_ms.push_back(run_serial(slots[0], input, output));
            if (!check("serial", output, reference)) return EXIT_FAILURE;
            pipeline_ms.push_back(run_pipeline(slots, input, output));
            if (!check("pipeline", output, reference)) return EXIT_FAILURE;
        } else {
            pipeline_ms.push_back(run_pipeline(slots, input, output));
            if (!check("pipeline", output, reference)) return EXIT_FAILURE;
            serial_ms.push_back(run_serial(slots[0], input, output));
            if (!check("serial", output, reference)) return EXIT_FAILURE;
        }
        std::cout << "round " << round + 1 << ": serial="
                  << serial_ms.back() << " ms, pipeline="
                  << pipeline_ms.back() << " ms\n";
    }
    double serial = median(serial_ms), pipeline = median(pipeline_ms);
    std::cout << std::fixed << std::setprecision(3)
              << "median serial=" << serial << " ms ("
              << FRAMES * 1000.0 / serial << " frames/s)\n"
              << "median pipeline=" << pipeline << " ms ("
              << FRAMES * 1000.0 / pipeline << " frames/s)\n";

    for (Slot& slot : slots) {
        CUDA_CHECK(cudaEventDestroy(slot.ready));
        CUDA_CHECK(cudaEventDestroy(slot.done));
        CUDA_CHECK(cudaStreamDestroy(slot.upload));
        CUDA_CHECK(cudaStreamDestroy(slot.work));
        CUDA_CHECK(cudaFree(slot.d_input));
        CUDA_CHECK(cudaFree(slot.d_output));
    }
    CUDA_CHECK(cudaFreeHost(input));
    CUDA_CHECK(cudaFreeHost(output));
    return EXIT_SUCCESS;
}
```

本例固定尺寸约为每帧 2.0 MiB；整批输入与输出各约 32.1 MiB 的页锁定主机内存，两个槽的设备输入与输出合计约 8.0 MiB。示例的固定小范围索引不会溢出 `int`；推广到任意尺寸时，还需检查乘法溢出、网格限制和可用内存。正常路径释放全部资源，CUDA 调用失败或结果校验失败时程序直接退出；长期运行的程序应让失败路径也能回收资源。

### 正确性与计时范围

预热及五轮正式测量中，串行和流水线的全部 `FRAMES × WIDTH × HEIGHT` 个输出都应与 CPU 参考值**逐字节相同**。`check` 在同步后运行，因此不会读取仍在下载的主机输出。若某轮出现 `FAIL`，先修正依赖或索引，再讨论性能。`cudaGetLastError` 检查启动阶段错误，流同步也会报告异步执行错误；这些检查不能替代结果比较。

两个时间都是主机时钟从**整批提交开始**到**最终流同步结束**的耗时，包括 `F` 次上传、核函数、下载以及主机提交和最终等待。它们不含内存申请、输入生成、CPU 参考计算和逐字节校验。串行版只用一条非默认流，所有帧按 `H → K → D` 入队后统一等待，并没有人为地逐帧主机同步；流水线版使用两个可循环复用的设备槽。`frames/s = F × 1000 / 毫秒` 是这批图像的端到端吞吐率，不能由单个核函数的事件时间代替。

在 NVIDIA GeForce RTX 4080 Laptop GPU、驱动 595.79、CUDA 13.1 与 `-O2` 下，设备报告 `asyncEngineCount=1`。程序独立启动三次，每次预热后运行五轮，全部逐字节检查均为 `PASS`。各次的五轮中位数如下（毫秒）：

| 独立运行 | 单流串行 | 双缓冲流水线 |
| --- | ---: | ---: |
| 1 | 6.641 | 6.681 |
| 2 | 6.674 | 6.862 |
| 3 | 6.655 | 6.653 |

本机这组批次没有显示稳定的吞吐收益；各次中位数的差异和运行间波动相近。它只描述上述设备、尺寸与测试时段，不能推广为双缓冲普遍无效。程序输出保留了每轮原始值，读者应在自己的设备上对照，并把更长的真实业务批次作为下一步实验。

不同流只提供并行机会。是否出现传输与计算重叠，受设备 `asyncEngineCount`、传输方向、核函数资源占用、队列提交顺序、主机总线和其他 GPU 工作影响；两个流上的核函数也可能依次执行。若流水线版更慢，事件与额外流的调度开销同样属于真实成本。表格或某次总时间只能证明该批任务的吞吐变化，不能单独证明各阶段真的重叠；需要时间线证据时，可使用 [Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/) 查看各流上的 H2D、kernel、D2H 区间，并与主机测得的整批时间对照。

本机另用 Nsight Systems 2025.5.2 对同一可执行程序采集 CUDA 时间线。安装分析器后，可在仓库外的练习目录执行以下命令；它会生成报告和逐条 GPU 活动的 CSV。分析器可能改变运行时序，普通运行的整批时间仍以上表为准。

```powershell
nsys profile --trace=cuda --sample=none --cpuctxsw=none -o batch_trace .\batch_pipeline.exe
nsys stats --report cuda_gpu_trace --format csv --output . batch_trace.nsys-rep
```

在一轮正式的双槽批处理中，CSV 记录了 16 次 H2D、16 次核函数和 16 次 D2H，分布在四条非默认流。以下时间以这一轮首个 H2D 的开始为 0，取报告中的前两帧及下一次同槽上传；数值单位为毫秒：

| 帧与阶段 | 流 | 开始 | 结束 |
| --- | ---: | ---: | ---: |
| 帧 0，H2D | 13 | 0.000 | 0.173 |
| 帧 0，核函数 | 14 | 0.314 | 0.343 |
| 帧 0，D2H | 14 | 0.361 | 0.522 |
| 帧 1，H2D | 15 | 0.523 | 0.698 |
| 帧 1，核函数 | 16 | 0.862 | 0.891 |
| 帧 1，D2H | 16 | 0.918 | 1.079 |
| 帧 2，H2D | 13 | 1.080 | 1.254 |

帧内始终是上传完成后才计算、计算完成后才下载；同槽的帧 2 也在帧 0 下载后才覆盖设备输入。对这次报告中五轮正式双槽批处理逐条检查，不同流上的 H2D、核函数与 D2H 区间均未发生重叠。**这是本次采集到的执行事实，不是“多流必然串行”的规则**；它与普通运行没有稳定吞吐收益的观察相容，但分析器本身也可能改变调度。若换设备、批次或负载，应重新采集时间线，而不能只凭 `asyncEngineCount` 或整批时间推断重叠。

## 4. CUDA Graph 的适用范围

当**相同的任务依赖图被反复执行**，而每轮包含许多很短的启动或拷贝时，CUDA Graph 可以把提交关系组织成图，实例化后重复启动，以减少主机逐节点提交成本。最小工作流是：确定稳定的节点与依赖，在允许的流上捕获或显式创建图，结束捕获、实例化，重复启动并同步，然后用同样的输入输出规则核对结果并比较整批时间。[CUDA Graph 官方章节](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html)说明了捕获、多流事件依赖和受限操作。

Graph 不是本例双缓冲的自动加速开关。它主要针对重复提交成本；如果时间主要花在传输或核函数中，收益可能很小。捕获期间不能同步正在捕获的流或使用不兼容的同步 API；跨流等待须满足捕获图的依赖规则。若每轮图像尺寸、缓冲区地址或任务结构变化，还要判断能否更新节点参数或需要重新建立图。页锁定输入、输出缓冲区在图执行期间仍须保持有效；判断收益时应把建图与实例化成本放在应用真实的重复次数中核算。本章的完整程序专门验证常规流与事件调度，Graph 留作独立的重复工作负载实验。

## 5. 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 偶发错帧或前后两帧结果混合 | 检查同槽复用前是否等待上一帧 `done`，每帧主机输入输出是否在传输期间保持有效。 |
| 首帧正确，后续帧错误 | 检查 `ready` 与 `done` 的记录和等待顺序，以及事件是否属于相应槽。 |
| `cudaMemcpyAsync` 已返回，输出仍是旧值 | 返回仅表示提交；等对应事件或流完成后才能读取输出。 |
| 双流仍无重叠 | 核对 pinned 主机内存、非默认流、设备拷贝能力，再查看时间线；流数量本身不是重叠证据。 |
| 流水线吞吐量下降 | 比较原始多轮时间；检查较小的任务、额外提交、资源竞争及其他 GPU 工作。 |
| Graph 捕获报错 | 检查同步调用、旧默认流行为、不受支持的操作及跨流事件是否属于同一捕获图。 |

## 规则速查

- `cudaMallocHost`：申请可用于异步主机传输的页锁定缓冲区；资源有限，传输完成前不得释放或改写相关区域。
- `cudaStreamCreateWithFlags`：建立非默认流；不同流只提供并行机会。
- `cudaMemcpyAsync`：将上传、下载提交到指定流；主机缓冲区须保持有效，访问结果前须同步。
- `cudaEventRecord`：标记该流此前工作完成的位置；重复记录会更新事件状态。
- `cudaStreamWaitEvent`：建立跨流依赖；等待调用时最近一次记录的工作。
- `cudaStreamSynchronize`：等待该流先前的工作；循环中逐帧等待会破坏整批流水线。

## 实践练习

1. 将 `FRAMES` 改为 `1`、`2` 和 `16` 分别运行。**验收标准**：全部输出仍为 `PASS`；保留五轮原始时间，说明流水线填充与排空在少量帧时为何更显著，不能仅凭一次运行宣布加速。
2. 将 `SLOTS` 扩展为 `3`，保持每槽各自的设备缓冲区、流与事件。**验收标准**：非整块图像的逐字节校验仍通过；与两个槽在同一设备上比较整批中位数，并解释更多槽未必更快。
3. 用 Nsight Systems 观察一次正式运行。**验收标准**：指出某一帧的 H2D、kernel、D2H 的先后关系，标出与另一帧交错的区间；如果没有重叠，就据时间线如实记录。

## 参考资料

- [NVIDIA CUDA Programming Guide：Asynchronous Execution](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/asynchronous-execution.html)
- [NVIDIA CUDA C++ Best Practices Guide：Asynchronous and Overlapping Transfers](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#asynchronous-and-overlapping-transfers-with-computation)
- [NVIDIA CUDA Runtime API：Event Management](https://docs.nvidia.com/cuda/cuda-runtime-api/cuda_runtime_api/group__CUDART__EVENT.html)
- [NVIDIA CUDA Programming Guide：CUDA Graphs](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cuda-graphs.html)
- [NVIDIA Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/)

**系列导航**：上一篇 · [分块计算与矩阵乘法]({{ '/posts/gpu-tiled-matrix-multiplication/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [计算库与框架集成]({{ '/posts/gpu-compute-libraries-and-framework-integration/' | relative_url }})。
