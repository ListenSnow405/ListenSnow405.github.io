---
layout: post
title: "Qt 课程项目第 8 章：Release、部署与课程答辩"
date: 2026-09-02 00:40:00 +0800
categories: [学习]
tags: [Qt, CMake, 软件发布, windeployqt, 课程答辩]
---

在[第七章]({% post_url 2026-09-02-qt-course-project-week-7-notes %})中，我们通过自动测试、异常矩阵和发布候选标准提高了项目稳定性。最后一章解决交付问题：构建 Release、收集运行依赖、验证干净环境、整理文档，并准备一条清晰的课程答辩叙事。

源代码能够在开发电脑上运行，不代表软件已经可以提交。真正的交付物应当在没有 Qt Creator、没有源代码、工作目录不同的环境中独立启动。

## 1. 本章目标

完成本章后，应当能够：

- 区分 Debug、Release 和部署目录；
- 为程序设置版本和发布属性；
- 使用 Qt 的 CMake 部署 API；
- 使用 windeployqt 检查 Windows 依赖；
- 验证平台插件和 SQLite 驱动；
- 在干净环境中测试最终程序；
- 整理 README、架构图、ER 图和测试报告；
- 设计 5～8 分钟答辩演示；
- 生成可复核的最终提交包。

## 2. 固定版本信息

项目版本应当有唯一来源：

```cmake
project(course_manager VERSION 1.0.0 LANGUAGES CXX)
```

程序中可以读取：

```cpp
QCoreApplication::setApplicationVersion(
    QStringLiteral(PROJECT_VERSION));
```

为目标传入版本宏：

```cmake
target_compile_definitions(course_manager PRIVATE
    PROJECT_VERSION="${PROJECT_VERSION}"
)
```

关于页面、README、压缩包名称和答辩文档都使用同一个版本号，例如 `CourseManager-1.0.0-windows-x64.zip`。

## 3. Release 构建

使用独立构建目录，避免 Debug 与 Release 产物混合：

```powershell
cmake -S . -B build-release
cmake --build build-release --config Release
```

构建前确认：

- 选择的 Qt Kit 与开发时一致；
- CMake 配置成功；
- 没有未处理的编译警告；
- 测试在 Release 配置下也能运行；
- 程序版本号正确；
- 没有依赖本地绝对路径的资源。

不要把 Debug DLL 与 Release 程序混合，也不要把整个构建目录直接作为最终提交包。

## 4. 使用 CMake 部署 API

Qt 6 可以通过 CMake 生成部署脚本。先加入安装规则：

```cmake
include(GNUInstallDirs)

install(TARGETS course_manager
    BUNDLE  DESTINATION .
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

qt_generate_deploy_app_script(
    TARGET course_manager
    OUTPUT_SCRIPT deploy_script
    NO_UNSUPPORTED_PLATFORM_ERROR
)

install(SCRIPT ${deploy_script})
```

构建后安装到独立目录：

```powershell
cmake --install build-release `
    --config Release `
    --prefix package
```

部署脚本会调用平台对应工具收集 Qt 运行依赖。最终 `package` 应是一个自包含的安装目录，而不是源码目录的复制品。

`qt_generate_deploy_app_script()` 适用于 Qt 6.3 及更高版本。如果课程环境固定在更早版本，需要改用对应版本支持的部署方式。

## 5. 使用 windeployqt 手工检查

在 Qt 对应 Kit 的命令行环境中，也可以对 Release 可执行文件运行：

```powershell
windeployqt --release --dir package CourseManager.exe
```

实际可执行文件路径根据生成器和构建目录而定。运行前先定位正确的 Release 程序，不要对 Debug 版本打包。

windeployqt 会收集 Qt DLL、平台插件、图像格式插件和编译器运行库等依赖，但项目自己的第三方库和外部资源仍需要自行检查。

## 6. 检查最终目录

一个简化的 Windows 包可能包含：

```text
CourseManager-1.0.0/
├── bin/
│   ├── course_manager.exe
│   ├── Qt6Core.dll
│   ├── Qt6Gui.dll
│   ├── Qt6Widgets.dll
│   ├── Qt6Sql.dll
│   ├── platforms/
│   │   └── qwindows.dll
│   ├── sqldrivers/
│   │   └── qsqlite.dll
│   └── styles/
├── README.md
├── 使用说明.pdf
└── LICENSES/
```

