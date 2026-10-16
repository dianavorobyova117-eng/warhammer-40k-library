#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KT3.0 对刀计算器 v2 — 精确枚举 + 逐刀子博弈完美均衡（2026-10-16重建，⚠待实战验收）

替代 造伤计算器.py 中被禁用的旧对刀模块（2026-09-24未过校验。两条结构性错误：
①把射击防御骰的"2普成合挡1暴击"混进近战——近战无此规则；②做成"防御方反应式接刀"
——对刀的挡是轮到自己时主动取消对面pending骰。规则锚点见 规则速查.md 14b）。

规则口径（核心规则原文2026-10-16核验）：
  1. 双方同时掷自己近战武器的攻骰（A颗，成功≥hit，6=恒暴，1=恒败，致命X+同射击）
  2. 掷骰阶段完成全部数值修饰（平衡重投等）；结算阶段不吃受创减益
  3. 从攻击方起轮流"结算一颗自己的保留成功"——宣告：
     劈（strike）：普成结算普伤 / 暴成结算暴伤，立即扣血
     挡（block）：普成取消对面一颗pending普成；暴成取消对面pending普成或暴成
     （近战没有2普挡暴；v1不实现"空挡弃骰"设计师注场景）
  4. 一方骰尽→另一方剩余连续结算；任一方倒地→序列立即截断（核心规则下互杀不可能；
     "死后额外结算"类队伍规则属例外层，v2）
  5. 支援（控制范围内友军每名命中值+1）＝调用时直接传改善后的hit值

均衡模型（用户2026-10-16定稿v1口径）：
  单方收益 = 1000·[对面倒地] − 1000·[自己倒地] + α·(对面有效掉血) − β·(自己有效掉血)
  （有效掉血=min(伤害,剩余血)，过量作废）
  - **理智版默认 α=1, β=2**：优先级=杀对面＞自己活＞自己不掉血＞打对面。
    对称僵局（收益差全零）自发收敛"双挡0-0"；活不成时自动切"拼命换血"（最大化输出）
  - 一般和博弈（双方收益不必互为相反数）+完美信息+确定性转移→逆向归纳逐节点求解，
    每个节点由轮到方最大化**自己的**收益；平局按动作排序破平（挡＞暴劈＞普劈，
    普挡普＞暴挡普＞暴挡暴——省暴成去挡对面的暴）
  - 态度旋钮（示例值，CLI可改）：
      理智 (1,2) 默认 ｜ 均势 (1,1) ｜ 好战 (2,1) ｜ 回血 (1,1.2)
    待细化的族向（v2，见 demo 态度表打印）：伤害触发族α↑（执政官之手痛令牌/
    蛇虫毒标/圣化者圣火——打中另有收益）；回血族β↓（VSM Medic!剩D3/机械教缝合/
    猎手团冗余系统/DKK医疗包——掉血可退款）；炮灰族own-death惩罚↓＋β↓（12~14人海
    的个体价值）；濒死/死亡触发族（蛇虫死亡狂乱/洁天使殉道——可能欢迎掉血，需专用
    目标函数）。见习修女自笞=激活内自伤，不属对刀态度。

输出：双方击杀率/存活率/无伤率/掉血分布/期望 + 模态骰型逐刀最优策略轨迹。
⚠纪律：数字在过用户实战验收前一律"待验收"，禁入手册结论（速查14禁令未解除）。

用法：python3 对刀计算器.py        # 自检+演示
     python3 对刀计算器.py trace   # 只看案例逐刀轨迹
