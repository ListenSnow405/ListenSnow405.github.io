---
layout: post
title: "数值精度与正确性"
date: 2026-09-28 00:56:00 +0800
categories: [学习]
tags: [GPU, CUDA, CUDA C++, 浮点数, 数值精度, 归约, GPU编程系列]
excerpt: "以浮点分块归约比较顺序求和、树形求和与双精度累加，建立参考值、误差容限和边界输入的检查方法。"
series: gpu-programming
series_order: 6
---

上一章对灰度像素求和时，整数结果可以与 CPU 逐位比较。若像素换成浮点数，即使索引、同步与数据传输都正确，分块归约仍可能和 CPU 顺序求和得到不同结果。本章延续[同步、原子操作与归约]({{ '/posts/gpu-synchronization-atomics-and-reduction/' | relative_url }})的分层求和，比较输入表示、加法顺序和累加类型的影响，并给出可执行的检查规则。读者需要了解线程块、共享内存和基本归约；运行案例需要 CUDA 编译器及设备。

## 1. 浮点求和的误差来源

### 输入表示与运算顺序

`float` 通常以有限的二进制位表示数值。`0.125` 可以精确表示，十进制 `0.1` 转成 `float` 后却是一个邻近值。本例的参考值从**已经存入 `float` 数组的值**计算；它回答“给定这些输入，归约结果有多接近”，并不声称恢复原始十进制实数。

