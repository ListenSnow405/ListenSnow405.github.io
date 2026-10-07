# 第六篇材料验证记录

实际核对日期：2026-10-05；系统：Windows；Python：3.11.9。在独立临时目录解压、复制与检查；没有启动模型、加载博客/用户级 Skill 或修改 Codex 配置。

## 实际完成

- D5 sources/contract copied byte-for-byte; both format files identical。
- 12 candidate records; exactly three injected errors, other nine unchanged。
- Missing-source variant removes only the complete P5 block。
- T01/T05 task bodies equal; T02 does not name the skill。
- All six complete manual-package blocks match original files; no gold input。
- SHA-256 manifest verified for every project payload file。
- Archive extracted in isolated temp directory; 14 files match; no answers/runs/active skill directory。
- Isolated two-file skill copy/rename passed; native discovery not executed。
- Fifth-chapter structural checker accepts candidate despite its three factual errors。
- Reference JSON parsed with python -m json.tool; corrections/evidence match D5 gold。
- All extracted project inputs retain their original SHA-256 after checks。

上述程序结果说明材料一致性和检查边界，不证明 Skill 已被宿主发现、选择或执行。候选三条事实错误为人为注入；正确参考 JSON 为按原资料编写的答案，不是模型输出。复制与改名用 Python 文件操作实际验证，正文中的 PowerShell/Bash 整组命令未完整执行。

## 未执行

- 原生 Skill 清单、显式调用、自然触发及五组独立模型运行。
- 跨模型、跨宿主或重复采样评估。
- token、费用、模型耗时和原生工具调用次数测量。
- 第三方 Skill 安装、凭据配置、网络调用和资料中虚构工具运行。

页面构建和响应式检查属于博客交付验证，按最终交付说明另行记录；不计为 Skill 运行证据。
