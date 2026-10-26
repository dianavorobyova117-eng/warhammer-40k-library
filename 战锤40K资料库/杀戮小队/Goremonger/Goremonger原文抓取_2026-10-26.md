# Goremonger 原文抓取（仅规则文本）· 2026-10-26

来源：https://wahapedia.ru/kill-team3/kill-teams/goremonger/ （WebFetch，2026-10-26）
性质：**只含机制文本，叙事/背景段落一律未抓取**（内容风控纪律）。
状态：Impaler数据卡+Drag全文已锚定；其余干员/计策/任务为建册时补充项。

## Impaler 数据卡

- APL 2 / 移动7寸 / 甲5+ / 10血 / 32mm底座
- 武器：Autopistol（4攻/4+/伤2/3，射程8寸）；Fleshskewer射击档（见下）；Fleshskewer stab近战档（4攻/3+/伤3/4，无词条）

### 独特动作 GORE-FUEL（1AP）

> "Decrease this operative's GORE TANK. Until this operative uses any profile of its fleshskewer, all profiles of it have the Severe weapon rule."

- 降一格Gore Tank → Fleshskewer所有档位获得严重Severe，直到他用掉任一档Fleshskewer为止（一次性，用完即失）。
- 限制：敌控范围内不能用；空罐不能用。

## Fleshskewer（射击档）

- 4攻 / 3+ / 伤4/5 / 射程8寸；词条：**Piercing Crits 1 + Stun + Drag**（本体不带Severe——Severe只能靠Gore-Fuel或Unbridled Aggression计策给）

### Drag全文

> "Whenever this operative is shooting with this weapon, at the start of the Resolve Attack Dice step (before inflicting damage), you can move the target up to x\"."
> "X is your total number of successful unblocked attack dice, multiplied by 2."
> "The target must be moved to a location it can be placed as close as possible to this operative, determined by the x\" you choose to use."
> "The move must be done in one or more straight-line increments, and increments are always rounded up to the nearest inch."
> "Whenever the target is dropping during that move, ignore the vertical distance."
> "Then you can discard any of your successful unblocked attack dice (in other words, you can choose not to inflict damage with any number of them)."

要点：
1. 拖拽发生在结算步开始、造伤之前；拖距按**全部**未被挡成功×2寸（骰子不被消耗）。
2. **路径=一段或多段直线增量**（可以拐弯绕行），每段向上取整到整寸。
3. **终点被钉死**：在所选x寸预算内"尽可能靠近Impaler"的可放置位置——不是任意选点。
4. 下落忽略垂直距离（免费下楼）。
5. 移动后**可选**弃任意未被挡成功（伤害与拖拽默认并存；弃骰=主动选择不造伤）。

## Sanguavitae六项（每次使用降一格罐）

**⚠逐字时机核验（2026-10-26第三次抓取，翻译差异第7案候选）**：总则原文="Each SANGUAVITAE rule specifies when it can be used"——**时机按条各写各的，激活/反应之分不是一刀切**：
- Rejuvenate："During a friendly GOREMONGER operative's **activation or counteraction**, before or after it performs an action"——**激活或反应都行**
- Mania／Fury："During ... **activation**, before or after it performs an action"——**仅激活**
- Rake："When ... performs the Charge action **during its activation**"——**仅激活**
- Surge："When ... performs the Charge or Reposition action"——**无激活限定→反应里也能开**
- Rage："When ... performs the Fight action"——**无激活限定→反应里也能开**（含Gorethirst反应的Fight）

总限制逐字："You cannot use the same SANGUAVITAE rule more than once per **activation or counteraction**"／"you cannot use more than two SANGUAVITAE rules per **activation or counteraction**"／"You cannot use Mania and Fury during the same activation."——总限制句的"or counteraction"措辞大概率就是中文翻译"激活或反应都能用"印象的来源；实际只有Rejuvenate/Surge/Rage反应可用。

| 名称 | 时机（逐字口径） | 效果 |
|---|---|---|
| Rejuvenate | **激活或反应**，动作前后 | 回复至多D3+1已损失血 |
| Mania | 仅激活，动作前后 | 至其下次激活开始APL+1 |
| Fury | 仅激活，动作前后 | 本次激活可两次Fight，第二次免费 |
| Rake | 仅激活中的Charge | 该动作移动结束后对控制范围内一名敌人造D3伤 |
| Surge | 任意Charge/Reposition（**含反应**） | 该动作结束前移动+1寸 |
| Rage | 任意Fight（**含反应**） | 该动作中近战武器攻+1 |

## Gore Tank

- 三档：full/half/empty，**开局半罐**；每次升降一格，满不加空不减。
- 充罐：己方Goremonger干员击倒"其控制范围内，或可见且2寸内"的干员时可升一格（另有干员专属充法：Bloodtaker的Ritual武器词条、Inciter的Bleeding标记）。
- 花费：用任何Sanguavitae规则/（Impaler的Gore-Fuel）时降一格。

**含义：每人开场自带半罐=自带一次性Sanguavitae/Gore-Fuel使用权，不需要击杀。"不送死卡半罐"的真实含义=对面每人有一发免费罐技，第二次开始才需要人头。**

