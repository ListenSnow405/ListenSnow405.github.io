---
layout: post
title: "Qt 课程项目第 3 章：事件、输入校验与 Model/View"
date: 2026-09-02 00:15:00 +0800
categories: [学习]
tags: [Qt, C++, 事件系统, Model-View, 软件架构]
series: qt
series_order: 3
---

在[第二章]({% post_url 2026-09-02-qt-course-project-week-2-notes %})中，我们完成了课程与作业管理系统的界面原型。本章将处理真实交互：阻止非法输入、响应关闭和键盘事件，并通过 Model/View 将作业数据与表格显示分离。

本章暂时仍然使用内存数据。这样可以先把界面交互和模型接口做正确，再在下一章替换为 SQLite 数据源。

## 1. 本章目标

完成本章后，应当能够：

- 区分事件、信号和槽；
- 重写关闭事件并正确接受或忽略；
- 使用事件过滤器统一处理局部交互；
- 使用 QValidator 和业务规则验证输入；
- 理解 Model、View、Delegate 的职责；
- 实现一个 QAbstractTableModel；
- 使用 QSortFilterProxyModel 搜索和排序；
- 把界面、领域数据和业务逻辑初步分层。

## 2. 事件与信号有什么区别

信号表示 QObject 的状态或行为发生了变化，例如按钮被点击、文本发生变化或网络请求结束。事件则是由 Qt 事件系统投递的 QEvent 对象，例如鼠标、键盘、绘制、窗口关闭和尺寸变化。

典型流程如下：

```text
操作系统或 Qt 产生事件
    → QApplication 事件循环
    → QObject::event()
    → closeEvent()、keyPressEvent() 等具体处理函数
```

处理按钮点击通常使用信号与槽；需要拦截窗口关闭、修改特定按键行为或观察另一个控件的事件时，再使用事件处理函数或事件过滤器。

不要把所有交互都塞进 `event()`。Qt 已经提供具体事件函数时，优先重写对应函数。

## 3. 关闭窗口前确认未保存数据

假设窗口维护一个 `dirty_` 标记，数据变化后设为 `true`，保存后恢复为 `false`。可以重写关闭事件：

```cpp
#include <QCloseEvent>
#include <QMessageBox>

void MainWindow::closeEvent(QCloseEvent *event) {
    if (!dirty_) {
        event->accept();
        return;
    }

    const auto answer = QMessageBox::question(
        this,
        tr("退出程序"),
        tr("还有未保存的修改，确定退出吗？"),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (answer == QMessageBox::Yes) {
        event->accept();
    } else {
        event->ignore();
    }
}
```

事件是否被接受会影响后续行为。仅仅弹出 QMessageBox 而不处理 `accept()` 和 `ignore()`，容易让退出逻辑与预期不一致。

## 4. 使用事件过滤器处理搜索框

如果希望在搜索框中按 Esc 清空内容，可以让主窗口观察搜索框的事件：

```cpp
ui->searchEdit->installEventFilter(this);
```

然后重写 `eventFilter()`：

```cpp
#include <QEvent>
#include <QKeyEvent>

bool MainWindow::eventFilter(QObject *watched, QEvent *event) {
    if (watched == ui->searchEdit && event->type() == QEvent::KeyPress) {
        auto *keyEvent = static_cast<QKeyEvent *>(event);

        if (keyEvent->key() == Qt::Key_Escape) {
            ui->searchEdit->clear();
            return true;
        }
    }

    return QMainWindow::eventFilter(watched, event);
}
```

返回 `true` 表示事件已经处理，不再交给目标控件；返回 `false` 则允许继续传递。过滤器适合局部、明确的需求，不应变成一个处理全应用所有事件的巨大函数。

## 5. 输入验证分为两层

第一层是控件级格式检查。例如课程学分只允许 1～10：

```cpp
creditsEdit->setValidator(new QIntValidator(1, 10, creditsEdit));
```

课程代码可以使用正则表达式：

```cpp
const QRegularExpression pattern(
    QStringLiteral("[A-Za-z]{2,8}-[0-9]{2,6}"));

courseCodeEdit->setValidator(
    new QRegularExpressionValidator(pattern, courseCodeEdit));
```

第二层是业务规则检查，例如标题不能为空、截止日期不能早于课程开始日期、同一课程下作业标题不能重复：

```cpp
QString validateAssignment(const QString &title,
                           const QDate &deadline) {
    if (title.trimmed().isEmpty()) {
        return QObject::tr("作业标题不能为空");
    }

    if (!deadline.isValid()) {
        return QObject::tr("截止日期无效");
    }

    return {};
}
```

QValidator 只能判断输入形式，不能替代业务规则。点击“确定”时仍要进行最终检查，并把焦点移到出错控件。

