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

# 血量=各武器归属者（见WEAPONS表）；受创线按各自起始血自动生效


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
    #  名称                血量  A  hit 普伤 暴伤 词条
    ("凡人刺刀",      7,  3, 4, 2, 3, dict(),                              "DKK士兵"),
    ("手斧/匕首",      8,  3, 4, 3, 4, dict(),                              "卡舍津=DKK海员"),
    ("星际战士拳",     15, 4, 3, 3, 4, dict(),                              "星际战士基准"),
    ("作战刃",        12, 5, 3, 3, 4, dict(),                              "VSM渗透者"),
    ("分子细剑",       8,  4, 3, 3, 6, dict(lethal=5),                       "Elucia"),
    ("NC战术刀",      15, 5, 3, 4, 5, dict(),                              "NC斩首者"),
    ("蛇虫骨镰",      18, 5, 3, 4, 5, dict(),                              "蛇虫战士"),
    ("首脑撕裂镰",     19, 5, 3, 4, 5, dict(rending=True),                   "蛇虫首脑"),
    ("剧团撕裂镰",      8, 5, 3, 4, 5, dict(rending=True),                   "剧团爱抚"),
    ("残暴拥抱",        8, 5, 3, 4, 5, dict(brutal=True),                    "剧团舞者"),
    ("刀刃",          8, 5, 3, 4, 6, dict(),                              "剧团舞者(主角9近似)"),
    ("动力·剧团",      9, 5, 3, 4, 6, dict(lethal=5),                        "剧团主角(刽子手8近似)"),
    ("动力·千子",     15, 5, 3, 4, 6, dict(lethal=5),                        "千子巫师"),
    ("之吻",          8, 5, 3, 3, 7, dict(),                              "剧团舞者"),
        ("镇压警棍盾",      8,  4, 4, 4, 4, dict(shock=True, block2=True, defender_first=True), "强征盾兵(Repress阵营规则)"),
    ("DW盾卫锤盾",     15, 5, 3, 4, 6, dict(shock=True, block2=True, defender_first=True), "DW盾卫(反击先手=用户卡面口径,Wahapedia未录·App终审)"),
    ("重雷神锤",       15, 5, 4, 6, 7, dict(shock=True),                      "DW破坏者"),
]


def build(A, hit, dn, dc, rules):
    pool = mkpool(A, hit, lethal=rules.get("lethal"), rending=rules.get("rending", False))
    return pool, rules


def duel_expect(a, b):
    """a攻b（a先手）→ (a期望造伤, a期望承伤)。各自归属者血量。"""
    (aHp, aA, aH, aDn, aDc, aR), (bHp, bA, bH, bDn, bDc, bR) = a, b
    mp = mkpool(aA, aH, lethal=aR.get("lethal"), rending=aR.get("rending", False))
    fp = mkpool(bA, bH, lethal=bR.get("lethal"), rending=bR.get("rending", False))
    first = 1 if bR.get("defender_first") else 0
    s = Duel(aDn, aDc, bDn, bDc, aHp, bHp, aHp, bHp, first=first,
             m_shock=aR.get("shock", False), f_shock=bR.get("shock", False),
             m_block2=aR.get("block2", False), f_block2=bR.get("block2", False),
             m_brutal=aR.get("brutal", False), f_brutal=bR.get("brutal", False))
    dist = defaultdict(float)
    for (mN, mC), p1 in mp.items():
        for (fN, fC), p2 in fp.items():
            _, (mh, fh) = s.solve(mN, mC, fN, fC, aHp, bHp, first)
            dist[(max(mh, 0), max(fh, 0))] += p1 * p2
    t = sum(dist.values())
    e_out = sum((bHp - fh) * p for (mh, fh), p in dist.items()) / t
    e_in = sum((aHp - mh) * p for (mh, fh), p in dist.items()) / t
    return e_out, e_in


def rule_tag(r):
    parts = []
    if r.get("lethal"):
        parts.append("致命5+")
    if r.get("rending"):
        parts.append("撕裂")
    if r.get("brutal"):
        parts.append("残暴")
    if r.get("shock"):
        parts.append("Shock")
    if r.get("block2"):
        parts.append("挡二")
    if r.get("defender_first"):
        parts.append("反击先手")
    return "+".join(parts) if parts else ""


def stat_tag(hp, A, H, dn, dc, r):
    t = "%d血 %d/%d+ %d/%d" % (hp, A, H, dn, dc)
    rt = rule_tag(r)
    return t + ("·" + rt if rt else "")


def main():
    ws = [(nm, (hp, A, H, dn, dc, r), src) for nm, hp, A, H, dn, dc, r, src in WEAPONS]
    names = [w[0] for w in ws]
    res = {}
    for i, (an, ap, _) in enumerate(ws):
        for j, (bn, bp, _) in enumerate(ws):
            if i == j:
                continue
            res[(i, j)] = duel_expect(ap, bp)

    # 面板清单（含词条）
    print("== 武器面板（血量 A/命中 普伤/暴伤 | 词条）==")
    for nm, (hp, A, H, dn, dc, r), src in ws:
        print("  %-8s %d血 %d/%d+ %d/%d | %-12s [%s]" % (nm, hp, A, H, dn, dc, rule_tag(r), src))

    # 全矩阵（行=攻/先手, 列=守; 格=打E/挨E）
    hdr = "%-8s%-10s" % ("攻\\守", "词条")
    for nm in names:
        hdr += "%12s" % nm[:6]
    print("\n" + hdr)
    for i, nm in enumerate(names):
        hp_, A_, H_, dn_, dc_, r_ = ws[i][1]
        row = "%-8s%-18s" % (nm[:6], stat_tag(hp_, A_, H_, dn_, dc_, r_))
        for j in range(len(names)):
            if i == j:
                row += "         ----"
            else:
                o, n = res[(i, j)]
                row += "  %4.1f/%4.1f" % (o, n)
        print(row)

    # 摘要（四列全口径: 攻方造伤/攻方承伤/守方造伤/守方承伤）
    print("\n== 摘要（跨全部12个对手的均值）==")
    print("%-10s %-18s %8s %8s %8s %8s %8s" % ("武器", "面板·词条", "攻造伤", "攻承伤", "守造伤", "守承伤", "总交换差"))
    stats = []
    for i, nm in enumerate(names):
        a_out = sum(res[(i, j)][0] for j in range(len(names)) if j != i) / (len(names) - 1)
        a_in = sum(res[(i, j)][1] for j in range(len(names)) if j != i) / (len(names) - 1)
        d_out = sum(res[(j, i)][1] for j in range(len(names)) if j != i) / (len(names) - 1)
        d_in = sum(res[(j, i)][0] for j in range(len(names)) if j != i) / (len(names) - 1)
        hp_, A_, H_, dn_, dc_, r_ = ws[i][1]
        stats.append((nm, stat_tag(hp_, A_, H_, dn_, dc_, r_), a_out, a_in, d_out, d_in, a_out + d_out - a_in - d_in))
    for nm, tag, ao, ai, do, di, diff in sorted(stats, key=lambda x: -x[6]):
        print("%-10s %-18s %8.2f %8.2f %8.2f %8.2f %+8.2f" % (nm, tag, ao, ai, do, di, diff))


if __name__ == "__main__":
    main()
