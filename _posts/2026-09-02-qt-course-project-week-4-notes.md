---
layout: post
title: "Qt 课程项目第 4 章：文件、设置与 SQLite 数据闭环"
date: 2026-09-02 00:20:00 +0800
categories: [学习]
tags: [Qt, C++, SQLite, Qt SQL, JSON]
series: qt
series_order: 4
---

在[第三章]({% post_url 2026-09-02-qt-course-project-week-3-notes %})中，我们通过自定义 Model/View 完成了内存中的作业管理流程。本章将把数据保存到 SQLite，同时用 QSettings 保存界面偏好，用 JSON 完成可读的导入导出。

本章结束后，用户关闭程序再重新打开，课程和作业数据仍然存在。输入、校验、写入、查询、显示、修改和删除将形成完整闭环。

## 1. 本章目标

完成本章后，应当能够：

- 为不同数据选择合适的持久化方式；
- 使用 QStandardPaths 确定应用数据目录；
- 使用 QFile、QSaveFile 和 JSON；
- 使用 QSettings 保存窗口与用户偏好；
- 使用 Qt SQL 连接 SQLite；
- 创建数据库表、索引和外键；
- 使用预处理语句完成增删改查；
- 使用事务保证多步操作的一致性；
- 把 Repository 与界面逻辑分离。

## 2. 三种存储方式各司其职

| 数据 | 推荐方式 | 示例 |
| --- | --- | --- |
| 用户偏好 | QSettings | 窗口大小、上次页面、主题 |
| 交换或备份文件 | JSON、CSV | 导入导出、调试样例 |
| 结构化业务数据 | SQLite | 课程、作业、状态、日期 |

不要把全部数据都塞进 QSettings，也不要为了保存几个偏好而建立数据库表。存储方式应该与数据的结构、规模和查询需求匹配。

## 3. 确定应用数据目录

运行目录在开发、打包和安装后可能不同，因此数据库不应依赖当前工作目录。可以使用 QStandardPaths：

```cpp
#include <QDir>
#include <QStandardPaths>

QString applicationDataDirectory() {
    const QString path = QStandardPaths::writableLocation(
        QStandardPaths::AppDataLocation);

    QDir directory;
    if (!directory.mkpath(path)) {
        return {};
    }

    return path;
}
```

在 `main()` 创建 QApplication 后，先设置组织名和应用名：

```cpp
QCoreApplication::setOrganizationName("ListenSnowCourse");
QCoreApplication::setApplicationName("CourseManager");
```

它们会影响 QSettings 和部分标准路径。名称一旦用于正式项目，就不要随意修改，否则程序可能找不到旧配置。

## 4. 使用 QSettings 保存界面状态

保存主窗口几何信息和上次打开页面：

```cpp
void MainWindow::saveSettings() {
    QSettings settings;
    settings.setValue("window/geometry", saveGeometry());
    settings.setValue("navigation/page",
                      ui->pageStack->currentIndex());
    settings.setValue("assignment/filter",
                      ui->searchEdit->text());
}
```

程序启动时恢复：

```cpp
void MainWindow::restoreSettings() {
    QSettings settings;

    restoreGeometry(
        settings.value("window/geometry").toByteArray());

    const int page = settings.value(
        "navigation/page", 0).toInt();

    if (page >= 0 && page < ui->pageStack->count()) {
        ui->pageStack->setCurrentIndex(page);
    }

    ui->searchEdit->setText(
        settings.value("assignment/filter").toString());
}
```

恢复来自旧版本的设置时要检查范围。不能假设配置值永远合法。

## 5. 为 SQLite 增加 Qt SQL 模块

修改 CMake：

```cmake
find_package(Qt6 REQUIRED COMPONENTS Widgets Sql)

target_link_libraries(course_manager PRIVATE
    Qt6::Widgets
    Qt6::Sql
)
```

Qt SQL 使用驱动插件访问具体数据库。SQLite 驱动名为 `QSQLITE`。开发环境中可以检查：

```cpp
qInfo() << "SQL drivers:" << QSqlDatabase::drivers();
```

如果列表中没有 `QSQLITE`，应检查 Qt 安装组件或 Kit，而不是立即重写数据库代码。

## 6. 封装数据库初始化

`databasemanager.h`：

```cpp
#pragma once

#include <QSqlDatabase>
#include <QString>

class DatabaseManager final {
public:
    bool open(QString *errorMessage = nullptr);
    QSqlDatabase database() const;

private:
    bool createSchema(QString *errorMessage);

    QSqlDatabase database_;
};
```

核心实现：