## 6. 定义领域数据

先用一个简单结构描述作业：

```cpp
#pragma once

#include <QDate>
#include <QString>

struct Assignment {
    qint64 id = 0;
    QString courseName;
    QString title;
    QDate deadline;
    bool completed = false;
};
```

领域对象不应保存 QLabel、QTableView 等界面指针。它只描述业务数据，可以被模型、数据库、测试和导出功能共同使用。

## 7. 为什么使用 Model/View

QTableWidget 会把数据直接存进单元格，适合非常小的临时表格。课程项目的数据还要被搜索、排序、保存和测试，如果界面单元格成为唯一数据源，很快就会出现同步问题。

Model/View 将职责分开：

```text
Assignment 数据
       ↓
AssignmentTableModel
       ↓
QSortFilterProxyModel
       ↓
QTableView
```

- Model 提供数据；
- View 负责显示和选择；
- Delegate 负责单元格绘制和编辑；
- Proxy Model 在不复制原数据的前提下排序或过滤。

## 8. 实现 AssignmentTableModel

头文件 `assignmenttablemodel.h`：

```cpp
#pragma once

#include <QAbstractTableModel>
#include <QVector>

#include "assignment.h"

class AssignmentTableModel final : public QAbstractTableModel {
    Q_OBJECT

public:
    enum Column {
        CourseColumn,
        TitleColumn,
        DeadlineColumn,
        StatusColumn,
        ColumnCount
    };

    explicit AssignmentTableModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = {}) const override;
    int columnCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index,
                  int role = Qt::DisplayRole) const override;
    QVariant headerData(int section,
                        Qt::Orientation orientation,
                        int role) const override;

    void setAssignments(QVector<Assignment> assignments);
    void addAssignment(const Assignment &assignment);
    bool removeAssignment(int row);
    const Assignment *assignmentAt(int row) const;

private:
    QVector<Assignment> assignments_;
};
```

核心实现：

```cpp
#include "assignmenttablemodel.h"

#include <utility>

AssignmentTableModel::AssignmentTableModel(QObject *parent)
    : QAbstractTableModel(parent) {}

int AssignmentTableModel::rowCount(const QModelIndex &parent) const {
    return parent.isValid() ? 0 : assignments_.size();
}

int AssignmentTableModel::columnCount(const QModelIndex &parent) const {
    return parent.isValid() ? 0 : ColumnCount;
}

QVariant AssignmentTableModel::data(const QModelIndex &index,
                                    int role) const {
    if (!index.isValid() || index.row() >= assignments_.size()) {
        return {};
    }

    const Assignment &item = assignments_.at(index.row());

    if (role == Qt::TextAlignmentRole) {
        return int(Qt::AlignCenter);
    }

    if (role != Qt::DisplayRole) {
        return {};
    }

    switch (index.column()) {
    case CourseColumn:
        return item.courseName;
    case TitleColumn:
        return item.title;
    case DeadlineColumn:
        return item.deadline.toString("yyyy-MM-dd");
    case StatusColumn:
        return item.completed ? tr("已完成") : tr("进行中");
    default:
        return {};
    }
}

QVariant AssignmentTableModel::headerData(
    int section, Qt::Orientation orientation, int role) const {
    if (orientation != Qt::Horizontal || role != Qt::DisplayRole) {
        return {};
    }

    switch (section) {
    case CourseColumn:
        return tr("课程");
    case TitleColumn:
        return tr("作业");
    case DeadlineColumn:
        return tr("截止日期");
    case StatusColumn:
        return tr("状态");
    default:
        return {};
    }
}

void AssignmentTableModel::setAssignments(
    QVector<Assignment> assignments) {
    beginResetModel();
    assignments_ = std::move(assignments);
    endResetModel();
}

void AssignmentTableModel::addAssignment(
    const Assignment &assignment) {
    const int row = assignments_.size();
    beginInsertRows({}, row, row);
    assignments_.append(assignment);
    endInsertRows();
}

bool AssignmentTableModel::removeAssignment(int row) {
    if (row < 0 || row >= assignments_.size()) {
        return false;
    }

    beginRemoveRows({}, row, row);
    assignments_.removeAt(row);
    endRemoveRows();
    return true;
}

const Assignment *AssignmentTableModel::assignmentAt(int row) const {
    if (row < 0 || row >= assignments_.size()) {
        return nullptr;
    }

    return &assignments_.at(row);
}
```

新增、删除和重置数据时必须调用对应的 `begin...()` 与 `end...()`，这样 View 才能正确更新内部索引和选中状态。

## 9. 接入表格、搜索和排序

在主窗口中创建源模型和代理模型：