## 全员数据卡（2026-10-26第二次抓取）

构成：1 Blood Herald（领袖）+7选（Aspirant可重复，其余各限1）。全员APL2/移7寸/甲5+/32mm。

| 干员 | 血 | 远程 | 近战 | 特殊 |
|---|---|---|---|---|
| **Blood Herald** | 11 | 圣像Icon of Khorne 4/**2+** 4/4 射8 **饱和**；autopistol | Chainblade 4/3+ 4/5 撕裂 | Khorne's Favour（激活内动作前后：空罐可升一格，每激活一次）；Impending Apotheosis（每场一次：忽略一颗攻骰的普伤） |
| **Aspirant**（可重复） | 10 | autopistol 4/4+ 2/3 射8 | Chainglaive 4/3+ 4/5 撕裂 | Obsessive Bloodlust（每TP一次：Fight结束不在敌控内→免费Charge（最多移2寸），已冲锋过也不禁，且不阻止后续Charge/Dash/Reposition） |
| **Bloodtaker** | 10 | autopistol | Ritual blade 4/3+ 3/5；Ritual（序列内首次造伤且目标在其控制范围内→可升自己一格罐，与击杀充罐叠加） | Transfusion Ritual（1AP）：降自己罐→升8寸内另一GM的罐（替代Sanguavitae；敌控内/空罐禁用） |
| **Impaler** | 10 | autopistol；**Fleshskewer**（上文全档） | Fleshskewer stab 4/3+ 3/4 无词条 | Gore-Fuel（上文） |
| **Inciter** | 10 | **聚焦**双枪 4/3+ 2/2 无休止+Dev1+撕裂；**贴脸**双枪 4/3+ 3/4 无休止+撕裂（均射8） | — | Dash and Spray（1AP：免费Dash+免费Shoot任意序，仅聚焦档；隐蔽令/敌控内禁）；Incite the Hunt（>2寸外远程击杀→升8寸内一名友方GM罐；任一双枪档非致命命中→目标获得Bleeding标记：GM激活/反击时8寸内有Bleeding敌→移除标记升自己罐） |
| **Skullclaimer** | 10 | autopistol | **Great chainaxe 4/3+ 5/6 残暴Brutal** | Brutish（任一攻骰将对本体造暴伤→可改判为普伤）；Claim Skull（每TP一次：大斧击杀→+1CP） |
| **Stalker** | 10 | autopistol | Pickrippers 4/3+ 4/5 撕裂 | Climbing Picks（垂直攀爬按2寸计）；Rooftop Stalker（本激活曾从制高点跳落或目标在制高点上→近战武器带无情） |

撕裂Rending/无休止Ceaseless/残暴Brutal等词条定义见规则速查与造伤计算器引擎（已入模；残暴近战语义=对面普挡普对本方非法，见对刀计算器v1.6）。

## Runes of Khorne（原文）

> "Each friendly GOREMONGER operative cannot lose more than 8 wounds per Shoot action."

- 按**射击动作**封顶（双射=两个动作各自封顶→两动作合计可杀10血）。
- 原型：Seek & Destroy / Recon。

## 计策全文（第二次抓取）

**战略**：
| 计策 | 效果 |
|---|---|
| Enhanced Violence | 半罐=近战武器带平衡；满罐=带无情 |
| Augmented Endurance | 被射击时：半罐=重投1颗防御骰；满罐=重投任意防御骰 |
| Gory Tenacity | 其近战/反击中，**对其造的该序列首刀伤害减半（上取整最低2）** |
| Hunt for Blood | 选一名友方：隐蔽令改交战令→免费Charge（最多移3寸） |

**交战**：
| 计策 | 效果 |
|---|---|
| Unbridled Aggression | 冲锋过的激活中近战时，掷攻骰步结束时：近战武器该序列带严重 |
| Gorethirst | 用隐蔽令GM乘隙反击：须转交战令，限Charge/Shoot/Fight |
| Destructive Demise | 被击倒移除前：对控制范围内一名敌人造伤——空罐D3/半罐D3+1/满罐D3+2 |
| Lacerate Flesh | 空罐干员激活/反击时：升罐→激活结束降罐（该降不能付Sanguavitae）；不能降则受D3 |

## 装备（4件）

| 装备 | 效果 |
|---|---|
| Gory Totem（标记） | 放己方区域、距其他标记>2寸；3寸内敌人射击/近战/反击**不能重投攻骰** |
| Bloody Cadaver（标记） | 放己方区域；友方可拾取；每个Ready阶段一名控制它的干员可升罐（敌控内禁） |
| Chaos Sigil | 每TP一次：被射击时掷防御骰步开始——来袭穿X恶化1（穿1被忽略） |
| Wrist Chains | 每TP一次射击动作：chainblade/chainglaive/great chainaxe（失去残暴）/pickrippers视作射程2寸远程至动作结束；Enhanced Violence给的平衡/无情**不**随之携带（FAQ） |

## 待建册补充项

- 任务页/装备分值、App终审项（计策CP费用）
- App级交互裁定：Repress挡二×残暴Brutal、Brutish×Shock/致命5+、Gory Tenacity×反击先手时序
