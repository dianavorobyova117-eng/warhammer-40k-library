#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""强征 vs GM 死亡交换场景 — 2026-10-26（⚠对刀引擎v1.6b未过实战验收，全表待验收）
场景A：GM冲锋炮手（8血，镇压警棍3/4+ 2/3，Repress反击先手+挡二仅反击）——炮手临死反击分布。
场景B：盾兵(射击手枪4/4+ 3/3先射一轮)→冲锋挡位→满罐GM全配开近战：
  Rage(+1攻,罐full→half) + Unbridled Aggression严重(近战普转暴=池变换C==0时N-1,C+1,仅第一刀序列)
  + Gory Tenacity变体(受击首刀减半) + Fury二连(第二刀=白板武器,无Severe无Rage,GT已用)
  满罐资金链：Rage(full→half)+Fury(half→empty)=两条上限恰用满。
  Brutish(大链斧主人)=对 Skullclaimer 时强征侧保留暴成全转普成(池变换)。
未入模：Enhanced Violence满罐无情(引擎只支持平衡级重投)、Destructive Demise死后溅射(注记)。
"""
import importlib.util, os
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("dd2", os.path.join(_HERE, "对刀计算器.py"))
dd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dd)
Duel, pool_dist = dd.Duel, dd.pool_dist
_sz = importlib.util.spec_from_file_location("sz2", os.path.join(_HERE, "造伤计算器.py"))
sz = importlib.util.module_from_spec(_sz)
_sz.loader.exec_module(sz)

def mkpool(A, hit, lethal=None, rending=False, balance=0, severe=False):
    d = pool_dist(A, hit, lethal, balance)
    out = defaultdict(float)
    for (N, C), p in d.items():
        if rending and C > 0 and N > 0:
            N, C = N - 1, C + 1
        if severe and C == 0 and N > 0:   # 严重：未保留暴成时1普升暴
            N, C = N - 1, 1
        out[(N, C)] += p
    return dict(out)

def duel_dist(aWpn, fWpn, aHp, fHp, aStart, fStart, first, m_halve=False,
              a_brutal=False, brutish_att=False, brutish_def=False):
    aA, aH, aDn, aDc, aR = aWpn
    fA, fH, fDn, fDc, fR = fWpn
    mp = mkpool(aA, aH + (1 if 2 * aHp < aStart else 0), aR.get("lethal"),
                aR.get("rending", False), aR.get("balance", 0), aR.get("severe", False))
    fp = mkpool(fA, fH + (1 if 2 * fHp < fStart else 0), fR.get("lethal"),
                fR.get("rending", False), fR.get("balance", 0), fR.get("severe", False))
    if brutish_att:  # 攻方暴成全转普（对面有Brutish）
        mp = {(N + C, 0): p for (N, C), p in mp.items()}
    if brutish_def:  # 守方暴成全转普
        fp = {(N + C, 0): p for (N, C), p in fp.items()}
    s = Duel(aDn, aDc, fDn, fDc, aHp, fHp, aStart, fStart, first=first,
             m_shock=aR.get("shock", False), f_shock=fR.get("shock", False),
             m_block2=aR.get("block2", False), f_block2=fR.get("block2", False) or fR.get("block2_def", False),
             m_brutal=a_brutal, m_halve=m_halve)
    dist = defaultdict(float)
    for (mN, mC), p1 in mp.items():
        for (fN, fC), p2 in fp.items():
            _, (mh, fh) = s.solve(mN, mC, fN, fC, aHp, fHp, first)
            dist[(max(mh, 0), max(fh, 0))] += p1 * p2
    return dict(dist)

def band(dist, fHp):
    out = defaultdict(float)
    for (mh, fh), p in dist.items():
        out[(("GM死" if mh <= 0 else f"GM{mh}血") + "/" + ("目标死" if fh <= 0 else f"目标{fh}血"))] += p
    return dict(out)

# ── 武器 (A,hit,dn,dc,规则) ──
GUNNER_BATON = (3, 4, 2, 3, dict())       # 炮手镇压警棍(2026-10-26四抓:警棍词条栏为空——无Repress,用户指出)
SHIELD_MAUL  = (4, 4, 4, 4, dict(shock=True, block2_def=True, defender_first=True))  # 盾兵电击警棍&盾
GLAIVE_R     = (5, 3, 4, 5, dict(rending=True))              # 锁链镰+Rage
GLAIVE       = (4, 3, 4, 5, dict(rending=True))
GLAIVE_RS    = (5, 3, 4, 5, dict(rending=True, severe=True)) # +UA严重
AXE_RS       = (5, 3, 5, 6, dict(brutal=True, severe=True))  # 大链斧+Rage+UA
AXE_R        = (5, 3, 5, 6, dict(brutal=True))

print("== 场景A：GM冲锋炮手（炮手8血/警棍3/4+ 2/3·反击先手+挡二）==")
print("行=充电者 | 炮手反击E | P(打0) P(打2) P(打3) P(打4+) | 炮手死率 | 反杀率 | E[反击|炮手死]")
for lbl, aW, aBrutal in [("锁链镰(裸)", GLAIVE, False), ("锁链镰+Rage", GLAIVE_R, False),
                          ("大链斧+Rage", AXE_R, False)]:
    d = duel_dist(aW, GUNNER_BATON, 10, 8, 10, 8, first=1, a_brutal=aBrutal, brutish_def=False)
    t = sum(d.values())
    edealt = sum((10 - mh) * p for (mh, fh), p in d.items()) / t
    p0 = sum(p for (mh, fh), p in d.items() if mh == 10) / t
    p2 = sum(p for (mh, fh), p in d.items() if mh == 8) / t
    p3 = sum(p for (mh, fh), p in d.items() if mh == 7) / t
    p4 = sum(p for (mh, fh), p in d.items() if 10 - mh >= 4) / t
    die = sum(p for (mh, fh), p in d.items() if fh <= 0) / t
    kill = sum(p for (mh, fh), p in d.items() if mh <= 0) / t
    cd = sum((10 - mh) * p for (mh, fh), p in d.items() if fh <= 0)
    cond = cd / (die * t) if die > 0 else 0
    print(f"{lbl}: E={edealt:.2f} | 打0={p0*100:.0f}% 打2={p2*100:.0f}% 打3={p3*100:.0f}% 打4+={p4*100:.0f}% | 炮手死{die*100:.0f}% 反杀{kill*100:.0f}% | 死时E={cond:.2f}")

print()
print("== 场景B：盾兵手枪先射(4/4+ 3/3 vs 5+甲)→冲锋挡位→满罐GM全配开近战（含Fury第二刀白板）==")
pistol = sz.shoot_dist(4, 4, 3, 3, 5)
def scenario(lbl, gm_base, gm_rage_severe, gm_rage, gm_hp0, a_brutal, gt, fury=True):
    total_die = total_kill = total_both_live = 0.0
    e_shield_dealt = e_shield_taken = 0.0
    for dmg, pw in pistol.items():
        hp = gm_hp0 - dmg
        d1 = duel_dist(gm_rage_severe, SHIELD_MAUL, hp, 8, gm_hp0, 8, first=1,
                       m_halve=gt, a_brutal=a_brutal)
        for (mh, fh), p in d1.items():
            w = pw * p
            if fh <= 0:
                total_die += w; e_shield_dealt += w * (gm_hp0 - mh); e_shield_taken += w * (8 - fh); continue
            if mh <= 0:
                total_kill += w; e_shield_dealt += w * gm_hp0; e_shield_taken += w * (8 - fh); continue
            if not fury:
                total_both_live += w; e_shield_dealt += w * (gm_hp0 - mh); e_shield_taken += w * (8 - fh); continue
            # Fury第二刀：白板武器（无Rage/无Severe/GT已用）
            d2 = duel_dist(gm_base, SHIELD_MAUL, mh, fh, gm_hp0, 8, first=1, a_brutal=a_brutal)
            for (mh2, fh2), p2 in d2.items():
                w2 = w * p2
                if fh2 <= 0: total_die += w2; e_shield_dealt += w2 * (gm_hp0 - mh2); e_shield_taken += w2 * (8 - fh2)
                elif mh2 <= 0: total_kill += w2; e_shield_dealt += w2 * (gm_hp0 - mh2); e_shield_taken += w2 * (8 - fh2)
                else: total_both_live += w2; e_shield_dealt += w2 * (gm_hp0 - mh2); e_shield_taken += w2 * (8 - fh2)
    print(f"{lbl}: 盾死{total_die*100:.0f}% | GM死于反击{total_kill*100:.0f}% | 双活{total_both_live*100:.0f}% | 盾E造/承 {e_shield_dealt:.1f}/{e_shield_taken:.1f}")

scenario("Aspirant锁链镰+Rage+UA严重+Fury (10血)", GLAIVE, GLAIVE_RS, GLAIVE_R, 10, False, False)
scenario("同上+GoryTenacity(战略CP改买GT)", GLAIVE, GLAIVE_RS, GLAIVE_R, 10, False, True)
scenario("Skullclaimer大链斧+Rage+UA+Brutish+Fury (10血)", (4, 3, 5, 6, dict(brutal=True)), AXE_RS, AXE_R, 10, True, False)
scenario("Herald锁链刃+Rage+UA+Fury (11血)", (4, 3, 4, 5, dict(rending=True)), (5, 3, 4, 5, dict(rending=True, severe=True)), (5, 3, 4, 5, dict(rending=True)), 11, False, False)
scenario("裸锁链镰+Fury二连(不花罐不花CP) (10血)", GLAIVE, GLAIVE, GLAIVE, 10, False, False)
scenario("对照:裸锁链镰单刀(无Fury) (10血)", GLAIVE, GLAIVE, GLAIVE, 10, False, False, fury=False)
