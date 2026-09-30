---
layout: post
title: "计算库与框架集成"
date: 2026-09-28 02:00:00 +0800
categories: [学习]
tags: [GPU, CUDA, CuPy, 计算库, 自定义核函数, GPU编程系列]
excerpt: "以图像均值滤波为例，比较现成计算接口与自定义 CUDA 核函数，并将算子接入接收 NumPy 图像的处理流程。"
series: gpu-programming
series_order: 10
---

前一章的[异步执行与批处理流水线]({{ '/posts/gpu-asynchronous-execution-and-batch-pipeline/' | relative_url }})已经用 CUDA C++ 核函数处理整批图像。应用开发还要回答另一个问题：已有计算接口能否完成同一任务，什么时候才值得维护自己的核函数？本章沿用逐帧 **3×3 均值滤波**，先明确两条路径的输出规则，再把它们接入同一个 Python 图像处理入口。读者需要理解设备数组、边界处理和端到端计时；运行示例需要受支持的 NVIDIA GPU、CUDA 环境以及 CuPy。

## 1. 算子选择与接口契约

矩阵乘法、傅里叶变换等常见运算通常应先考察成熟计算库。例如，NVIDIA 的 [cuBLAS](https://docs.nvidia.com/cuda/cublas/) 提供 BLAS 与矩阵运算接口，[cuFFT](https://docs.nvidia.com/cuda/cufft/)提供傅里叶变换接口。应用框架又在这些能力之上提供数组、内存管理和调用入口；使用 `cp.matmul(A, B)` 时，开发者主要约定形状、布局、数据类型和结果要求，不必先重写矩阵乘法。具体后端、精度模式和性能仍应以实际版本与运行结果为准。

| 路线 | 适用情形 | 需要承担的工作 |
| --- | --- | --- |
| 现成库或框架算子 | 运算语义能够直接匹配，性能满足应用要求。 | 核对边界、布局、数据类型与精度；测量整个调用链。 |
| 组合多个框架算子 | 现成操作可以表达任务，但可能产生中间数组或多次启动。 | 检查中间数据与重复调用成本，不能只看其中一个算子的时间。 |
| 自定义核函数 | 语义特殊，或经测量确认组合方案的开销值得优化。 | 维护索引、越界保护、类型、并发正确性、测试及不同设备上的性能。 |

本章输入是一张二维、行优先、连续存储的 `uint8` 单通道图像，宽和高均大于零。每个输出像素取自身与八邻域的整数和，边界外坐标钳位到最近的合法像素，最后执行整数除法 `sum // 9`，得到 `uint8`。例如最左上角像素会在九个采样位置中出现四次。这个规则与上一章相同；它不是所有图像库“均值滤波”函数的默认规则。

应用接口固定为 `process_image(image, method)`：输入是 CPU 上的 NumPy 数组，返回同形状、同类型的 NumPy 数组。`method="library"` 调用 CuPy 的图像卷积接口，`method="kernel"` 调用自定义 CUDA 核函数；**两者是替代方案**，不是先后执行的两个滤波步骤。

```text
NumPy 图像 ─上传→ CuPy 设备数组 ─选择一种滤波实现→ CuPy 设备结果 ─下载→ NumPy 图像
                                      ├─ 现成卷积接口
                                      └─ RawKernel 中的 CUDA C++ 核函数
```

数组在设备上时可以继续交给其他 CuPy 操作；只有应用确实需要 CPU 结果时才下载。若在每个中间步骤后都转回 NumPy，就会反复支付传输与同步成本。[CuPy 基础文档](https://docs.cupy.dev/en/stable/user_guide/basic.html)说明了 NumPy 与 CuPy 数组的设备边界。

## 2. 均值滤波的两种实现

### 现成卷积接口

`cupyx.scipy.ndimage.convolve` 接受二维权重和边界模式。九个权重全为 `1` 时先得到邻域和；`mode="nearest"` 对应本例的边界钳位。输入先转成 `float32`，卷积输出也指定为 `float32`，再除以 `9` 并转成 `uint8`。本例输入最大为 `255`，九项和最大为 `2295`；这些整数能被 `float32` 精确表示。除法后的值非负，转换为 `uint8` 时舍去小数部分，因此与整数除法规则一致。这里要比较的是**卷积、类型转换和除法组成的完整方案**，不能只量卷积调用。

文档提示：整型输出的卷积可能受内部浮点舍入影响；本例显式使用浮点中间结果，并仍对全部输出做逐字节检查。[CuPy 卷积接口文档](https://docs.cupy.dev/en/stable/reference/generated/cupyx.scipy.ndimage.convolve.html)列出了 `output` 与边界模式的约定。

### 自定义核函数

`cp.RawKernel` 接收 CUDA C++ 源码并按网格、线程块和参数启动核函数。下面的核函数保留上一章的坐标钳位与 `sum / 9` 规则，只把设备缓冲区交给 CuPy 管理。`RawKernel` **不会替调用者检查参数类型，也不会自动处理数组视图的步长**；因此应用入口先拒绝非连续、非二维或类型不符的输入，宽高用 `np.int32` 传入，以匹配 CUDA 侧的 `int`。[CuPy 自定义核函数文档](https://docs.cupy.dev/en/stable/user_guide/kernel.html)解释了这些调用约束。

两条实现都返回设备数组，调用方不需要知道内部使用了多少个 GPU 操作。CuPy 会在首次需要时编译 `RawKernel` 并缓存结果；首次调用还可能包含 CUDA 上下文初始化，所以不能把它直接当作稳定的核函数耗时。[CuPy 性能指南](https://docs.cupy.dev/en/stable/user_guide/performance.html)给出了预热与事件计时的依据。

## 3. 完整集成程序

### 练习目录与环境

在博客仓库之外建立 `gpu-practice/framework-integration/`，将下面整个代码块保存为 UTF-8 编码的 `integrate_mean.py`。先用 `nvidia-smi` 和 `nvcc --version` 确认前面章节使用的 CUDA 环境，再按 [CuPy 官方安装说明](https://docs.cupy.dev/en/stable/install.html)选择与 CUDA 主版本匹配的包。以下 Windows 示例适用于 **CUDA 13.x**；CUDA 12.x 应将包名改为 `cupy-cuda12x`。一个环境中只安装一个 CuPy 包。

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install numpy cupy-cuda13x
.\.venv\Scripts\python.exe integrate_mean.py
```

Linux 可使用 `python3 -m venv .venv`，再调用 `.venv/bin/python` 执行相同的安装与运行步骤。这里的 `.venv` 位于独立练习目录，既不属于博客依赖，也不应提交到博客仓库。CuPy 包安装成功仍不等于设备与 CUDA 组件可用；首次运行的实际输出才是环境验证。

```python
import statistics
import time

import cupy as cp
import numpy as np
from cupyx.scipy.ndimage import convolve


# 权重固定为 3×3 的全 1 矩阵；卷积先求整数邻域和。
ONES = cp.ones((3, 3), dtype=cp.float32)

# 与上一章相同的像素规则。CuPy 管理输入和输出的设备内存，
# 此处仍由 CUDA C++ 线程负责坐标、边界和最终像素值。
MEAN_KERNEL = cp.RawKernel(r'''
extern "C" __global__
void mean3x3(const unsigned char* input, unsigned char* output,
             int width, int height) {
    const int x = blockIdx.x * blockDim.x + threadIdx.x;
    const int y = blockIdx.y * blockDim.y + threadIdx.y;
    if (x >= width || y >= height) return;

    int sum = 0;
    for (int dy = -1; dy <= 1; ++dy) {
        const int yy = min(max(y + dy, 0), height - 1);
        for (int dx = -1; dx <= 1; ++dx) {
            const int xx = min(max(x + dx, 0), width - 1);
            sum += input[yy * width + xx];
        }
    }
    output[y * width + x] = static_cast<unsigned char>(sum / 9);
}
''', 'mean3x3')


def library_mean(device_image):
    # float32 中间结果避免 uint8 的邻域和溢出；库方案还包含
    # 输入转换、卷积、除法和输出转换，不能只计卷积这一步。
    sums = convolve(device_image.astype(cp.float32), ONES,
                    output=cp.float32, mode='nearest')
    return (sums / cp.float32(9)).astype(cp.uint8)


def kernel_mean(device_image):
    height, width = device_image.shape
    output = cp.empty_like(device_image)
    block = (16, 16)
    grid = ((width + 15) // 16, (height + 15) // 16)
    MEAN_KERNEL(grid, block,
                (device_image, output, np.int32(width), np.int32(height)))
    return output


def process_image(image, method):
    # RawKernel 按连续内存计算下标；只接受明确约定的应用输入。
    if not isinstance(image, np.ndarray) or image.ndim != 2:
        raise ValueError('image must be a 2D NumPy array')
    if image.dtype != np.uint8 or not image.flags.c_contiguous:
        raise ValueError('image must be contiguous uint8')
    if image.size == 0 or image.size > np.iinfo(np.int32).max:
        raise ValueError('image size is outside the supported range')
    if method not in ('library', 'kernel'):
        raise ValueError('method must be library or kernel')

    device_image = cp.asarray(image)  # CPU → GPU
    if method == 'library':
        device_result = library_mean(device_image)
    else:
        device_result = kernel_mean(device_image)
    return cp.asnumpy(device_result)  # GPU → CPU；返回时结果可供 CPU 检查


def cpu_reference(image):
    # 独立的 CPU 参考：复制边缘后将九个错位区域相加。
    height, width = image.shape
    padded = np.pad(image.astype(np.int32), 1, mode='edge')
    sums = np.zeros((height, width), dtype=np.int32)
    for dy in range(3):
        for dx in range(3):
            sums += padded[dy:dy + height, dx:dx + width]
    return (sums // 9).astype(np.uint8)


def main():
    # 小图检查边界；非整块尺寸检查线程块末端。
    small = np.array([[0, 9, 18], [27, 36, 45]], dtype=np.uint8)
    large = ((np.arange(257 * 259, dtype=np.uint32) * 37 + 13) % 256)
    large = large.astype(np.uint8).reshape(257, 259)

    # 入口契约的反例在上传前拒绝，两条实现的行为应一致。
    invalid = [
        ('empty', np.empty((0, 3), dtype=np.uint8)),
        ('dtype', small.astype(np.float32)),
        ('non-contiguous', small[:, ::-1]),
    ]
    for name, image in invalid:
        for method in ('library', 'kernel'):
            try:
                process_image(image, method)
            except ValueError:
                print(f'{name}/{method}: REJECTED')
            else:
                raise AssertionError(f'{name}/{method}: should be rejected')

    for name, image in [('small', small), ('non-aligned', large)]:
        expected = cpu_reference(image)
        for method in ('library', 'kernel'):
            observed = process_image(image, method)
            if not np.array_equal(observed, expected):
                where = np.argwhere(observed != expected)[0]
                y, x = map(int, where)
                raise AssertionError(
                    f'{name}/{method} mismatch at ({y}, {x}): '
                    f'{observed[y, x]} != {expected[y, x]}')
            print(f'{name}/{method}: PASS')

    # 计时输入只生成一次；CPU 参考计算和首次编译不计入结果。
    image = ((np.arange(1027 * 2051, dtype=np.uint32) * 17 + 29) % 256)
    image = image.astype(np.uint8).reshape(1027, 2051)
    expected = cpu_reference(image)
    for method in ('library', 'kernel'):
        process_image(image, method)  # 预热、初始化与按需编译

    samples = {'library': [], 'kernel': []}
    for round_index in range(5):
        order = ('library', 'kernel') if round_index % 2 == 0 else (
            'kernel', 'library')
        for method in order:
            start = time.perf_counter()
            observed = process_image(image, method)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if not np.array_equal(observed, expected):
                raise AssertionError(f'benchmark/{method}: FAIL')
            samples[method].append(elapsed_ms)

    for method, values in samples.items():
        raw = ', '.join(f'{value:.3f}' for value in values)
        print(f'{method}: [{raw}] ms; median={statistics.median(values):.3f} ms')


if __name__ == '__main__':
    main()
```

程序先检查三个无效输入：空图、错误数据类型和非连续视图。两种方法都应各输出三行 `REJECTED`，而且这些输入在上传前即被拒绝；这只验证应用入口的契约，不调用 GPU 核函数。`small` 与 `non-aligned` 两组有效输入要求四次检查均打印 `PASS`；否则先修正环境或结果，再看计时。较大输入要求每轮均通过 CPU 参考结果检查，随后打印两组五轮原值与中位数。时间从应用入口调用前开始，到 `cp.asnumpy` 返回后结束，包括上传、设备分配或复用、框架调度、滤波、下载及必要等待；不含输入生成、CPU 参考计算和结果比较。`cp.asnumpy` 默认采用阻塞传输，因此此处的主机计时有明确的完成边界。[CuPy `asnumpy` 文档](https://docs.cupy.dev/en/stable/reference/generated/cupy.asnumpy.html)列出了 `blocking` 参数。

本例没有预设哪条路径更快。库方案可能受益于已有实现，也会承担转换及中间数组成本；自定义方案可能以一次核函数完成计算，但仍有编译、维护和形状适配成本。只比较 `RawKernel` 的设备执行时间与库方案的端到端时间没有意义。若真实应用让图像始终留在 GPU，应另测**已在设备上的完整处理链**；[CuPy 性能指南](https://docs.cupy.dev/en/stable/user_guide/performance.html)提供基于 CUDA 事件的 `cupyx.profiler.benchmark()`，可以在排除首次编译后观察设备侧时间。

在 NVIDIA GeForce RTX 4080 Laptop GPU、驱动 595.79、CUDA 13.1、Python 3.11、NumPy 2.4.3 与 CuPy 14.2.0 的本机环境中，原程序独立运行三次。每次的四项小图与非整块尺寸检查均为 `PASS`，较大输入在五轮计时中也逐轮通过逐字节检查。新增入口反例后，完整程序又运行一次，六项无效输入检查均为 `REJECTED`，四项有效输入检查仍为 `PASS`。下表只列原有三次运行各自的五轮中位数，单位为毫秒：

| 独立运行 | 库方案 | 自定义核函数方案 |
| --- | ---: | ---: |
| 1 | 0.995 | 0.910 |
| 2 | 1.007 | 0.919 |
| 3 | 1.059 | 1.139 |

第三次运行中，自定义方案的中位数高于库方案；这组数据不足以支持稳定的加速结论。程序会打印每轮原值，读者应在自己的设备和实际图像任务中重复检查。代码中的 CUDA 核函数还曾单独编译运行，并以 `1×1`、`3×2`、`259×257` 输入对照 CPU 整数参考结果，均逐字节一致。

## 4. 集成约束与选择依据

框架接入后，核函数代码只是接口的一部分。`RawKernel` 不会替应用推断数组是否连续，也不会把 `float32` 图像自动变成 `uint8`；传入转置视图时，按照本例的行优先下标读取会产生错误。真实图像输入若带颜色通道、行填充或不同灰度定义，应先明确转换规则，再选择库函数或改写核函数，不能悄悄当作本例输入。

如果上游已经生成 CuPy 数组，可直接调用 `library_mean` 或 `kernel_mean`，在最终需要 CPU 访问结果时再 `cp.asnumpy`。使用其他框架的设备张量时，还要核对设备归属、流依赖和内存所有权；不能仅凭它们都位于 GPU 就把指针任意传入 `RawKernel`。本章只演示 NumPy 与 CuPy 的明确边界，不将跨框架共享内存混入入门案例。

选择方案时先让两种实现满足同一接口契约，再分别记录正确性、端到端时间和维护成本。对标准矩阵乘法等操作，现成库往往是合理的起点；对本章的特殊整数输出和边界规则，可以先尝试框架接口组合。只有测量表明该组合成为瓶颈，而且自定义实现通过代表性尺寸与设备验证时，才有依据承担维护成本。性能结论应限定设备、输入、软件版本与计时范围。

## 5. 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 两条路径在图像边缘不同 | 核对 `mode='nearest'`、坐标钳位和整数除法，不要沿用库函数的默认边界模式。 |
| 只有转置或裁剪后的图像出错 | 检查是否为连续二维数组；`RawKernel` 不会自动按 NumPy/CuPy 视图步长访问。 |
| 首次调用明显较慢 | 区分 CUDA 上下文初始化、CuPy 的按需编译与稳定运行时间。 |
| 设备时间很短而应用仍慢 | 量上传、下载、类型转换和中间数组；检查是否在每步后都转回 CPU。 |
| 库方案与自定义方案都通过检查，但时间接近 | 保留五轮原值并重复运行；微小差异不足以单独支持维护新核函数。 |
| 更换数据类型后出现异常 | `RawKernel` 参数类型必须与 CUDA C++ 签名一致；本例只接受 `uint8` 输入与输出。 |

## 规则速查

| 内容 | 本例约定 |
| --- | --- |
| 应用输入与输出 | CPU 上连续二维 `uint8` NumPy 数组，形状不变 |
| 边界与舍入 | 最近像素钳位；九项整数和除以 `9`，舍去余数 |
| 库方案 | `convolve` 计算和，随后除法与类型转换 |
| 自定义方案 | `RawKernel` 一条线程处理一个输出像素 |
| 正确性 | 逐字节对照独立 CPU 参考结果 |
| 端到端计时 | 上传至下载完成；预热与结果检查在计时之外 |

## 实践练习

1. 将小图改为 `1×1`、`1×5` 和 `5×1`，分别输入全零、全 `255` 与交替像素。**验收标准**：两条路径对每种输入都与 CPU 参考结果逐字节相同，并能解释单行、单列的边界复制。
2. 让调用方在 GPU 上连续执行两次滤波，仅在最后下载。**验收标准**：两条实现各自与连续执行两次的 CPU 参考结果一致；分别报告一次与两次处理的端到端时间，指出传输次数是否改变。
3. 对相同图像在设备上预先保留输入，使用 `cupyx.profiler.benchmark()` 测量两条**完整设备方案**。**验收标准**：注明软件版本、设备、输入尺寸、预热与测量次数，保留原值；解释为何设备时间不能代替本章的应用入口时间。

## 参考资料

- [NVIDIA cuBLAS Documentation](https://docs.nvidia.com/cuda/cublas/)
- [NVIDIA cuFFT Documentation](https://docs.nvidia.com/cuda/cufft/)
- [CuPy Installation](https://docs.cupy.dev/en/stable/install.html)
- [CuPy User-Defined Kernels](https://docs.cupy.dev/en/stable/user_guide/kernel.html)
- [CuPy `cupyx.scipy.ndimage.convolve`](https://docs.cupy.dev/en/stable/reference/generated/cupyx.scipy.ndimage.convolve.html)
- [CuPy Performance Best Practices](https://docs.cupy.dev/en/stable/user_guide/performance.html)

**系列导航**：上一篇 · [异步执行与批处理流水线]({{ '/posts/gpu-asynchronous-execution-and-batch-pipeline/' | relative_url }}) · [GPU 编程系列入口]({{ '/series/' | relative_url }}#gpu-programming) · 下一篇计划：多 GPU 任务划分与通信。
