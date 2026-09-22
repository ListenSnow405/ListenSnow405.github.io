---
layout: post
title: "Qt 课程项目第 2 章：主窗口、布局与界面原型"
date: 2026-09-02 00:10:00 +0800
categories: [学习]
tags: [Qt, C++, Qt Widgets, Qt Designer, 界面设计]
---

在[第一章]({% post_url 2026-09-01-qt-course-project-week-1-notes %})中，我们用学习计时器打通了 Qt 项目的构建、运行和信号连接流程。本章开始进入正式课程项目，以“课程与作业管理系统”为例，搭建主窗口、页面导航、输入对话框和统一视觉样式。

本章的目标不是立刻接入数据库，而是得到一个可以点击、切换和演示的界面原型。页面可以暂时使用模拟数据，但窗口结构和对象命名应当能够支撑后续开发。

## 1. 本章目标

完成本章后，应当能够：

- 理解 QWidget、QMainWindow 和 QDialog 的职责；
- 使用 Qt Widgets Designer 编辑 `.ui` 文件；
- 使用布局管理器构建可缩放界面；
- 创建菜单栏、工具栏、状态栏和 QAction；
- 使用 QStackedWidget 组织多个业务页面；
- 使用自定义 QDialog 收集用户输入；
- 使用 `.qrc` 管理图标和 QSS；
- 完成课程项目的可交互界面原型。

## 2. QWidget、QMainWindow 与 QDialog

三类窗口各自解决不同问题：

| 类型 | 适用场景 | 特点 |
| --- | --- | --- |
| QWidget | 普通页面、自定义控件 | 是大多数 Widgets 控件的基础 |
| QMainWindow | 应用主窗口 | 内置菜单栏、工具栏、状态栏和中心区域 |
| QDialog | 新增、编辑、设置等临时任务 | 支持接受、拒绝和模态执行 |

QMainWindow 自带一套特殊布局。业务内容应放入 `centralWidget`，不要直接给 QMainWindow 调用 `setLayout()`。菜单栏、工具栏和状态栏则使用 QMainWindow 提供的接口管理。

课程项目只保留一个主窗口。新增课程、编辑作业和应用设置等短流程使用对话框完成，避免每个功能都创建一个独立顶层窗口。

## 3. 使用 Qt Designer 创建主窗口

可以在 Qt Creator 中创建 `Qt Widgets Application`，基类选择 QMainWindow。向导通常会生成：

```text
course-manager/
├── CMakeLists.txt
├── main.cpp
├── mainwindow.h
├── mainwindow.cpp
└── mainwindow.ui
```

`.ui` 文件本质上是 XML。构建时，Qt 的 UIC 会把它转换成 C++ 头文件。只要使用 `qt_standard_project_setup()` 并将 `.ui` 文件加入目标，CMake 就会处理自动 UIC：

```cmake
cmake_minimum_required(VERSION 3.16)

project(course_manager VERSION 0.1 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)
qt_standard_project_setup()

qt_add_executable(course_manager
    main.cpp
    mainwindow.cpp
    mainwindow.h
    mainwindow.ui
    resources.qrc
)

target_link_libraries(course_manager PRIVATE Qt6::Widgets)
```

不要直接修改构建目录里生成的 `ui_mainwindow.h`，因为下一次构建会覆盖它。界面结构修改 `.ui`，交互逻辑修改自己的 `.h` 和 `.cpp`。

## 4. 规划主窗口信息架构

“课程与作业管理系统”可以划分为四个页面：

```text
MainWindow
├── 左侧导航
│   ├── 总览
│   ├── 课程
│   ├── 作业
│   └── 设置
├── QStackedWidget
│   ├── overviewPage
│   ├── coursePage
│   ├── assignmentPage
│   └── settingsPage
├── 菜单栏
├── 工具栏
└── 状态栏
```

在 Designer 中为控件设置稳定的 `objectName`，例如：

| 控件 | objectName |
| --- | --- |
| 页面容器 | `pageStack` |
| 总览按钮 | `overviewButton` |
| 课程按钮 | `courseButton` |
| 作业按钮 | `assignmentButton` |
| 作业表格 | `assignmentTableView` |
| 搜索框 | `searchEdit` |
| 新增操作 | `actionAddAssignment` |

对象名是代码和 `.ui` 文件之间的接口。不要保留 `pushButton_3`、`widget_7` 等无法表达含义的名字。

