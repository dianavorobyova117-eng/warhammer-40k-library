#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KT3.0 对刀计算器 v1.1 — 精确枚举 + 逐刀子博弈完美均衡（⚠待实战验收）

替代 造伤计算器.py 中被禁用的旧对刀模块（2026-09-24未过校验。两条结构性错误：
①把射击防御骰的"2普成合挡1暴击"混进近战——近战无此规则；②做成"防御方反应式接刀"
——对刀的挡是轮到自己时主动取消对面pending骰。规则锚点见 规则速查.md 14b）。

规则口径（核心规则原文2026-10-16核验）：
  1. 双方同时掷自己近战武器的攻骰（A颗，成功≥hit，6=恒暴，1=恒败，致命X+同射击）
  2. 掷骰阶段完成全部数值修饰（平衡重投等）；结算阶段不吃受创减益
  3. 从攻击方起轮流"结算一颗自己的保留成功"——宣告：
     劈（strike）：普成结算普伤 / 暴成结算暴伤，立即扣血（已结算的刀不可再挡）
     挡（block）：普成取消对面一颗pending普成；暴成取消对面pending普成或暴成
     （近战没有2普挡暴；v1不实现"空挡弃骰"设计师注场景）
  4. 一方骰尽→另一方剩余连续结算；任一方倒地→序列立即截断（核心规则下互杀不可能；
     "死后额外结算"类队伍规则属例外层，v2）
  5. 支援（控制范围内友军每名命中值+1）＝调用时直接传改善后的hit值

收益模型（用户2026-10-16第二稿口径：受创阈值资产 + 攻方效果奖励）：
  单方收益 = 1000·[对面倒地] − 1000·[自己倒地]
           + INJ·[对面新跨受创线] − INJ·[自己新跨受创线]     ← 受创线=起始血的半数
           + α·(对面有效掉血) − β·(自己有效掉血)
           + ATK·[双方终局均未受创时，攻方至少落了一刀]
  （有效掉血=min(伤害,剩余血)，过量作废）
  - 受创injured（速查19）＝血量<起始半数：移速-2寸+全系命中恶化1——**受创才是资产，
    血量只是离线的距离**。线按**起始血**算；**已受创者无新线可跨、再掉血不二次罚**
    （残血受创单位打对刀天然无所畏惧，自动涌现）
  - "血量更多的一方想用自己掉血(不受创)换对面掉血(受创)"**不需要显式规则**——阈值
    入收益后自然涌现：同样的掉血血多者不跨线、对面跨线，均衡里他自然主战
  - "双方都不受创→攻方起码换血一刀"＝ATK破平项。注意挡只能挡pending骰，攻方第一刀
    本来就能保证落地——这条实际是攻方自己的出刀偏好，不构成博弈冲突
  - INJ默认6（受创≈移速-2+命中恶化的长期损失，约4~8血当量，可调）；ATK默认2
  - 态度预置 (INJ, ATK, α, β)：
      标准 (6,2,1,1) 默认 ｜ 保守 (4,0,1,2) v1旧理智版近似（对称僵局双挡0-0）
      好战 (8,4,2,1) ｜ 回血 (3,2,1,0.6)（有医疗退款的族：掉血可回、受创可抬回线）
    待细化族向：伤害触发族α↑（执政官之手痛令牌/蛇虫毒标/圣化者圣火）；炮灰族
    own-death↓+β↓（人海队个体价值）；濒死死亡触发族（蛇虫死亡狂乱/洁天使殉道，
    需专用目标函数）。见习修女自笞=激活内自伤，不属对刀态度。

