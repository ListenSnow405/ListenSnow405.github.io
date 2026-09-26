---
layout: post
title: "Qt 课程项目第 1 章：环境、事件循环与信号槽"
date: 2026-09-01 10:10:00 +0800
categories: [学习]
tags: [Qt, C++, CMake, Qt Creator, 信号与槽]
series: qt
series_order: 1
---

在[《Qt 课程项目：8 个章节的项目驱动学习路线》]({% post_url 2026-09-01-qt-course-project-eight-week-roadmap %})中，我们把课程项目拆成了八个阶段。第一章不急着设计复杂页面，而是先理解 Qt 程序为什么能够响应操作，并建立“编辑、构建、运行、调试、提交”的最小开发闭环。

本章最终会完成一个小型学习计时器。它支持开始、暂停和重置，并用 QLabel 显示累计时间。这个项目会用到 QApplication、QWidget、布局、QObject 父子关系、信号与槽、QTimer 和 CMake。

## 1. 本章目标

完成第一章后，应当能够：

- 在 Qt Creator 中选择正确的 Kit 并构建项目；
- 读懂一个基础 Qt CMake 项目；
- 解释 QApplication 和事件循环的作用；
- 理解 QObject 父子关系与对象生命周期；
- 使用函数指针和 Lambda 连接信号与槽；
- 使用 QString、QTimer 等常见 Qt 类型；
- 独立完成并调试一个小型 Widgets 程序。

这一阶段不要求掌握数据库、网络、QML 或复杂界面美化。

## 2. 认识 Qt 开发环境

Qt 项目通常涉及四个部分：

- **Qt 框架**：提供窗口、事件、网络、数据库等模块；
- **编译器**：把 C++ 源代码编译为程序，例如 MinGW 或 MSVC；
- **CMake**：描述项目包含哪些文件、使用哪些 Qt 模块；
- **Qt Creator**：负责编辑、配置、构建、运行和调试。

Qt Creator 中的 **Kit** 是一套能够共同工作的 Qt 版本、编译器、调试器和构建工具组合。第一次创建项目时，应确认：

1. 选择的是 Qt 6 Kit；
2. 编译器和 Qt 库的体系结构一致；
3. 构建目录与源代码目录分离；
4. Debug 配置能够正常启动调试器。

MinGW 和 MSVC 都可以完成课程项目，但不要在同一个构建目录中混用两套编译器。切换 Kit 后应使用新的构建目录。

## 3. 第一个 CMake Qt 项目

学习计时器项目使用下面的结构：

```text
qt-study-timer/
├── CMakeLists.txt
├── main.cpp
├── studytimerwindow.h
└── studytimerwindow.cpp
```

`CMakeLists.txt` 可以写成：

```cmake
cmake_minimum_required(VERSION 3.16)

project(qt_study_timer VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

qt_standard_project_setup()

qt_add_executable(qt_study_timer
    main.cpp
    studytimerwindow.cpp
    studytimerwindow.h
)

target_link_libraries(qt_study_timer PRIVATE Qt6::Widgets)
```

各部分的职责如下：

- `project()` 定义项目名称、版本和语言；
- `CMAKE_CXX_STANDARD` 指定使用 C++17；
- `find_package()` 查找 Qt 6 的 Widgets 模块；
- `qt_standard_project_setup()` 启用 Qt 项目常用配置；
- `qt_add_executable()` 定义可执行程序及其源文件；
- `target_link_libraries()` 把 Qt Widgets 链接到程序。

可以在 Qt Creator 中直接配置和构建，也可以在配置好 Qt 环境的终端中执行：

```powershell
cmake -S . -B build
cmake --build build --config Debug
```

Qt Creator 生成的构建目录名称可能不同，不需要为了和示例完全一致而修改它。

## 4. QApplication 与事件循环

最小的 Widgets 程序入口如下：

```cpp
#include <QApplication>

#include "studytimerwindow.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    StudyTimerWindow window;
    window.show();

    return app.exec();
}
```

这里发生了三件重要的事：

