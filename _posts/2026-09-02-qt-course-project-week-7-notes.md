---
layout: post
title: "Qt 课程项目第 7 章：测试、异常处理与发布候选"
date: 2026-09-02 00:35:00 +0800
categories: [学习]
tags: [Qt, C++, Qt Test, 软件测试, 调试]
series: qt
series_order: 7
---

在[第六章]({% post_url 2026-09-02-qt-course-project-week-6-notes %})中，课程与作业管理系统已经成为可以完整演示的 MVP。本章停止新增业务功能，通过 Qt Test、模型测试、异常场景和性能检查，把“能够运行”推进为“可以稳定交付”。

测试不是在项目完成后随便点几下。它需要明确输入、预期结果和失败证据，并且能够在每次修改后重复执行。

## 1. 本章目标

完成本章后，应当能够：

- 区分单元测试、集成测试和界面流程测试；
- 使用 Qt Test 与 CTest；
- 编写数据驱动测试；
- 使用 QSignalSpy 验证信号；
- 使用 QAbstractItemModelTester 检查模型约定；
- 为 SQLite Repository 建立隔离测试库；
- 建立异常场景测试矩阵；
- 使用日志、断点和最小复现定位缺陷；
- 形成可发布候选版本。

## 2. 测试层次

| 层次 | 测试对象 | 特点 |
| --- | --- | --- |
| 单元测试 | Validator、Service、Model | 快速、定位明确 |
| 集成测试 | Repository 与 SQLite | 验证真实模块协作 |
| 界面流程测试 | 新增、搜索、导入、重启 | 接近用户操作 |
| 部署测试 | 打包后的独立目录 | 检查 DLL、插件和路径 |

课程项目不需要追求一个漂亮但没有意义的覆盖率数字。优先覆盖业务规则、数据写入、模型边界和最容易出错的异常路径。

## 3. 在 CMake 中加入 Qt Test

将可测试的业务代码放进独立库，界面程序和测试程序共同链接它：

```cmake
find_package(Qt6 REQUIRED COMPONENTS
    Core
    Widgets
    Sql
    Test
)

add_library(course_core STATIC
    src/domain/assignment.h
    src/services/assignmentvalidator.cpp
    src/services/assignmentvalidator.h
    src/services/assignmentservice.cpp
    src/services/assignmentservice.h
    src/data/assignmentrepository.cpp
    src/data/assignmentrepository.h
    src/models/assignmenttablemodel.cpp
    src/models/assignmenttablemodel.h
)

target_link_libraries(course_core PUBLIC
    Qt6::Core
    Qt6::Sql
)

target_include_directories(course_core PUBLIC src)

target_link_libraries(course_manager PRIVATE
    course_core
    Qt6::Widgets
)

include(CTest)

if(BUILD_TESTING)
    qt_add_executable(test_assignment_validator
        tests/tst_assignmentvalidator.cpp
    )

    target_link_libraries(test_assignment_validator PRIVATE
        course_core
        Qt6::Test
    )

    add_test(
        NAME assignment_validator
        COMMAND test_assignment_validator
    )
endif()
```

配置、构建和运行测试：

```powershell
cmake -S . -B build -DBUILD_TESTING=ON
cmake --build build --config Debug
ctest --test-dir build -C Debug --output-on-failure
```

多配置生成器需要通过 `-C Debug` 告诉 CTest 使用哪个配置。

## 4. 数据驱动的输入验证测试

Qt Test 可以把多组输入与同一段测试逻辑分开：

```cpp
#include <QtTest>

#include "services/assignmentvalidator.h"

class TestAssignmentValidator final : public QObject {
    Q_OBJECT

private slots:
    void validate_data();
    void validate();
};

void TestAssignmentValidator::validate_data() {
    QTest::addColumn<QString>("title");
    QTest::addColumn<QDate>("deadline");
    QTest::addColumn<bool>("expectedValid");

    QTest::newRow("valid")
        << QStringLiteral("完成数据库作业")
        << QDate(2026, 9, 20)
        << true;

    QTest::newRow("blank-title")
        << QStringLiteral("   ")
        << QDate(2026, 9, 20)
        << false;

    QTest::newRow("invalid-date")
        << QStringLiteral("完成数据库作业")
        << QDate()
        << false;
}

void TestAssignmentValidator::validate() {
    QFETCH(QString, title);
    QFETCH(QDate, deadline);
    QFETCH(bool, expectedValid);

    const QString error =
        AssignmentValidator::validate(title, deadline);

    QCOMPARE(error.isEmpty(), expectedValid);
}

QTEST_APPLESS_MAIN(TestAssignmentValidator)
#include "tst_assignmentvalidator.moc"
```

