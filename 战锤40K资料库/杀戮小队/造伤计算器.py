#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KT3.0 造伤概率计算器 — 精确枚举引擎（无随机模拟，结果为精确概率）。

机制依据（2026-09-21 Wahapedia核心规则页+附录核验，摘要见 规则速查.md「造伤引擎机制」节）：
  攻击骰=武器攻击数；≥命中=普成；6=恒暴成；1=恒失败；致命X+→≥X的成功按暴成保留；平衡=重投1颗失败骰
  防御骰=恒定3颗（与命中数无关）；≥防御=普成；6=暴成；1=恒失败；穿X=防御方少收集X颗
  掩体豁免=不掷骰白得1个普成（饱和=剥掉它）；遮挡=弃1颗攻击骰+暴成按普成保留
  格挡：1普成挡1普击；暴成可挡普击或暴击；2普成合挡1暴击（按防守方最优分配）
  Devastating X：每颗保留暴成立即造X伤，暴成不弃仍可砍击
  两次射击=两次独立序列；目标累计伤害≥当前血量=击杀，过量作废
注：猎潜卡宾自带穿1——同名武器规则不叠加（appendix总则），特种弹药只能给无穿1的卡宾
"""
from collections import defaultdict
from math import comb


def dice_dist(n):
    """n颗D6的全部组成 → {(c1..c6): 概率}"""
    assert 0 <= n <= 12
    dist = defaultdict(float)
    if n == 0:
        dist[(0, 0, 0, 0, 0, 0)] = 1.0
        return dict(dist)
    comp = [0] * 6

    def rec(i, left):
        if i == 5:
            comp[5] = left
            p, rem = 1.0, n
            for c in comp:
                p *= comb(rem, c)
                rem -= c
            dist[tuple(comp)] += p / 6.0 ** n
            return
        for k in range(left + 1):
            comp[i] = k
            rec(i + 1, left - k)
        comp[i] = 0

    rec(0, n)
    return dict(dist)


def _balance(dist, hit):
    """平衡：重投1颗失败骰（本引擎场景致命阈值≥命中值，失败面=1..hit-1）"""
    out = defaultdict(float)
    for comp, p in dist.items():
        ff = next((f for f in range(1, hit) if comp[f - 1] > 0), None)
        if ff is None:
            out[comp] += p
        else:
            base = list(comp)
            base[ff - 1] -= 1
            for g in range(1, 7):
                c2 = list(base)
                c2[g - 1] += 1
                out[tuple(c2)] += p / 6.0
    return dict(out)


def _discard_one(comp, hit, lethal):
    """遮挡弃1颗成功（自选，2026-09-29按核心规则原文修正：'discard one success
    of their choice instead of retaining it'——弃的是成功不是骰；无成功则不减）：
    先弃普成、无普成弃暴成；全失败=无成功可弃，分布不变"""
    c = list(comp)

    def cat(f):
        crit = f == 6 or (lethal is not None and f >= lethal)
        if f >= hit or crit:
            return 2 if crit else 1
        return 0

    for want in (1, 2):
        for f in range(1, 7):
            if c[f - 1] > 0 and cat(f) == want:
                c[f - 1] -= 1
                return tuple(c)
    return tuple(c)


def _retain(comp, hit, lethal):
    N = C = 0
    for f in range(1, 7):
        n = comp[f - 1]
        if not n:
            continue
        crit = f == 6 or (lethal is not None and f >= lethal)
        if f >= hit or crit:
            if crit:
                C += n
            else:
                N += n
    return N, C


def shoot_dist(A, hit, dmg_n, dmg_c, save, lethal=None, pierce=0,
               in_cover=False, saturate=False, obscured=False,
               balance=0, crit_d3=None, dev=None, auto_norm=0, severe=False,
               relentless=False, punishing=False, promote=False, rending=False, ceaseless=False):
    """一次射击动作的造伤分布 {伤害: 概率}

    A/ hit / dmg_n,dmg_c / save: 武器攻击数、命中值、普伤/暴伤、目标防御值
    （目标重创injured=低于半血: 命中值恶化1——hit参数直接传恶化后数值; 攻方自身重创同理; 移动力-2寸引擎不涉及）
    lethal: 致命X+（None=无）; pierce: 穿X; in_cover: 目标在掩体
    saturate: 本武器带饱和（剥掩体豁免）; obscured: 目标被遮挡
    balance: 单骰重投次数（平衡=每次掷攻骰重投1次；指挥重掷=再+1总额度）
    crit_d3: 'strike'=暴击砍穿结算时+D3 / 'retention'=每颗掷出暴击即+D3（致命一击两种读法；传其他名=静默无效）
    dev: Devastating X
    auto_norm: 精准Accurate——不掷直接留为普成的攻骰数（只掷A-auto_norm颗；用几颗玩家自选）
    """
    dist = dice_dist(A - auto_norm)
    if ceaseless:
        # 无休止: 重投自选一种点数的全部骰(附录)——最优=失败面中计数最大者
        d2 = defaultdict(float)
        for comp, p in dist.items():
            best_r, best_n = None, -1
            for f in range(1, hit):
                if f != 6 and (lethal is None or f < lethal) and comp[f-1] > best_n:
                    best_r, best_n = f, comp[f-1]
            if best_r is None or best_n == 0:
                d2[comp] += p; continue
            keep = list(comp); keep[best_r-1] = 0
            for c2, p2 in dice_dist(best_n).items():
                merged = tuple(a+b for a, b in zip(keep, c2))
                d2[merged] += p * p2
        dist = dict(d2)
    for _ in range(balance):
        dist = _balance(dist, hit)
    if relentless:
        d2 = defaultdict(float)
        for comp, p in dist.items():
            keep = [0]*6
            F = 0
            for f in range(1, 7):
                ok = f >= hit or f == 6 or (lethal is not None and f >= lethal)
                if ok: keep[f-1] = comp[f-1]
                else: F += comp[f-1]
            for c2, p2 in dice_dist(F).items():
                merged = tuple(a+b for a, b in zip(keep, c2))
                d2[merged] += p * p2
        dist = dict(d2)
    if punishing:
        d3 = defaultdict(float)
        for comp, p in dist.items():
            N, C = _retain(comp, hit, lethal)
            if C > 0:
                for f in range(1, 7):
                    ok = f >= hit or f == 6 or (lethal is not None and f >= lethal)
                    if not ok and comp[f-1] > 0:
                        # 救回的失败骰改判为普成: 移到命中面上(命中面在致命X+下仍是普成)
                        c = list(comp); c[f-1] -= 1; c[hit-1] += 1
                        d3[tuple(c)] += p
                        break
                else:
                    d3[comp] += p
            else:
                d3[comp] += p
        dist = dict(d3)
    if obscured:
        d2 = defaultdict(float)
        for c, p in dist.items():
            d2[_discard_one(c, hit, lethal)] += p
        dist = dict(d2)
    cover_save = in_cover and not saturate
    ndice = max(0, 3 - pierce)
    ddist = dice_dist(ndice)
    full = defaultdict(float)
    for comp, p in dist.items():
        N, C = _retain(comp, hit, lethal)
        if promote and N > 0:
            N -= 1; C += 1  # 普成转暴成(EMBOLDENED ASPIRANT类: 无条件一颗)
        if rending and C > 0 and N > 0:
            N -= 1; C += 1  # 撕裂Rending: 保留暴击时把1颗普成按暴成保留(附录2026-10-12)
        if severe and C == 0 and N > 0:
            N -= 1; C = 1  # 严重Severe: 未保留任何暴击时1颗普成升暴(2026-09-29按附录补)
        if obscured:
            N += C
            C = 0
        N += auto_norm  # 精准：不掷直接保留的普成
        if N + C == 0:
            full[0] += p
            continue
        for dc, dp in ddist.items():
            K = dc[5]  # 防御暴成=6
            D = sum(dc[f - 1] for f in range(max(2, save), 7)) - K  # 防御普成
            ndef = D + (1 if cover_save else 0)
            # 最优格挡：暴成先挡暴击→富余暴成挡普击→普成挡普击→富余普成两颗合挡1暴击
            c1 = min(C, K)
            spare_k = K - c1
            n1 = min(N, ndef + spare_k)
            dleft = ndef + spare_k - n1
            c2 = min(C - c1, dleft // 2)
            crit_thru = C - c1 - c2
            dmg = crit_thru * dmg_c + (N - n1) * dmg_n
            # 毁灭X(2026-09-29附录原文修正): 每颗被保留的暴击立即白给X伤——不掷防御、
            # 不可格挡、被挡也照给; 该暴击之后照常参与结算("success isn't discarded")
            if dev:
                dmg += dev * C
            k = C if crit_d3 == 'retention' else (crit_thru if crit_d3 == 'strike' else 0)
            for extra, p3 in d3_sums(k).items():
                full[dmg + extra] += p * dp * p3
    return dict(full)


def conv(a, b):
    out = defaultdict(float)
    for x, px in a.items():
        for y, py in b.items():
            out[x + y] += px * py
    return dict(out)


_D3 = {1: 1 / 3, 2: 1 / 3, 3: 1 / 3}
_d3_cache = {0: {0: 1.0}}


def d3_sums(k):
    """k颗D3之和的分布（缓存）"""
    assert 0 <= k <= 12
    if k not in _d3_cache:
        out = defaultdict(float)
        for x, px in d3_sums(k - 1).items():
            for y, py in _D3.items():
                out[x + y] += px * py
        _d3_cache[k] = dict(out)
    return _d3_cache[k]


def volley(seq, hp):
    """seq: 按结算顺序的单射分布列表 → (杀率, 期望有效造伤, 结束时残余血量分布)"""
    total = {0: 1.0}
    for d in seq:
        total = conv(total, d)
    p_kill = sum(p for x, p in total.items() if x >= hp)
    e = 0.0
    state = {hp: 1.0}
    for d in seq:
        nxt = defaultdict(float)
        for h, ph in state.items():
            if h <= 0:
                nxt[0] += ph
                continue
            for x, px in d.items():
                e += ph * px * min(x, h)
                nxt[max(0, h - x)] += ph * px
        state = dict(nxt)
    return p_kill, e, state


def report(seq, hp, save, cover, label):
    print(f"\n===== {label}（目标 防{save}+ {hp}血{'·在掩体' if cover else '·无掩体'}）=====")
    all_shots = []
    for name, nshots, kw in seq:
        ds = [shoot_dist(save=save, in_cover=cover, **kw) for _ in range(nshots)]
        unit = {0: 1.0}
        for d in ds:
            unit = conv(unit, d)
        e = sum(x * p for x, p in unit.items())
        solo = sum(p for x, p in unit.items() if x >= hp)
        print(f"{name}: 期望伤(未截断)={e:.2f}  单独杀率={solo * 100:.1f}%")
        all_shots += ds
    pk, edealt, state = volley(all_shots, hp)
    bands = [("死亡", lambda h: h == 0), ("剩1-3血", lambda h: 1 <= h <= 3),
             ("剩4-6血", lambda h: 4 <= h <= 6), ("剩7血+", lambda h: h >= 7)]
    print("  → 集火合计: 杀率={:.1f}%  期望有效造伤={:.2f}".format(pk * 100, edealt))
    print("  → 残余血量: " + "  ".join(
        "{}={:.1f}%".format(tag, sum(p for h, p in state.items() if fn(h)) * 100)
        for tag, fn in bands))


def sergeant_ladder():
    """渗透士官双射猎杀腹语师：资源阶梯（2026-09-21）
    目标 9/14血 防3+ 无掩体 无防守计策；神射爆弹卡宾 4/3+ 3/4 致命5+ ×2射（射-射-跑，跑不影响前两枪增益）
    增益：SIA穿1(装备)｜致命一击Critical Shot=暴击砍穿+D3(交战计策,TA可0CP)
          致命射击Deadly Shots=平衡(战略计策1CP)｜指挥重掷=攻骰单骰再重投1颗(交战计策,TA可0CP)
    """
    hp, save = 9, 3
    base = dict(A=4, hit=3, dmg_n=3, dmg_c=4, lethal=5)

    def shots(r1, r2, **kw):
        return [shoot_dist(save=save, balance=r1, **base, **kw),
                shoot_dist(save=save, balance=r2, **base, **kw)]

    ladder = [
        ("A 裸双射（TA留着）",                     "0CP·TA不用", shots(0, 0)),
        ("B +SIA穿1（TA留着）",                    "0CP·TA不用", shots(0, 0, pierce=1)),
        ("C B+致命一击（TA→致命一击）",            "0CP·TA花掉", shots(0, 0, pierce=1, crit_d3='strike')),
        ("F C+指挥重掷（1CP买重掷）",              "1CP·TA花掉", shots(1, 0, pierce=1, crit_d3='strike')),
        ("D C+致命射击（1CP买平衡）",              "1CP·TA花掉", shots(1, 1, pierce=1, crit_d3='strike')),
        ("E 全投入=TA→重掷+2CP买齐",               "2CP·TA花掉", shots(2, 1, pierce=1, crit_d3='strike')),
    ]
    print("\n===== 渗透士官猎杀腹语师：资源阶梯（射-射-跑·无掩体·无防守计策）=====")
    prev = None
    for name, cost, seq in ladder:
        pk, e, _ = volley(seq, hp)
        delta = "" if prev is None else "  (Δ{:+.1f}pp)".format((pk - prev) * 100)
        print(f"{name} [{cost}]: 杀率={pk * 100:.1f}%  期望有效伤={e:.2f}{delta}")
        prev = pk


def marksman_ladder():
    """先遣射手3楼单射 vs 复仇之爪老大（2026-09-21）
    目标 8/15血 防3+ 在掩体（白得1普成掩体豁免）带交战 无防守计策
    枪 猎潜卡宾 4/2+ 3/4 致命5+ 穿1；上楼2AP→本激活仅1次射击
    精准X=最多X颗攻骰不掷直留普成（逐档枚举保留颗数取杀率最优）
    """
    hp, save = 8, 3
    base = dict(A=4, hit=2, dmg_n=3, dmg_c=4, lethal=5, in_cover=True)

    def best_shot(accurate, **kw):
        out = None
        for k in range(accurate + 1):
            d = shoot_dist(save=save, auto_norm=k, **base, **kw)
            pk, e, _ = volley([d], hp)
            if out is None or pk > out[1]:
                out = (k, pk, e)
        return out

    rows = [
        ("A 裸单射",                dict()),
        ("B +SIA穿1（1装备·0CP）",  dict(pierce=1)),
        ("C B+致命一击（1CP战术）", dict(pierce=1, crit_d3='strike')),
        ("D C+指挥重掷（2CP顶格）", dict(pierce=1, crit_d3='strike', balance=1)),
    ]
    for label, acc in (("精准2（你的口径）", 2), ("精准1（标准伏击档·敏感性对照）", 1)):
        print(f"\n===== 先遣射手3楼单射 vs 老大 8/15·防3+·掩体 —— {label} =====")
        for name, kw in rows:
            k, pk, e = best_shot(acc, **kw)
            print(f"{name}: 自动保留{k}颗最优  杀率={pk * 100:.1f}%  期望伤={e:.2f}")


def breacher_ladder():
    """先遣布雷兵跑-射-射 vs 复仇之爪老大（2026-09-21）
    目标 8/15血 防3+ 在掩体（本枪自带饱和→掩体豁免被剥，含裸射）带交战 无防守计策
    枪 欧库鲁斯爆弹卡宾 4/3+ 3/4 饱和（无致命5+，暴击仅自然6）；上2楼1AP→双射
    致命射击不适用（本激活已转移）；2楼对1楼=精准1（逐档枚举保留颗数取杀率最优）
    """
    hp, save = 8, 3
    base = dict(A=4, hit=3, dmg_n=3, dmg_c=4, lethal=None,
                in_cover=True, saturate=True)

    def best_pair(accurate, r1, r2, **kw):
        out = None
        for k in range(accurate + 1):
            ds = [shoot_dist(save=save, auto_norm=k, balance=r1, **base, **kw),
                  shoot_dist(save=save, auto_norm=k, balance=r2, **base, **kw)]
            pk, e, _ = volley(ds, hp)
            if out is None or pk > out[1]:
                out = (k, pk, e)
        return out

    rows = [
        ("A 裸双射（跑-射-射）",     0, 0, dict()),
        ("B +SIA穿1（1装备·0CP）",   0, 0, dict(pierce=1)),
        ("C B+致命一击（1CP战术）",  0, 0, dict(pierce=1, crit_d3='strike')),
        ("D C+指挥重掷（2CP顶格）",  1, 0, dict(pierce=1, crit_d3='strike')),
    ]
    print("\n===== 先遣布雷兵跑-射-射 vs 老大 8/15·防3+·掩体（饱和剥豁免）·精准1 =====")
    for name, r1, r2, kw in rows:
        k, pk, e = best_pair(1, r1, r2, **kw)
        print(f"{name}: 自动保留{k}颗最优  杀率={pk * 100:.1f}%  期望伤={e:.2f}")


def duo_assignment():
    """士官站定双射的猎杀分配分析（2026-09-21）
    目标A=敌方老大 8/15 防3+ 掩体（2楼→1楼=精准1）；目标B=腹语师 9/14 防3+ 无掩体（同层3寸直击）
    士官站定双射→致命射击平衡合法；布雷兵跑射射→平衡不合法；CS=致命一击(每TP一次)
    """
    sgt = dict(A=4, hit=3, dmg_n=3, dmg_c=4, lethal=5)
    mrk = dict(A=4, hit=2, dmg_n=3, dmg_c=4, lethal=5)
    brc = dict(A=4, hit=3, dmg_n=3, dmg_c=4, lethal=None)

    def package(gun, hp, save, n=2, accurate=0, cover=False, saturate=False,
                sia=False, cs=False, bal=0, cr=False):
        rs = [bal + (1 if cr else 0)] + [bal] * (n - 1)
        out = None
        for k in range(accurate + 1):
            ds = [shoot_dist(save=save, in_cover=cover, saturate=saturate,
                             auto_norm=k, balance=r,
                             crit_d3=('strike' if cs else None), pierce=1 if sia else 0,
                             **gun) for r in rs]
            pk, e, _ = volley(ds, hp)
            if out is None or pk > out[1]:
                out = (k, pk, e)
        return out

    def show(tag, res):
        k, pk, e = res
        print(f"{tag}: 保留{k}  杀率={pk * 100:.1f}%  期望={e:.2f}")
        return pk

    print("\n===== §1 士官站定双射 → 敌方老大 8/15（掩体·精准1）=====")
    show("裸", package(sgt, 8, 3, accurate=1, cover=True))
    show("+SIA", package(sgt, 8, 3, accurate=1, cover=True, sia=True))
    show("+CS", package(sgt, 8, 3, accurate=1, cover=True, cs=True))
    show("+SIA+CS", package(sgt, 8, 3, accurate=1, cover=True, sia=True, cs=True))
    show("+SIA+CS+平衡(站定合法)", package(sgt, 8, 3, accurate=1, cover=True, sia=True, cs=True, bal=1))
    show("顶格+SIA+CS+平衡+重掷", package(sgt, 8, 3, accurate=1, cover=True, sia=True, cs=True, bal=1, cr=True))
    p_a = show("分火·单枪→老大(满配)", package(sgt, 8, 3, n=1, accurate=1, cover=True, sia=True, cs=True, bal=1, cr=True))

    print("\n===== §2 腹语师 9/14（无掩体·同层无精准）候选包 =====")
    print("— 先遣射手 站定双射（2+/致命5+）—")
    show("裸", package(mrk, 9, 3))
    show("+平衡(战略计策全场生效)", package(mrk, 9, 3, bal=1))
    show("+SIA", package(mrk, 9, 3, sia=True))
    print("— 士官 双射（3+/致命5+）—")
    show("裸(回归校验=43.2%)", package(sgt, 9, 3))
    show("+CS(TA)+平衡", package(sgt, 9, 3, cs=True, bal=1))
    show("+平衡+重掷(2CP)", package(sgt, 9, 3, bal=1, cr=True))
    print("— 布雷兵 双射（3+饱和·跑射射无平衡）—")
    show("裸", package(brc, 9, 3, saturate=True))
    show("+SIA", package(brc, 9, 3, saturate=True, sia=True))
    p_b = show("分火·单枪→腹语师(满配)", package(sgt, 9, 3, n=1, sia=True, cs=True, bal=1, cr=True))
    print(f"\n§3 士官分火（1枪老大+1枪腹语师，满配）：老大死={p_a * 100:.1f}%  腹语师死={p_b * 100:.1f}%  → 双杀={p_a * p_b * 100:.1f}%")


# ---------- 对刀模块（近战互殴，2026-09-23） ----------
def _pool_dist(n, hit):
    """n颗攻击骰(命中hit+) → {(普成, 暴成): 概率}（6恒为暴成）"""
    out = defaultdict(float)
    for comp, p in dice_dist(n).items():
        N = sum(comp[f - 1] for f in range(2, 6) if f >= hit)
        out[(N, comp[5])] += p
    return dict(out)


def _play(w, mN, mC, fN, fC, hp, ihp, i_took, hits, amb, me,
          mDn, mDc, fDn, fDc, smart=False):
    """单条决定论对刀路径（隐蔽突袭的加掷骰分三支枚举）。
    策略：双方暴击先出。smart=False（保守口径）=能挡就挡；
    smart=True（实战口径）=只挡会致命的刀，其余全部出刀换血。
    返回 [累计杀率, 累计我承伤, 累计无伤杀率, 累计两刀内杀率]"""
    out = [0.0, 0.0, 0.0, 0.0]
    while True:
        if mN + mC == 0 and fN + fC == 0:
            out[1] += w * i_took
            return out
        if me:
            if mN + mC == 0:
                me = False
                continue
            if mC > 0:
                mC -= 1; dmg = mDc
                can = fC > 0 or fN >= 2
                if can and smart and hp > dmg:
                    can = (fN + fC - 1) >= -((ihp) // -fDn)
                if can:
                    if fC > 0: fC -= 1
                    else: fN -= 2
                else:
                    hp -= dmg
            else:
                mN -= 1; dmg = mDn
                can = fN > 0 or fC > 0
                if can and smart and hp > dmg:
                    can = (fN + fC - 1) >= -((ihp) // -fDn)
                if can:
                    if fN > 0: fN -= 1
                    else: fC -= 1
                else:
                    hp -= dmg
            hits += 1
            if hp <= 0:
                out[0] += w
                out[1] += w * i_took
                out[2] += w if i_took == 0 else 0.0
                out[3] += w if hits <= 2 else 0.0
                return out
            if amb and hits == 1:
                amb = False
                for (dn, dc), pr in ((((1, 0)), 0.5), (((0, 1)), 1 / 6), (((0, 0)), 1 / 3)):
                    bN, bC, hp2 = fN, fC, hp
                    dmg2 = mDc if dc > 0 else (mDn if dn > 0 else 0)
                    if dmg2 == 0:  # 加掷挥空
                        sub = _play(w * pr, mN, mC, fN, fC, hp, ihp, i_took,
                                    hits + 1, amb, False, mDn, mDc, fDn, fDc, smart)
                        out = [o + s for o, s in zip(out, sub)]
                        continue
                    can = fC > 0 or fN >= 2
                    if can and smart and hp2 > dmg2:
                        can = (fN + fC - 1) >= -((ihp) // -fDn)
                    if can:
                        if dc > 0:
                            if fC > 0: bC = fC - 1
                            else: bN = fN - 2
                        else:
                            if fN > 0: bN = fN - 1
                            else: bC = fC - 1
                    else:
                        hp2 -= dmg2
                    if hp2 <= 0:
                        out[0] += w * pr
                        out[1] += w * pr * i_took
                        out[2] += w * pr if i_took == 0 else 0.0
                        out[3] += w * pr
                    else:
                        sub = _play(w * pr, mN, mC, bN, bC, hp2, ihp, i_took,
                                    hits + 1, amb, False, mDn, mDc, fDn, fDc, smart)
                        out = [o + s for o, s in zip(out, sub)]
                return out
            me = False
        else:
            if fN + fC == 0:
                me = True
                continue
            if fC > 0:
                fC -= 1; dmg = fDc
                can = mC > 0 or mN >= 2
                if can and smart and ihp > dmg:
                    can = (mN + mC - 1) >= -((hp) // -mDn)
                if can:
                    if mC > 0: mC -= 1
                    else: mN -= 2
                else:
                    ihp -= dmg; i_took += dmg
            else:
                fN -= 1; dmg = fDn
                can = mN > 0 or mC > 0
                if can and smart and ihp > dmg:
                    can = (mN + mC - 1) >= -((hp) // -mDn)
                if can:
                    if mN > 0: mN -= 1
                    else: mC -= 1
                else:
                    ihp -= dmg; i_took += dmg
            me = True


def fight_odds(my_wpn, foe_wpn, foe_hp, ambush=True, smart=False, my_hp=12):
    """对刀概率：my_wpn/foe_wpn=(攻击数,命中,普伤,暴伤)。
    隐蔽突袭=我方先攻，首刀结算后立刻加掷结算1颗，然后轮流。
    smart=False=保守口径（双方能挡就挡）；True=实战口径（双方只挡致命刀，其余换血）。"""
    mA, mHit, mDn, mDc = my_wpn
    fA, fHit, fDn, fDc = foe_wpn
    agg = [0.0, 0.0, 0.0, 0.0, 0.0]  # 两刀内杀/无伤杀/杀/我不挨打/我承伤
    tot = 0.0
    for (mN, mC), mp in _pool_dist(mA, mHit).items():
        for (fN, fC), fp in _pool_dist(fA, fHit).items():
            p = mp * fp
            r = _play(p, mN, mC, fN, fC, foe_hp, my_hp, 0, 0, ambush, True,
                      mDn, mDc, fDn, fDc, smart)
            agg[0] += r[3]; agg[1] += r[2]; agg[2] += r[0]
            agg[4] += r[1]
            tot += p
    return dict(two=agg[0], nodmg_kill=agg[1], kill=agg[2], e_taken=agg[4] / tot)


def melee_scenarios():
    """隐蔽突袭冲锋对刀：渗透系作战刃 5/3+ 3/4；双口径=保守(对手全挡)/实战(只挡致命)"""
    blades = (5, 3, 3, 4)
    foes = [
        ("凡人刺刀 3/4+ 2/3（DKK士兵）", (3, 4, 2, 3), 7),
        ("星际战士拳 4/3+ 3/4", (4, 3, 3, 4), 15),
        ("NC战术刀 5/3+ 4/5（斩首者）", (5, 3, 4, 5), 15),
    ]
    print("\n===== 作战刃隐蔽突袭对刀：保守口径(对手全挡) vs 实战口径(只挡致命·换血) =====")
    for foe_name, foe, full in foes:
        for case, hp in ((f"满血{full}血", full), ("补刀6血", 6), ("补刀7血", 7)):
            a = fight_odds(blades, foe, hp, smart=False)
            b = fight_odds(blades, foe, hp, smart=True)
            print(f"{foe_name}·{case}:")
            print(f"   保守: 两刀内杀{a['two'] * 100:5.1f}%  无伤杀{a['nodmg_kill'] * 100:5.1f}%"
                  f"  整场杀{a['kill'] * 100:5.1f}%  我承伤{a['e_taken']:4.2f}")
            print(f"   实战: 两刀内杀{b['two'] * 100:5.1f}%  无伤杀{b['nodmg_kill'] * 100:5.1f}%"
                  f"  整场杀{b['kill'] * 100:5.1f}%  我承伤{b['e_taken']:4.2f}")
    print("\n----- 复盘你那场：被NC级近战(按5/3+ 4/5)冲锋，你11血持作战刃防守(无隐蔽突袭) -----")
    r = fight_odds((5, 3, 4, 5), blades, 11, ambush=False, smart=True, my_hp=11)
    print(f"实战口径: 你被击杀率={r['kill'] * 100:.1f}%  你承伤期望={r['e_taken']:.2f}")
    r2 = fight_odds((5, 3, 4, 5), blades, 11, ambush=False, smart=False, my_hp=11)
    print(f"保守口径: 你被击杀率={r2['kill'] * 100:.1f}%  你承伤期望={r2['e_taken']:.2f}")


def demo():
    """演示：福博斯TP2集火复仇之爪腹语师（数据经Wahapedia Nov'25审计核验，2026-09-21）"""
    hp, save = 9, 3  # 腹语师 9/14，复仇之爪防御3+（交接文档口径）
    plan = [
        ("渗透士官 神射卡宾×2 (4/3+ 3/4 致命5+)", 2,
         dict(A=4, hit=3, dmg_n=3, dmg_c=4, lethal=5)),
        ("先遣射手 猎潜卡宾×1 (4/2+ 3/4 致命5+ 穿1)", 1,
         dict(A=4, hit=2, dmg_n=3, dmg_c=4, lethal=5, pierce=1)),
        ("先遣布雷兵 爆弹卡宾×2 (4/3+ 3/4 饱和)", 2,
         dict(A=4, hit=3, dmg_n=3, dmg_c=4, saturate=True)),
    ]
    report(plan, hp, save, cover=False, label="场景A")
    report(plan, hp, save, cover=True, label="场景B")


if __name__ == "__main__":
    for n in range(0, 9):  # 自检
        assert abs(sum(dice_dist(n).values()) - 1.0) < 1e-9
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "ladder":
        sergeant_ladder()
    elif mode == "marksman":
        marksman_ladder()
    elif mode == "breacher":
        breacher_ladder()
    elif mode == "duo":
        duo_assignment()
    elif mode == "melee":
        melee_scenarios()
    else:
        demo()
        sergeant_ladder()
        marksman_ladder()
        breacher_ladder()
        duo_assignment()
        melee_scenarios()
