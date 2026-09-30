#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

// 限制练习规模，拒绝负数、尾随字符和超大输入，避免意外耗尽资源。
int positive(const std::string& text, int limit) {
    std::size_t used = 0;
    int value = std::stoi(text, &used);
    if (used != text.size() || value < 1 || value > limit)
        throw std::invalid_argument("argument outside allowed range");
    return value;
}

// A 使用中间数组和两个循环，B 融合循环；数学任务相同。
// 独立函数方便设置断点，具体机器上是否更快由实验决定。
void compute(const std::vector<float>& a, const std::vector<float>& b,
             std::vector<float>& temp, std::vector<float>& out, char variant) {
    if (variant == 'A') {
        for (std::size_t i = 0; i < a.size(); ++i) temp[i] = 3.0f * a[i];
        for (std::size_t i = 0; i < a.size(); ++i) out[i] = temp[i] + 2.0f * b[i];
    } else {
        for (std::size_t i = 0; i < a.size(); ++i) out[i] = 3.0f * a[i] + 2.0f * b[i];
    }
}

int main(int argc, char** argv) {
    try {
        if (argc != 4) throw std::invalid_argument("usage: vector_lab N A|B REPEAT");
        const int n = positive(argv[1], 10000000);
        const std::string version = argv[2];
        if (version != "A" && version != "B") throw std::invalid_argument("variant must be A or B");
        const int repeat = positive(argv[3], 10000);
        std::vector<float> a(n), b(n), temp(n), out(n);
        for (int i = 0; i < n; ++i) {
            a[i] = static_cast<float>(i % 251);
            b[i] = static_cast<float>(i % 127);
        }

        // 每轮只计 compute，初始化、参考校验、checksum 和输出均在计时外。
        // 每轮读取结果，避免重复调用成为完全不可观察的死代码。
        double total_ms = 0.0, checksum = 0.0;
        bool correct = true;
        for (int r = 0; r < repeat; ++r) {
            const auto start = std::chrono::steady_clock::now();
            compute(a, b, temp, out, version[0]);
            const auto stop = std::chrono::steady_clock::now();
            total_ms += std::chrono::duration<double, std::milli>(stop - start).count();
            for (int i = 0; i < n; ++i) {
                const double ref = 3.0 * (i % 251) + 2.0 * (i % 127);
                correct = correct && std::isfinite(out[i]) && std::abs(out[i] - ref) <= 1e-6;
                checksum += out[i];
            }
        }
        std::cout << "input_id=formula-v1\nn=" << n << "\nvariant=" << version
                  << "\nrepeat=" << repeat << "\nthreads=1\nseed=0\ncorrectness="
                  << (correct ? "pass" : "fail") << "\nmetric=compute_ms\nunit=ms"
                  << "\nscope=compute-only\nvalue=" << std::setprecision(17)
                  << total_ms / repeat << "\nchecksum=" << checksum << '\n';
        return correct ? 0 : 3;
    } catch (const std::exception& e) {
        std::cerr << "# error: " << e.what() << '\n';
        return 2;
    }
}