测试名称应描述场景，而不是写成 `test1`、`test2`。测试失败时，名称本身就是定位线索。

## 5. 使用 QSignalSpy 验证状态通知

如果 Service 保存成功后应发出 `assignmentsChanged`，可以这样验证：

```cpp
QSignalSpy changedSpy(
    &service,
    &AssignmentService::assignmentsChanged);

const OperationResult result = service.createAssignment(
    courseId,
    QStringLiteral("复习 Qt Model/View"),
    QDate(2026, 9, 25));

QVERIFY(result.success);
QCOMPARE(changedSpy.count(), 1);
```

还要测试失败时不应发出信号：

```cpp
const OperationResult result = service.createAssignment(
    courseId,
    QStringLiteral("   "),
    QDate());

QVERIFY(!result.success);
QCOMPARE(changedSpy.count(), 0);
```

测试不仅检查返回值，还要检查可观察副作用是否准确发生一次。

## 6. 使用 QAbstractItemModelTester

自定义模型需要满足大量索引和通知约定。Qt Test 提供模型测试器：

```cpp
#include <QAbstractItemModelTester>

AssignmentTableModel model;

QAbstractItemModelTester tester(
    &model,
    QAbstractItemModelTester::FailureReportingMode::QtTest);

model.addAssignment({
    1,
    QStringLiteral("数据库原理"),
    QStringLiteral("事务恢复实验"),
    QDate(2026, 9, 30),
    false
});

QCOMPARE(model.rowCount(), 1);
QCOMPARE(
    model.index(0, AssignmentTableModel::TitleColumn)
        .data(Qt::DisplayRole).toString(),
    QStringLiteral("事务恢复实验"));
```

如果 `beginInsertRows()`、父索引或行列范围错误，模型测试器能够提供比“表格偶尔崩溃”更直接的证据。

## 7. 隔离 SQLite 集成测试

测试不应访问真实用户数据库。可以使用 SQLite 内存数据库，并为每个测试连接指定唯一名称：

```cpp
const QString connectionName =
    QStringLiteral("test-%1")
        .arg(QUuid::createUuid().toString(QUuid::WithoutBraces));

QSqlDatabase database = QSqlDatabase::addDatabase(
    "QSQLITE", connectionName);
database.setDatabaseName(":memory:");

QVERIFY(database.open());
```

测试内容至少包括：

- 首次创建表；
- 新增并查询；
- 更新完成状态；
- 删除作业；
- 重复课程或作业被拒绝；
- 外键删除行为；
- 事务失败后回滚。

清理连接时，要先销毁所有使用它的 QSqlQuery 和 QSqlDatabase 副本，再调用：

```cpp
database.close();
database = {};
QSqlDatabase::removeDatabase(connectionName);
```

否则 Qt 会提示连接仍在使用。

## 8. 手工界面测试矩阵

部分交互仍适合通过明确的人工用例验证：

| 编号 | 场景 | 操作 | 预期结果 |
| --- | --- | --- | --- |
| UI-01 | 空数据启动 | 删除测试库后启动 | 显示空状态和新增入口 |
| UI-02 | 新增作业 | 输入合法内容并确定 | 列表与统计同步更新 |
| UI-03 | 空标题 | 只输入空格并确定 | 阻止保存并定位输入框 |
| UI-04 | 取消新增 | 输入后点击取消 | 数据库不产生新记录 |
| UI-05 | 搜索 | 输入课程或标题关键字 | 只显示匹配记录 |
| UI-06 | 排序后删除 | 排序并删除选中行 | 删除正确数据库记录 |
| UI-07 | 重启恢复 | 修改数据后重启 | 数据和设置保持一致 |
| UI-08 | 导入损坏 JSON | 选择无效文件 | 提示错误且数据库不变 |

每次修复缺陷后，把能够复现它的步骤加入测试矩阵，防止同类问题再次出现。

## 9. 异常场景清单

除了正常路径，还要主动测试：

- 应用数据目录不可写；
- 数据库文件被占用或损坏；
- SQLite 驱动缺失；
- 配置值类型或范围错误；
- JSON 为空、截断或字段缺失；
- 导入数据重复；
- 文件选择被取消；
- 网络离线、超时或返回无效 JSON；
- 工作线程失败或用户取消；
- 模型为空时执行编辑和删除；
- 用户连续快速点击同一操作。

测试异常时不仅看程序是否崩溃，还要检查数据库有没有被部分修改、界面能否恢复操作、错误信息是否清楚。

## 10. 日志与调试流程

