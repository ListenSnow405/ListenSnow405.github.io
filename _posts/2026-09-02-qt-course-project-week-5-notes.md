---
layout: post
title: "Qt 课程项目第 5 章：绘图、网络与多线程的取舍"
date: 2026-09-02 00:25:00 +0800
categories: [学习]
tags: [Qt, C++, QPainter, 网络编程, 多线程]
---

在[第四章]({% post_url 2026-09-02-qt-course-project-week-4-notes %})中，课程与作业管理系统已经形成 SQLite 数据闭环。本章进入项目专题阶段：从绘图、网络和多线程中选择真正服务于需求的能力，而不是为了展示技术把所有模块堆进项目。

默认项目将实现一个“作业完成率圆环”，学习 QPainter 和自定义控件。网络与多线程作为可选路线：只有项目确实需要外部数据或耗时任务时才加入。

## 1. 本章目标

完成本章后，应当能够：

- 根据项目需求选择专题模块；
- 理解 QWidget 的绘制流程；
- 使用 QPainter 编写自定义统计控件；
- 从数据库聚合统计数据；
- 使用 QNetworkAccessManager 发起异步请求；
- 判断何时不需要额外线程；
- 使用 worker object 模式执行耗时任务；
- 正确处理进度、取消、错误和对象释放。

## 2. 先选择，再实现

可以按照下面的标准判断：

| 项目需求 | 推荐模块 | 不建议的做法 |
| --- | --- | --- |
| 自定义统计图、绘图板 | QPainter | 只为一张静态图片引入复杂绘图库 |
| HTTP API、文件下载 | Qt Network | 为异步 HTTP 请求额外创建线程 |
| TCP 聊天、局域网通信 | QTcpSocket、QTcpServer | 用阻塞循环等待消息 |
| 大量文件处理、复杂计算 | QThread、QtConcurrent | 把 GUI 控件移动到工作线程 |
| 普通 SQLite 增删改查 | 通常保持主线程 | 每次简单查询都开新线程 |

本章最多选择一个主要亮点和一个辅助能力。功能越多，测试、错误处理和答辩解释的成本也越高。

## 3. QWidget 的绘制流程

当控件需要重绘时，Qt 会投递绘制事件并调用 `paintEvent()`。我们在这个函数中创建 QPainter：

```text
数据或尺寸发生变化
    → 调用 update()
    → Qt 合并重绘请求
    → 触发 paintEvent()
    → QPainter 在控件上绘制
```

不要在 `paintEvent()` 中修改数据库、发网络请求或改变业务状态。绘制函数应读取当前状态并完成显示，尽量保持快速和可重复。

`update()` 会安排一次稍后的重绘；`repaint()` 通常会立即绘制。普通界面更新优先使用 `update()`。

## 4. 自定义作业完成率圆环

创建 `completionringwidget.h`：

```cpp
#pragma once

#include <QWidget>

class CompletionRingWidget final : public QWidget {
    Q_OBJECT
    Q_PROPERTY(qreal progress READ progress WRITE setProgress
               NOTIFY progressChanged)

public:
    explicit CompletionRingWidget(QWidget *parent = nullptr);

    qreal progress() const;
    void setProgress(qreal value);

signals:
    void progressChanged(qreal value);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    qreal progress_ = 0.0;
};
```

实现 `completionringwidget.cpp`：

```cpp
#include "completionringwidget.h"

#include <QPainter>
#include <QPaintEvent>
#include <QPen>
#include <QtMath>

CompletionRingWidget::CompletionRingWidget(QWidget *parent)
    : QWidget(parent) {
    setMinimumSize(140, 140);
}

qreal CompletionRingWidget::progress() const {
    return progress_;
}

void CompletionRingWidget::setProgress(qreal value) {
    const qreal bounded = qBound(0.0, value, 1.0);

    if (qFuzzyCompare(progress_, bounded)) {
        return;
    }

    progress_ = bounded;
    update();
    emit progressChanged(progress_);
}

void CompletionRingWidget::paintEvent(QPaintEvent *event) {
    Q_UNUSED(event)

    QPainter painter(this);
    painter.setRenderHint(QPainter::Antialiasing);

    const int side = qMin(width(), height());
    const qreal penWidth = qMax(10.0, side * 0.08);
    const qreal margin = penWidth / 2.0 + 4.0;

    const QRectF ringRect(
        (width() - side) / 2.0 + margin,
        (height() - side) / 2.0 + margin,
        side - 2.0 * margin,
        side - 2.0 * margin);

    QPen backgroundPen(QColor("#d8e2ef"));
    backgroundPen.setWidthF(penWidth);
    backgroundPen.setCapStyle(Qt::RoundCap);

    painter.setPen(backgroundPen);
    painter.drawArc(ringRect, 0, 360 * 16);

    QPen progressPen(QColor("#2f80ed"));
    progressPen.setWidthF(penWidth);
    progressPen.setCapStyle(Qt::RoundCap);

    painter.setPen(progressPen);
    painter.drawArc(
        ringRect,
        90 * 16,
        -qRound(progress_ * 360.0 * 16.0));

    painter.setPen(palette().color(QPalette::Text));
    const QString percent = QStringLiteral("%1%")
        .arg(qRound(progress_ * 100.0));
    painter.drawText(rect(), Qt::AlignCenter, percent);
}
```