1. 创建 `QApplication`，初始化整个 GUI 应用；
2. 创建窗口并调用 `show()`；
3. 调用 `exec()` 进入事件循环。

GUI 程序不能像普通命令行程序一样执行完几行代码就退出。用户可能在任意时刻点击按钮、按下键盘、移动鼠标或关闭窗口。事件循环会持续等待操作，再把事件分发给对应对象。

因此，进入 `app.exec()` 后程序并不是“卡住了”，而是在等待和处理事件。也正因为如此，主线程中不能执行长时间循环，否则界面将没有机会刷新和响应输入。

## 5. QObject 与对象树

QObject 是许多 Qt 类的基类，它提供了信号与槽、事件、动态属性和父子对象管理等能力。

例如：

```cpp
auto *timer = new QTimer(this);
```

这里的 `this` 是父对象。当父对象销毁时，Qt 会自动销毁它管理的子 QObject。这样能够减少 GUI 代码中手工 `delete` 的数量。

需要注意：

- 父子管理只适用于 QObject 体系；
- 栈对象离开作用域时仍按照 C++ 规则析构；
- 不要同时依赖父对象和错误的手工释放；
- 没有父对象的堆对象仍需要明确管理生命周期。

窗口中的按钮、标签和定时器通常可以把窗口作为父对象。局部布局加入窗口主布局后，也会被 Qt 接管。

## 6. 信号与槽

信号表示“某件事情发生了”，槽是收到通知后执行的函数。例如按钮发出 `clicked` 信号，窗口执行 `toggleTimer()`：

```cpp
connect(toggleButton_, &QPushButton::clicked,
        this, &StudyTimerWindow::toggleTimer);
```

QTimer 每次超时也会发出信号：

```cpp
connect(timer_, &QTimer::timeout,
        this, &StudyTimerWindow::updateElapsedTime);
```

连接的发送者和接收者不需要直接调用对方，从而降低对象之间的耦合。

简单逻辑也可以使用 Lambda：

```cpp
connect(helpButton, &QPushButton::clicked, this, [this] {
    statusLabel_->setText(tr("计时器用于记录本次学习时间"));
});
```

Lambda 的捕获列表需要谨慎。只有确实需要访问当前窗口时才捕获 `this`，并确保连接的生命周期不会超过被捕获对象。

## 7. 常见 Qt 类型

第一章先掌握下面几种类型：

| 类型 | 用途 |
| --- | --- |
| QString | Unicode 字符串和格式化文本 |
| QList | 保存同一类型的多个元素 |
| QVariant | 保存多种可能的数据类型 |
| QDateTime | 日期和时间处理 |
| QTimer | 周期或单次定时任务 |
| QFile | 文件读写 |
| QObject | 信号、槽、事件和对象树基础 |

QString 可以通过占位符格式化内容：

```cpp
const QString message = QStringLiteral("本次学习 %1 分钟").arg(25);
```

界面中需要翻译的用户可见文本，可以使用 `tr()`：

```cpp
setWindowTitle(tr("Qt 学习计时器"));
```

`QStringLiteral()` 适合固定字符串；`tr()` 则为后续国际化保留翻译入口。

## 8. 实践项目：学习计时器

### 8.1 窗口类声明

创建 `studytimerwindow.h`：

```cpp
#pragma once

#include <QWidget>

class QLabel;
class QPushButton;
class QTimer;

class StudyTimerWindow final : public QWidget {
    Q_OBJECT

public:
    explicit StudyTimerWindow(QWidget *parent = nullptr);

private slots:
    void toggleTimer();
    void resetTimer();
    void updateElapsedTime();

private:
    void refreshView();

    QLabel *timeLabel_;
    QLabel *statusLabel_;
    QPushButton *toggleButton_;
    QTimer *timer_;
    int elapsedSeconds_ = 0;
    bool running_ = false;
};
```

头文件只声明需要使用的类，具体控件头文件放在 `.cpp` 中包含，可以减少不必要的编译依赖。

`Q_OBJECT` 让类获得完整的 Qt 元对象能力。包含它的头文件必须加入 CMake 目标，Qt 的自动 MOC 才能稳定处理这个类。

