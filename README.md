# 卢怡然 C4A —— 技能提交自动评审

> 挑战：C4A 技能提交自动评审 ｜ 交付日期：2026-10-06 ｜ **v5 加固轮：2026-10-07** ｜ 截止：2026-12-31
> 一句话：**不是做一个技能，是做一个评审别人技能的东西——并且它自己也被测过。**

---

## 〇、本包里有什么

| 必交物 | 文件 |
|---|---|
| 方案设计 | `卢怡然_C4A_方案设计.md` |
| skill-evaluator | `c4-skill-evaluator/`（+ `c4-skill-evaluator.skill` 打包件） |
| 评审报告 | `卢怡然_C4A_评审报告.md`（3 份真实提交） |
| AI日志 | `卢怡然_C4A_AI日志.md` |
| 复盘 | `卢怡然_C4A_AAR.md` |
| Demo | `demo/`（一条命令 + 真跑出来的输出示例 + **真终端截图**） |

---

## 一、评审器怎么跑

```bash
# 0) 自检：17 项必须全 PASS（含无 PyYAML 环境的解析回归 + 2 项结构形态用例）
python c4-skill-evaluator/scripts/c4_evaluator.py selftest

# 1) 评审一个装着技能提交的文件夹
python c4-skill-evaluator/scripts/c4_evaluator.py evaluate "C:/群文件/C4_提交" \
    --out ./评审输出 --json ./评审输出/result.json

# 2) 测评审器自己的误判率（9 例人工标注黄金集）
python c4-skill-evaluator/scripts/golden_test.py --out ./evidence/golden.txt
```

**环境**：Python 3.9+，**零强制依赖**——有 PyYAML 就优先用 PyYAML，没有就用内置迷你解析器读评分标准（文本抽取自实现）。内置解析器与 PyYAML 的深度一致性有自检项担保（17 项里的第 2、3 项）。
`openpyxl` 可选——装了才出 Excel 详表，没装只出 Markdown/JSON，不报错。

**输出**：`C4评审报告.md`（主）+ `C4评审详表.xlsx`（可选）+ JSON（可选）。

### 行尾不变式（v5 新增，外部复核 P1 逼出来的）

Windows 上 `git clone` 默认带 `core.autocrlf=true`，工作区文本会变成 CRLF，而 `.skill` 包里是 LF——
v4 的 `build_skill_pkg.py --check` 逐字节比对，**会把 39 个"只差行尾"的文件报成内容漂移**。
护栏误报和漏报一样致命：误报多了，没人再信它。

三重防线（改 rubric/代码后仍按此验收）：
1. `.gitattributes` 写 `* -text` —— git 不做任何行尾转换；
2. 打包时文本文件统一按 LF 写入（`zipfile.ZipInfo` + `writestr`）；
3. `--check` 对文本文件先归一成 LF 再比内容，**纯行尾差异只给 warning、不计入漂移**；
   二进制文件不归一（归一 = 破坏 zip/png）。

验收证据：`evidence/克隆验收_默认配置.txt`（在**默认 autocrlf=true** 的全新克隆下 exit=0）。
自检第 17 项是这条的回归测试。

---

## 二、它判什么

### 完整性（5 槽位）

Skill 说明文档 / 可执行内容 / Demo / 教学说明 / AI 生成日志。
文件名模式 + 内容信号双通道；只命中文件名时会标注 `filename`，提示人工复核。

### 质量（4 条件 × 5–6 检测项）

| 条件 | 关注 | 真实执行的项 |
|---|---|---|
| 可复用 Reusable | 换台机器能用吗 | — |
| 可执行 Executable | 真能跑吗 | `py_compile` 语法校验、`.skill` 包解包校验 |
| 可验证 Verifiable | 怎么证明它对 | Demo 是否真实产物（读字节数、判空/判占位） |
| IO 明确 Clear I/O | 输入输出说清了没 | — |

**每条判定都带证据锚点**（`SKILL.md:78` 或 `未发现：C:\Users\, /Users/, ...`），可当场核对。

