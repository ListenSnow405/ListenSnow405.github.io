# ListenSnow's Blog

个人技术博客，记录计算机学习、开发实践与持续探索。使用 GitHub Pages、Jekyll、Minima、Liquid 和原生 JavaScript 构建。

- **博客地址**：[https://listensnow05.top/](https://listensnow05.top/)
- **源码仓库**：[ListenSnow405/ListenSnow405.github.io](https://github.com/ListenSnow405/ListenSnow405.github.io)
- **部署方式**：推送到 `main` 后，由 GitHub Pages 自动构建发布。

## 页面与功能

提供雾蓝深色、霜白浅色与暖纸三套外观，默认使用雾蓝深色。使用系统字体栈，兼顾长文阅读与移动端访问。

- **首页**：个人信息与导航、紧凑的介绍区、最新 6 篇文章信息流，以及搜索、年份归档、分类和精简标签云侧栏。介绍区标题按屏幕宽度自然换行，提供“开始阅读”按钮与“了解更多”文字链接。
- **主导航**：首页、文章、系列、关于四个入口。首页桌面搜索框位于右侧发现栏顶部；其他页面与侧栏收起后的平板布局在内容区右上方提供搜索入口，移动端保留导航旁的独立搜索按钮。
- **文章浏览**：[文章](https://listensnow05.top/archives/)沿用 `/archives/`，保留年份锚点，按时间列出全部文章；分类和标签可组合筛选，显示匹配数量及空结果提示，可清除筛选。筛选状态写入 `?category=…&tag=…`，刷新或分享链接后恢复；分类、标签选项与数量由文章数据生成。[分类](https://listensnow05.top/categories/)和[标签](https://listensnow05.top/tags/)保留为二级索引，禁用 JavaScript 时仍能浏览全部文章及这两个索引。
- **系列导读**：[系列](https://listensnow05.top/series/)集中展示 Git、Qt 的简介、阅读前提、导读和有序篇目。文章页底部提供所属系列入口；系列页从文章元数据自动汇总篇目与数量。
- **发现侧栏**：年份及篇数、分类均由文章自动生成；标签云按文章使用频次自动取前 8 个标签，并提供完整标签索引入口，不删改文章本身的标签。
- **站内搜索**：在浏览器中检索文章标题、摘要、正文、分类和标签，显示匹配数量，支持通过 `?q=关键词` 分享搜索结果。
- **阅读偏好**：文章页右下角提供“阅读设置”，可切换外观、三级正文字号和紧凑／标准／宽松宽度；窄屏自动受可用宽度约束。专注阅读收起侧栏、背景装饰与相邻文章推荐，正文居中，目录改为可折叠（窄屏或专注时选择章节后自动收起），并始终提供“退出专注”按钮。字号、宽度与专注状态记忆在当前浏览器，仅作用于文章页，同源标签页自动同步；“恢复阅读默认值”重置这三项，不改变外观。存储不可用时仍可在当前页调整；脚本不可用时保留基础阅读布局。
- **文章阅读**：自动生成二、三级标题目录与章节锚点，跟随当前章节高亮；提供阅读进度、代码复制、上一篇和下一篇导航。
- **响应式布局**：各页面共用外层宽度、边距及左侧导航列位置，预留滚动条空间，避免跨页跳动；首页宽屏三栏；宽度不超过 `1100px` 时隐藏发现栏，不超过 `760px` 时切换为单栏与顶部粘性导航。文章目录在大于 `1280px` 时位于右侧，不超过该宽度时移至正文上方并默认折叠。
- **基础支持**：RSS、SEO 元信息、404 页面、键盘焦点提示、跳转到正文链接与减少动态效果偏好支持。

文章目录在正文中至少有两个有效的二、三级标题时显示。目录、进度和代码复制由 JavaScript 渐进增强；基础文章内容仍由 Jekyll 直接输出。

### 系列维护

`_data/series.yml` 只维护系列的 `id`、标题、简介与阅读前提，不重复维护文章列表。加入系列时，在文章 front matter 设置 `series`（对应系列 id）和 `series_order`（同系列内唯一整数，0 为导读，其余按学习顺序递增）。独立速查文章增加 `series_role: reference`，排序放在专题之后。文章正文和既有永久链接不受这些字段影响。

### 外观切换

桌面端入口位于左侧导航下方，移动端位于顶部个人信息右侧；文章页的“阅读设置”中也提供相同入口，专注阅读时仍可使用。入口采用“开关图标 + 当前模式名称”的横排按钮，不使用下拉选择框。

- 点击按钮按“暗色模式 → 浅色模式 → 暖纸模式 → 暗色模式”循环切换，分别对应雾蓝、霜白和暖纸配色。文字显示当前模式，悬停提示和辅助技术标签说明下一次点击的目标；键盘聚焦后可用 Enter 或空格切换。
- 首次访问默认深色，系统外观变化不会自动切换站点主题。已保存的手动选择优先于默认值，因此再次访问时仍可保持浅色或暖纸。
- 偏好保存在当前浏览器的 `localStorage`，键为 `listensnow-theme`，有效值为 `dark`、`light`、`paper`。刷新、跨页和再次访问时恢复选择，同源标签页以及同页两个入口同步更新；不同浏览器或设备之间不自动同步。
- 无保存记录、旧值 `system` 或无效值均回退为深色。存储受限时切换仍对当前页面有效；JavaScript 不可用时隐藏按钮，保持深色基础阅读。
- “恢复阅读默认值”只重置字号、正文宽度和专注状态，不重置外观。

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
| `_includes/theme-button.html` | 导航区域和阅读设置共用的主题切换按钮 |
| `_includes/reading-controls.html` | 文章阅读设置面板及退出专注入口 |
| `_includes/discover-sidebar.html` | 首页搜索、年份归档、分类与精简标签云侧栏 |
| `_includes/nav-icon.html` | 主导航与搜索共用的线性 SVG 图标 |
| `_data/series.yml`、`series.html` | 系列说明与按文章元数据生成的学习顺序 |
| `assets/main.scss` | 共享视觉变量、组件样式和响应式规则 |
| `_sass/themes.scss` | 三套主题变量、主题切换按钮和代码高亮配色 |
| `_sass/navigation.scss` | 导航、文章筛选、系列页面及其响应式样式 |
| `_sass/reading.scss` | 阅读设置面板、字号、宽度与专注布局 |
| `assets/js/reading.js` | 首屏阅读偏好恢复、设置记忆与段落位置保持 |
| `assets/js/theme.js` | 首屏深色默认值、主题循环切换与本地选择记忆 |
| `assets/js/site.js` | 移动端导航位置与布局尺寸更新 |
| `assets/js/post.js` | 文章目录、章节锚点、代码复制和阅读进度 |
| `assets/js/articles.js` | 分类与标签组合筛选、结果计数及 URL 状态恢复 |
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
node --check assets/js/articles.js
node --check assets/js/search.js
node --check assets/js/site.js
node --check assets/js/post.js
node --check assets/js/theme.js
node --check assets/js/reading.js
git diff --check
bundle exec jekyll build
```

页面改动还需检查首页、文章页和受影响的内容发现页面，分别验证桌面与移动端的横向溢出、导航和可读性。搜索改动后，用现有标题或标签验证结果；发布后确认 GitHub Pages 的实际构建结果。

修改外观切换时，检查以下行为：

- 在系统浅色环境、无保存偏好的浏览器中打开站点，确认仍默认深色；旧值 `system` 和无效值同样回退为深色。
- 用鼠标和键盘完成三种模式循环，确认按钮文字、下一模式提示、导航入口和阅读设置入口同步更新；专注模式下仍能切换。
- 检查刷新、跨页及同源标签页同步，并验证存储受限时可在当前页切换、禁用 JavaScript 时保留深色阅读。
- 检查三套主题的正文、代码高亮、表格及焦点可见性，以及移动端按钮是否挤压站点名称或导致横向溢出。

不要删除 `_includes/head.html` 中 `assets/main.css?v=<build-revision>` 的版本参数。若发布后仍看到旧样式，应先检查页面中版本号是否已更新，再排查缓存或部署问题。