```cpp
assignmentModel_ = new AssignmentTableModel(this);
assignmentProxy_ = new QSortFilterProxyModel(this);

assignmentProxy_->setSourceModel(assignmentModel_);
assignmentProxy_->setFilterCaseSensitivity(Qt::CaseInsensitive);
assignmentProxy_->setFilterKeyColumn(-1);
assignmentProxy_->setDynamicSortFilter(true);

ui->assignmentTableView->setModel(assignmentProxy_);
ui->assignmentTableView->setSortingEnabled(true);
ui->assignmentTableView->setSelectionBehavior(
    QAbstractItemView::SelectRows);
ui->assignmentTableView->setSelectionMode(
    QAbstractItemView::SingleSelection);
```

搜索框变化时更新过滤表达式：

```cpp
connect(ui->searchEdit, &QLineEdit::textChanged,
        this, [this](const QString &text) {
    assignmentProxy_->setFilterRegularExpression(
        QRegularExpression(
            QRegularExpression::escape(text),
            QRegularExpression::CaseInsensitiveOption));
});
```

用户在 View 中选择的行属于代理模型。删除或编辑前要映射回源模型：

```cpp
const QModelIndex proxyIndex =
    ui->assignmentTableView->currentIndex();

if (proxyIndex.isValid()) {
    const QModelIndex sourceIndex =
        assignmentProxy_->mapToSource(proxyIndex);
    assignmentModel_->removeAssignment(sourceIndex.row());
}
```

忘记映射索引是排序和过滤后删错数据的常见原因。

## 10. 初步划分项目职责

本章结束时，可以形成下面的职责边界：

| 层次 | 负责内容 | 不负责内容 |
| --- | --- | --- |
| UI | 显示、收集输入、触发操作 | 直接拼接 SQL |
| Model | 将领域数据暴露给 View | 弹窗和导航 |
| Service | 校验业务规则、组织操作 | 控件颜色和布局 |
| Repository | 下一章负责持久化 | 页面切换 |

MainWindow 可以连接这些对象，但不应把每一层的实现都写进槽函数。

## 11. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 区分事件和信号，重写关闭事件 |
| 第 2 步 | 为搜索框安装事件过滤器 |
| 第 3 步 | 为输入框添加格式校验和错误提示 |
| 第 4 步 | 定义 Assignment 领域对象 |
| 第 5 步 | 实现只读 AssignmentTableModel |
| 第 6 步 | 接入 QTableView、搜索、排序和选择 |
| 第 7 步 | 完成内存中的新增、删除和刷新流程 |

## 12. 常见问题

### 修改 QVector 后表格没有刷新

不能只修改底层容器。插入、删除、重置和局部更新都要使用 QAbstractItemModel 对应的通知接口。

### 排序后删除了错误记录

QTableView 返回的是代理模型索引。调用 `mapToSource()` 后，才能访问源模型中的正确行。

### eventFilter 拦截后控件失去正常行为

只有明确要停止传播时才返回 `true`。其余情况调用父类实现并返回结果。

### 正则验证通过但数据仍然不合理

格式正确不代表业务正确。控件级验证之外，还要检查空白、重复、日期关系等规则。

### 所有代码仍在 MainWindow

先把领域对象和 TableModel 提取成独立文件，再把验证函数移动到 Service。每次只拆一类职责，避免一次性重构失控。

## 13. 本章验收清单

- [ ] 能说明事件与信号的区别；
- [ ] 未保存数据时关闭窗口会提示确认；
- [ ] 搜索框按 Esc 可以清空；
- [ ] 输入格式和业务规则分别验证；
- [ ] 表格使用 QTableView 而不是把 QTableWidget 当数据库；
- [ ] 自定义模型正确实现行数、列数和数据显示；
- [ ] 插入和删除使用模型通知接口；
- [ ] 搜索和排序通过代理模型完成；
- [ ] 排序后编辑或删除能够映射到正确源数据；
- [ ] 项目已经形成 UI、Model 和 Service 的初步边界。

下一章将把内存数据替换为 SQLite，并加入 QSettings、JSON 导入导出和可靠的错误处理，形成真正的数据持久化闭环。

官方参考：[Qt 事件系统](https://doc.qt.io/qt-6/eventsandfilters.html) ｜ [Model/View 教程](https://doc.qt.io/qt-6/modelview.html) ｜ [QValidator](https://doc.qt.io/qt-6/qvalidator.html)

上一篇：[第 2 章：主窗口、布局与界面原型]({% post_url 2026-09-02-qt-course-project-week-2-notes %}) ｜ 下一篇：[第 4 章：文件、设置与 SQLite 数据闭环]({% post_url 2026-09-02-qt-course-project-week-4-notes %})
