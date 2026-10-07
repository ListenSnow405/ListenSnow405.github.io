# 第八篇程序验收快照

`validate_workflow.py` 在新的系统临时目录复制 `projects/08-agent-workflow/`，使用独立第五篇主记录夹具执行 19 项程序检查。测试临时目录保留，不删除现场；候选与确认均为程序验收，不是模型运行证据。`program-validation.json` 保存本次真实命令、退出码与输出，环境为 Windows / Python 3.11.9。

在博客根目录可复现检查，写入一个全新记录文件（不会在博客练习项目内生成 runs）：

```text
python assets/examples/llm-practice/snapshots/08-workflow-validation/validate_workflow.py --out _site/08-validation-new.json
```

脚本不在下载包内，避免独立参考夹具进入读者提取任务。摘要、故障恢复、上限、范围、确认、事实检查边界的说明见 `expected/08-validation.md`。