这个控件把进度限制在 0～1，并根据控件尺寸动态计算圆环。`Q_PROPERTY` 让属性可以被 Designer、属性系统或动画框架使用。

## 5. 在 Designer 中使用自定义控件

最简单的方法是“提升控件”：

1. 在页面中拖入一个 QWidget；
2. 设置合适的 objectName，例如 `completionRing`；
3. 右键选择“提升为”；
4. 类名填写 `CompletionRingWidget`；
5. 头文件填写 `completionringwidget.h`；
6. 将自定义类文件加入 CMake 目标。

Designer 只保存提升信息，真正的对象仍在构建和运行时由 C++ 类创建。

## 6. 从数据库计算完成率

统计值应由数据库或 Service 计算，而不是遍历表格单元格：

```cpp
struct AssignmentStatistics {
    int total = 0;
    int completed = 0;

    qreal completionRate() const {
        return total == 0
            ? 0.0
            : static_cast<qreal>(completed) / total;
    }
};
```

查询语句：

```sql
SELECT
    COUNT(*) AS total,
    COALESCE(SUM(completed), 0) AS completed
FROM assignments;
```

刷新总览页：

```cpp
const AssignmentStatistics statistics =
    assignmentService_->statistics();

ui->completionRing->setProgress(
    statistics.completionRate());
ui->totalLabel->setText(QString::number(statistics.total));
ui->completedLabel->setText(
    QString::number(statistics.completed));
```

每次新增、删除或更新作业后发出统一的 `assignmentsChanged` 信号，列表和统计页都监听它，而不是在多个槽函数中分别手工刷新。

## 7. 可选路线：异步 HTTP 请求

如果项目需要从公开 API 获取数据，可以链接 Network 模块：

```cmake
find_package(Qt6 REQUIRED COMPONENTS Widgets Sql Network)

target_link_libraries(course_manager PRIVATE
    Qt6::Widgets
    Qt6::Sql
    Qt6::Network
)
```

QNetworkAccessManager 本身提供异步接口。一个应用通常复用一个 manager：

```cpp
networkManager_ = new QNetworkAccessManager(this);
```

发送请求并处理响应：

```cpp
#include <QScopeGuard>

QNetworkRequest request(
    QUrl("https://example.com/api/semester"));

request.setHeader(
    QNetworkRequest::UserAgentHeader,
    QStringLiteral("CourseManager/0.1"));

QNetworkReply *reply = networkManager_->get(request);

connect(reply, &QNetworkReply::finished, this, [this, reply] {
    const auto cleanup = qScopeGuard([reply] {
        reply->deleteLater();
    });

    if (reply->error() != QNetworkReply::NoError) {
        showNetworkError(reply->errorString());
        return;
    }

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(
        reply->readAll(), &parseError);

    if (parseError.error != QJsonParseError::NoError) {
        showNetworkError(tr("服务器返回了无效 JSON"));
        return;
    }

    applySemesterData(document.object());
});
```

如果不使用 `qScopeGuard`，则要保证每条返回路径都调用 `reply->deleteLater()`。还应处理超时、取消、HTTP 状态码、JSON 字段缺失和重复请求。

不要通过忽略 `sslErrors` 来“解决”证书问题。应修复证书、系统时间或服务器配置。

## 8. 网络请求为什么通常不需要 QThread

`QNetworkAccessManager`、QTcpSocket 和 QTimer 都是事件驱动的。发起请求后，它们把等待交还给事件循环，不会像阻塞式读取那样占住主线程。

下面这种写法会冻结界面：

```cpp
// 错误思路：在主线程循环等待网络结果。
while (!finished) {
    // 持续轮询
}
```

正确方式是连接 `finished`、`readyRead`、`downloadProgress` 等信号，在状态变化时继续工作。

只有请求完成后还要进行大量 CPU 计算时，才考虑把那部分计算移到工作线程。

## 9. 可选路线：worker object 多线程模式

假设导入文件非常大，需要逐行解析并提供进度，可以创建 worker：

```cpp
class ImportWorker final : public QObject {
    Q_OBJECT

public:
    explicit ImportWorker(QString filePath);

public slots:
    void run();

signals:
    void progressChanged(int percent);
    void succeeded(QVector<Assignment> assignments);
    void failed(QString message);
    void finished();

private:
    QString filePath_;
};
```