```cpp
#include "databasemanager.h"

#include <QDir>
#include <QSqlError>
#include <QSqlQuery>
#include <QStandardPaths>

bool DatabaseManager::open(QString *errorMessage) {
    const QString dataDirectory =
        QStandardPaths::writableLocation(
            QStandardPaths::AppDataLocation);

    if (!QDir().mkpath(dataDirectory)) {
        if (errorMessage) {
            *errorMessage = QObject::tr("无法创建数据目录");
        }
        return false;
    }

    database_ = QSqlDatabase::addDatabase("QSQLITE");
    database_.setDatabaseName(
        dataDirectory + "/course-manager.db");

    if (!database_.open()) {
        if (errorMessage) {
            *errorMessage = database_.lastError().text();
        }
        return false;
    }

    QSqlQuery pragma(database_);
    if (!pragma.exec("PRAGMA foreign_keys = ON")) {
        if (errorMessage) {
            *errorMessage = pragma.lastError().text();
        }
        return false;
    }

    return createSchema(errorMessage);
}

QSqlDatabase DatabaseManager::database() const {
    return database_;
}
```

## 7. 设计数据库结构

课程与作业之间是一对多关系：

```text
courses
┌────────────┬──────────────┐
│ id         │ INTEGER PK   │
│ name       │ TEXT UNIQUE  │
└────────────┴──────────────┘
       1
       │
       N
assignments
┌────────────┬──────────────┐
│ id         │ INTEGER PK   │
│ course_id  │ INTEGER FK   │
│ title      │ TEXT         │
│ due_date   │ TEXT         │
│ completed  │ INTEGER      │
└────────────┴──────────────┘
```

创建表时每次 `exec()` 只执行一条 SQL：

```cpp
bool DatabaseManager::createSchema(QString *errorMessage) {
    const QStringList statements = {
        QStringLiteral(R"SQL(
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        )SQL"),
        QStringLiteral(R"SQL(
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
                    CHECK (completed IN (0, 1)),
                UNIQUE (course_id, title),
                FOREIGN KEY (course_id)
                    REFERENCES courses(id)
                    ON DELETE CASCADE
            )
        )SQL"),
        QStringLiteral(R"SQL(
            CREATE INDEX IF NOT EXISTS
                idx_assignments_due_date
            ON assignments(due_date)
        )SQL")
    };

    for (const QString &statement : statements) {
        QSqlQuery query(database_);
        if (!query.exec(statement)) {
            if (errorMessage) {
                *errorMessage = query.lastError().text();
            }
            return false;
        }
    }

    return true;
}
```

日期以 `yyyy-MM-dd` 保存为文本时，可以正确进行字典序排序。更复杂的时间场景还要明确时区和精度。

## 8. 使用 Repository 执行参数化查询

界面不应拼接 SQL。可以建立 `AssignmentRepository`，由它接收 QSqlDatabase 并执行查询。

新增作业：

```cpp
bool AssignmentRepository::add(
    qint64 courseId,
    const QString &title,
    const QDate &deadline,
    QString *errorMessage) {
    QSqlQuery query(database_);
    query.prepare(R"SQL(
        INSERT INTO assignments
            (course_id, title, due_date, completed)
        VALUES
            (:course_id, :title, :due_date, :completed)
    )SQL");

    query.bindValue(":course_id", courseId);
    query.bindValue(":title", title.trimmed());
    query.bindValue(":due_date",
                    deadline.toString("yyyy-MM-dd"));
    query.bindValue(":completed", false);

    if (!query.exec()) {
        if (errorMessage) {
            *errorMessage = query.lastError().text();
        }
        return false;
    }

    return true;
}
```

永远不要这样拼接用户输入：

```cpp
// 错误示例：既容易出错，也存在 SQL 注入风险。
query.exec("INSERT INTO assignments(title) VALUES('" + title + "')");
```

查询列表时使用 JOIN 获取课程名称：

```sql
SELECT
    assignments.id,
    courses.name,
    assignments.title,
    assignments.due_date,
    assignments.completed
FROM assignments
JOIN courses ON courses.id = assignments.course_id
ORDER BY assignments.due_date, assignments.id;
```

Repository 把查询结果转换为 `QVector<Assignment>`，再交给上一章的 AssignmentTableModel。这样 View 不需要知道数据来自内存、SQLite 还是其他来源。

## 9. 更新与删除

修改完成状态：

```cpp
QSqlQuery query(database_);
query.prepare(R"SQL(
    UPDATE assignments
    SET completed = :completed
    WHERE id = :id
)SQL");

query.bindValue(":completed", completed);
query.bindValue(":id", assignmentId);

if (!query.exec() || query.numRowsAffected() != 1) {
    // 记录 query.lastError()，并向调用方返回失败。
}
```

删除时使用稳定的数据库 ID，而不是表格行号：

```cpp
QSqlQuery query(database_);
query.prepare("DELETE FROM assignments WHERE id = :id");
query.bindValue(":id", assignmentId);
```

排序和过滤会改变显示行号，但不会改变数据库 ID。业务层始终使用 ID 定位实体。

## 10. 使用事务保护多步操作

例如导入一个课程及其多条作业时，应当全部成功或全部失败：

```cpp
if (!database_.transaction()) {
    return false;
}

bool success = insertCourse(course);

for (const Assignment &assignment : assignments) {
    if (!success || !insertAssignment(assignment)) {
        success = false;
        break;
    }
}

if (success) {
    success = database_.commit();
} else {
    database_.rollback();
}
```