## 5. 正确使用布局

Designer 中拖入控件后，还要为每个容器设置布局。常用布局包括：

- QHBoxLayout：横向排列；
- QVBoxLayout：纵向排列；
- QGridLayout：网格排列；
- QFormLayout：标签与输入框组成的表单；
- QSplitter：允许用户拖动调整两个区域的比例。

设计主页面时可以使用下面的嵌套关系：

```text
centralWidget
└── QHBoxLayout
    ├── navigationWidget
    │   └── QVBoxLayout
    └── pageStack
        └── 每个页面都有自己的顶层布局
```

完成后使用 Designer 的预览功能反复缩放窗口。如果控件位置不跟随窗口变化，通常是某一层容器缺少顶层布局。

不要通过大量 `setGeometry()` 修复布局问题。应优先检查：

- 容器是否设置了布局；
- `sizePolicy` 是否合理；
- 是否需要 stretch；
- 控件是否设置了不必要的最小或最大尺寸。

## 6. 连接页面导航

`mainwindow.h` 可以保持简洁：

```cpp
#pragma once

#include <QMainWindow>

QT_BEGIN_NAMESPACE
namespace Ui {
class MainWindow;
}
QT_END_NAMESPACE

class MainWindow final : public QMainWindow {
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private:
    void setupNavigation();

    Ui::MainWindow *ui;
};
```

在 `mainwindow.cpp` 中连接导航按钮：

```cpp
#include "mainwindow.h"
#include "ui_mainwindow.h"

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent), ui(new Ui::MainWindow) {
    ui->setupUi(this);
    setupNavigation();

    ui->pageStack->setCurrentWidget(ui->overviewPage);
    statusBar()->showMessage(tr("系统已就绪"));
}

MainWindow::~MainWindow() {
    delete ui;
}

void MainWindow::setupNavigation() {
    connect(ui->overviewButton, &QPushButton::clicked, this, [this] {
        ui->pageStack->setCurrentWidget(ui->overviewPage);
        statusBar()->showMessage(tr("总览"));
    });

    connect(ui->courseButton, &QPushButton::clicked, this, [this] {
        ui->pageStack->setCurrentWidget(ui->coursePage);
        statusBar()->showMessage(tr("课程管理"));
    });

    connect(ui->assignmentButton, &QPushButton::clicked, this, [this] {
        ui->pageStack->setCurrentWidget(ui->assignmentPage);
        statusBar()->showMessage(tr("作业管理"));
    });
}
```

页面索引可能随着 Designer 中的顺序变化，因此比起 `setCurrentIndex(2)`，使用 `setCurrentWidget(ui->assignmentPage)` 更容易维护。

## 7. QAction、菜单和工具栏

“新增作业”可能同时出现在菜单栏、工具栏和快捷键中。不要为三处分别编写业务逻辑，而应复用同一个 QAction：

```cpp
ui->actionAddAssignment->setShortcut(QKeySequence::New);

connect(ui->actionAddAssignment, &QAction::triggered,
        this, &MainWindow::openAssignmentDialog);
```

在 Designer 中把 `actionAddAssignment` 同时拖到菜单和工具栏。这样它们的启用状态、快捷键和提示文字始终一致。

建议至少准备：

- 新增课程；
- 新增作业；
- 导入；
- 导出；
- 退出；
- 关于。

目前没有实现的操作可以先显示提示，但不要让按钮点击后完全没有反馈。

## 8. 创建输入对话框

新增作业对话框可以包含：

- 作业标题 QLineEdit；
- 所属课程 QComboBox；
- 截止日期 QDateEdit；
- 完成状态 QCheckBox；
- 确定与取消 QDialogButtonBox。

基础调用方式如下：

```cpp
AssignmentDialog dialog(this);

if (dialog.exec() == QDialog::Accepted) {
    const QString title = dialog.title().trimmed();
    const QDate deadline = dialog.deadline();

    statusBar()->showMessage(
        tr("已创建：%1，截止日期 %2")
            .arg(title, deadline.toString("yyyy-MM-dd")),
        4000);
}
```

对话框只负责收集和初步校验输入，不应直接操作主窗口中的表格，也不应自行打开数据库。后续会把数据交给业务层处理。

## 9. 使用资源文件管理图标和样式

资源文件 `resources.qrc` 可以写成：

