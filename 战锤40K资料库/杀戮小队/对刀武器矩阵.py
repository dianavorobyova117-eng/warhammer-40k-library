#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""近战武器全配对矩阵（2026-10-16，⚠对刀引擎v1.6未过实战验收——数字同样待验收）

去重规则（用户2026-10-16定）：数值(A/命中/普伤/暴伤)完全相同且仅差 平衡/致命5+ ⇒同类；
撕裂/残暴/Shock/挡二 等改变对刀过程的词条 ⇒不同武器。

标准局设定：双方15血满血（同一标尺使期望可比；击杀截断照常生效）、标准态度、
无计谋无支援无预伤——纯武器面板对武器面板。
攻防切换：行=攻方（先手），列=守方；格="打E/挨E"（攻方期望造伤/攻方期望承伤）。

用法：python3 对刀武器矩阵.py          # 全矩阵+摘要
"""
import importlib.util
import os
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("d2", os.path.join(_HERE, "对刀计算器.py"))
d2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d2)
Duel, dice_dist = d2.Duel, d2.dice_dist

HP = 15  # 标准局血量（双方同）


def mkpool(A, hit, lethal=None, rending=False):
    out = defaultdict(float)
    for comp, p in dice_dist(A).items():
        N = C = 0
        for f in range(1, 7):
            crit = f == 6 or (lethal is not None and f >= lethal)
            if crit:
                C += comp[f - 1]
            elif f >= hit:
                N += comp[f - 1]
        if rending and C > 0 and N > 0:
            N, C = N - 1, C + 1
        out[(N, C)] += p
    return dict(out)


# 武器清单（代表面板；同类合并注明出处）
WEAPONS = [
    #  名称              A  hit 普伤 暴伤 词条(致命/撕裂/Shock/挡二)
    ("凡人刺刀",   3, 4, 2, 3, dict(),                                  "DKK士兵刺刀"),
    ("手斧/匕首",   3, 4, 3, 4, dict(),                                  "DKK手斧=卡舍津格斗匕首(同类)"),
    ("星际战士拳",  4, 3, 3, 4, dict(),                                  "星际战士基准"),
    ("作战刃",     5, 3, 3, 4, dict(),                                  "VSM装备件"),
    ("分子细剑",   4, 3, 3, 6, dict(lethal=5),                           "Elucia(致命5+同类不单列)"),
    ("骨镰",      5, 3, 4, 5, dict(),                                  "蛇虫全系=NC斩首者刀(同类)"),
    ("撕裂镰",     5, 3, 4, 5, dict(rending=True),                       "蛇虫首脑=剧团爱抚(同类)"),
    ("残暴拥抱",   5, 3, 4, 5, dict(brutal=True),                        "剧团拥抱(残暴)"),
    ("刀刃",      5, 3, 4, 6, dict(),                                  "剧团舞者/主角"),
    ("动力武器",   5, 3, 4, 6, dict(lethal=5),                           "剧团主角=千子弯刀=星旅刽子手(同类)"),
    ("之吻",      5, 3, 3, 7, dict(),                                  "剧团"),
    ("镇压警棍盾",  4, 4, 4, 4, dict(shock=True, block2=True),             "强征盾兵(监督官支配锤4/3+同族)"),
    ("重雷神锤",   5, 4, 6, 7, dict(shock=True),                         "DW破坏者"),
]


def build(A, hit, dn, dc, rules):
    pool = mkpool(A, hit, lethal=rules.get("lethal"), rending=rules.get("rending", False))
    return pool, rules


def duel_expect(a, b):
    """a攻b（a先手）→ (a期望造伤, a期望承伤)。15/15标准局。"""
    (aA, aH, aDn, aDc, aR), (bA, bH, bDn, bDc, bR) = a, b
    mp = mkpool(aA, aH, lethal=aR.get("lethal"), rending=aR.get("rending", False))
    fp = mkpool(bA, bH, lethal=bR.get("lethal"), rending=bR.get("rending", False))
    s = Duel(aDn, aDc, bDn, bDc, HP, HP, HP, HP, first=0,
             m_shock=aR.get("shock", False), f_shock=bR.get("shock", False),
             m_block2=aR.get("block2", False), f_block2=bR.get("block2", False),
             m_brutal=aR.get("brutal", False), f_brutal=bR.get("brutal", False))
    dist = defaultdict(float)
    for (mN, mC), p1 in mp.items():
        for (fN, fC), p2 in fp.items():
            _, (mh, fh) = s.solve(mN, mC, fN, fC, HP, HP, 0)
            dist[(max(mh, 0), max(fh, 0))] += p1 * p2
    t = sum(dist.values())
    e_out = sum((HP - fh) * p for (mh, fh), p in dist.items()) / t
    e_in = sum((HP - mh) * p for (mh, fh), p in dist.items()) / t
    return e_out, e_in


def main():
    ws = [(nm, (A, H, dn, dc, r), src) for nm, A, H, dn, dc, r, src in WEAPONS]
    names = [w[0] for w in ws]
    res = {}
    for i, (an, ap, _) in enumerate(ws):
        for j, (bn, bp, _) in enumerate(ws):
            if i == j:
                continue
            res[(i, j)] = duel_expect(ap, bp)

    # 全矩阵（行=攻/先手, 列=守; 格=打E/挨E）
    hdr = "%-8s" % "攻\\守"
    for nm in names:
        hdr += "%12s" % nm[:6]
    print(hdr)
    for i, nm in enumerate(names):
        row = "%-8s" % nm[:6]
        for j in range(len(names)):
            if i == j:
                row += "         ----"
            else:
                o, n = res[(i, j)]
                row += "  %4.1f/%4.1f" % (o, n)
        print(row)

    # 摘要
    print("\n== 摘要（跨全部12个对手的均值）==")
    print("%-10s %8s %8s %8s" % ("武器", "攻期望", "守承伤", "攻防差"))
    stats = []
    for i, nm in enumerate(names):
        atk = sum(res[(i, j)][0] for j in range(len(names)) if j != i) / (len(names) - 1)
        dfn = sum(res[(j, i)][1] for j in range(len(names)) if j != i) / (len(names) - 1)
        stats.append((nm, atk, dfn, atk - dfn))
    for nm, a, d, diff in sorted(stats, key=lambda x: -x[1]):
        print("%-10s %8.2f %8.2f %+8.2f" % (nm, a, d, diff))


if __name__ == "__main__":
    main()
