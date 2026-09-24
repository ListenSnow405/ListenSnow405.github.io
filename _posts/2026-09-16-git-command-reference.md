---
layout: post
title: "Git 命令速查与专题索引"
date: 2026-09-16 10:10:00 +0800
categories: [学习]
tags: [Git, GitHub, 命令速查, 版本控制, Git系列]
excerpt: "Git 五篇系列的按需查阅入口，保留常用命令、操作边界和原手册章节索引。"
---

原《Git 常用命令手册：从日常操作到历史恢复》已按学习与使用场景重构为五篇文章。本页保留命令速查与原章节入口，详细概念、案例、状态对照和实践练习见各专题。

## 系列索引

| 顺序 | 文章 | 主要内容 |
| --- | --- | --- |
| 一 | [Git 基本原理与学习路径]({% post_url 2026-09-16-git-learning-roadmap %}) | 工作区域、提交与引用、首次提交、学习顺序 |
| 二 | [Git 基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %}) | 状态、差异、暂存、忽略规则、合并冲突 |
| 三 | [Git 远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %}) | 同步、分叉、协作、stash、worktree、标签 |
| 四 | [Git 历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %}) | amend、rebase、cherry-pick、reset、revert、reflog |
| 五 | [Git 历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %}) | 历史检索、代码溯源、bisect、导出与维护 |

## 常用命令

| 场景 | 命令 |
| --- | --- |
| 状态与分支 | `git status --short --branch` |
| 未暂存差异 | `git diff` |
| 已暂存差异 | `git diff --cached` |
| 分块暂存 | `git add -p` |
| 取消暂存 | `git restore --staged <file>` |
| 创建提交 | `git commit -m "message"` |
| 检查提交 | `git show --stat HEAD` |
| 创建分支 | `git switch -c <branch>` |
| 合并分支 | `git merge <branch>` |
| 放弃合并 | `git merge --abort` |
| 获取远程 | `git fetch origin` |
| 快进同步 | `git merge --ff-only origin/main` |
| 建立上游 | `git push -u origin <branch>` |
| 暂存现场 | `git stash push -u -m "message"` |
| 工作区列表 | `git worktree list` |
| 撤销共享修改 | `git revert <commit>` |
| 查看恢复线索 | `git reflog` |
| 保护旧提交 | `git branch recovery/<name> <commit>` |
| 历史图 | `git log --graph --oneline --decorate --all` |
| 文件历史 | `git log -p -- <file>` |
| 忽略来源 | `git check-ignore -v <file>` |
| 清理预览 | `git clean -nd` |

## 操作约定

`<file>`、`<branch>`、`<commit>` 是占位符，执行前应替换为实际路径或引用。`origin` 和 `main` 也是本系列的约定名称，实际仓库可能不同。

执行会改变状态的命令前，检查当前仓库、分支、未提交修改和目标引用。备份分支仅保护已有提交，未提交内容需要另行保存。涉及历史重写、文件覆盖或实际清理时，应先阅读对应专题，不能把速查表当成无条件执行的脚本。

操作后用状态、差异与日志核对结果，并完成项目自身的测试。命令成功不等于内容正确，远程信息也应在获取后再比较。

## 原章节索引

原手册章节链接继续保留，以下条目对应新的主要讲解位置。跨主题章节会在相关专题中分开解释。