创建线程并移动 worker：

```cpp
auto *thread = new QThread(this);
auto *worker = new ImportWorker(filePath);

worker->moveToThread(thread);

connect(thread, &QThread::started,
        worker, &ImportWorker::run);
connect(worker, &ImportWorker::progressChanged,
        this, &MainWindow::updateImportProgress);
connect(worker, &ImportWorker::succeeded,
        this, &MainWindow::applyImportedData);
connect(worker, &ImportWorker::failed,
        this, &MainWindow::showImportError);
connect(worker, &ImportWorker::finished,
        thread, &QThread::quit);
connect(worker, &ImportWorker::finished,
        worker, &QObject::deleteLater);
connect(thread, &QThread::finished,
        thread, &QObject::deleteLater);

thread->start();
```

需要特别注意：

- worker 中不能访问 QWidget；
- 通过信号发送值或不可变结果；
- 取消操作应采用协作式检查；
- 线程结束前清理属于该线程的 QObject；
- 每个线程中的数据库连接应在该线程创建和使用。

不要把槽函数直接写进 QThread 子类并假设它会在新线程执行。QThread 对象本身通常仍属于创建它的线程。

## 10. 进度、取消和错误状态

耗时操作至少需要四种状态：

```text
Idle → Running → Succeeded
            ├── Failed
            └── Cancelled
```

运行期间：

- 禁用会重复启动任务的按钮；
- 显示进度或“不确定进度”的忙碌状态；
- 保留取消入口；
- 结束后恢复界面；
- 不论成功、失败还是取消，都释放资源。

不要只处理成功信号。异常路径才是课程项目现场演示时最容易暴露的问题。

## 11. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 根据需求选择一个主要特色功能 |
| 第 2 步 | 理解 paintEvent、QPainter 和 update() |
| 第 3 步 | 实现可缩放的完成率圆环 |
| 第 4 步 | 从 SQLite 聚合统计并刷新总览页 |
| 第 5 步 | 按需练习一个异步 HTTP 请求 |
| 第 6 步 | 按需实现带进度的 worker object |
| 第 7 步 | 测试成功、失败、取消和空数据状态 |

默认课程项目完成前四步即可。只有需求确实涉及网络或大文件时，才继续对应路线。

## 12. 常见问题

### 自定义控件更新数据后没有重绘

状态变化后调用 `update()`，并确认 `paintEvent()` 读取的是最新成员变量。

### 绘制内容在窗口缩放后偏移

根据 `width()`、`height()` 和 `rect()` 动态计算，而不是写死坐标。使用 `qMin(width(), height())` 保持圆形比例。

### 网络请求完成后程序偶尔崩溃

检查 QNetworkReply 生命周期，不要在回调外保留已经 `deleteLater()` 的裸指针，也不要重复删除。

### 开了线程后界面仍然卡顿

确认耗时函数真的在 worker 所在线程执行，并检查主线程是否在等待 `wait()`、锁或大数据复制。

### 工作线程修改 QLabel 后崩溃

GUI 只能在主线程访问。worker 发出进度信号，由主窗口的槽更新 QLabel。

## 13. 本章验收清单

- [ ] 特色功能与项目需求直接相关；
- [ ] 自定义控件能够随尺寸正确重绘；
- [ ] `paintEvent()` 不修改业务数据；
- [ ] 完成率能够处理零条数据；
- [ ] 数据变化后统计和列表统一刷新；
- [ ] HTTP 请求使用异步信号而不是轮询；
- [ ] 网络错误和 JSON 解析错误有明确处理；
- [ ] 只有真实耗时任务才使用线程；
- [ ] worker 不访问 GUI 对象；
- [ ] 线程能够正常结束并释放对象；
- [ ] 成功、失败、取消和空数据状态都已测试。

完成特色功能后，应当停止继续堆叠模块。下一章将冻结需求、整理架构和错误处理，把已有功能组合成可以从头到尾稳定演示的 MVP。

官方参考：[QPainter](https://doc.qt.io/qt-6/qpainter.html) ｜ [QNetworkAccessManager](https://doc.qt.io/qt-6/qnetworkaccessmanager.html) ｜ [QThread](https://doc.qt.io/qt-6/qthread.html) ｜ [线程与 QObject](https://doc.qt.io/qt-6/threads-qobject.html)

上一篇：[第 4 章：文件、设置与 SQLite 数据闭环]({% post_url 2026-09-02-qt-course-project-week-4-notes %}) ｜ 下一篇：[第 6 章：功能整合与 MVP]({% post_url 2026-09-02-qt-course-project-week-6-notes %})