遇到问题时使用固定流程：

1. 写出最短复现步骤；
2. 记录输入、环境和实际结果；
3. 查看日志中的第一个异常；
4. 在业务入口和失败分支设置断点；
5. 检查模型索引、数据库 ID 和线程归属；
6. 缩小到最少对象和最少数据；
7. 修复后补充自动或人工测试；
8. 运行完整测试集确认没有回归。

不要同时修改多个可能原因。一次只验证一个假设，才能知道是哪项改动真正解决了问题。

## 11. 性能与响应性检查

课程项目的常见性能问题并不是算法极限，而是：

- 每次输入一个字符就查询整个数据库；
- 同一个变化触发多次全量刷新；
- 在主线程读取巨大文件；
- 模型更新时错误地反复 reset；
- 表格一次加载远超实际需要的数据；
- 日志在循环中输出大量内容。

可以使用 QElapsedTimer 测量关键操作：

```cpp
QElapsedTimer timer;
timer.start();

const QVector<Assignment> items = repository.all();

qCInfo(lcAssignment)
    << "Loaded" << items.size()
    << "assignments in" << timer.elapsed() << "ms";
```

先测量再优化。不要为了理论上的性能牺牲清晰架构，也不要把短暂的简单查询随意移到线程。

## 12. 发布候选版本标准

可以为准备发布的版本打标签，例如 `v0.9.0-rc1`。它应该满足：

- Must 功能全部完成；
- 自动测试全部通过；
- 手工主流程测试通过；
- 没有已知崩溃和数据损坏问题；
- 没有未处理的编译警告；
- Debug 和 Release 都能构建；
- 默认数据与真实个人数据已经分离；
- 日志不包含敏感信息；
- 版本号、README 和变更记录一致。

发布候选阶段只修复缺陷，不继续调整大范围架构或加入新模块。

## 13. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 把可测试业务代码提取为 course_core |
| 第 2 步 | 配置 Qt Test、CTest 和测试目标 |
| 第 3 步 | 为输入验证编写数据驱动测试 |
| 第 4 步 | 用 QSignalSpy 测试 Service 信号 |
| 第 5 步 | 用 QAbstractItemModelTester 检查模型 |
| 第 6 步 | 用内存 SQLite 测试 Repository 和事务 |
| 第 7 步 | 完成异常矩阵并生成发布候选版本 |

## 14. 常见问题

### 测试只能在 Qt Creator 中运行

确认测试已经通过 `add_test()` 注册，并使用 CTest 从构建目录执行。可重复的命令行测试更适合最终验收。

### 测试修改了真实数据库

Repository 不应在内部硬编码生产路径。测试时注入命名的内存连接或临时数据库文件。

### QSignalSpy 一直为零

检查信号是否在成功分支发出、对象是否为同一实例，以及操作是否因为验证失败提前返回。

### 模型测试器报告行数错误

检查 `beginInsertRows()` 和 `beginRemoveRows()` 的范围，以及数据容器修改发生在 begin 与 end 之间。

### 手工测试每次结果不同

固定初始数据、操作步骤和预期结果。测试开始前明确恢复干净数据库还是使用迁移后的旧数据库。

## 15. 本章验收清单

- [ ] 业务代码可以脱离 MainWindow 测试；
- [ ] CTest 能发现并执行全部测试；
- [ ] Validator 有正常和边界输入测试；
- [ ] Service 的成功与失败信号数量正确；
- [ ] 自定义 Model 通过模型测试器检查；
- [ ] Repository 使用隔离 SQLite 测试；
- [ ] 事务回滚经过验证；
- [ ] 手工测试矩阵记录了实际结果；
- [ ] 空数据、损坏文件和取消操作均已测试；
- [ ] 主线程没有明显长时间冻结；
- [ ] Release 构建没有新增警告；
- [ ] 发布候选版本可以稳定完成演示流程。

下一章将把发布候选版本构建成独立目录，检查 Qt DLL、平台插件和 SQLite 驱动，并准备最终文档与答辩演示。

官方参考：[Qt Test](https://doc.qt.io/qt-6/qttest-index.html) ｜ [Qt Test 概览](https://doc.qt.io/qt-6/qtest-overview.html) ｜ [QAbstractItemModelTester](https://doc.qt.io/qt-6/qabstractitemmodeltester.html)

上一篇：[第 6 章：功能整合与 MVP]({% post_url 2026-09-02-qt-course-project-week-6-notes %}) ｜ 下一篇：[第 8 章：Release、部署与课程答辩]({% post_url 2026-09-02-qt-course-project-week-8-notes %})
