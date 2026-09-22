---
layout: post
title: "Qt 课程项目第 6 章：功能整合与 MVP"
date: 2026-09-02 00:30:00 +0800
categories: [学习]
tags: [Qt, C++, 课程项目, MVP, 软件工程]
---

在[第五章]({% post_url 2026-09-02-qt-course-project-week-5-notes %})中，我们为课程项目选择了特色功能。现在停止继续扩张需求，把窗口、模型、数据库、导入导出和统计功能整合成一个可以完整演示的 MVP。

MVP 不是随便拼出的半成品，而是围绕核心用户流程形成的最小完整版本。它可以暂时缺少次要功能，但不能在主流程中留下断点。

## 1. 本章目标

完成本章后，应当能够：

- 冻结课程项目的功能范围；
- 用用户故事定义核心流程；
- 明确 UI、Model、Service 和 Repository 的职责；
- 设计一致的成功与失败返回方式；
- 通过信号统一刷新多个页面；
- 处理空白、加载、成功和错误状态；
- 建立可追踪的日志；
- 准备一条稳定的完整演示流程。

## 2. 冻结功能范围

可以使用 Must、Should、Could、Won't 四组整理需求：

| 级别 | 本项目示例 |
| --- | --- |
| Must | 课程与作业增删改查、搜索、SQLite、错误提示 |
| Should | JSON 导入导出、完成率统计、设置恢复 |
| Could | 日历视图、托盘提醒、主题切换 |
| Won't | 账号系统、云同步、多人协作、移动端 |

MVP 只承诺 Must，并选择少量风险可控的 Should。Could 只有在主流程稳定后才进入开发，Won't 明确记录为本版本不做。

冻结范围后，新想法先记录到 backlog，不立即修改正在验收的版本。

## 3. 用用户故事定义完成标准

与其写“完成作业模块”，不如写成可验证的用户故事：

```text
作为学生，
我希望创建一门课程并添加带截止日期的作业，
以便在作业列表中按日期查看和管理任务。
```

对应验收条件：

1. 课程名称不能为空且不能重复；
2. 新增作业必须关联已有课程；
3. 截止日期必须有效；
4. 保存成功后列表和统计立即刷新；
5. 程序重启后数据仍然存在；
6. 保存失败时不显示虚假的成功状态。

每个 Must 功能都应该有类似的输入、操作和可观察结果。

## 4. 确认最终架构

项目可以整理成：

```text
src/
├── main.cpp
├── app/
│   └── applicationcontroller.*
├── ui/
│   ├── mainwindow.*
│   ├── assignmentdialog.*
│   └── widgets/completionringwidget.*
├── domain/
│   ├── assignment.h
│   └── course.h
├── models/
│   └── assignmenttablemodel.*
├── services/
│   └── assignmentservice.*
├── data/
│   ├── databasemanager.*
│   └── assignmentrepository.*
└── utils/
    └── jsonexporter.*
resources/
tests/
```

依赖方向应尽量保持单向：

```text
UI → Service → Repository → SQLite
 ↓       ↓
Model  Domain
```

Repository 不包含 QMessageBox，领域对象不包含 QWidget，Service 不负责控件颜色，MainWindow 不直接拼接 SQL。

## 5. 统一操作结果

跨层调用不能只返回 `bool` 后丢失错误信息，也不应把底层 SQL 错误原样展示给用户。可以定义：

```cpp
struct OperationResult {
    bool success = false;
    QString userMessage;
    QString technicalMessage;

    static OperationResult ok(QString message = {}) {
        return {true, message, {}};
    }

    static OperationResult fail(QString userMessage,
                                QString technicalMessage = {}) {
        return {false,
                userMessage,
                technicalMessage};
    }
};
```

用户信息应简洁可操作，例如“课程名称已存在”；技术信息可以记录数据库错误、文件路径和上下文，用于调试。

不要向最终用户弹出一大段驱动内部错误，也不要为了界面简洁而完全丢弃技术信息。

## 6. Service 组织完整业务流程

`AssignmentService` 可以继承 QObject，并在数据变化后发出统一信号：

```cpp
class AssignmentService final : public QObject {
    Q_OBJECT

public:
    explicit AssignmentService(
        AssignmentRepository *repository,
        QObject *parent = nullptr);

    OperationResult createAssignment(
        qint64 courseId,
        const QString &title,
        const QDate &deadline);

    QVector<Assignment> assignments() const;
    AssignmentStatistics statistics() const;

signals:
    void assignmentsChanged();

private:
    AssignmentRepository *repository_;
};
```