事务开始后再创建和执行相关查询。发生错误时保留原始数据库状态，并把具体错误记录到日志。

## 11. 使用 JSON 导出备份

JSON 适合可读备份和数据交换。使用 QSaveFile 可以避免写到一半留下损坏文件：

```cpp
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QSaveFile>

bool exportAssignments(const QString &filePath,
                       const QVector<Assignment> &items) {
    QJsonArray array;

    for (const Assignment &item : items) {
        array.append(QJsonObject{
            {"id", item.id},
            {"course", item.courseName},
            {"title", item.title},
            {"deadline", item.deadline.toString(Qt::ISODate)},
            {"completed", item.completed}
        });
    }

    const QJsonObject root{
        {"formatVersion", 1},
        {"assignments", array}
    };

    QSaveFile file(filePath);
    if (!file.open(QIODevice::WriteOnly)) {
        return false;
    }

    file.write(QJsonDocument(root).toJson(
        QJsonDocument::Indented));
    return file.commit();
}
```

导入时要检查：

- JSON 是否能成功解析；
- 根对象和字段是否存在；
- `formatVersion` 是否受支持；
- 日期和布尔值类型是否正确；
- 重复数据采用跳过、覆盖还是报错策略；
- 导入失败时是否回滚事务。

不能因为文件扩展名是 `.json` 就信任其内容。

## 12. 刷新模型的统一流程

一次新增操作可以组织为：

```text
AssignmentDialog 获取输入
    → AssignmentService 校验业务规则
    → AssignmentRepository 写入 SQLite
    → Repository 重新查询列表
    → AssignmentTableModel::setAssignments()
    → QTableView 自动刷新
```

数据库写入失败时不要先更新界面。只有持久化成功后，才刷新模型并显示成功状态。

## 13. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 设置应用名称并确定 AppDataLocation |
| 第 2 步 | 使用 QSettings 保存和恢复界面状态 |
| 第 3 步 | 链接 Qt SQL 并检查 QSQLITE 驱动 |
| 第 4 步 | 创建课程表、作业表、外键和索引 |
| 第 5 步 | 实现 Repository 的查询和增删改操作 |
| 第 6 步 | 将数据库查询结果接入 TableModel |
| 第 7 步 | 完成 JSON 导入导出与重启测试 |

## 14. 常见问题

### 提示 `QSQLITE driver not loaded`

先检查 `QSqlDatabase::drivers()`。开发环境缺少驱动时检查 Qt 安装和 Kit；发布环境则检查 `sqldrivers/qsqlite.dll` 是否随程序部署。

### 数据库能打开，但没有创建到预期位置

输出 `database_.databaseName()` 和 QStandardPaths 的结果确认实际路径，不要根据当前工作目录猜测。

### 外键没有生效

SQLite 连接打开后执行 `PRAGMA foreign_keys = ON`，并检查执行结果。每个数据库连接都需要正确配置。

### 中文或引号导致 SQL 报错

不要拼接 SQL 字符串。使用 `prepare()`、`bindValue()` 和参数占位符。

### 表格显示旧数据

数据库成功写入后重新查询 Repository，并通过模型通知接口更新数据。不要同时维护多个互不知情的缓存副本。

### 多线程访问数据库出现随机问题

QSqlDatabase 连接具有线程归属。不要把主线程创建的连接直接拿到工作线程使用；需要时在目标线程建立独立连接。

## 15. 本章验收清单

- [ ] 数据库位于可写的应用数据目录；
- [ ] 首次启动可以自动创建表和索引；
- [ ] `QSQLITE` 驱动可用；
- [ ] 所有用户输入通过绑定参数写入 SQL；
- [ ] 课程和作业具有正确外键关系；
- [ ] 新增、查询、修改、删除均能刷新表格；
- [ ] 程序重启后数据仍然存在；
- [ ] 多步导入失败时可以回滚；
- [ ] QSettings 能保存并恢复界面偏好；
- [ ] JSON 导出文件包含格式版本；
- [ ] 数据库错误能够记录并显示为用户可理解的信息。

完成这一章后，课程项目已经具备可靠的数据闭环。下一章将根据需求选择绘图、网络和多线程能力，并为默认项目实现一个真正有辨识度的特色功能。

官方参考：[QSettings](https://doc.qt.io/qt-6/qsettings.html) ｜ [Qt JSON](https://doc.qt.io/qt-6/json.html) ｜ [QSqlDatabase](https://doc.qt.io/qt-6/qsqldatabase.html) ｜ [QSqlQuery](https://doc.qt.io/qt-6/qsqlquery.html)

上一篇：[第 3 章：事件、输入校验与 Model/View]({% post_url 2026-09-02-qt-course-project-week-3-notes %}) ｜ 下一篇：[第 5 章：绘图、网络与多线程的取舍]({% post_url 2026-09-02-qt-course-project-week-5-notes %})