每次浮点加法也会舍入。对于 `{1e8f, 1.0f, -1e8f, 1.0f}`，按数组顺序在 `float` 中求和时，第一个 `1.0f` 可能在加到 `1e8f` 时被舍去，最后得到 `1`。若先分别相加第 1、3 项和第 2、4 项，则得到 `0 + 2 = 2`。并行归约改变了括号的位置，因此不能把“与顺序 `float` 结果逐位相同”当作通用正确性标准。[NVIDIA CUDA C++ 最佳实践指南](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/#floating-point-math-is-not-associative)也明确说明浮点加法不满足结合律。

### 参考值与容差

本例将每个输入 `float` 转为 `double`，在 CPU 上顺序累加，作为**较高精度的参考值**；它不是任意规模、任意输入的数学精确和。对于本章的测试输入，`double` 能明显减小累加舍入。真实应用若有严重消去或更高精度要求，还需要更可靠的参考算法，并依据误差预算验证。

先排除 `NaN` 和无穷值，再使用下面的比较式，其中两个容差均为非负：

```text
绝对误差 = |计算结果 - 参考值|
通过条件：绝对误差 ≤ 绝对容差 + 相对容差 × |参考值|
```

接近零时，绝对容差承担主要作用；参考值很大时，相对容差能表达与结果规模相关的允许误差。容差要由输入规模、数值范围和应用需求确定，不能把一个宽松阈值当作所有算子的“正确证明”。同时记录实际误差，才能发现虽然通过阈值但精度正在退化的实现。

## 2. 浮点分块归约

### 数据流与实现选择

每个线程块处理最多 256 个 `float`。越界线程写入 0，全块完成加载后在共享内存中按步长减半归约。每块写出一个部分和；主机以 `double` 合并这些部分和。我们只替换块内累加类型，得到两种**独立的对照实现**：

| 实现 | 块内加法 | 块间合并 | 观察重点 |
| --- | --- | --- | --- |
| CPU 顺序 | `float` | 无 | 展示固定顺序的低精度累加 |
| GPU 树形 | `float` | CPU `double` | 展示顺序变化，减少块间累加误差 |
| GPU 混合精度 | `double` | CPU `double` | 输入仍为 `float`，提高中间累加精度 |

两种 GPU 实现都使用同一组输入和索引，因此比较结果主要反映累加类型的差异。`double` 共享内存部分和占用更多空间，计算吞吐也取决于设备；本章只检查正确性，不据此推断性能。尤其要区分“用 `double` 累加 `float` 输入”和“输入本身就是 `double`”。

### 完整程序

在独立练习目录中把下面的代码保存为 `precision_reduction.cu`。需要可用的 NVIDIA GPU、CUDA Toolkit 和受支持的 C++ 编译器；Windows PowerShell 使用 `.\precision_reduction.exe`，Linux 使用 `./precision_reduction`。四组输入按程序顺序分别运行，不必手动更换数据。

```cpp
#include <cuda_runtime.h>

#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

#define CUDA_CHECK(call)                                                     \
    do {                                                                     \
        cudaError_t status = (call);                                         \
        if (status != cudaSuccess) {                                         \
            std::cerr << #call << ": " << cudaGetErrorString(status)        \
                      << '\n';                                               \
            std::exit(EXIT_FAILURE);                                         \
        }                                                                    \
    } while (0)

constexpr int kBlockSize = 256;

template <typename Acc>
__global__ void reduce_blocks(const float* input, Acc* partial, int n) {
    __shared__ Acc values[kBlockSize];
    const int tid = threadIdx.x;
    const int i = blockIdx.x * blockDim.x + tid;
    values[tid] = i < n ? static_cast<Acc>(input[i]) : Acc{0};
    __syncthreads();

    for (int stride = kBlockSize / 2; stride > 0; stride /= 2) {
        if (tid < stride) {
            values[tid] += values[tid + stride];
        }
        __syncthreads();
    }
    if (tid == 0) partial[blockIdx.x] = values[0];
}

bool close_enough(double got, double reference,
                  double abs_tol, double rel_tol) {
    if (!std::isfinite(got) || !std::isfinite(reference)) return false;
    return std::fabs(got - reference) <=
           abs_tol + rel_tol * std::fabs(reference);
}

template <typename Acc>
double gpu_sum(const float* d_input, int n, int blocks) {
    Acc* d_partial = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_partial),
                          static_cast<size_t>(blocks) * sizeof(Acc)));
    reduce_blocks<Acc><<<blocks, kBlockSize>>>(d_input, d_partial, n);
    CUDA_CHECK(cudaGetLastError());
    CUDA_CHECK(cudaDeviceSynchronize());

    std::vector<Acc> partial(blocks);
    CUDA_CHECK(cudaMemcpy(partial.data(), d_partial,
                          partial.size() * sizeof(Acc),
                          cudaMemcpyDeviceToHost));
    CUDA_CHECK(cudaFree(d_partial));

    double total = 0.0;
    for (Acc part : partial) total += static_cast<double>(part);
    return total;
}

bool run_case(const std::string& name, const std::vector<float>& input,
              double abs_tol, double rel_tol) {
    if (input.empty()) {
        std::cerr << "Empty input is not supported\n";
        return false;
    }
    for (float value : input) {
        if (!std::isfinite(value)) {
            std::cerr << "Non-finite input in " << name << '\n';
            return false;
        }
    }

    float cpu_float = 0.0f;
    double reference = 0.0;
    for (float value : input) {
        cpu_float += value;
        reference += static_cast<double>(value);
    }

    const int n = static_cast<int>(input.size());
    const int blocks = (n + kBlockSize - 1) / kBlockSize;
    float* d_input = nullptr;
    CUDA_CHECK(cudaMalloc(reinterpret_cast<void**>(&d_input),
                          input.size() * sizeof(float)));
    CUDA_CHECK(cudaMemcpy(d_input, input.data(),
                          input.size() * sizeof(float),
                          cudaMemcpyHostToDevice));

    const double gpu_float = gpu_sum<float>(d_input, n, blocks);
    const double gpu_double = gpu_sum<double>(d_input, n, blocks);
    CUDA_CHECK(cudaFree(d_input));

    const bool float_ok =
        close_enough(gpu_float, reference, abs_tol, rel_tol);
    const bool double_ok =
        close_enough(gpu_double, reference, abs_tol, rel_tol);
    std::cout << name << " | reference=" << reference
              << " | CPU float=" << cpu_float
              << " | GPU float=" << gpu_float
              << " (error=" << std::fabs(gpu_float - reference) << ", "
              << (float_ok ? "PASS" : "FAIL") << ")"
              << " | GPU double=" << gpu_double
              << " (error=" << std::fabs(gpu_double - reference) << ", "
              << (double_ok ? "PASS" : "FAIL") << ")\n";
    return float_ok && double_ok;
}

int main() {
    std::cout << std::setprecision(12);
    bool ok = true;
    ok = run_case("cancellation", {1e8f, 1.0f, -1e8f, 1.0f},
                  1e-6, 0.0) && ok;
    ok = run_case("zero", {1e8f, 1.0f, -1e8f, -1.0f},
                  1e-6, 0.0) && ok;
    ok = run_case("partial block", std::vector<float>(257, 0.125f),
                  1e-6, 0.0) && ok;
    ok = run_case("many tenths", std::vector<float>(1000003, 0.1f),
                  1e-4, 1e-7) && ok;
    return ok ? EXIT_SUCCESS : EXIT_FAILURE;
}
```

编译并运行：

```bash
nvcc -std=c++17 -O2 precision_reduction.cu -o precision_reduction
./precision_reduction
```

Windows 的 MSVC 编译环境若需要明确源文件编码，可给 `nvcc` 加上 `-Xcompiler /utf-8`；执行命令换成 `.\precision_reduction.exe`。程序在每次核函数启动后检查启动错误并等待执行完成，数据拷贝和资源释放也检查返回值。任一 GPU 对照未通过容差检查时，进程返回非零状态。

### 结果核对

| 输入 | `double` 参考值 | 应观察到的现象 |
| --- | ---: | --- |
| 消去序列 `[1e8, 1, -1e8, 1]` | 2 | CPU 顺序 `float` 可得 1；本例树形归约得到 2。 |
| 零和序列 `[1e8, 1, -1e8, -1]` | 0 | CPU 顺序 `float` 可得 -1；绝对容差决定能否接纳接近零的结果。 |
| 257 个 `0.125f` | 32.125 | 检查最后一个不完整线程块的零填充；此输入可以精确求和。 |
| 1,000,003 个 `0.1f` | 约 100000.30149 | 参考值是已表示为 `float` 的输入之和，不是十进制的 100000.3。 |

前两组值用来说明顺序影响，不表示所有设备和编译选项下的 CPU 顺序输出都必须完全相同。第三组可定位边界处理错误。第四组让小的表示与累加误差在大量元素上显现；比较 `GPU float` 和 `GPU double` 的**实际误差**，不要只看 `PASS`。改成不同数据规模或数值分布时，重新论证容差。

## 3. 正确性判断与常见问题

先确认输入、输出长度、越界保护和同步无误，再分析数值误差。与参考值有差异并不自动说明核函数错误；反过来，容差通过也不能替代对索引和竞争条件的检查。

| 现象 | 检查方向 |
| --- | --- |
| 只有末块相关输入错误 | 核对块数、`i < n` 和无效线程的零填充；无效线程仍须参加屏障。 |
| 大量小数时误差增大 | 核对输入实际的 `float` 表示、块内加法顺序和累加类型。 |
| 参考值接近零时相对误差巨大 | 检查绝对误差与绝对容差，不仅看相对误差。 |
| 某次结果为 `NaN` 或无穷 | 检查输入、溢出和非法运算；不要让非有限值因比较逻辑而被当成通过。 |
| 更改归约方式后结果变动 | 对同一输入记录参考值、实际误差与容差，再判断是否满足应用要求。 |

本例固定每块树形求和，再按块序在 CPU 合并，便于重复测试；其他并行调度、原子浮点累加或编译选项可能改变运算顺序。需要跨实现逐位复现时，必须把归约顺序、精度与编译环境一起纳入约束。卷积等包含乘加的算子还要考虑融合乘加带来的舍入差异；可沿用“代表性输入—较可靠参考—明确容差—记录误差”的验证流程，不能直接搬用本例阈值。

## 规则速查

| 需求 | 本例做法 |
| --- | --- |
| 定义比较对象 | 以已存储的 `float` 输入建立较高精度参考值。 |
| 处理顺序差异 | 区分 CPU 顺序累加和 GPU 树形归约。 |
| 处理近零结果 | 使用绝对容差，并记录绝对误差。 |
| 处理大规模结果 | 结合相对容差及应用误差预算。 |
| 检查边界 | 覆盖消去、零和、非整块及大量不可精确表示的小数。 |
| 检查异常 | 对输入和输出中的 `NaN`、无穷值单独处理。 |

## 实践练习

1. 把 `partial block` 的长度依次改成 1、256、257 和 513。**验收标准**：四次 GPU 结果都通过检查，并能说明最后一块的有效元素数。
2. 把 `many tenths` 的输入长度改成 1,000、10,000 和 1,000,003，记录 CPU `float`、GPU `float` 和 GPU `double` 的误差。**验收标准**：表中写明每次参考值和误差，解释观察到的趋势，不预设误差一定单调。
3. 给 `run_case` 增加一个包含 `NaN` 的独立实验输入。**验收标准**：程序明确拒绝该输入，且不会把无效数值报告为 `PASS`。

## 参考资料

- [NVIDIA CUDA C++ Best Practices Guide：Verification 与 Numerical Accuracy](https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/)
- [NVIDIA Floating Point and IEEE 754](https://docs.nvidia.com/cuda/floating-point/contents.html)

**系列导航**：上一篇 · [同步、原子操作与归约]({{ '/posts/gpu-synchronization-atomics-and-reduction/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇 · [性能测量与瓶颈分析]({{ '/posts/gpu-performance-measurement-and-bottleneck-analysis/' | relative_url }})。