创建流程：

```cpp
OperationResult AssignmentService::createAssignment(
    qint64 courseId,
    const QString &title,
    const QDate &deadline) {
    const QString normalizedTitle = title.trimmed();

    if (normalizedTitle.isEmpty()) {
        return OperationResult::fail(tr("作业标题不能为空"));
    }

    if (!deadline.isValid()) {
        return OperationResult::fail(tr("请选择有效的截止日期"));
    }

    QString error;
    if (!repository_->add(
            courseId, normalizedTitle, deadline, &error)) {
        return OperationResult::fail(
            tr("保存作业失败，请稍后重试"), error);
    }

    emit assignmentsChanged();
    return OperationResult::ok(tr("作业已保存"));
}
```

业务规则和数据写入全部成功后才发出变化信号。

## 7. 让一个信号刷新所有依赖页面

主窗口只建立一次连接：

```cpp
connect(assignmentService_,
        &AssignmentService::assignmentsChanged,
        this,
        [this] {
    assignmentModel_->setAssignments(
        assignmentService_->assignments());

    const auto statistics =
        assignmentService_->statistics();
    ui->completionRing->setProgress(
        statistics.completionRate());
    ui->totalLabel->setText(
        QString::number(statistics.total));
});
```

新增、修改、删除和导入都通过 Service 完成，因此不需要在每个操作后复制一套刷新代码。

如果刷新代价较高，可以进一步拆成更具体的信号，但 MVP 阶段先保证一致性和清晰性。

## 8. 统一新增流程

主窗口槽函数只负责协调：

```cpp
void MainWindow::openAssignmentDialog() {
    AssignmentDialog dialog(courseService_->courses(), this);

    if (dialog.exec() != QDialog::Accepted) {
        return;
    }

    const OperationResult result =
        assignmentService_->createAssignment(
            dialog.courseId(),
            dialog.title(),
            dialog.deadline());

    if (!result.success) {
        qCWarning(lcAssignment)
            << "Create assignment failed:"
            << result.technicalMessage;
        QMessageBox::warning(
            this, tr("保存失败"), result.userMessage);
        return;
    }

    statusBar()->showMessage(result.userMessage, 4000);
}
```

这里的 MainWindow 不知道 SQL 内容，也不直接修改 TableModel。它只收集输入、调用 Service、显示结果。

## 9. 应用启动顺序

稳定的启动流程可以写成：

```text
创建 QApplication
    → 设置组织名、应用名和版本
    → 加载资源与基础样式
    → 确定应用数据目录
    → 打开数据库并执行迁移
    → 创建 Repository 与 Service
    → 创建 MainWindow 并注入依赖
    → 恢复设置
    → 查询初始数据
    → 显示窗口
```

数据库无法打开属于关键错误。此时应显示一条明确消息并终止启动，而不是打开一个无法保存数据的主窗口。

## 10. 为空白、加载和错误设计状态

一个页面至少要考虑：

| 状态 | 用户看到的内容 |
| --- | --- |
| Loading | 进度提示，避免重复操作 |
| Empty | 为什么为空，以及下一步按钮 |
| Content | 正常列表和统计 |
| Error | 简短原因、重试或修复入口 |

可以使用 QStackedWidget 在这些状态间切换。不要让空表格、禁用按钮和失败状态看起来完全一样。

例如课程为空时，作业对话框不应只显示一个空 QComboBox，而应提示“请先创建课程”并提供跳转入口。

## 11. 建立可追踪日志

使用 QLoggingCategory 区分模块：

```cpp
#include <QLoggingCategory>

Q_LOGGING_CATEGORY(lcDatabase, "course.database")
Q_LOGGING_CATEGORY(lcAssignment, "course.assignment")
```

记录信息：

```cpp
qCInfo(lcDatabase) << "Database opened:" << databasePath;
qCWarning(lcAssignment)
    << "Import skipped duplicate title:" << title;
qCCritical(lcDatabase)
    << "Schema migration failed:" << error;
```

日志中不要记录密码、令牌或其他敏感信息。课程项目至少应保留关键初始化、导入导出和数据库错误，便于现场排查。

## 12. 整合导入导出

建议采用下面的流程：