### 8.2 创建界面并连接信号

创建 `studytimerwindow.cpp`：

```cpp
#include "studytimerwindow.h"

#include <QHBoxLayout>
#include <QLabel>
#include <QPushButton>
#include <QString>
#include <QTimer>
#include <QVBoxLayout>

StudyTimerWindow::StudyTimerWindow(QWidget *parent)
    : QWidget(parent),
      timeLabel_(new QLabel(this)),
      statusLabel_(new QLabel(tr("准备开始"), this)),
      toggleButton_(new QPushButton(tr("开始"), this)),
      timer_(new QTimer(this)) {
    setWindowTitle(tr("Qt 学习计时器"));
    resize(420, 240);

    auto *titleLabel = new QLabel(tr("本次学习时间"), this);
    auto *resetButton = new QPushButton(tr("重置"), this);

    titleLabel->setAlignment(Qt::AlignCenter);
    timeLabel_->setAlignment(Qt::AlignCenter);
    statusLabel_->setAlignment(Qt::AlignCenter);

    auto *buttonLayout = new QHBoxLayout;
    buttonLayout->addWidget(toggleButton_);
    buttonLayout->addWidget(resetButton);

    auto *mainLayout = new QVBoxLayout(this);
    mainLayout->addStretch();
    mainLayout->addWidget(titleLabel);
    mainLayout->addWidget(timeLabel_);
    mainLayout->addWidget(statusLabel_);
    mainLayout->addLayout(buttonLayout);
    mainLayout->addStretch();

    timer_->setInterval(1000);

    connect(toggleButton_, &QPushButton::clicked,
            this, &StudyTimerWindow::toggleTimer);
    connect(resetButton, &QPushButton::clicked,
            this, &StudyTimerWindow::resetTimer);
    connect(timer_, &QTimer::timeout,
            this, &StudyTimerWindow::updateElapsedTime);

    refreshView();
}

void StudyTimerWindow::toggleTimer() {
    running_ = !running_;

    if (running_) {
        timer_->start();
        toggleButton_->setText(tr("暂停"));
        statusLabel_->setText(tr("正在学习"));
    } else {
        timer_->stop();
        toggleButton_->setText(tr("继续"));
        statusLabel_->setText(tr("计时已暂停"));
    }
}

void StudyTimerWindow::resetTimer() {
    timer_->stop();
    running_ = false;
    elapsedSeconds_ = 0;
    toggleButton_->setText(tr("开始"));
    statusLabel_->setText(tr("准备开始"));
    refreshView();
}

void StudyTimerWindow::updateElapsedTime() {
    ++elapsedSeconds_;
    refreshView();
}

void StudyTimerWindow::refreshView() {
    const int hours = elapsedSeconds_ / 3600;
    const int minutes = elapsedSeconds_ / 60 % 60;
    const int seconds = elapsedSeconds_ % 60;

    timeLabel_->setText(
        QStringLiteral("%1:%2:%3")
            .arg(hours, 2, 10, QLatin1Char('0'))
            .arg(minutes, 2, 10, QLatin1Char('0'))
            .arg(seconds, 2, 10, QLatin1Char('0')));
}
```

这个例子刻意不使用 Qt Designer，以便直接观察对象创建、布局和信号连接。后续制作正式课程项目界面时，再学习 `.ui` 文件和 Designer。

### 8.3 运行时发生了什么

按下“开始”后，执行顺序可以概括为：

```text
用户点击按钮
    → QPushButton 发出 clicked 信号
    → toggleTimer() 启动 QTimer
    → QTimer 每秒发出 timeout 信号
    → updateElapsedTime() 增加秒数
    → refreshView() 更新 QLabel
```

这里没有用于等待一秒的阻塞循环。QTimer 把定时任务交给事件循环，因此窗口仍能正常移动、缩放和响应按钮。

## 9. 调试练习

在 Qt Creator 中给 `toggleTimer()` 第一行设置断点，然后执行下面的操作：