### 四条防作弊

证据锚点 / `real:true` 真实校验（缺证即 fail）/ 负信号硬地板（硬编码路径·密钥·占位符 → 封顶）/
反堆砌（重复关键词不累计加分）。

---

## 三、实测数字（不是估计）

### 3.1 评审器自己的准确率（黄金集 9 fixture）

| 指标 | 数值 |
|---|---|
| 完整性判定（n=45） | 97.8%（误报 1 例 / 7.7%，漏报 0 例） |
| 质量评级（n=36） | 精确匹配 63.9% ｜ ≤1 级 97.2%（过判 5、漏判 8） |
| **严重误判（✅↔❌）** | **1 例，2.8%** |
| 作者识别 | 9/9 |

⚠️ 精确匹配 63.9%（不是 100%）是**故意**的：测试集含边界样本，打满 100% 说明测试集太简单或标签照输出填。
原始报告：`evidence/golden_test_v3.txt`（本轮新增第 9 个 fixture `G09_flat_dir`，人工标签先写后测，机器与人工完全一致）。

### 3.2 评审 3 份真实提交的结果

| 提交 | 完整性 | 综合分 | 主要缺口 |
|---|---|---|---|
| `challenge-submit-guard`（我的 C4 技能） | 4/5 | 84.5 | Demo |
| `c4a-skill-evaluator-starter`（官方样例） | 4/5 | 84.5 | Demo |
| `wechat-doc-mapper`（基座技能） | 3/5 | 76.5 | Skill 说明文档、Demo |

原始输出：`evidence/reviews/`（每份 Markdown + Excel + JSON）。

---

## 四、目录

```
C4A/
├─ 卢怡然_C4A_方案设计.md      设计原则、架构、防作弊、测试策略、已知边界
├─ 卢怡然_C4A_评审报告.md      3 份真实提交的评审结论 + 评审器自身准确率
├─ 卢怡然_C4A_AI日志.md        时间线、AI 参与的三处、反向举证、6 条失败 + v4/v5 两轮加固
├─ 卢怡然_C4A_AAR.md           复盘：6 个失败 + 1 个未做项 + 自评
├─ README.md                   本文件
├─ .gitattributes              * -text：关掉 git 行尾转换（v5 P1 第一道防线）
├─ c4-skill-evaluator/         ★ 评审器（可独立运行）
│  ├─ SKILL.md                 技能说明（frontmatter + 用法）
│  ├─ 教学说明.md              分步教学
│  ├─ 拿来说明.md              拿了谁的 / 改了什么 / 没拿什么
│  ├─ scripts/c4_evaluator.py  引擎（含 17 项自检）
│  ├─ scripts/build_golden_set.py / golden_test.py / build_skill_pkg.py
│  ├─ references/c4_rubric_v2.yaml        机器可读评分标准
│  └─ references/golden_set/              9 个人工标注 fixture
├─ c4-skill-evaluator.skill    打包件（zip，54 个文件 / 94,766 字节，由 build_skill_pkg.py 生成）
├─ demo/                       Demo：一条命令 + 真跑出来的输出 + 真终端截图
└─ evidence/
   ├─ golden_test_v3.txt       评审器误判率实测（9 fixture）
   ├─ reviews/                 3 份真实提交的评审输出
   ├─ skill安装验证.txt        .skill 解包到另一目录后真跑的记录（含行尾限定条件）
   ├─ 克隆验收_默认配置.txt     ★ v5：默认 autocrlf=true 下全新克隆 --check exit=0
   ├─ 终端截图_取证说明.txt     ★ v5：demo 截图的三项机器核验与指纹
   ├─ 终端截图脚本.py           ★ v5：上述截图的复现脚本（Windows，仅需 Pillow）
   ├─ 解包复验脚本.py           ★ v5：.skill 解包到纯 ASCII 路径的验收五连，可一键复跑
   ├─ submit_guard_audit.txt   提交前体检报告（4/4 交付物，粗估 90.0）
   └─ 审计说明_空文件与命名告警.md   ⚠️ 评审如见「空文件」红线告警请先读它
```

