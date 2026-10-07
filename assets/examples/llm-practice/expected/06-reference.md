# 第六篇独立核对依据

这是按固定来源整理的教学参考，不是模型运行记录，不作为被检查模型输入。先完成自己的任务，再查看本文件。本章不排名模型或 Skill，也没有测得原生触发率。

## 完整来源：T01、T02、T05 与手动分支

来源为完整 D5-v1、S1、S2、S3、S5、P5、E5。候选 12 条记录结构合法，三条事实错误由写作侧人为植入。每个标识合并计一条问题。

| 标识 | 候选 value/state | 应有 value/state | 必要定位 | 核对原因 |
| --- | --- | --- | --- | --- |
| BT-FILES | 8 / known | null / conflict | S2:L4、S5:L2、S5:L3 | 同版本上限为 8 与 4；没有取代、更正或条件说明 |
| RS-LICENSE | MIT / known | null / missing | S3:L8 | 未提供许可证，不能补成 MIT |
| RUN-02 | 0 / known | null / missing | E5:L2、P5:P1:L2 | 破折号表示未记录，不能补零 |

其余九条不列入 findings：LB-FILES=2/known，LB-PROTECT=true/known，LB-LICENSE=null/missing，BT-PROTECT=true/known，BT-LICENSE=MIT/known，RS-FILES=20/known，RS-PROTECT=null/missing，RUN-01=1250/known/ms，RUN-03=0/known/ms。核验仍应读取全部记录，不只查三个关键词。

完整参考审查 JSON：

```json
{
  "status": "reviewed",
  "findings": [
    {
      "record_id": "BT-FILES",
      "expected_value": null,
      "expected_state": "conflict",
      "source_refs": ["S2:L4", "S5:L2", "S5:L3"],
      "reason": "同版本说明分别为 8 与 4，S5:L3 没有说明取代、更正或不同适用条件，不能只采用 8。"
    },
    {
      "record_id": "RS-LICENSE",
      "expected_value": null,
      "expected_state": "missing",
      "source_refs": ["S3:L8"],
      "reason": "S3:L8 明确未提供许可证，不能填成 MIT。"
    },
    {
      "record_id": "RUN-02",
      "expected_value": null,
      "expected_state": "missing",
      "source_refs": ["E5:L2", "P5:P1:L2"],
      "reason": "E5:L2 为破折号，P5:P1:L2 定义其为未记录，不能转换成已知零值。"
    }
  ],
  "pending": [],
  "boundary": "仅按完整 D5-v1 固定来源、契约与候选审查教学记录；未验证真实产品，未修改输入，未保存文件。"
}
```

reason 和 boundary 的措辞允许变化；必要定位必须齐全、真实并支持修订，不能用另一工具的同号行替代。多余来源只有确实相关时接受。格式文件不是 JSON Schema 或可执行评分器，键、类型与语义由读者逐项检查。

内容正确只支持结果通过。T01 还要核对指定 Skill 的选择/加载记录；T02 的自然触发不能由正确答案推断；T05 的无 Skill 条件要查看实际清单和运行过程。手动分支只验证提供的流程与结果，不验证原生触发。

## 缺少 P5：T03

本轮只允许 sources-no-units.txt。S1—S3、S5、E5 保留；P5 完全缺失，不能读取同目录的 sources.txt。

- status 为 partial。
- findings 保留 BT-FILES、RS-LICENSE 两条确认错误及上述必要定位。
- pending 明确缺少 P5，RUN-01/02/03 的原始单位、转换与符号定义无法完整核验；候选中出现 P5 引用不代表对应原文已经取得。
- 不得引用 P5 的任何行，不照搬完整来源对 RUN-02 的结论，不把候选里的单位说明或注释当成独立证据。
- 其余工具属性仍可审查，不需要因部分缺失否定整份来源；没有修改、保存或联网。

若输出把缺失来源引用也列为问题，需要核对是否仅描述证据缺口，不能因此推断应有数值；本练习的格式约定将无法确认的部分放入 pending。

## 不适用请求：T04

自然语言要求两句生日祝福，没有指定 Skill。合格结果直接返回两句祝福，不读取资料、不选择本 Skill。此条件不使用审查 JSON 格式，不要求 status=not_applicable。后者仅适用于显式强行调用但任务不适用的可选扩展。

## 人工评分与记录

T01/T02/T05 的每条完整命中须满足 record_id、应有 value/state、必要证据、解释全部正确。记录确认问题数/3、证据完整数/3、遗漏与额外误报，另列 JSON 契约、加载、流程和边界。T03 单独按缺失条件评分，T04 按适用范围评分。

未经独立运行，所有加载、触发、耗时、工具次数与 token 项都填未执行或不可得。参考 JSON 不是实测输出；人为故障不是模型失败；首次结果与反馈后的结果分开。基础条件重复三次仍只是小样本，不足以排名或证明普遍优势。