输出：双方击杀率/存活率/无伤率/**受创率**/掉血分布/期望 + 模态骰型逐刀最优策略轨迹。
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
# 态度预置：名称 -> (受创权重INJ, 攻方一刀ATK, α打人, β挨打)
ATTITUDES = {
    "标准": (6.0, 2.0, 1.0, 1.0),
    "保守": (4.0, 0.0, 1.0, 2.0),
    "好战": (8.0, 4.0, 2.0, 1.0),
    "回血": (3.0, 2.0, 1.0, 0.6),
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

    m/f 侧武器各自 (普伤, 暴伤)；m_hp/f_hp=对刀开始时血量；m_start/f_start=起始血
    （受创线=2*当前血<起始血 才算受创；默认start=当前血即满血进场）。
    first: 0=m侧先劈（m=发起Fight方）。
    破平动作序（同收益时先列者胜）：挡(普挡普>暴挡普>暴挡暴) > 暴劈 > 普劈。
    solve() 返回 ((m收益, f收益), (m终血, f终血))；best_action() 给当前最优动作。
    """

    def __init__(self, m_dn, m_dc, f_dn, f_dc, m_hp, f_hp,
                 m_start=None, f_start=None, m_att="标准", f_att="标准", first=0,
                 m_shock=False, f_shock=False, m_halve=False, f_halve=False,
                 m_block2=False, f_block2=False):
        self.m_dn, self.m_dc = m_dn, m_dc
        self.f_dn, self.f_dc = f_dn, f_dc
        self.m_hp0, self.f_hp0 = m_hp, f_hp
        self.m_start = m_start if m_start is not None else m_hp
        self.f_start = f_start if f_start is not None else f_hp
        self.m_inj, self.m_atk, self.m_a, self.m_b = ATTITUDES[m_att]
        self.f_inj, self.f_atk, self.f_a, self.f_b = ATTITUDES[f_att]
        self.first = first
        # Shock击震(附录2026-10-16核验): 每序列首次以暴成出刀时，额外弃对面一颗
        # 未结算普成(无普成则弃暴成)——树内机制，v1.2入引擎
        self.m_shock, self.f_shock = m_shock, f_shock
        # 无畏探索者类"每TP首次被攻击骰伤害减半(上取整,最低2)"(星旅者页原文2026-10-16
        # 核验——近战劈砍同适用)；1伤刀按字面会升伤不合理，实现取"只减不增"口径
        self.m_halve, self.f_halve = m_halve, f_halve
        # 镇压Repress挡二(强征页原文2026-10-16核验:"Each of your blocks can be
        # allocated to block two unresolved successes (instead of one)"——**无条件**,
        # 攻防均生效；普挡取消至多2颗敌普成、暴挡取消至多2颗合法pending[按伤害取高])
        self.m_block2, self.f_block2 = m_block2, f_block2
        self.memo = {}

    def _nblock(self, foeN, block2):
        return (min(2, foeN) if block2 else 1) if foeN > 0 else 0

    def _cblock(self, foeN, foeC, block2, dn_val, dc_val):
        """暴挡取消的(普成数,暴成数)：非挡二=1颗合法最高伤；挡二=至多2颗最高伤。"""
        if not block2:
            if foeC > 0 and dc_val >= dn_val:
                return 0, 1
            if foeN > 0:
                return 1, 0
            return 0, 1 if foeC > 0 else 0
        picks = sorted(([dn_val] * foeN + [dc_val] * foeC), reverse=True)[:2]
        return picks.count(dn_val), picks.count(dc_val)

    def _halve(self, dmg):
        """首次伤害减半：上取整、最低2、只减不增（1伤原样）。"""
        if dmg >= 2:
            return max(2, (dmg + 1) // 2)
        return dmg

    def _crossed(self, hp_end, hp_beg, start):
        """新跨受创线：终局活着且低于半数、且对刀开始时未低于（已受创不二次罚）。"""
        return 0 < hp_end and 2 * hp_end < start and 2 * hp_beg >= start

    def _terminal(self, mhp, fhp):
        mh, fh = max(mhp, 0), max(fhp, 0)
        m_dealt = self.f_hp0 - fh
        f_dealt = self.m_hp0 - mh
        m_cross = self._crossed(mh, self.m_hp0, self.m_start)
        f_cross = self._crossed(fh, self.f_hp0, self.f_start)
        calm = (mh > 0 and fh > 0 and not m_cross and not f_cross)  # 双方终局均未受创
        return ((KILL * (fh <= 0) - KILL * (mh <= 0)
                 + self.m_inj * f_cross - self.m_inj * m_cross
                 + self.m_a * m_dealt - self.m_b * f_dealt
                 + (self.m_atk if (calm and self.first == 0 and m_dealt >= 1) else 0.0),
                 KILL * (mh <= 0) - KILL * (fh <= 0)
                 + self.f_inj * m_cross - self.f_inj * f_cross
                 + self.f_a * f_dealt - self.f_b * m_dealt
                 + (self.f_atk if (calm and self.first == 1 and f_dealt >= 1) else 0.0)),
                (mh, fh))

    def solve(self, mN, mC, fN, fC, mhp, fhp, turn, msu=False, fsu=False, mhu=False, fhu=False):
        """(收益对, 终局血量对)；msu/fsu=Shock已用，mhu/fhu=减半已用。"""
        if fhp <= 0 or mhp <= 0:
            return self._terminal(mhp, fhp)
        if mN + mC + fN + fC == 0:
            return self._terminal(mhp, fhp)
        if turn == 0 and mN + mC == 0:
            turn = 1
        elif turn == 1 and fN + fC == 0:
            turn = 0
        key = (mN, mC, fN, fC, mhp, fhp, turn, msu, fsu, mhu, fhu)
        if key in self.memo:
            return self.memo[key][0]

        # 轮到方动作清单（破平序：挡[省暴成] > 暴劈 > 普劈）
        acts = []
        if turn == 0:
            if mN > 0 and fN > 0:
                k = self._nblock(fN, self.m_block2)
                acts.append(("m:普挡普", (mN - 1, mC, fN - k, fC, mhp, fhp, 1, msu, fsu, mhu, fhu)))
            if mC > 0 and fN + fC > 0:
                cn, cc = self._cblock(fN, fC, self.m_block2, self.f_dn, self.f_dc)
                acts.append(("m:暴挡", (mN, mC - 1, fN - cn, fC - cc, mhp, fhp, 1, msu, fsu, mhu, fhu)))
            if mC > 0:
                # Shock: 首次暴劈额外弃对面1颗pending普成(无普成弃暴成)
                x_fN, x_fC = fN, fC
                x_msu = msu or self.m_shock
                if self.m_shock and not msu:
                    if fN > 0:
                        x_fN = fN - 1
                    elif fC > 0:
                        x_fC = fC - 1
                # 减半: 对面每TP首次被攻击骰伤害(无畏探索者类)
                x_fhu = fhu or self.f_halve
                eff = self.m_dc
                if self.f_halve and not fhu:
                    eff = self._halve(eff)
                acts.append(("m:暴劈", (mN, mC - 1, x_fN, x_fC, mhp, fhp - eff, 1, x_msu, fsu, mhu, x_fhu)))
            if mN > 0:
                x_fhu = fhu or self.f_halve
                eff = self.m_dn
                if self.f_halve and not fhu:
                    eff = self._halve(eff)
                acts.append(("m:普劈", (mN - 1, mC, fN, fC, mhp, fhp - eff, 1, msu, fsu, mhu, x_fhu)))
            idx = 0
        else:
            if fN > 0 and mN > 0:
                k = self._nblock(mN, self.f_block2)
                acts.append(("f:普挡普", (mN - k, mC, fN - 1, fC, mhp, fhp, 0, msu, fsu, mhu, fhu)))
            if fC > 0 and mN + mC > 0:
                cn, cc = self._cblock(mN, mC, self.f_block2, self.m_dn, self.m_dc)
                acts.append(("f:暴挡", (mN - cn, mC - cc, fN, fC - 1, mhp, fhp, 0, msu, fsu, mhu, fhu)))
            if fC > 0:
                x_mN, x_mC = mN, mC
                x_fsu = fsu or self.f_shock
                if self.f_shock and not fsu:
                    if mN > 0:
                        x_mN = mN - 1
                    elif mC > 0:
                        x_mC = mC - 1
                x_mhu = mhu or self.m_halve
                eff = self.f_dc
                if self.m_halve and not mhu:
                    eff = self._halve(eff)
                acts.append(("f:暴劈", (x_mN, x_mC, fN, fC - 1, mhp - eff, fhp, 0, msu, x_fsu, x_mhu, fhu)))
            if fN > 0:
                x_mhu = mhu or self.m_halve
                eff = self.f_dn
                if self.m_halve and not mhu:
                    eff = self._halve(eff)
                acts.append(("f:普劈", (mN, mC, fN - 1, fC, mhp - eff, fhp, 0, msu, fsu, x_mhu, fhu)))
            idx = 1

        best_val, best_label = None, None
        for label, st in acts:
            val = self.solve(*st)
            if best_val is None or val[0][idx] > best_val[0][idx]:  # 严格>：平局保先列动作
                best_val, best_label = val, label
        self.memo[key] = (best_val, best_label)
        return best_val

    def best_action(self, mN, mC, fN, fC, mhp, fhp, turn, msu=False, fsu=False, mhu=False, fhu=False):
        """当前状态最优动作标签（轨迹展示用；solve已保证memo命中）。"""
        if fhp <= 0 or mhp <= 0 or mN + mC + fN + fC == 0:
            return None
        if turn == 0 and mN + mC == 0:
            turn = 1
        elif turn == 1 and fN + fC == 0:
            turn = 0
        self.solve(mN, mC, fN, fC, mhp, fhp, turn, msu, fsu, mhu, fhu)
        return self.memo[(mN, mC, fN, fC, mhp, fhp, turn, msu, fsu, mhu, fhu)][1]

    def stance_root(self, mN, mC, fN, fC, side):
        """刀锋架势层(v1.4)：序列开始前，架势方把自己的**一颗**成功提前结算为挡
        （不占正常轮换——原文"resolve one of your successes before the normal
        order"，攻防两用·2026-10-16原文核验；骰少时最优解=跳过，由收益自动判定）。
        side: 0=m方持架势, 1=f方。返回 (收益对, 终局血量对)。"""
        st0 = (mN, mC, fN, fC, self.m_hp0, self.f_hp0, self.first)
        opts = [("跳过", st0)]
        if side == 0:
            if mN > 0 and fN > 0:
                opts.append(("普挡普", (mN - 1, mC, fN - 1, fC, self.m_hp0, self.f_hp0, self.first)))
            if mC > 0 and fN > 0:
                opts.append(("暴挡普", (mN, mC - 1, fN - 1, fC, self.m_hp0, self.f_hp0, self.first)))
            if mC > 0 and fC > 0:
                opts.append(("暴挡暴", (mN, mC - 1, fN, fC - 1, self.m_hp0, self.f_hp0, self.first)))
            idx = 0
        else:
            if fN > 0 and mN > 0:
                opts.append(("普挡普", (mN - 1, mC, fN - 1, fC, self.m_hp0, self.f_hp0, self.first)))
            if fC > 0 and mN > 0:
                opts.append(("暴挡普", (mN - 1, mC, fN, fC - 1, self.m_hp0, self.f_hp0, self.first)))
            if fC > 0 and mC > 0:
                opts.append(("暴挡暴", (mN, mC - 1, fN, fC - 1, self.m_hp0, self.f_hp0, self.first)))
            idx = 1
        best = None
        for _, st in opts:
            val = self.solve(*st)
            if best is None or val[0][idx] > best[0][idx]:
                best = val
        return best

    def trace(self, mN, mC, fN, fC):
        """固定骰型下的逐刀最优轨迹（教学/验收用）。"""
        mhp, fhp, turn = self.m_hp0, self.f_hp0, self.first
        msu, fsu, mhu, fhu = False, False, False, False
        steps = []
        while True:
            a = self.best_action(mN, mC, fN, fC, mhp, fhp, turn, msu, fsu, mhu, fhu)
            if a is None:
                break
            note = ""
            if a.endswith("普挡普"):
                if a[0] == "m":
                    k = self._nblock(fN, self.m_block2)
                    mN, fN = mN - 1, fN - k
                else:
                    k = self._nblock(mN, self.f_block2)
                    fN, mN = fN - 1, mN - k
            elif a.endswith("暴挡"):
                if a[0] == "m":
                    cn, cc = self._cblock(fN, fC, self.m_block2, self.f_dn, self.f_dc)
                    mC, fN, fC = mC - 1, fN - cn, fC - cc
                else:
                    cn, cc = self._cblock(mN, mC, self.f_block2, self.m_dn, self.m_dc)
                    fC, mN, mC = fC - 1, mN - cn, mC - cc
            elif a == "m:暴劈" or a == "m:普劈":
                dmg = self.m_dc if a == "m:暴劈" else self.m_dn
                mN, mC = (mN, mC - 1) if a == "m:暴劈" else (mN - 1, mC)
                if a == "m:暴劈" and self.m_shock and not msu:
                    msu = True
                    if fN > 0:
                        fN -= 1; note = "（Shock弃敌1普成）"
                    elif fC > 0:
                        fC -= 1; note = "（Shock弃敌1暴成）"
                if self.f_halve and not fhu:
                    fhu = True; eff = self._halve(dmg); note += "（减半%d→%d）" % (dmg, eff)
                else:
                    eff = dmg
                fhp -= eff
            elif a == "f:暴劈" or a == "f:普劈":
                dmg = self.f_dc if a == "f:暴劈" else self.f_dn
                fN, fC = (fN, fC - 1) if a == "f:暴劈" else (fN - 1, fC)
                if a == "f:暴劈" and self.f_shock and not fsu:
                    fsu = True
                    if mN > 0:
                        mN -= 1; note = "（Shock弃我1普成）"
                    elif mC > 0:
                        mC -= 1; note = "（Shock弃我1暴成）"
                if self.m_halve and not mhu:
                    mhu = True; eff = self._halve(dmg); note += "（减半%d→%d）" % (dmg, eff)
                else:
                    eff = dmg
                mhp -= eff
            steps.append("我方%d血/敌方%d血 %s%s" % (mhp, fhp, a, note))
            turn = 1 - turn
        tag_m = "我死" if mhp <= 0 else ("我受创" if 2 * max(mhp, 0) < self.m_start else "我%d血" % mhp)
        tag_f = "敌死" if fhp <= 0 else ("敌受创" if 2 * max(fhp, 0) < self.f_start else "敌%d血" % fhp)
        steps.append("终局：%s（%d/%d血），%s（%d/%d血）" %
                     (tag_m, max(mhp, 0), self.m_start, tag_f, max(fhp, 0), self.f_start))
        return steps


def duel(m_wpn, f_wpn, m_hp, f_hp, m_start=None, f_start=None,
         m_att="标准", f_att="标准", first=0):
    """全量精确枚举一场对刀。wpn=dict(A=,hit=,dn=,dc=,lethal=,balance=)。
    start缺省=当前血（**默认满血进场**——用户2026-10-16定：除非点名"某血量的xxx带增益"
    类场景，否则一律按满血算）。**出刀开始已受创者（2*当前血<起始血）掷骰阶段命中值
    恶化1**（速查19，3+→4+；结算阶段仍不触发、中途跨线不回头改骰）。
    返回 dict(P_m_kill, P_f_kill, P_alive, P_m_clean, P_m_inj, P_f_inj, E_dealt, E_taken, dist)。"""
    m_st = m_start if m_start is not None else m_hp
    f_st = f_start if f_start is not None else f_hp
    m_hit = m_wpn["hit"] + (1 if 2 * m_hp < m_st else 0)
    f_hit = f_wpn["hit"] + (1 if 2 * f_hp < f_st else 0)
    mp = pool_dist(m_wpn["A"], m_hit, m_wpn.get("lethal"), m_wpn.get("balance", 0))
    fp = pool_dist(f_wpn["A"], f_hit, f_wpn.get("lethal"), f_wpn.get("balance", 0))
    solver = Duel(m_wpn["dn"], m_wpn["dc"], f_wpn["dn"], f_wpn["dc"], m_hp, f_hp,
                  m_start, f_start, m_att, f_att, first,
                  m_shock=m_wpn.get("shock", False), f_shock=f_wpn.get("shock", False))
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
        P_m_inj=sum(p for (mh, fh), p in dist.items() if mh > 0 and 2 * mh < m_st) / total,
        P_f_inj=sum(p for (mh, fh), p in dist.items() if fh > 0 and 2 * fh < f_st) / total,
        E_dealt=sum((f_hp - fh) * p for (mh, fh), p in dist.items()) / total,
        E_taken=sum((m_hp - mh) * p for (mh, fh), p in dist.items()) / total,
        dist=dict(dist), solver=solver)
    return out


def report(label, r, m_hp, f_hp):
    print("\n===== %s =====" % label)
    print("我杀=%.1f%% 我被杀=%.1f%% 双活=%.1f%%  我无伤=%.1f%%  敌受创=%.1f%% 我受创=%.1f%%" %
          (r["P_m_kill"] * 100, r["P_f_kill"] * 100, r["P_alive"] * 100,
           r["P_m_clean"] * 100, r["P_f_inj"] * 100, r["P_m_inj"] * 100))
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
    # 案例B(11血)：我2暴2普(3/4) 15血 vs 敌1暴1普(3/4) 11血 → 我无伤白打7血、敌挡刀求生(剩4血且受创)
    d = Duel(3, 4, 3, 4, 15, 11)
    (vm, vf), (mh, fh) = d.solve(2, 2, 1, 1, 15, 11, 0)
    assert mh == 15 and fh == 4, (mh, fh)
    print("案例B(11血) ✓ 我无伤白打7血、敌方终局4血（已跨受创线≤5）")
    # 案例B(7血)：敌必死 → 我先手暴挡暴拆他的暴成，他普刀拼命换3血（初版手算-4被求解器纠正）
    d = Duel(3, 4, 3, 4, 15, 7)
    (vm, vf), (mh, fh) = d.solve(2, 2, 1, 1, 15, 7, 0)
    assert fh <= 0 and mh == 12, (mh, fh)
    print("案例B(7血) ✓ 敌必死→我先暴挡暴拆刀、敌普刀拼命换3血")
    # 血量优势局(v1.1新口径)：我15/15 vs 敌8/8，同样骰型 → 敌双挡也拦不住跨线(受创线≤3)
    d = Duel(3, 4, 3, 4, 15, 8, m_start=15, f_start=8)
    (vm, vf), (mh, fh) = d.solve(2, 2, 1, 1, 15, 8, 0)
    assert mh == 15 and fh == 1, (mh, fh)
    print("血量优势局 ✓ 我无伤把8血敌打到1血(深度受创)——'血多换对面受创'由阈值自然涌现")
    # 对称无跨线局(v1.1新口径)：双方15/15(2普,4/4) → 攻方一刀落地、防方挡余+尾刀回敬=11-11
    d = Duel(4, 4, 4, 4, 15, 15)
    (vm, vf), (mh, fh) = d.solve(2, 0, 2, 0, 15, 15, 0)
    assert mh == 11 and fh == 11, (mh, fh)
    print("对称无跨线 ✓ 攻方起码一刀落地(4-4)、不再0-0")
    # 保守预置回归：同局用保守(ATK=0,β=2) → 双挡0-0（v1理智行为保留为预置）
    d = Duel(4, 4, 4, 4, 15, 15, m_att="保守", f_att="保守")
    (vm, vf), (mh, fh) = d.solve(2, 0, 2, 0, 15, 15, 0)
    assert mh == 15 and fh == 15, (mh, fh)
    print("对称无跨线(保守预置) ✓ 双挡0-0（旧理智行为保留为预置）")
    # 已受创者无新线可跨：我7/15(已受创) vs 敌15/15对称 → 我更敢打(无二次罚)
    d1 = Duel(4, 4, 4, 4, 7, 15, m_start=15)          # 我已受创
    (v1, _), (mh1, fh1) = d1.solve(2, 0, 2, 0, 7, 15, 0)
    d2 = Duel(4, 4, 4, 4, 15, 15)                     # 对照：我满血
    (v2, _), (mh2, fh2) = d2.solve(2, 0, 2, 0, 15, 15, 0)
    assert v1 >= v2  # 我方收益不因已受创而进一步恶化（价值函数无二次罚；骰型固定）
    print("已受创不二次罚 ✓ （已受创方收益%.2f ≥ 满血对照%.2f）" % (v1, v2))
    # 出刀前已受创→掷骰阶段命中恶化1（速查19，用户2026-10-16补）：同武器同血杀率必须更低
    r_full = duel(dict(A=5, hit=3, dn=4, dc=5), dict(A=5, hit=3, dn=3, dc=4), 15, 12)
    r_inj = duel(dict(A=5, hit=3, dn=4, dc=5), dict(A=5, hit=3, dn=3, dc=4), 7, 12, m_start=15)
    assert r_inj["P_m_kill"] <= r_full["P_m_kill"] + 1e-9
    print("出刀前已受创掷骰恶化 ✓ （满血杀率%.1f%% ≥ 受创杀率%.1f%%）" %
          (r_full["P_m_kill"] * 100, r_inj["P_m_kill"] * 100))
    # Shock击震方向性(v1.2): 带Shock一方收益不低于无Shock同款（首暴劈白弃对面一骰）
    d_s = Duel(3, 4, 3, 3, 12, 12, m_shock=True)
    d_n = Duel(3, 4, 3, 3, 12, 12)
    (vs, _), _ = d_s.solve(0, 1, 2, 0, 12, 12, 0)
    (vn, _), _ = d_n.solve(0, 1, 2, 0, 12, 12, 0)
    assert vs >= vn - 1e-9, (vs, vn)
    print("Shock击震方向性 ✓ （带%.2f ≥ 无%.2f——首暴劈弃掉敌1普成）" % (vs, vn))
    # 首伤减半方向性(v1.3): 带减半方承伤更低（首刀6→3）；只减首次
    d_h = Duel(3, 4, 3, 6, 15, 15, m_halve=True)
    d_n2 = Duel(3, 4, 3, 6, 15, 15)
    (_, _), (mh_h, _) = d_h.solve(0, 0, 0, 2, 15, 15, 1)
    (_, _), (mh_n, _) = d_n2.solve(0, 0, 0, 2, 15, 15, 1)
    assert mh_h == 6 and mh_n == 3, (mh_h, mh_n)  # 敌2暴: 无减半吃12→剩3; 减半吃9→剩6
    print("首伤减半 ✓ （敌两暴6/6: 无减半吃12血, 减半后吃%d血——首刀6→3）" % (15 - mh_h))
    # 刀锋架势方向性(v1.4): 持架势方收益≥无架势同款（攻防两用；最优解可自动跳过）
    d_t = Duel(4, 4, 4, 4, 15, 15)
    (vn2, _), _ = d_t.solve(2, 0, 1, 0, 15, 15, 0)
    (vs2, _), _ = d_t.stance_root(2, 0, 1, 0, 0)
    assert vs2 >= vn2 - 1e-9, (vs2, vn2)
    print("刀锋架势 ✓ （攻方2普vs1普: 无架势打4血, 带架势开局垫挡后打%.0f血——不占先手刀）"
          % (vs2,))
    # 镇压挡二方向性(v1.5): 挡二方承伤更低（一颗暴挡吃掉对面两颗普成）
    d_b2 = Duel(3, 3, 4, 4, 15, 15, f_block2=True)
    d_b0 = Duel(3, 3, 4, 4, 15, 15)
    (_, _), (mh2, fh2) = d_b2.solve(2, 0, 0, 1, 15, 15, 0)   # 攻2普 vs 守1暴
    (_, _), (mh0, fh0) = d_b0.solve(2, 0, 0, 1, 15, 15, 0)
    assert mh2 >= mh0, (mh2, mh0)
    print("镇压挡二 ✓ （守方1暴挡我2普: 无镇压我终%d血, 带镇压%d血）" % (mh0, mh2))
    # 单调性：攻骰更多→杀率不降；敌血更低→杀率不降；分布归一
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
    print("===== 态度预置 (INJ受创权重, ATK攻方一刀, α, β) =====")
    for k, v in ATTITUDES.items():
        print("  %s: %s" % (k, v))

    # 池内对局组合（武器面板出处：NC战术刀/星际战士拳=旧模块测试集面板沿用，
    # VSM作战刃=Nov'25手册，DKK手斧=速查13条，卡舍津格斗匕首=2026-10-16核验。
    # ⚠全部数字待实战验收）
    nc = dict(A=5, hit=3, dn=4, dc=5)      # NC斩首者战术刀
    blade = dict(A=5, hit=3, dn=3, dc=4)   # VSM作战刃
    axe = dict(A=3, hit=4, dn=3, dc=4)     # DKK手斧
    dagger = dict(A=3, hit=4, dn=3, dc=4)  # 卡舍津格斗匕首
    fist = dict(A=4, hit=3, dn=3, dc=4)    # 星际战士拳

    report("① NC斩首者(15血) 先手砍 VSM渗透者(作战刃, 12血)",
           duel(nc, blade, 15, 12), 12, 15)
    report("② VSM渗透者(12血) 先手反砍 NC斩首者(15血)",
           duel(blade, nc, 12, 15), 15, 12)
    report("③ 已受创NC斩首者(剩7/15血,掷骰4+) 先手砍 VSM渗透者(12血)",
           duel(nc, blade, 7, 12, m_start=15), 12, 7)
    report("④ DKK士兵(手斧, 7血) 先手砍 卡舍津(格斗匕首, 8血)",
           duel(axe, dagger, 7, 8), 8, 7)
    report("⑤ 星际战士(拳, 15血) 先手砍 DKK士兵(手斧, 7血)",
           duel(fist, axe, 15, 7), 7, 15)
    report("⑥ 血量优势局：15血(作战刃) 先手砍 8血卡舍津(格斗匕首)",
           duel(blade, dagger, 15, 8), 8, 15)


if __name__ == "__main__":
    import sys
    selftest()
    if len(sys.argv) > 1 and sys.argv[1] == "trace":
        print("\n===== 案例B(11血) 逐刀轨迹 =====")
        for s in Duel(3, 4, 3, 4, 15, 11).trace(2, 2, 1, 1):
            print(" ", s)
        print("\n===== 血量优势局(15/15 vs 8/8) 逐刀轨迹 =====")
        for s in Duel(3, 4, 3, 4, 15, 8, m_start=15, f_start=8).trace(2, 2, 1, 1):
            print(" ", s)
    else:
        demo()
        print("\n（轨迹模式：python3 对刀计算器.py trace）")
