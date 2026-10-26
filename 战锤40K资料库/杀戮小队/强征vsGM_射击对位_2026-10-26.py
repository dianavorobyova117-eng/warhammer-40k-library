#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""强征(Exaction) vs Goremonger 射击对位速算 — 2026-10-26（同日用户纠错后修正标注）
用已验收的造伤计算器(射击引擎)跑双向关键线。
⚠法警无双射规则（速查#15：同一动作一激活限一次；双射=阿斯塔特阵营规则，卡舍津须速射条）——
  表头"双射杀10血"一律读作"两枪集火杀10血"=两个射击动作的卷积（两干员同TP交错集火/同人跨激活）。
Runes of Khorne: 每次Shoot动作GM干员至多掉8血（按动作封顶,两枪=两动作各自封顶→合计可杀10血）;
  强征无此保护。引擎不含Augmented Endurance防守重投——本表=无防守重投基线,
  对面半罐以上时实际数字略降(标场景层)。神射手重型站桩+无双射：其"双射"行仅作纯数学对照、
  实战不可达。
"""
from 造伤计算器 import shoot_dist

def capped(dist, cap=None):
    out = {}
    for d, p in dist.items():
        k = min(d, cap) if cap else d
        out[k] = out.get(k, 0.0) + p
    return out

def E(dist):
    return sum(d * p for d, p in dist.items())

def killP(dist, hp):
    return sum(p for d, p in dist.items() if d >= hp)

def double_kill(dist, hp):
    d1 = capped(dist, 8)  # cap已在外层做过则原样
    conv = {}
    for a, pa in d1.items():
        for b, pb in d1.items():
            s = a + b
            conv[s] = conv.get(s, 0.0) + pa * pb
    return sum(p for s, p in conv.items() if s >= hp)

def row(label, dist, hp_list, cap8=False):
    d = capped(dist, 8) if cap8 else dist
    parts = [f"{E(d):5.2f}", f"{killP(d, hp_list[0])*100:5.1f}%" if len(hp_list) >= 1 else "",
             f"{double_kill(dist, hp_list[1])*100:5.1f}%" if len(hp_list) >= 2 else ""]
    return f"| {label} | " + " | ".join(parts) + " |"

S5, S4, S3 = 5, 4, 3   # GM甲5+ / 强征甲4+ / 盾兵甲3+
print("## 强征 → Goremonger（甲5+；Runes封顶8/射击动作；列=期望伤|单发杀10血|双射杀10血）")
print("| 线 | E伤(封8) | 单发杀10血 | 双射杀10血 |")
print("|---|---|---|---|")
sg       = shoot_dist(4, 3, 4, 4, S5)
sg_ver   = shoot_dist(4, 3, 4, 4, S5, lethal=5, ceaseless=True)
sg_bal   = shoot_dist(4, 3, 4, 4, S5, balance=1)
ldr      = shoot_dist(4, 2, 4, 4, S5)
ldr_ver  = shoot_dist(4, 2, 4, 4, S5, lethal=5)
marks    = shoot_dist(4, 2, 4, 0, S5, dev=4, lethal=5)
webber   = shoot_dist(4, 3, 4, 5, S5, ceaseless=True)
pistol   = shoot_dist(4, 3, 3, 3, S5)
for lbl, d in [("标准霰弹近档 4/3+ 4/4", sg),
               ("霰弹+VERISCANT(致命5+严酷)", sg_ver),
               ("霰弹+终极判决(平衡)", sg_bal),
               ("监督官近档 4/2+ 4/4", ldr),
               ("监督官近档+VERISCANT", ldr_ver),
               ("神射手站桩+OPTICS 4/2+ 4/0 Dev4致命5+", marks),
               ("网枪 4/3+ 4/5 严酷", webber),
               ("射击手枪 4/3+ 3/3", pistol)]:
    print(row(lbl, d, [10, 10], cap8=True))

print()
print("残血清理线（重创GM=命中恶化1 → hit=4+；血≤5；单发）：")
inj = shoot_dist(4, 4, 4, 4, S5, lethal=5, ceaseless=True)
print(f"| 霰弹+VERISCANT vs 重创GM(5血) | 单发杀={killP(capped(inj,8),5)*100:.1f}% |")
inj2 = shoot_dist(4, 4, 4, 4, S5)
print(f"| 裸霰弹 vs 重创GM(5血) | 单发杀={killP(capped(inj2,8),5)*100:.1f}% |")

print()
print("## Goremonger → 强征（无封顶；列=期望伤|单发杀8血[4+甲]）")
print("| 线 | E伤 | 单发杀8血 |")
print("|---|---|---|")
ap    = shoot_dist(4, 4, 2, 3, S4)
icon  = shoot_dist(4, 2, 4, 4, S4, saturate=True, in_cover=True)
icon3 = shoot_dist(4, 2, 4, 4, S3, saturate=True, in_cover=True)
icon3n= shoot_dist(4, 2, 4, 4, S3, in_cover=True)
incPb = shoot_dist(4, 3, 3, 4, S4, ceaseless=True, rending=True)
incF  = shoot_dist(4, 3, 2, 2, S4, ceaseless=True, rending=True, dev=1)
fs    = shoot_dist(4, 3, 4, 5, S4, pierce_crits=1)
fsSev = shoot_dist(4, 3, 4, 5, S4, pierce_crits=1, severe=True)
fs3   = shoot_dist(4, 3, 4, 5, S3, pierce_crits=1, severe=True)
for lbl, d in [("Autopistol 4/4+ 2/3 vs 4+甲", ap),
               ("Herald圣像 4/2+ 4/4 饱和 vs 4+甲掩体内", icon),
               ("Herald圣像 vs 盾兵3+甲掩体内(饱和)", icon3),
               ("Herald圣像 vs 盾兵3+甲掩体内(无饱和对照)", icon3n),
               ("Inciter贴脸双枪 4/3+ 3/4 无休止+撕裂 vs 4+", incPb),
               ("Inciter聚焦 4/3+ 2/2 Dev1 vs 4+", incF),
               ("Fleshskewer 4/3+ 4/5 穿暴1 vs 4+甲", fs),
               ("Fleshskewer+Gore-Fuel严重 vs 4+甲", fsSev),
               ("Fleshskewer+严重 vs 盾兵3+甲", fs3)]:
    print(f"| {lbl} | {E(d):5.2f} | {killP(d,8)*100:5.1f}% |")

print()
print("## 炮手三选对比（vs GM甲5+；列=期望伤|双射杀10血）")
frag = shoot_dist(4, 4, 2, 4, S5)
krak = shoot_dist(5, 4, 4, 5, S5, pierce=1)
for lbl, d in [("榴弹frag 4/4+ 2/4（单目标；爆炸2寸为场景层×目标数）", frag),
               ("榴弹krak 5/4+ 4/5 穿1", krak),
               ("网枪 4/3+ 4/5 严酷+晕（射12）", webber)]:
    print(f"| {lbl} | {E(capped(d,8)):5.2f} | {double_kill(d,10)*100:5.1f}% |")
