# ListenSnow's Blog

个人技术博客，记录计算机学习、开发实践与持续探索。使用 GitHub Pages、Jekyll、Minima、Liquid 和原生 JavaScript 构建。

- **博客地址**：[https://listensnow05.top/](https://listensnow05.top/)
- **源码仓库**：[ListenSnow405/ListenSnow405.github.io](https://github.com/ListenSnow405/ListenSnow405.github.io)
- **部署方式**：推送到 `main` 后，由 GitHub Pages 自动构建发布。

## 页面与功能

整体采用雾蓝夜色背景与冰蓝强调色，使用系统字体栈，兼顾长文阅读与移动端访问。

- **首页**：个人信息与导航、最新 6 篇文章信息流，以及搜索、年份归档、分类和标签发现栏。
- **内容发现**：提供[归档](https://listensnow05.top/archives/)、[分类](https://listensnow05.top/categories/)、[标签](https://listensnow05.top/tags/)和[站内搜索](https://listensnow05.top/search/)。索引由文章自动生成，无需手工维护重复列表。
- **站内搜索**：在浏览器中检索文章标题、摘要、正文、分类和标签，显示匹配数量，支持通过 `?q=关键词` 分享搜索结果。
- **文章阅读**：自动生成二、三级标题目录与章节锚点，跟随当前章节高亮；提供阅读进度、代码复制、上一篇和下一篇导航。
- **响应式布局**：首页宽屏三栏；宽度不超过 `1100px` 时隐藏发现栏，不超过 `760px` 时切换为单栏与顶部粘性导航。文章目录在大于 `1280px` 时位于右侧，不超过该宽度时移至正文上方并默认折叠。
- **基础支持**：RSS、SEO 元信息、404 页面、键盘焦点提示、跳转到正文链接与减少动态效果偏好支持。

文章目录在正文中至少有两个有效的二、三级标题时显示。目录、进度和代码复制由 JavaScript 渐进增强；基础文章内容仍由 Jekyll 直接输出。

## 本地运行

当前项目使用 Ruby `3.1.7`（见 `.ruby-version`）、Bundler `2.3.27` 和 `github-pages ~> 232` 依赖集，对应 Jekyll `3.10.0`、Minima `2.5.1`。Windows 环境使用 RubyInstaller + Devkit，当前安装目录为 `C:\Ruby31-x64`。

在仓库根目录执行：

```powershell
# 首次安装依赖
bundle config set --local path vendor/bundle
bundle install

# 完整构建，输出到 _site/
bundle exec jekyll build

# 启动本地预览
bundle exec jekyll serve --host 127.0.0.1 --port 4000
```

预览地址为 [http://127.0.0.1:4000/](http://127.0.0.1:4000/)。如需预览 `_drafts/` 中的草稿，在预览命令末尾加上 `--drafts`。修改 `_config.yml` 后需要重启预览服务。

安装 Ruby 后应重新打开终端以加载新的 `PATH`。构建时的 `To use retry middleware with Faraday v2.0+` 提示属于当前依赖组合的非致命提示；应结合退出码和最终构建结果判断是否成功。

`.bundle/`、`vendor/`、`Gemfile.lock`、`_site/` 和 Jekyll 缓存已加入 `.gitignore`，无需提交。

## 发布文章

1. 复制 `_drafts/post-template.md`，将副本放入 `_posts/`。
2. 文件名使用 `YYYY-MM-DD-英文短标题.md`，例如 `2026-09-24-my-first-note.md`。
3. 修改 front matter，编写 Markdown 正文。
4. 本地构建并预览，确认分类、标签、目录和代码块正常。
5. 提交并推送到 `main`，等待 GitHub Pages 构建完成。

```yaml
---
layout: post
title: "文章标题"
date: 2026-09-24 12:00:00 +0800
categories: [学习]
tags: [算法, C++, OI]
---
```

- 用 `##` 表示章节、`###` 表示子章节，便于自动生成文章目录。
- 代码块使用带语言标记的围栏语法，以获得语法高亮。
- `categories` 和 `tags` 自动驱动分类页、标签页、侧栏和搜索索引。
- 当前文章永久链接为 `/posts/:title/`，发布后应谨慎修改文件名中的英文短标题，以免改变已有链接。
- 默认构建不会发布未来日期的文章；若文章未显示，先检查 front matter 时间和 `Asia/Shanghai` 时区。

## 自定义域名与站点配置

当前自定义域名记录在根目录 `CNAME` 中：

```text
listensnow05.top
```

站点名称、作者、简介、邮箱、头像、语言、时区和 URL 均由 `_config.yml` 管理。GitHub Pages 的域名设置入口为[仓库 Settings → Pages](https://github.com/ListenSnow405/ListenSnow405.github.io/settings/pages)。

**当前配置待同步项**：`CNAME` 已使用自定义域名，但 `_config.yml` 的 `url` 仍为 `https://listensnow405.github.io`。为保持 SEO canonical、RSS 等绝对链接与正式访问地址一致，应将该配置同步为：

```yaml
url: "https://listensnow05.top"
baseurl: ""
```

上述片段是待同步的目标配置；本次 README 更新没有修改 `_config.yml`。日后更换域名时，应同时核对 DNS、Pages 自定义域名、`CNAME` 和 `url`，并确认 HTTPS 可用。

## 目录结构

| 文件或目录 | 职责 |
| --- | --- |
| `_config.yml` | 站点身份、URL、主题和插件配置 |
| `CNAME` | GitHub Pages 自定义域名 |
| `Gemfile`、`.ruby-version` | 本地依赖与 Ruby 版本 |
| `_posts/` | 已发布文章 |
| `_drafts/` | 草稿与文章模板 |
| `_layouts/default.html` | 全局页面骨架、背景装饰和页脚 |
| `_layouts/post.html` | 文章元信息、目录容器和相邻文章导航 |
| `_includes/head.html` | SEO、RSS 和带构建版本号的样式引用 |
| `_includes/profile-sidebar.html` | 个人信息与主导航 |
| `_includes/discover-sidebar.html` | 搜索、年份归档、分类与标签侧栏 |
| `assets/main.scss` | 共享视觉变量、组件样式和响应式规则 |
| `assets/js/site.js` | 移动端导航位置与布局尺寸更新 |
| `assets/js/post.js` | 文章目录、章节锚点、代码复制和阅读进度 |
| `assets/js/search.js` | 浏览器端搜索交互 |
| `index.html` | 首页介绍与文章信息流 |
| `archives.html`、`categories.html`、`tags.html` | 内容发现页面 |
| `search.html`、`search.json` | 搜索页面与自动生成的文章索引 |
| `about.md`、`404.html` | 关于页面与未找到页面 |
| `AGENTS.md` | 仓库维护规范和验证要求 |

## 维护与验证

修改布局、样式或交互前，先阅读 `AGENTS.md` 及相关源文件。保持 GitHub Pages 原生兼容，优先复用共享组件与颜色变量，站内模板链接使用 Liquid 的 `relative_url`。

常用检查：

```powershell
node --check assets/js/search.js
node --check assets/js/site.js
node --check assets/js/post.js
git diff --check
bundle exec jekyll build
```

页面改动还需检查首页、文章页和受影响的内容发现页面，分别验证桌面与移动端的横向溢出、导航和可读性。搜索改动后，用现有标题或标签验证结果；发布后确认 GitHub Pages 的实际构建结果。

不要删除 `_includes/head.html` 中 `assets/main.css?v=<build-revision>` 的版本参数。若发布后仍看到旧样式，应先检查页面中版本号是否已更新，再排查缓存或部署问题。
