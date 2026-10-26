#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""强征(Exaction) vs Goremonger 对刀对位 — 2026-10-26（⚠对刀引擎v1.6b未过实战验收，全表数字待验收）
口径：强征Repress=挡二仅反击+反击先手（用户定案，2026-10-16矩阵同口径）；
  GM近战词条：撕裂Rending=有暴成时1普转暴（矩阵口径）、残暴Brutal=对面普挡普非法。
  Rage(+1攻)/Gory Tenacity(受击首刀减半min2)/Enhanced Violence(半罐平衡)以变体行呈现。
  Brutish(暴伤改判普伤)=对大链斧主人时强征侧(N,C)→(N+C,0)变换——致命5+/Shock自动失效。
交叉核对锚点：剧团撕裂镰攻盾兵应=4.8/4.7；盾兵攻剧团撕裂镰应=5.2/5.8（对刀武器矩阵_2026-10-16.md L36/L42）。
"""
import importlib.util, os
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ddjsq", os.path.join(_HERE, "对刀计算器.py"))
ddjsq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ddjsq)
Duel, pool_dist = ddjsq.Duel, ddjsq.pool_dist


def mkpool(A, hit, lethal=None, rending=False, balance=0):
    """pool_dist(含平衡重投) + 撕裂后处理（同矩阵mkpool口径）。"""
    d = pool_dist(A, hit, lethal, balance)
    out = defaultdict(float)
    for (N, C), p in d.items():
        if rending and C > 0 and N > 0:
            N, C = N - 1, C + 1
        out[(N, C)] += p
    return dict(out)


def run(att, dfn, att_halve=False, dfn_halve=False, brutish_target=False, label="",
        att_start=None, dfn_start=None):
    """att攻dfn。武器=(血,A,hit,dn,dc,规则dict)。返回E_out/E_in/杀率。
    brutish_target=True: 守方带Brutish→攻方暴成全转普成(N+C,0)。
    att_start/dfn_start: 起始血（带伤冲锋场景——已受创者hit恶化1由引擎处理）。"""
    aHp, aA, aH, aDn, aDc, aR = att
    fHp, fA, fH, fDn, fDc, fR = dfn
    aSt = att_start if att_start is not None else aHp
    fSt = dfn_start if dfn_start is not None else fHp
    mp = mkpool(aA, aH + (1 if 2 * aHp < aSt else 0), aR.get("lethal"), aR.get("rending", False), aR.get("balance", 0))
    fp = mkpool(fA, fH + (1 if 2 * fHp < fSt else 0), fR.get("lethal"), fR.get("rending", False), fR.get("balance", 0))
    if brutish_target:
        mp = {(N + C, 0): p for (N, C), p in mp.items()}
    first = 1 if fR.get("defender_first") else 0
    s = Duel(aDn, aDc, fDn, fDc, aHp, fHp, aSt, fSt, first=first,
             m_shock=aR.get("shock", False), f_shock=fR.get("shock", False),
             m_block2=aR.get("block2", False), f_block2=fR.get("block2", False) or fR.get("block2_def", False),
             m_brutal=aR.get("brutal", False), f_brutal=fR.get("brutal", False),
             m_halve=att_halve, f_halve=dfn_halve)
    dist = defaultdict(float)
    for (mN, mC), p1 in mp.items():
        for (fN, fC), p2 in fp.items():
            _, (mh, fh) = s.solve(mN, mC, fN, fC, aHp, fHp, first)
            dist[(max(mh, 0), max(fh, 0))] += p1 * p2
    t = sum(dist.values())
    e_out = sum((fHp - fh) * p for (mh, fh), p in dist.items()) / t
    e_in = sum((aHp - mh) * p for (mh, fh), p in dist.items()) / t
    k_a = sum(p for (mh, fh), p in dist.items() if fh <= 0) / t
    k_d = sum(p for (mh, fh), p in dist.items() if mh <= 0) / t
    inj_d = sum(p for (mh, fh), p in dist.items() if fh > 0 and 2 * fh < fHp) / t
    return e_out, e_in, k_a, k_d, inj_d


# ── 强征（Repress=挡二仅反击+反击先手；规则dict与矩阵同键名） ──
SHIELD = (8, 4, 4, 4, 4, dict(shock=True, block2_def=True, defender_first=True))          # 盾兵 电击警棍&盾
MAUL   = (9, 4, 3, 4, 4, dict(lethal=5, shock=True, block2_def=True, defender_first=True))  # 监督官 支配锤&盾
PAIN   = (8, 4, 3, 5, 5, dict(shock=True, block2_def=True, defender_first=True))          # 惩戒官 拷问锤(裂解不建模=近战无甲)

# ── GM近战（10~11血；撕裂/残暴） ──
GLAIVE  = (10, 4, 3, 4, 5, dict(rending=True))   # Aspirant 锁链镰
BLADE   = (11, 4, 3, 4, 5, dict(rending=True))   # Herald 锁链刃
AXE     = (10, 4, 3, 5, 6, dict(brutal=True))    # Skullclaimer 大链斧
RITUAL  = (10, 4, 3, 3, 5, dict())               # Bloodtaker 仪式刃
PICKS   = (10, 4, 3, 4, 5, dict(rending=True))   # Stalker 掘裂爪
STAB    = (10, 4, 3, 3, 4, dict())               # Impaler 刺入档
# 变体
GLAIVE_R = (10, 5, 3, 4, 5, dict(rending=True))                  # 锁链镰+Rage
GLAIVE_RB = (10, 5, 3, 4, 5, dict(rending=True, balance=1))      # +Rage+Enhanced Violence(半罐平衡)
AXE_R    = (10, 5, 3, 5, 6, dict(brutal=True))                   # 大链斧+Rage
# 交叉核对用：剧团撕裂镰（8血 5/3+ 4/5 撕裂）
TR_SCY = (8, 5, 3, 4, 5, dict(rending=True))

print("== 交叉核对（应≈4.8/4.7与5.2/5.8）==")
eo, ei, ka, kd, _ = run(TR_SCY, SHIELD)
print(f"剧团撕裂镰 攻 盾兵: {eo:.1f}/{ei:.1f} (锚4.8/4.7)")
eo, ei, ka, kd, _ = run(SHIELD, TR_SCY)
print(f"盾兵 攻 剧团撕裂镰: {eo:.1f}/{ei:.1f} (锚5.2/5.8)")

print()
print("== 主表：GM冲锋（m=GM攻，强征反击先手+挡二仅反击）==")
print("格式：攻方E造/攻方E承 | GM击杀率→强征击杀率(GM受创率)")
rows = [
    ("锁链镰(Aspirant)→盾兵", GLAIVE, SHIELD, {}),
    ("锁链镰→监督官", GLAIVE, MAUL, {}),
    ("锁链镰→惩戒官", GLAIVE, PAIN, {}),
    ("锁链刃(Herald)→盾兵", BLADE, SHIELD, {}),
    ("锁链刃→监督官", BLADE, MAUL, {}),
    ("大链斧(Skullclaimer)→盾兵", AXE, SHIELD, dict(brutish=True)),
    ("大链斧→监督官", AXE, MAUL, dict(brutish=True)),
    ("大链斧→惩戒官", AXE, PAIN, dict(brutish=True)),
    ("仪式刃(Bloodtaker)→盾兵", RITUAL, SHIELD, {}),
    ("掘裂爪(Stalker)→盾兵", PICKS, SHIELD, {}),
    ("刺入档(Impaler)→盾兵", STAB, SHIELD, {}),
]
for lbl, a, f, opt in rows:
    eo, ei, ka, kd, inj = run(a, f, brutish_target=opt.get("brutish", False))
    print(f"{lbl}: {eo:.1f}/{ei:.1f} | 杀{ka*100:.0f}%↔{kd*100:.0f}% (GM受创{inj*100:.0f}%)")

print()
print("== 变体（满配冲锋 vs 盾兵/监督官）==")
for lbl, a, f, kw in [
    ("锁链镰+Rage→盾兵", GLAIVE_R, SHIELD, {}),
    ("锁链镰+Rage→监督官", GLAIVE_R, MAUL, {}),
    ("锁链镰+Rage+GoryTenacity→盾兵", GLAIVE_R, SHIELD, dict(att_halve=True)),
    ("锁链镰+Rage+EnhancedViolence→盾兵", GLAIVE_RB, SHIELD, {}),
    ("大链斧+Rage+Brutish→盾兵", AXE_R, SHIELD, dict(brutish=True)),
    ("大链斧+Rage+Brutish→监督官", AXE_R, MAUL, dict(brutish=True)),
    ("大链斧+Rage+Brutish+GoryTenacity→监督官", AXE_R, MAUL, dict(brutish=True, att_halve=True)),
]:
    eo, ei, ka, kd, inj = run(a, f, brutish_target=kw.get("brutish", False), att_halve=kw.get("att_halve", False))
    print(f"{lbl}: {eo:.1f}/{ei:.1f} | 杀{ka*100:.0f}%↔{kd*100:.0f}% (GM受创{inj*100:.0f}%)")

print()
print("== 强征主动近战（验证『别主动冲』结论）==")
for lbl, a, f in [
    ("盾兵→锁链镰", SHIELD, GLAIVE),
    ("监督官→锁链镰", MAUL, GLAIVE),
    ("惩戒官→锁链镰", PAIN, GLAIVE),
    ("惩戒官→大链斧+Brutish", PAIN, AXE),
]:
    brut = "大链斧" in lbl
    eo, ei, ka, kd, inj = run(a, f, brutish_target=brut)
    print(f"{lbl}: {eo:.1f}/{ei:.1f} | 杀{ka*100:.0f}%↔{kd*100:.0f}%")

print()
print("== 带伤冲锋线（真实到达墙边的GM：先吃了枪剩5血、受创hit恶化1；起始血10/11）==")
G5  = (5, 5, 3, 4, 5, dict(rending=True))   # 锁链镰+Rage 残5血
A5  = (5, 5, 3, 5, 6, dict(brutal=True))    # 大链斧+Rage 残5血
B6  = (6, 4, 3, 4, 5, dict(rending=True))   # Herald锁链刃 残6血
for lbl, a, f, st, kw in [
    ("锁链镰+Rage(5血)→盾兵", G5, SHIELD, 10, {}),
    ("锁链镰+Rage(5血)→监督官", G5, MAUL, 10, {}),
    ("锁链镰+Rage(5血)→惩戒官", G5, PAIN, 10, {}),
    ("大链斧+Rage(5血)+Brutish→盾兵", A5, SHIELD, 10, dict(brutish=True)),
    ("大链斧+Rage(5血)+Brutish→惩戒官", A5, PAIN, 10, dict(brutish=True)),
    ("Herald锁链刃(6血)→监督官", B6, MAUL, 11, {}),
]:
    eo, ei, ka, kd, inj = run(a, f, brutish_target=kw.get("brutish", False), att_start=st)
    print(f"{lbl}: {eo:.1f}/{ei:.1f} | 杀{ka*100:.0f}%↔{kd*100:.0f}% (强征反杀{kd*100:.0f}%)")