项目使用 SQLite 时，要特别检查 `sqldrivers/qsqlite.dll`；Widgets 程序启动需要 `platforms/qwindows.dll`。只有把 DLL 放在正确的插件子目录中，Qt 才能发现它们。

不要把自己的真实课程数据库、个人姓名、令牌或调试日志打进提交包。演示数据使用专门准备的匿名样例。

## 7. 数据库首次启动策略

程序首次启动时：

1. 使用 QStandardPaths 获取用户数据目录；
2. 创建目录；
3. 创建空数据库；
4. 执行表结构和版本迁移；
5. 可选地询问是否导入演示数据；
6. 显示正常空状态。

不要默认在程序安装目录写数据库。该目录可能只读，也可能在更新或解压新版本时被覆盖。

如果要附带演示数据，可以把 JSON 模板放进 `.qrc`，首次启动时由用户主动选择导入，而不是把开发数据库复制到安装目录。

## 8. 干净环境部署测试

理想情况下，在没有安装 Qt 的另一台 Windows 电脑或虚拟机测试。至少执行：

1. 解压到一个全新目录；
2. 直接双击可执行文件；
3. 确认没有 Qt Creator 或构建目录依赖；
4. 测试首次数据库初始化；
5. 完成新增、搜索、修改、删除；
6. 测试中文路径和包含空格的路径；
7. 关闭并重启；
8. 测试导入导出；
9. 断网后测试本地核心功能；
10. 删除用户配置后再次首次启动。

不能只在源码目录旁运行，因为程序可能无意中读取了构建目录中的插件或资源。

## 9. 部署问题定位

### 提示找不到 Qt6Widgets.dll

运行依赖没有部署，或者程序与 DLL 的体系结构、编译器不一致。使用同一 Qt Kit 的 windeployqt 重新生成目录。

### 提示无法初始化平台插件

检查 `platforms/qwindows.dll` 的目录层级。不要把它直接放在 exe 同级后就删除 `platforms` 目录。

### 开发环境能查数据库，打包后提示驱动未加载

检查 `sqldrivers/qsqlite.dll`，并输出 `QSqlDatabase::drivers()` 进行诊断。

### 图标、样式或模板丢失

应打包的静态资源优先放入 `.qrc`。确实需要外部文件时，使用应用目录或标准数据路径构造位置，并在安装规则中显式复制。

### 程序启动后无法创建数据库

检查是否错误地把数据库写到安装目录。改用 `QStandardPaths::AppDataLocation`，并显示实际错误原因。

## 10. 最终文档清单

### README

至少包含：

- 项目简介；
- 主要功能；
- 技术栈；
- 开发环境；
- 源码构建步骤；
- 程序运行方式；
- 数据文件位置；
- 已知限制；
- 项目结构。

### 使用说明

面向普通用户说明：

- 首次启动；
- 创建课程和作业；
- 搜索、修改、删除；
- 导入导出；
- 数据备份；
- 常见错误处理。

### 设计与测试材料

准备：

- 需求与功能范围；
- 模块架构图；
- 数据库 ER 图；
- 关键类关系；
- 测试用例表；
- 测试结果；
- 关键界面截图；
- 已知问题和后续计划。

文档中的截图、功能和版本必须与最终提交程序一致。

## 11. 最终提交包结构

建议分开交付源代码、运行程序和文档：

```text
QtCourseProject-1.0.0/
├── source/
│   ├── CMakeLists.txt
│   ├── src/
│   ├── resources/
│   ├── tests/
│   └── README.md
├── application/
│   ├── bin/
│   ├── README.md
│   └── 使用说明.pdf
├── documents/
│   ├── 需求分析.pdf
│   ├── 设计说明.pdf
│   ├── 测试报告.pdf
│   └── 答辩演示.pdf
└── checksums.txt
```

压缩前从该结构直接运行一次程序，并确认没有临时构建文件、个人数据库、绝对路径和大体积无关素材。

可以生成校验值：

```powershell
Get-FileHash .\CourseManager-1.0.0-windows-x64.zip `
    -Algorithm SHA256