1. 以 Debug 模式启动程序；
2. 点击“开始”；
3. 查看 `running_` 和 `elapsedSeconds_`；
4. 单步执行，观察按钮文本变化；
5. 继续运行，再测试暂停和重置。

还可以主动制造几个问题，练习定位：

- 暂时注释一条 `connect()`，观察哪个按钮失效；
- 将定时间隔改为 100 毫秒，观察计数含义为什么不再正确；
- 在主线程中加入耗时循环，观察界面为什么失去响应；
- 切换 Kit 后复用旧构建目录，观察配置错误，再改用新目录。

调试的目标不是记住所有按钮位置，而是学会从构建输出、断点、变量值和调用栈寻找证据。

## 10. 常见问题

### CMake 找不到 Qt6

先确认 Qt Creator 选择了有效的 Qt 6 Kit。命令行构建时，还需要让 CMake 能够找到 Qt 安装位置。不要随意复制其他电脑上的绝对路径到项目文件中。

### 出现 `undefined reference to vtable`

常见原因是带有 `Q_OBJECT` 的文件没有被 MOC 正确处理。检查头文件是否加入 `qt_add_executable()`，并确认使用了 `qt_standard_project_setup()`。

### 点击按钮没有反应

检查：

- `connect()` 是否执行；
- 发送者、信号和接收者是否正确；
- 是否连接到了错误的局部对象；
- 程序是否在主线程执行了耗时任务。

### 窗口关闭后程序仍未退出

检查是否还存在顶层窗口或未结束的线程。普通单窗口 Widgets 程序关闭最后一个窗口后通常会退出。

## 11. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 安装并检查 Qt 6 Kit，运行一个空白窗口 |
| 第 2 步 | 阅读 CMakeLists，练习 Debug 和 Release 构建 |
| 第 3 步 | 理解 QApplication、事件循环和 QObject 对象树 |
| 第 4 步 | 练习信号与槽、Lambda 和 QTimer |
| 第 5 步 | 编写学习计时器的窗口与布局 |
| 第 6 步 | 完成暂停、重置、调试和异常操作测试 |
| 第 7 步 | 整理 README、复盘知识点并提交 Git |

每个练习步骤可以分成：30 分钟阅读、60～90 分钟编程、15 分钟记录问题。只有两三天集中学习时，可以在同一天连续完成多个步骤，但每完成一组知识点都应得到一个可运行结果。

## 12. 本章练习

完成基础计时器后，按顺序增加功能：

1. 增加“完成本次学习”按钮；
2. 完成时显示本次学习分钟数；
3. 禁止在计时为零时完成记录；
4. 使用 QSettings 保存窗口大小；
5. 增加一个“关于”对话框；
6. 为开始、暂停和重置设置键盘快捷键。

前四项完成后就可以停止扩展，把注意力转向代码清理和知识复盘。

## 13. 第一章验收清单

- [ ] 能从空目录创建并构建 Qt Widgets 项目；
- [ ] 能解释 `QApplication::exec()` 为什么不会立即返回；
- [ ] 能解释 `new QTimer(this)` 中 `this` 的作用；
- [ ] 能独立写出至少两条信号与槽连接；
- [ ] 学习计时器可以开始、暂停和重置；
- [ ] 主线程没有阻塞等待；
- [ ] Debug 断点和变量查看能够正常使用；
- [ ] 项目包含 README，并已提交到 Git；
- [ ] 能删除构建目录后重新配置并成功构建。

第一章真正需要建立的是一套可靠的开发循环。等到创建窗口、连接信号和调试程序不再陌生，第二章就可以开始搭建正式课程项目的主窗口、页面导航和输入对话框。

官方参考：[Qt 入门](https://doc.qt.io/qt-6/gettingstarted.html) ｜ [使用 CMake 构建 Qt 项目](https://doc.qt.io/qt-6/cmake-get-started.html)

返回：[8 个章节的项目驱动学习路线]({% post_url 2026-09-01-qt-course-project-eight-week-roadmap %}) ｜ 下一篇：[第 2 章：主窗口、布局与界面原型]({% post_url 2026-09-02-qt-course-project-week-2-notes %})
