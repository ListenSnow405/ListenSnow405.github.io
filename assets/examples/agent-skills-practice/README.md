# 常用 Agent Skills 配套练习

对应文章《常用 Agent Skills 的功能与使用技巧》。课程记录、需求答复和参考结果是教学模拟；实际运行与未验证范围见 `VALIDATION.md`。

- `agent-skills-practice.zip`：解压即可得到 `project/`、`prompts/`、`templates/`，不含独立参考答案或已生成产物。
- `project/`：Python 3.10+ 标准库生成程序、六条 CSV、需求草案和原生网页。
- `prompts/`：与文章逐字同步的 P01—P10；宿主入口不同，显式选择方式按当前产品核对。
- `templates/`：空白运行记录与交接模板。
- `reference.md`：练习后核对的独立参考。
- `sources.json`：核对过的来源及入口文件摘要，不是可信度证明或 Git 提交号。
- `VALIDATION.md`：实际检查记录、未验证分支与后续维护要求。

先读 `project/README.md`，在隔离的解压目录生成页面。独立参考材料不作为被检查模型的输入。提示词、素材与模板的存在不代表已运行独立模型、原生 Skill 访谈、架构调查或文档导出。

维护时同步正文与请求、CSV 与预期结果、程序与实际验证，再重建 ZIP。`project/` 内使用普通相对路径，避免依赖博客的 Liquid 渲染。本文是独立实践专题，不改变大模型应用系列的章节编号。