"""
from collections import defaultdict
import importlib.util
import os

# 复用射击引擎已验证件：骰组成分布与平衡重投（只import，不改动其文件）
_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("szjsq", os.path.join(_HERE, "造伤计算器.py"))
szjsq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(szjsq)
dice_dist = szjsq.dice_dist
_balance = szjsq._balance

KILL = 1000.0
# 态度预置：名称 -> (α打人权重, β挨打权重)
ATTITUDES = {
    "理智": (1.0, 2.0),
    "均势": (1.0, 1.0),
    "好战": (2.0, 1.0),
    "回血": (1.0, 1.2),
}


def pool_dist(A, hit, lethal=None, balance=0):
    """近战攻骰 -> {(普成N, 暴成C): 概率}。致命X+/平衡与射击引擎同口径。"""
    dist = dice_dist(A)
    for _ in range(balance):
        dist = _balance(dist, hit)
    out = defaultdict(float)
    for comp, p in dist.items():
        N = C = 0
        for f in range(1, 7):
            crit = f == 6 or (lethal is not None and f >= lethal)
            if crit:
                C += comp[f - 1]
            elif f >= hit:
                N += comp[f - 1]
        out[(N, C)] += p
    return dict(out)


class Duel:
    """一场对刀的逐刀博弈求解器（精确逆向归纳+记忆化）。

    m/f 侧武器各自 (普伤, 暴伤)；m0/f0 初始血；first: 0=m侧先劈（m=发起Fight方）。
    破平动作序（同收益时先列者胜）：挡(普挡普>暴挡普>暴挡暴) > 暴劈 > 普劈。
    solve() 返回 ((m收益, f收益), (m终血, f终血))；best_action() 给当前最优动作。
    """

    def __init__(self, m_dn, m_dc, f_dn, f_dc, m0, f0,
                 m_att="理智", f_att="理智", first=0):
        self.m_dn, self.m_dc = m_dn, m_dc
        self.f_dn, self.f_dc = f_dn, f_dc
        self.m0, self.f0 = m0, f0
        self.m_a, self.m_b = ATTITUDES[m_att]
        self.f_a, self.f_b = ATTITUDES[f_att]
        self.first = first
        self.memo = {}

    def _terminal(self, mhp, fhp):
        m_dealt = self.f0 - max(fhp, 0)
        f_dealt = self.m0 - max(mhp, 0)
        return ((KILL * (fhp <= 0) - KILL * (mhp <= 0) + self.m_a * m_dealt - self.m_b * f_dealt,
                 KILL * (mhp <= 0) - KILL * (fhp <= 0) + self.f_a * f_dealt - self.f_b * m_dealt),
                (mhp, fhp))

    def solve(self, mN, mC, fN, fC, mhp, fhp, turn):
        """(收益对, 终局血量对)，轮到turn方决策（0=m，1=f）。"""
        if fhp <= 0 or mhp <= 0:
            return self._terminal(mhp, fhp)
        if mN + mC + fN + fC == 0:
            return self._terminal(mhp, fhp)
        if turn == 0 and mN + mC == 0:
            turn = 1
        elif turn == 1 and fN + fC == 0:
            turn = 0
        key = (mN, mC, fN, fC, mhp, fhp, turn)
        if key in self.memo:
            return self.memo[key][0]

        # 轮到方动作清单：(标签, 下一状态参数, 收益比较键属于轮到方)
        acts = []
        if turn == 0:
            # 挡（省暴成：先用普挡普）
            if mN > 0 and fN > 0:
                acts.append(("m:普挡普", (mN - 1, mC, fN - 1, fC, mhp, fhp, 1)))
            if mC > 0 and fN > 0:
                acts.append(("m:暴挡普", (mN, mC - 1, fN - 1, fC, mhp, fhp, 1)))
            if mC > 0 and fC > 0:
                acts.append(("m:暴挡暴", (mN, mC - 1, fN, fC - 1, mhp, fhp, 1)))
            if mC > 0:
                acts.append(("m:暴劈", (mN, mC - 1, fN, fC, mhp, fhp - self.m_dc, 1)))
            if mN > 0:
                acts.append(("m:普劈", (mN - 1, mC, fN, fC, mhp, fhp - self.m_dn, 1)))
            idx = 0
        else:
            if fN > 0 and mN > 0:
                acts.append(("f:普挡普", (mN - 1, mC, fN - 1, fC, mhp, fhp, 0)))
            if fC > 0 and mN > 0:
                acts.append(("f:暴挡普", (mN - 1, mC, fN, fC - 1, mhp, fhp, 0)))
            if fC > 0 and mC > 0:
                acts.append(("f:暴挡暴", (mN, mC - 1, fN, fC - 1, mhp, fhp, 0)))
            if fC > 0:
                acts.append(("f:暴劈", (mN, mC, fN, fC - 1, mhp - self.f_dc, fhp, 0)))
            if fN > 0:
                acts.append(("f:普劈", (mN, mC, fN - 1, fC, mhp - self.f_dn, fhp, 0)))
            idx = 1

        best_val, best_label = None, None
        for label, st in acts:
            val = self.solve(*st)
            if best_val is None or val[0][idx] > best_val[0][idx]:  # 严格>：平局保先列动作
                best_val, best_label = val, label
        self.memo[key] = (best_val, best_label)
        return best_val

    def best_action(self, mN, mC, fN, fC, mhp, fhp, turn):
        """当前状态最优动作标签（轨迹展示用；solve已保证memo命中）。"""
        if fhp <= 0 or mhp <= 0 or mN + mC + fN + fC == 0:
            return None
        if turn == 0 and mN + mC == 0:
            turn = 1
        elif turn == 1 and fN + fC == 0:
            turn = 0
        self.solve(mN, mC, fN, fC, mhp, fhp, turn)
        return self.memo[(mN, mC, fN, fC, mhp, fhp, turn)][1]

    def trace(self, mN, mC, fN, fC):
        """固定骰型下的逐刀最优轨迹（教学/验收用）。"""
        mhp, fhp, turn = self.m0, self.f0, self.first
        steps = []
        while True:
            a = self.best_action(mN, mC, fN, fC, mhp, fhp, turn)
            if a is None:
                break
            steps.append("我方%d血/敌方%d血 %s" % (mhp, fhp, a))
            if a.endswith("普挡普"):
                mN, fN = mN - 1, fN - 1
            elif a.endswith("暴挡普"):
                if a[0] == "m":
                    mC, fN = mC - 1, fN - 1
                else:
                    mN, fC = mN - 1, fC - 1
            elif a.endswith("暴挡暴"):
                mC, fC = mC - 1, fC - 1
            elif a == "m:暴劈":
                mC, fhp = mC - 1, fhp - self.m_dc
            elif a == "m:普劈":
                mN, fhp = mN - 1, fhp - self.m_dn
            elif a == "f:暴劈":
                fC, mhp = fC - 1, mhp - self.f_dc
            elif a == "f:普劈":
                fN, mhp = fN - 1, mhp - self.f_dn
            turn = 1 - turn
        steps.append("终局：我方%d/%d血，敌方%d/%d血" %
                     (max(mhp, 0), self.m0, max(fhp, 0), self.f0))
        return steps


def duel(m_wpn, f_wpn, m_hp, f_hp, m_att="理智", f_att="理智", first=0):
    """全量精确枚举一场对刀。wpn=dict(A=,hit=,dn=,dc=,lethal=,balance=)。
    返回 dict(P_m_kill, P_f_kill, P_alive, P_m_clean, E_dealt, E_taken, dist)。"""
    mp = pool_dist(m_wpn["A"], m_wpn["hit"], m_wpn.get("lethal"), m_wpn.get("balance", 0))
    fp = pool_dist(f_wpn["A"], f_wpn["hit"], f_wpn.get("lethal"), f_wpn.get("balance", 0))
    solver = Duel(m_wpn["dn"], m_wpn["dc"], f_wpn["dn"], f_wpn["dc"], m_hp, f_hp,
                  m_att, f_att, first)
    dist = defaultdict(float)
    for (mN, mC), p1 in mp.items():
        for (fN, fC), p2 in fp.items():
            _, (mh, fh) = solver.solve(mN, mC, fN, fC, m_hp, f_hp, first)
            dist[(max(mh, 0), max(fh, 0))] += p1 * p2
    total = sum(dist.values())
    out = dict(
        P_m_kill=sum(p for (mh, fh), p in dist.items() if fh <= 0) / total,
        P_f_kill=sum(p for (mh, fh), p in dist.items() if mh <= 0) / total,
        P_alive=sum(p for (mh, fh), p in dist.items() if mh > 0 and fh > 0) / total,
        P_m_clean=sum(p for (mh, fh), p in dist.items() if mh >= m_hp) / total,
        E_dealt=sum((f_hp - fh) * p for (mh, fh), p in dist.items()) / total,
        E_taken=sum((m_hp - mh) * p for (mh, fh), p in dist.items()) / total,
        dist=dict(dist), solver=solver)
    return out


def report(label, r, m_hp, f_hp):
    print("\n===== %s =====" % label)
    print("我杀率=%.1f%%  我被杀率=%.1f%%  双活=%.1f%%  我无伤=%.1f%%" %
          (r["P_m_kill"] * 100, r["P_f_kill"] * 100, r["P_alive"] * 100, r["P_m_clean"] * 100))
    print("期望：我打对面%.2f血 / 我挨%.2f血" % (r["E_dealt"], r["E_taken"]))
    bands = defaultdict(float)
    for (mh, fh), p in r["dist"].items():
        tag = ("敌死" if fh <= 0 else "敌%d血" % fh) + "/" + ("我死" if mh <= 0 else "我%d血" % mh)
        bands[tag] += p
    for tag, p in sorted(bands.items(), key=lambda kv: -kv[1])[:6]:
        print("  %-12s %.1f%%" % (tag, p * 100))


def selftest():
    print("===== 自检 =====")
    # 案例A：我2暴1普 vs 敌1普，敌4血，我普3/暴4 → 首刀暴劈截断，敌方骰作废，我无伤
    d = Duel(3, 4, 3, 3, 12, 4)
    (vm, vf), (mh, fh) = d.solve(1, 2, 1, 0, 12, 4, 0)
    assert fh <= 0 and mh == 12, (mh, fh)
    print("案例A ✓ 敌方首刀即死截断、我方无伤")
    # 案例B(11血)：我2暴2普(3/4) 15血 vs 敌1暴1普(3/4) 11血 → 均衡=敌双挡保命，我-0敌-7(剩4)
    d = Duel(3, 4, 3, 4, 15, 11)
    (vm, vf), (mh, fh) = d.solve(2, 2, 1, 1, 15, 11, 0)
    assert mh == 15 and fh == 4, (mh, fh)
    print("案例B(11血) ✓ 我无伤白打7血、敌方挡刀求生（剩4血）")
    # 案例B(7血)：活不成 → 敌全力换血；我方最优=先手暴挡暴拆掉他的暴成 → 敌死，我只挨普刀3
    #   （此预期初版手算写-4被求解器纠正：拆刀线只挨3——精确求解优于手推的实证）
    d = Duel(3, 4, 3, 4, 15, 7)
    (vm, vf), (mh, fh) = d.solve(2, 2, 1, 1, 15, 7, 0)
    assert fh <= 0 and mh == 12, (mh, fh)
    print("案例B(7血) ✓ 敌必死→我先暴挡暴拆刀、敌普刀拼命换3血")
    # 对称理智：2普 vs 2普，双方15血普伤4 → 双挡0-0（用户对称僵局案例）
    d = Duel(4, 4, 4, 4, 15, 15)
    (vm, vf), (mh, fh) = d.solve(2, 0, 2, 0, 15, 15, 0)
    assert mh == 15 and fh == 15, (mh, fh)
    print("对称僵局(理智) ✓ 双挡0-0无事发生")
    # 对称好战：同局面 → 换血
    d = Duel(4, 4, 4, 4, 15, 15, m_att="好战", f_att="好战")
    (vm, vf), (mh, fh) = d.solve(2, 0, 2, 0, 15, 15, 0)
    assert mh < 15 and fh < 15, (mh, fh)
    print("对称僵局(好战) ✓ 双方选择换血 (%d-%d)" % (15 - mh, 15 - fh))
    # 单调性：攻骰更多→杀率不降；血更多→被杀率不降
    wpn_m = dict(A=5, hit=3, dn=3, dc=4)
    wpn_f = dict(A=4, hit=3, dn=3, dc=4)
    r1 = duel(wpn_m, wpn_f, 12, 15)
    r2 = duel(dict(A=6, hit=3, dn=3, dc=4), wpn_f, 12, 15)
    r3 = duel(wpn_m, wpn_f, 12, 10)
    assert r2["P_m_kill"] >= r1["P_m_kill"] - 1e-9
    assert r3["P_m_kill"] >= r1["P_m_kill"] - 1e-9
    assert abs(sum(r1["dist"].values()) - 1.0) < 1e-9
    print("单调性/归一 ✓  （A=5杀率%.1f%% ≤ A=6杀率%.1f%%；敌10血杀率%.1f%%）" %
          (r1["P_m_kill"] * 100, r2["P_m_kill"] * 100, r3["P_m_kill"] * 100))
    print("全部自检通过")


def demo():
    print("===== 态度轴可能性表（v1旋钮+待细化族向） =====")
    for k, (a, b) in ATTITUDES.items():
        print("  %s: α=%.1f β=%.1f" % (k, a, b))
    print("  待细化：伤害触发族α↑（执政官之手/蛇虫毒标/圣化者）｜回血族β↓（VSM/机械教/猎手团/DKK医疗）"
          "｜炮灰族β↓+own-death↓（人海队）｜濒死死亡触发族（蛇虫死亡狂乱/洁天使殉道，需专用目标函数）")

    # 池内镜像：NC斩首者先手砍VSM渗透者（旧模块同款场景，数字全新且待验收）
    nc = dict(A=5, hit=3, dn=4, dc=5)
    blade = dict(A=5, hit=3, dn=3, dc=4)
    report("NC斩首者(5/3+ 4/5, 15血) 先手砍 VSM渗透者(作战刃5/3+ 3/4, 12血)",
           duel(nc, blade, 15, 12), 12, 15)
    report("VSM渗透者(作战刃, 12血) 先手砍 NC斩首者(15血)",
           duel(blade, nc, 12, 15), 15, 12)
    # 用户对称案例的枚举版：双方4攻3+ 3/4 15血互砍（理智）
    report("对称精英互砍（4/3+ 3/4, 15血, 理智）", duel(dict(A=4, hit=3, dn=3, dc=4),
           dict(A=4, hit=3, dn=3, dc=4), 15, 15), 15, 15)
    report("同局但我方好战（换血意愿）", duel(dict(A=4, hit=3, dn=3, dc=4),
           dict(A=4, hit=3, dn=3, dc=4), 15, 15, m_att="好战"), 15, 15)


if __name__ == "__main__":
    import sys
    selftest()
    if len(sys.argv) > 1 and sys.argv[1] == "trace":
        print("\n===== 案例B(11血) 逐刀轨迹 =====")
        for s in Duel(3, 4, 3, 4, 15, 11).trace(2, 2, 1, 1):
            print(" ", s)
        print("\n===== 案例B(7血) 逐刀轨迹 =====")
        for s in Duel(3, 4, 3, 4, 15, 7).trace(2, 2, 1, 1):
            print(" ", s)
    else:
        demo()
        print("\n（轨迹模式：python3 对刀计算器.py trace）")