- <span id="1-阅读约定与风险等级"></span>1. 阅读约定与风险等级：[操作约定](#操作约定)
- <span id="2-帮助版本与基础配置"></span><span id="查看版本和帮助"></span><span id="查看配置"></span><span id="常用初始化配置"></span>2. 帮助、版本与基础配置：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="3-创建克隆与定位仓库"></span><span id="初始化仓库"></span><span id="克隆仓库"></span><span id="判断当前是否在仓库中"></span>3. 创建、克隆与定位仓库：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="4-查看工作区状态"></span>4. 查看工作区状态：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="5-比较文件与提交"></span><span id="工作区和暂存区"></span><span id="暂存区和当前提交"></span><span id="工作区和当前提交"></span><span id="比较提交或分支"></span><span id="控制输出范围"></span>5. 比较文件与提交：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})；[历史差异]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="6-暂存移动与删除文件"></span><span id="暂存修改"></span><span id="取消暂存"></span><span id="移动和删除已跟踪文件"></span>6. 暂存、移动与删除文件：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="7-创建检查与修改提交"></span><span id="创建提交"></span><span id="修改最近一次提交"></span><span id="为交互式变基准备修正提交"></span><span id="查看单个提交"></span>7. 创建、检查与修改提交：[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})；[基础提交]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="8-浏览和搜索提交历史"></span><span id="常用日志视图"></span><span id="按范围查看"></span><span id="按条件过滤"></span><span id="汇总贡献"></span>8. 浏览和搜索提交历史：[历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="9-分支操作"></span><span id="查看分支"></span><span id="创建与切换"></span><span id="重命名和删除"></span><span id="detached-head"></span>9. 分支操作：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="10-合并与冲突处理"></span><span id="合并分支"></span><span id="查看冲突"></span><span id="选择冲突一侧的内容"></span>10. 合并与冲突处理：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="11-rebase-与历史整理"></span><span id="把当前分支变基到新起点"></span><span id="冲突控制"></span><span id="交互式整理"></span>11. Rebase 与历史整理：[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})
- <span id="12-远程仓库管理"></span><span id="查看远程信息"></span><span id="添加修改和删除远程"></span><span id="获取远程引用"></span><span id="拉取并整合"></span><span id="推送"></span>12. 远程仓库管理：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="13-比较本地与远程状态"></span>13. 比较本地与远程状态：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="14-撤销重置与恢复"></span><span id="恢复工作区文件"></span><span id="取消暂存-1"></span><span id="用新提交撤销旧提交"></span><span id="reset-三种模式"></span><span id="使用-reflog-找回位置"></span>14. 撤销、重置与恢复：[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})
- <span id="15-临时保存未完成工作"></span><span id="创建-stash"></span><span id="查看和恢复"></span><span id="删除-stash"></span>15. 临时保存未完成工作：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="16-移动提交与交换补丁"></span><span id="cherry-pick"></span><span id="生成和应用邮件补丁"></span>16. 移动提交与交换补丁：[历史重写与撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})；[补丁交换]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="17-标签与版本发布"></span><span id="查看和创建标签"></span><span id="推送和删除标签"></span><span id="从标签描述版本"></span>17. 标签与版本发布：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="18-查找修改来源与定位回归"></span><span id="blame"></span><span id="搜索内容"></span><span id="搜索历史中的变化"></span><span id="使用-bisect-二分定位"></span>18. 查找修改来源与定位回归：[历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="19-使用-worktree-并行处理分支"></span>19. 使用 worktree 并行处理分支：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="20-忽略规则与跟踪状态"></span>20. 忽略规则与跟踪状态：[基础操作与分支管理]({% post_url 2026-09-25-git-basics-and-branches %})
- <span id="21-子模块稀疏检出与大型文件"></span><span id="submodule"></span><span id="sparse-checkout"></span><span id="git-lfs"></span>21. 子模块、稀疏检出与大型文件：[历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="22-仓库清理维护与打包"></span><span id="预览和删除未跟踪文件"></span><span id="检查和维护对象数据库"></span><span id="导出源码快照"></span><span id="创建可传输的-git-bundle"></span>22. 仓库清理、维护与打包：[历史分析与仓库维护]({% post_url 2026-09-25-git-analysis-and-maintenance %})
- <span id="23-认证和远程故障排查"></span><span id="检查远程地址"></span><span id="检查-ssh-身份"></span><span id="常见错误"></span><span id="fatal-not-a-git-repository"></span><span id="author-identity-unknown"></span><span id="remote-origin-already-exists"></span><span id="repository-not-found"></span><span id="non-fast-forward"></span><span id="refusing-to-merge-unrelated-histories"></span><span id="detected-dubious-ownership"></span>23. 认证和远程故障排查：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})
- <span id="24-高频工作流模板"></span><span id="开始一个新功能"></span><span id="提交当前功能"></span><span id="推送并建立上游"></span><span id="更新功能分支"></span><span id="把做在错误分支上的未提交修改移到新分支"></span><span id="把最近提交移动到新分支"></span><span id="撤销已经进入共享分支的提交"></span><span id="找回误删分支"></span><span id="紧急修复但不打断当前工作"></span>24. 高频工作流模板：[远程协作与版本管理]({% post_url 2026-09-25-git-remotes-and-collaboration %})；[撤销恢复]({% post_url 2026-09-25-git-history-and-recovery %})
- <span id="25-一页速查表"></span>25. 一页速查表：[常用命令](#常用命令)
- <span id="26-操作前后的检查清单"></span>26. 操作前后的检查清单：[操作约定](#操作约定)
- <span id="27-官方参考资料"></span>27. 官方参考资料：[参考资料](#参考资料)

## 参考资料

- [Git 命令参考](https://git-scm.com/docs)
- [Pro Git 在线书籍](https://git-scm.com/book/zh/v2)

**阅读入口**：[基本原理与学习路径]({% post_url 2026-09-16-git-learning-roadmap %})