```xml
<RCC>
  <qresource prefix="/">
    <file>icons/add.svg</file>
    <file>icons/course.svg</file>
    <file>styles/app.qss</file>
  </qresource>
</RCC>
```

代码通过 `:/` 路径访问资源：

```cpp
ui->actionAddAssignment->setIcon(QIcon(":/icons/add.svg"));
```

加载全局 QSS：

```cpp
QFile styleFile(":/styles/app.qss");

if (styleFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
    qApp->setStyleSheet(QString::fromUtf8(styleFile.readAll()));
}
```

样式文件先保持克制：

```css
QPushButton {
    min-height: 32px;
    padding: 0 12px;
    border: 1px solid #bcc8d6;
    border-radius: 6px;
}

QPushButton:hover {
    background: #e8f3ff;
}

QPushButton:focus {
    border-color: #2f80ed;
}
```

优先保证层级、间距、状态和可读性，不要在原型阶段花大量时间制作复杂动画或高强度渐变。

## 10. 原型数据与占位状态

在数据库接入前，可以向页面加入少量模拟内容：

```cpp
ui->courseComboBox->addItems({
    tr("数据结构"),
    tr("数据库原理"),
    tr("计算机网络")
});
```

空页面也应提供明确状态，例如“还没有作业，点击右上角新增”。这比放置一个完全空白的表格更容易演示，也能提前暴露页面布局问题。

模拟数据只用于验证界面，不要把它散落在多个槽函数中。可以集中在 `loadPrototypeData()`，接入真实数据后统一删除。

## 11. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 创建正式项目，认识 QMainWindow 和 `.ui` 文件 |
| 第 2 步 | 在 Designer 中建立主窗口和四个页面 |
| 第 3 步 | 为全部容器设置布局并测试窗口缩放 |
| 第 4 步 | 使用 QStackedWidget 实现页面导航 |
| 第 5 步 | 添加菜单、工具栏、状态栏和 QAction |
| 第 6 步 | 创建新增作业 QDialog 并读取用户输入 |
| 第 7 步 | 加入资源文件、基础 QSS 和模拟数据 |

## 12. 常见问题

### 修改 `.ui` 后代码没有变化

确认 `.ui` 文件已经加入 CMake 目标，并重新构建。如果手工创建项目，还要确认调用了 `qt_standard_project_setup()`。

### Designer 中窗口不能正确缩放

通常是 centralWidget、QGroupBox、QStackedWidget 页面等容器没有顶层布局。逐层点击对象检查布局，而不是继续拖动控件位置。

### 图标在自己的电脑正常，换目录后消失

不要把本地绝对路径写进代码。将图标加入 `.qrc`，并通过 `:/icons/...` 访问。

### 对话框关闭后数据丢失

对话框中的局部数据本来就会随对象销毁。主窗口应在 `exec()` 返回 Accepted 后读取结果，并交给模型或业务层保存。

### 界面代码越来越难维护

把页面拆成独立 QWidget 类，把输入流程拆成 QDialog，把共用操作放进 QAction。不要让 MainWindow 同时负责所有页面细节。

## 13. 本章验收清单

- [ ] 主窗口包含菜单栏、工具栏、状态栏和中心区域；
- [ ] 至少三个业务页面能够正常切换；
- [ ] 每个容器都设置了合理布局；
- [ ] 窗口缩放时控件不会明显重叠；
- [ ] QAction 能被菜单、工具栏和快捷键复用；
- [ ] 新增作业对话框能够接受和取消；
- [ ] 图标和 QSS 通过 `.qrc` 加载；
- [ ] 控件 objectName 能表达业务含义；
- [ ] 当前版本可以使用模拟数据完整演示导航流程。

完成界面原型后，下一章将加入事件处理、输入校验和 Model/View，让页面从“可以点击”升级为“能够正确维护内存数据”。

官方参考：[Qt Widgets](https://doc.qt.io/qt-6/qtwidgets-index.html) ｜ [布局管理](https://doc.qt.io/qt-6/layout.html) ｜ [使用 Designer 布局](https://doc.qt.io/qt-6/designer-layouts.html)

上一篇：[第 1 章：环境、事件循环与信号槽]({% post_url 2026-09-01-qt-course-project-week-1-notes %}) ｜ 下一篇：[第 3 章：事件、输入校验与 Model/View]({% post_url 2026-09-02-qt-course-project-week-3-notes %})