```text
选择文件
    → 读取并解析
    → 完整验证
    → 展示导入摘要
    → 用户确认
    → 开启事务写入
    → 提交或回滚
    → 发出 assignmentsChanged
```

摘要可以显示：新增多少条、跳过多少条、发现多少条错误。不要解析一条就立即写一条，否则中途失败后很难恢复。

导出文件应包含：

- 格式版本；
- 导出时间；
- 应用版本；
- 课程与作业数据；
- 明确的 UTF-8 编码。

## 13. 可用性与一致性检查

MVP 不需要华丽，但要易用：

- 同类按钮使用一致文案和位置；
- 删除等危险操作需要确认；
- 默认焦点落在第一个输入控件；
- Tab 顺序符合阅读顺序；
- Enter 接受对话框，Esc 取消；
- 错误消息靠近问题或明确指出字段；
- 所有重要操作都能通过键盘完成；
- 不只用颜色区分“已完成”和“未完成”。

QSS 只负责视觉表达，不能掩盖控件禁用、焦点缺失或信息层级问题。

## 14. 准备完整演示流程

推荐演示脚本：

1. 首次启动并展示空状态；
2. 创建两门课程；
3. 新增三条不同截止日期的作业；
4. 搜索并按日期排序；
5. 标记一条作业完成，观察统计圆环更新；
6. 修改并删除一条作业；
7. 导出 JSON；
8. 关闭并重启程序，确认数据保留；
9. 演示一次非法输入和一次取消操作。

提前准备固定数据和操作顺序，能让演示集中体现软件能力，而不是现场思考输入什么。

## 15. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 将需求分为 Must、Should、Could、Won't |
| 第 2 步 | 为每个 Must 功能编写用户故事和验收条件 |
| 第 3 步 | 整理 UI、Service、Repository 和 Domain 目录 |
| 第 4 步 | 统一 OperationResult 与日志策略 |
| 第 5 步 | 用 assignmentsChanged 串联列表与统计刷新 |
| 第 6 步 | 补齐空白、加载、错误和取消状态 |
| 第 7 步 | 按固定脚本完成一次从头到尾演示 |

## 16. 常见问题

### 功能很多，但没有一条流程能完整走通

停止新增页面，按用户故事逐条打通输入、保存、显示、重启和错误处理。先保证 Must 功能闭环。

### Service 和 MainWindow 都在验证同一规则

控件可以做即时提示，但最终业务规则由 Service 统一判断。避免不同入口得到不同结果。

### 数据保存成功，统计没有刷新

确认所有写操作都经过 Service，并且成功后统一发出变化信号。不要依赖某个按钮槽函数手工刷新。

### 错误信息只有“失败”

面向用户说明可以采取的动作，同时把底层原因写入日志。错误既不能过度暴露，也不能完全不可诊断。

### 为了赶进度删除所有错误检查

课程项目最容易在空数据、重复输入、取消文件选择和数据库路径异常处出问题。宁可减少次要功能，也不要删除主流程保护。

## 17. 本章验收清单

- [ ] Must 功能范围已经冻结；
- [ ] 每个核心功能都有可验证的用户故事；
- [ ] UI 不直接执行 SQL；
- [ ] Repository 不显示对话框；
- [ ] Service 统一处理业务规则；
- [ ] 数据变更通过统一信号刷新列表与统计；
- [ ] 启动失败不会进入不可用主窗口；
- [ ] 空白、加载、内容和错误状态可以区分；
- [ ] 日志保留关键技术上下文；
- [ ] 导入操作能够验证并回滚；
- [ ] 完整演示流程可以连续执行；
- [ ] 程序重启后数据和设置保持正确。

得到稳定 MVP 后，下一章不再新增业务功能，而是通过 Qt Test、模型测试、异常场景和性能检查，把它推进为发布候选版本。

官方参考：[QLoggingCategory](https://doc.qt.io/qt-6/qloggingcategory.html) ｜ [QStackedWidget](https://doc.qt.io/qt-6/qstackedwidget.html) ｜ [QMessageBox](https://doc.qt.io/qt-6/qmessagebox.html)

上一篇：[第 5 章：绘图、网络与多线程的取舍]({% post_url 2026-09-02-qt-course-project-week-5-notes %}) ｜ 下一篇：[第 7 章：测试、异常处理与发布候选]({% post_url 2026-09-02-qt-course-project-week-7-notes %})