> ⚠️ **给评审的提示**：自检器会报 6 个"空文件"和若干命名告警，
> 全部来自黄金测试集里**故意**造的空文件 fixture（`G07_empty_files`）与第三方参考件，
> **不是交付物缺失**——说明见 `evidence/审计说明_空文件与命名告警.md`。

`_starter/`（官方 starter）与 `_upstream/`（基座技能 wechat-doc-mapper）是挑战资料自带的参考件，
**不是我的交付物**，保留在此仅为评审对照——出处、拿了什么、没拿什么，逐项见 `c4-skill-evaluator/拿来说明.md`。

---

## 五、诚实清单（没做的事）

- [ ] **黄金集只有 1 个标注者（我自己）** —— 这是误判率数字的可信度上限，没有第二人可找，也不编
- [x] ~~没有结构类 fixture~~ **v4 补自检用例 + v5 补黄金集 fixture**：自检 2 项结构形态用例（v4）；黄金集新增 `G09_flat_dir`（v5，扁平目录 + 5/5 齐全 + 真 demo.png）
- [ ] ~~多人目录（一个文件夹装 N 个技能包）的 fixture~~ **仍未建**：`G09` 覆盖的是"扁平目录不误触发单技能包"，不是"多人目录正确分组"
- [ ] **Demo 是截图，不是录屏** —— 截图已换成真实终端实拍（见 `demo/演示.md` 第 4 节与取证说明），录屏未做
- [ ] **不用 LLM 做内容级评估** —— 刻意选择：评审器是确定性的，可复现可审计
- [ ] 不评价技能"有没有用"——那是人的活，机器不越界

---

## 六、已知缺陷（修完也要写下来）

| 缺陷 | 状态 |
|---|---|
| `scripts/` `references/` 被当成作者名 | **v3 已修**（`detect_single_skill` + `SKILL_SUBDIRS` 白名单） |
| `YOUR_` 大小写误伤 `your_file.py` | **已修**（显式 `case_sensitive`） |
| `real:true` 未实现"缺证即 fail" | **已修**（`REAL_CHECKS` 路由） |
| 负信号硬地板没接上评级 | **已修** |
| YAML 中文引号嵌套导致自检失败 | **已修** |
| **rubric 行内注释击穿内置解析器**：`min_content_hits: 2 # R1…` 让 `int()` 崩溃，无 PyYAML 环境第一条命令就挂，且自检该项在无 PyYAML 时是"自己比自己"的空转 | **v4 已修**（解析器加引号感知的行内注释剥离 + 数值兜底；自检补真检查） |
| 内置解析器转义还原与 PyYAML 不一致（`\\n`、`\\\\`、内联列表里的 `\"`） | **v4 已修**（自检升级为深度比对，靠它抓出来的） |
| 结构类输入形态无测试覆盖 | **v4 已修**（自检 2 项结构用例）+ **v5 补黄金集层**（`G09_flat_dir` 扁平目录 fixture） |
| 改 rubric 后 `.skill` 包内副本漂移 | **v4 已修**（`build_skill_pkg.py --check` 可校验；铁律写死在脚本头） |
| **防漂移护栏把 CRLF/LF 误判成漂移**（v5，外部复核 P1）：Windows 默认 `core.autocrlf=true` 克隆后，`--check` 报 39 条"内容漂移"——逐字节比对不认行尾差异。**护栏误报和漏报一样致命**：误报一多，真漂移也没人信了 | **v5 已修**（`.gitattributes` `* -text` + 包内统一 LF + 比对前行尾归一 + 纯行尾差异只 warning；自检第 17 项回归）。验收：默认配置全新克隆 exit=0（`evidence/克隆验收_默认配置.txt`） |
| **Demo 展示图是"输出排版成的终端卡片"，不是截图**（v5，P2）：rubric 写的是"视频/截图" | **v5 已修**：换成真实终端截图（`demo/终端运行展示.png`），附三项机器核验与复现脚本；录屏仍未做，如实标注 |