```

校验值便于确认上传和下载后的文件没有损坏。

## 12. 设计 5～8 分钟答辩

推荐节奏：

| 时间 | 内容 |
| --- | --- |
| 0:00～0:40 | 问题背景和项目目标 |
| 0:40～1:20 | 功能范围与技术选型 |
| 1:20～4:30 | 按固定脚本演示核心流程 |
| 4:30～5:30 | 架构、Model/View 与数据库设计 |
| 5:30～6:20 | 特色功能和关键技术难点 |
| 6:20～7:10 | 测试、异常处理和部署验证 |
| 7:10～8:00 | 总结、限制和后续方向 |

答辩应围绕“问题—设计—实现—证据”展开，而不是逐个朗读类名。

## 13. 演示准备

演示前准备：

- 一份干净数据库；
- 一份包含少量匿名数据的演示数据库；
- 一份可成功导入的 JSON；
- 一份故意损坏的 JSON；
- 固定的课程和作业名称；
- 离线可用的程序包；
- 关键界面截图或短视频作为备用；
- 源代码关键位置书签。

现场演示顺序与第六章中的脚本保持一致。不要临时输入过长内容，也不要依赖不稳定的外部网络完成核心演示。

## 14. 常见答辩问题

### 为什么选择 Qt Widgets 而不是 QML

项目以传统桌面管理界面、表格和表单为主，Qt Widgets 组件成熟，Model/View 支持完整，并与 C++ 业务代码直接配合。

### 为什么使用 SQLite

项目是单机课程软件，数据量和并发要求有限。SQLite 无需单独部署服务器，支持事务和结构化查询，适合独立桌面应用。

### 为什么不用 QTableWidget

数据需要被查询、排序、过滤、持久化和测试。Model/View 能把数据与显示分离，并通过代理模型复用排序和过滤能力。

### 如何保证数据库一致性

输入先经过业务校验，查询使用绑定参数，多步导入使用事务，失败时回滚，并通过集成测试验证关键约束。

### 多线程解决了什么问题

只有真实耗时任务才移到 worker，GUI 始终留在主线程。普通网络请求使用 Qt 的异步 API，不额外创建线程。

## 15. 七个练习步骤

| 顺序 | 学习与实践 |
| --- | --- |
| 第 1 步 | 固定 1.0.0 版本号并构建 Release |
| 第 2 步 | 添加 CMake 安装与部署脚本 |
| 第 3 步 | 使用 windeployqt 检查 Qt 依赖 |
| 第 4 步 | 在干净目录或另一台电脑测试 |
| 第 5 步 | 整理 README、使用说明和设计文档 |
| 第 6 步 | 按 5～8 分钟结构完成一次模拟答辩 |
| 第 7 步 | 生成最终压缩包、校验值和备份 |

## 16. 最终验收清单

- [ ] Release 构建和全部测试通过；
- [ ] 程序版本号在各处一致；
- [ ] 部署目录不依赖 Qt Creator；
- [ ] `platforms/qwindows.dll` 存在且位置正确；
- [ ] `sqldrivers/qsqlite.dll` 存在且可加载；
- [ ] 首次启动可以创建用户数据库；
- [ ] 中文路径和含空格路径测试通过；
- [ ] 程序重启后数据和设置正确；
- [ ] 提交包没有个人数据库和敏感日志；
- [ ] README、使用说明、架构图和测试报告完整；
- [ ] 演示数据、损坏样例和备用截图已经准备；
- [ ] 5～8 分钟答辩可以在规定时间内完成；
- [ ] 最终压缩包能够重新解压并独立运行；
- [ ] 已保存最终压缩包的 SHA-256 校验值。

至此，这条 Qt 课程项目路线完成了从开发环境、界面原型、事件与 Model/View、SQLite 数据闭环，到特色功能、MVP、测试和部署的完整过程。真正值得保留的不只是最终软件，还有一套可以迁移到下一次桌面项目中的开发方法。

官方参考：[使用 CMake 部署 Qt 应用](https://doc.qt.io/qt-6/cmake-deployment.html) ｜ [Windows 部署](https://doc.qt.io/qt-6/windows-deployment.html) ｜ [qt_generate_deploy_app_script](https://doc.qt.io/qt-6/qt-generate-deploy-app-script.html)

上一篇：[第 7 章：测试、异常处理与发布候选]({% post_url 2026-09-02-qt-course-project-week-7-notes %}) ｜ 返回：[8 个章节的项目驱动学习路线]({% post_url 2026-09-01-qt-course-project-eight-week-roadmap %})
