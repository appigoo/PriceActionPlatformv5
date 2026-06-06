"""
K線型態辨識 - 精確位置版
單K   = 只分析最新第 -1 根（永遠有輸出）
雙K   = 只分析最新第 -2, -1 根（有條件輸出）
三K以上 = 只分析最新第 -5 ~ -1 根（有條件輸出）
型態學  = 用全部數據做長期結構判斷
"""
import numpy as np
import pandas as pd


def _body(r):    return abs(r['Close'] - r['Open'])
def _upper(r):   return r['High'] - max(r['Open'], r['Close'])
def _lower(r):   return min(r['Open'], r['Close']) - r['Low']
def _rng(r):     return r['High'] - r['Low']
def _is_bull(r): return r['Close'] > r['Open']
def _is_bear(r): return r['Close'] < r['Open']
def _mid(r):     return (r['Open'] + r['Close']) / 2


def detect_all_patterns(df: pd.DataFrame) -> dict:
    n = len(df)
    if n < 3:
        return {"detected":[], "single_k":[], "double_k":[],
                "triple_k":[], "macro":[], "bull_count":0, "bear_count":0}

    single_k = []
    double_k = []
    triple_k = []

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 單K型態 ── 最新第 -1 根，永遠輸出至少一條描述
    # ══════════════════════════════════════════════════════════════════════════
    c   = df.iloc[-1]
    rng = _rng(c)

    if rng > 0:
        body   = _body(c)
        up     = _upper(c)
        lo     = _lower(c)
        body_r = body / rng
        up_r   = up   / rng
        lo_r   = lo   / rng
        is_bull_c = _is_bull(c)

        # 近20日價格位置（0=最低，1=最高）
        win = df['Close'].iloc[max(0,n-21):n-1]
        lo20, hi20 = win.min(), win.max()
        price_rank = (c['Close'] - lo20) / (hi20 - lo20 + 1e-9)
        pos_label = ("低位" if price_rank < 0.35 else
                     "高位" if price_rank > 0.65 else "中位")

        named = False  # 是否已識別出具名型態

        # ── 具名單K型態（條件放寬）────────────────────────────────────────
        # 十字線（最寬鬆，最先判斷）
        if body_r < 0.10:
            single_k.append({
                "name": "十字線 ✚", "bias": "neutral", "bar": n-1, "category": "single",
                "desc": f"多空膠著：實體極小（{body_r*100:.0f}%），開收幾乎同價，動能轉換訊號，關注下一根方向確認"
            }); named = True

        # 錘頭線：低位，下影長
        elif lo_r > 0.50 and up_r < 0.20 and price_rank < 0.45:
            single_k.append({
                "name": "錘頭線 🔨", "bias": "bull", "bar": n-1, "category": "single",
                "desc": f"低位錘頭：下影 {lo/rng*100:.0f}%，上影僅 {up/rng*100:.0f}%，低位強力承接，主力掃盤後護盤"
            }); named = True

        # 上吊線：高位，下影長
        elif lo_r > 0.50 and up_r < 0.20 and price_rank > 0.60:
            single_k.append({
                "name": "上吊線 🪢", "bias": "bear", "bar": n-1, "category": "single",
                "desc": f"高位上吊線：下影 {lo/rng*100:.0f}%，高位出現警惕主力誘多後反轉"
            }); named = True

        # 流星線：高位，上影長
        elif up_r > 0.50 and lo_r < 0.20 and price_rank > 0.55:
            single_k.append({
                "name": "流星線 ⭐", "bias": "bear", "bar": n-1, "category": "single",
                "desc": f"高位流星：上影 {up/rng*100:.0f}%，主力誘多後強力打壓，看跌訊號"
            }); named = True

        # 低位長下影（倒錘頭也算入）
        elif lo_r > 0.50 and price_rank < 0.45:
            single_k.append({
                "name": "長下影線 ↓", "bias": "bull", "bar": n-1, "category": "single",
                "desc": f"低位長下影：下影 {lo/rng*100:.0f}%，下方強力承接，低位買盤積極介入"
            }); named = True

        # 高位長上影
        elif up_r > 0.50 and price_rank > 0.55:
            single_k.append({
                "name": "長上影線 ↑", "bias": "bear", "bar": n-1, "category": "single",
                "desc": f"高位長上影：上影 {up/rng*100:.0f}%，上方拋壓沉重，高位賣盤主動"
            }); named = True

        # 墓碑線
        elif body_r < 0.08 and up_r > 0.75:
            single_k.append({
                "name": "墓碑線 🪦", "bias": "bear", "bar": n-1, "category": "single",
                "desc": "墓碑線：多方拉升後被空方全面壓回，看跌信號強烈"
            }); named = True

        # 蜻蜓線
        elif body_r < 0.08 and lo_r > 0.75:
            single_k.append({
                "name": "蜻蜓線 🌿", "bias": "bull", "bar": n-1, "category": "single",
                "desc": "蜻蜓線：空方打壓後被多方完全承接，看漲信號強烈"
            }); named = True

        # 光頭光腳陽線
        elif is_bull_c and up_r < 0.05 and lo_r < 0.05 and body_r > 0.85:
            single_k.append({
                "name": "光頭光腳陽線 ▮", "bias": "bull", "bar": n-1, "category": "single",
                "desc": f"完美陽線：全程多方主導，無任何賣壓，主力主動拉升（漲幅 {body/c['Open']*100:.1f}%）"
            }); named = True

        # 光頭光腳陰線
        elif not is_bull_c and up_r < 0.05 and lo_r < 0.05 and body_r > 0.85:
            single_k.append({
                "name": "光頭光腳陰線 ▮", "bias": "bear", "bar": n-1, "category": "single",
                "desc": f"完美陰線：全程空方主導，無任何買盤，主力主動打壓（跌幅 {body/c['Open']*100:.1f}%）"
            }); named = True

        # ── 無具名型態：根據K線特徵描述（永遠兜底）──────────────────────────
        if not named:
            # 基本方向
            direction = "陽線" if is_bull_c else "陰線"
            chg_pct   = body / c['Open'] * 100 if c['Open'] > 0 else 0
            bias      = "bull" if is_bull_c else "bear"

            # 影線描述
            shadow_desc = ""
            if up_r > 0.25 and lo_r > 0.25:
                shadow_desc = f"，上下均有影線（上影{up/rng*100:.0f}%/下影{lo/rng*100:.0f}%），多空拉鋸"
            elif up_r > 0.30:
                shadow_desc = f"，帶上影（{up/rng*100:.0f}%），上方有賣壓"
            elif lo_r > 0.30:
                shadow_desc = f"，帶下影（{lo/rng*100:.0f}%），下方有支撐"

            # 實體強度
            if body_r > 0.70:
                strength = "強勢"
            elif body_r > 0.45:
                strength = "中等"
            else:
                strength = "小實體"

            single_k.append({
                "name": f"{pos_label}{strength}{direction}",
                "bias": bias,
                "bar": n-1, "category": "single",
                "desc": (f"{pos_label}{strength}{direction}：實體佔振幅 {body_r*100:.0f}%"
                         f"，漲跌 {chg_pct:.1f}%{shadow_desc}。"
                         f"{'買方積極，動能偏多' if is_bull_c else '賣方積極，動能偏空'}。")
            })

    # ══════════════════════════════════════════════════════════════════════════
    # 2. 雙K型態 ── 最新第 -2（prev）和 -1（curr）
    # ══════════════════════════════════════════════════════════════════════════
    if n >= 2:
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        bc, bp = _body(curr), _body(prev)
        rc, rp = _rng(curr),  _rng(prev)

        if rc > 0 and rp > 0 and bp > 0:
            named_double = False

            # 多頭吞噬
            if (_is_bear(prev) and _is_bull(curr) and
                    curr['Open'] <= prev['Close'] and curr['Close'] >= prev['Open'] and
                    bc >= bp * 0.75):
                tag = "完全吞噬" if bc >= bp else "部分吞噬"
                double_k.append({
                    "name": "多頭吞噬 🟢", "bias": "bull", "bar": n-1, "category": "double",
                    "desc": (f"多頭吞噬（{tag}）：今日陽線實體 {bc:.2f} 覆蓋昨日陰線 {bp:.2f}，"
                             f"空方進攻失敗，多方全面接管")
                }); named_double = True

            # 空頭吞噬
            elif (_is_bull(prev) and _is_bear(curr) and
                    curr['Open'] >= prev['Close'] and curr['Close'] <= prev['Open'] and
                    bc >= bp * 0.75):
                double_k.append({
                    "name": "空頭吞噬 🔴", "bias": "bear", "bar": n-1, "category": "double",
                    "desc": (f"空頭吞噬：今日陰線實體 {bc:.2f} 覆蓋昨日陽線 {bp:.2f}，"
                             f"多方進攻失敗，空方全面接管")
                }); named_double = True

            # 多頭孕線
            elif (_is_bear(prev) and _is_bull(curr) and
                    curr['Open'] > prev['Close'] and curr['Close'] < prev['Open'] and
                    bc < bp * 0.65):
                double_k.append({
                    "name": "多頭孕線", "bias": "bull", "bar": n-1, "category": "double",
                    "desc": "多頭孕線：小陽線孕於昨日大陰線內，空頭動能耗盡，反轉前置訊號"
                }); named_double = True

            # 空頭孕線
            elif (_is_bull(prev) and _is_bear(curr) and
                    curr['Open'] < prev['Close'] and curr['Close'] > prev['Open'] and
                    bc < bp * 0.65):
                double_k.append({
                    "name": "空頭孕線", "bias": "bear", "bar": n-1, "category": "double",
                    "desc": "空頭孕線：小陰線孕於昨日大陽線內，多頭動能衰竭，回調前置訊號"
                }); named_double = True

            # 烏雲蓋頂
            elif (_is_bull(prev) and _is_bear(curr) and
                    curr['Open'] > prev['High'] and
                    curr['Close'] < _mid(prev) and curr['Close'] > prev['Open']):
                double_k.append({
                    "name": "烏雲蓋頂 ☁️", "bias": "bear", "bar": n-1, "category": "double",
                    "desc": "烏雲蓋頂：今日跳空高開後強力回落過前日中點，主力高位誘多後出貨"
                }); named_double = True

            # 穿刺線
            elif (_is_bear(prev) and _is_bull(curr) and
                    curr['Open'] < prev['Low'] and
                    curr['Close'] > _mid(prev) and curr['Close'] < prev['Open']):
                double_k.append({
                    "name": "穿刺線 💉", "bias": "bull", "bar": n-1, "category": "double",
                    "desc": "穿刺線：今日低開後強力上攻過前日中點，空方進攻失敗，多方反撲"
                }); named_double = True

            # 無具名雙K：描述兩根K線的關係
            if not named_double:
                prev_dir = "陽" if _is_bull(prev) else "陰"
                curr_dir = "陽" if _is_bull(curr) else "陰"
                # 連續同向
                if _is_bull(prev) and _is_bull(curr):
                    if curr['Close'] > prev['Close']:
                        double_k.append({
                            "name": "連續上漲", "bias": "bull", "bar": n-1, "category": "double",
                            "desc": f"連續兩根陽線且收盤依次上升（{prev['Close']:.2f}→{curr['Close']:.2f}），多頭動能持續"
                        })
                    else:
                        double_k.append({
                            "name": "高位二連陽", "bias": "neutral", "bar": n-1, "category": "double",
                            "desc": f"連續兩根陽線但第二根收盤較低，動能略有減弱，注意上方壓力"
                        })
                elif _is_bear(prev) and _is_bear(curr):
                    if curr['Close'] < prev['Close']:
                        double_k.append({
                            "name": "連續下跌", "bias": "bear", "bar": n-1, "category": "double",
                            "desc": f"連續兩根陰線且收盤依次下降（{prev['Close']:.2f}→{curr['Close']:.2f}），空頭動能持續"
                        })
                    else:
                        double_k.append({
                            "name": "低位二連陰", "bias": "neutral", "bar": n-1, "category": "double",
                            "desc": f"連續兩根陰線但第二根收盤較高，跌勢動能減弱，注意下方支撐"
                        })
                else:
                    # 多空交替
                    bias = "bull" if _is_bull(curr) else "bear"
                    double_k.append({
                        "name": f"前{prev_dir}後{curr_dir}（多空交替）",
                        "bias": bias, "bar": n-1, "category": "double",
                        "desc": (f"前一根{prev_dir}線後接{curr_dir}線，"
                                 f"{'今日多方反攻，注意能否持續' if _is_bull(curr) else '今日空方反壓，注意支撐是否守住'}")
                    })

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 三K以上型態 ── 最新 5 根（-5 到 -1）
    # ══════════════════════════════════════════════════════════════════════════
    if n >= 3:
        c0 = df.iloc[-3]
        c1 = df.iloc[-2]
        c2 = df.iloc[-1]
        named_triple = False

        # 啟明星
        if (_is_bear(c0) and _body(c0) > _rng(c0) * 0.40 and
                _body(c1) < _body(c0) * 0.40 and
                _is_bull(c2) and c2['Close'] > _mid(c0)):
            triple_k.append({
                "name": "啟明星 🌟", "bias": "bull", "bar": n-1, "category": "triple",
                "desc": (f"啟明星（最近3根）：大陰→小實體過渡→大陽，"
                         f"今日收 ${c2['Close']:.2f} 超越三日前陰線中點，底部反轉最強訊號")
            }); named_triple = True

        # 黃昏星
        elif (_is_bull(c0) and _body(c0) > _rng(c0) * 0.40 and
                _body(c1) < _body(c0) * 0.40 and
                _is_bear(c2) and c2['Close'] < _mid(c0)):
            triple_k.append({
                "name": "黃昏星 🌙", "bias": "bear", "bar": n-1, "category": "triple",
                "desc": (f"黃昏星（最近3根）：大陽→小實體→大陰，"
                         f"今日收 ${c2['Close']:.2f} 跌破三日前陽線中點，頂部反轉強訊號")
            }); named_triple = True

    # 紅三兵（最近3根）
    if n >= 3:
        t1, t2, t3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        if (all(_is_bull(x) for x in [t1,t2,t3]) and
                t2['Close'] > t1['Close'] and t3['Close'] > t2['Close'] and
                t2['Open'] > t1['Open']   and t3['Open'] > t2['Open'] and
                _body(t1) > _rng(t1)*0.30 and _body(t2) > _rng(t2)*0.30 and _body(t3) > _rng(t3)*0.30):
            triple_k.append({
                "name": "紅三兵 🪖", "bias": "bull", "bar": n-1, "category": "triple",
                "desc": (f"紅三兵（最近3根）：三連陽依次遞增，"
                         f"${t1['Close']:.2f}→${t2['Close']:.2f}→${t3['Close']:.2f}，"
                         f"主力資金連續進場，強勢多頭確認")
            })

    # 三隻烏鴉（最近3根）
    if n >= 3:
        t1, t2, t3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        if (all(_is_bear(x) for x in [t1,t2,t3]) and
                t2['Close'] < t1['Close'] and t3['Close'] < t2['Close'] and
                t2['Open'] < t1['Open']   and t3['Open'] < t2['Open'] and
                _body(t1) > _rng(t1)*0.30 and _body(t2) > _rng(t2)*0.30):
            triple_k.append({
                "name": "三隻烏鴉 🐦‍⬛", "bias": "bear", "bar": n-1, "category": "triple",
                "desc": (f"三隻烏鴉（最近3根）：三連陰依次遞減，"
                         f"${t1['Close']:.2f}→${t2['Close']:.2f}→${t3['Close']:.2f}，"
                         f"空方全面主導，下跌加速")
            })

    # 上升三法（最近5根）
    if n >= 5:
        big1 = df.iloc[-5]; sm1 = [df.iloc[-4],df.iloc[-3],df.iloc[-2]]; big2 = df.iloc[-1]
        if (_is_bull(big1) and _body(big1) > _rng(big1)*0.45 and
                all(_is_bear(s) for s in sm1) and
                all(s['Close'] > big1['Open'] for s in sm1) and
                all(s['High']  < big1['Close'] for s in sm1) and
                _is_bull(big2) and big2['Close'] > big1['Close']):
            triple_k.append({
                "name": "上升三法 📶", "bias": "bull", "bar": n-1, "category": "triple",
                "desc": ("上升三法（最近5根）：大陽→三根小陰整理（均在前陽實體內）→今日大陽突破，"
                         "主升段延續，做多訊號明確")
            })

    # 下跌三法（最近5根）
    if n >= 5:
        big1 = df.iloc[-5]; sm1 = [df.iloc[-4],df.iloc[-3],df.iloc[-2]]; big2 = df.iloc[-1]
        if (_is_bear(big1) and _body(big1) > _rng(big1)*0.45 and
                all(_is_bull(s) for s in sm1) and
                all(s['Close'] < big1['Open'] for s in sm1) and
                all(s['Low']   > big1['Close'] for s in sm1) and
                _is_bear(big2) and big2['Close'] < big1['Close']):
            triple_k.append({
                "name": "下跌三法 📉", "bias": "bear", "bar": n-1, "category": "triple",
                "desc": ("下跌三法（最近5根）：大陰→三根小陽反彈（均在前陰實體內）→今日大陰突破，"
                         "主跌段延續，做空訊號明確")
            })

    # 無三K型態時：描述最近3根趨勢
    if not triple_k and n >= 3:
        last3 = [df.iloc[-3], df.iloc[-2], df.iloc[-1]]
        bull3 = sum(1 for x in last3 if _is_bull(x))
        bear3 = 3 - bull3
        c3_chg = (df.iloc[-1]['Close'] - df.iloc[-3]['Open']) / df.iloc[-3]['Open'] * 100
        if bull3 >= 2:
            triple_k.append({
                "name": f"近3根偏多（{bull3}陽{bear3}陰）",
                "bias": "bull", "bar": n-1, "category": "triple",
                "desc": f"最近3根K線以陽線為主（{bull3}陽{bear3}陰），3根合計{'+' if c3_chg>=0 else ''}{c3_chg:.1f}%，短線動能偏多"
            })
        elif bear3 >= 2:
            triple_k.append({
                "name": f"近3根偏空（{bull3}陽{bear3}陰）",
                "bias": "bear", "bar": n-1, "category": "triple",
                "desc": f"最近3根K線以陰線為主（{bull3}陽{bear3}陰），3根合計{'+' if c3_chg>=0 else ''}{c3_chg:.1f}%，短線動能偏空"
            })
        else:
            triple_k.append({
                "name": "近3根多空交替",
                "bias": "neutral", "bar": n-1, "category": "triple",
                "desc": f"最近3根陽陰交替，3根合計{'+' if c3_chg>=0 else ''}{c3_chg:.1f}%，多空拉鋸，方向不明"
            })

    # ══════════════════════════════════════════════════════════════════════════
    # 4. 型態學 ── 全期數據
    # ══════════════════════════════════════════════════════════════════════════
    macro = _detect_macro_patterns(df)

    all_patterns = single_k + double_k + triple_k + macro
    bull_ct = sum(1 for p in all_patterns if p['bias']=='bull')
    bear_ct = sum(1 for p in all_patterns if p['bias']=='bear')

    return {
        "detected":  all_patterns,
        "single_k":  single_k,
        "double_k":  double_k,
        "triple_k":  triple_k,
        "macro":     macro,
        "bull_count": bull_ct,
        "bear_count": bear_ct,
    }


def _detect_macro_patterns(df: pd.DataFrame) -> list:
    patterns = []
    closes = df['Close'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    n      = len(df)
    current = closes[-1]

    # W 底
    if n >= 30:
        for window in [30, 45, 60, 80]:
            if n < window: continue
            seg_c = closes[-window:]; seg_l = lows[-window:]; mid = window//2
            li = np.argmin(seg_l[:mid]); ri = np.argmin(seg_l[mid:]) + mid
            ll, rl = seg_l[li], seg_l[ri]
            neck = np.max(seg_c[li:ri]) if ri > li else seg_c[mid]
            if abs(ll-rl)/(ll+1e-9) < 0.07 and neck > min(ll,rl)*1.015:
                h = neck - min(ll,rl); tgt = neck + h
                st = "已突破頸線 ✅" if current > neck else f"頸線 ${neck:.2f} 待突破"
                patterns.append({
                    "name":"W底型態 📐","bias":"bull","bar":n-1,"category":"macro",
                    "neckline":neck,"target":tgt,
                    "urgency": 2 if current > neck else 1,   # 已突破=2，待突破=1
                    "desc":f"W底：左低 ${ll:.2f} / 右低 ${rl:.2f}，{st}，突破後目標 ${tgt:.2f}（+{h/current*100:.1f}%）"
                }); break

    # M 頂
    if n >= 30:
        for window in [30, 45, 60, 80]:
            if n < window: continue
            seg_c = closes[-window:]; seg_h = highs[-window:]; mid = window//2
            li = np.argmax(seg_h[:mid]); ri = np.argmax(seg_h[mid:]) + mid
            lh, rh = seg_h[li], seg_h[ri]
            neck = np.min(seg_c[li:ri]) if ri > li else seg_c[mid]
            if abs(lh-rh)/(lh+1e-9) < 0.07 and neck < max(lh,rh)*0.985:
                h = max(lh,rh) - neck; tgt = neck - h
                st = "已跌破頸線 ⚠️" if current < neck else f"頸線 ${neck:.2f} 警戒"
                patterns.append({
                    "name":"M頂型態 📐","bias":"bear","bar":n-1,"category":"macro",
                    "neckline":neck,"target":tgt,
                    "urgency": 2 if current < neck else 1,   # 已跌破=2（最緊急），待跌破=1
                    "desc":f"M頂：左高 ${lh:.2f} / 右高 ${rh:.2f}，{st}，目標 ${tgt:.2f}"
                }); break

    # 頭肩底
    if n >= 40:
        for window in [40, 60, 80]:
            if n < window: continue
            seg_l = lows[-window:]; seg_c = closes[-window:]; w3 = window//3
            ls = np.min(seg_l[:w3]); hd = np.min(seg_l[w3:2*w3]); rs = np.min(seg_l[2*w3:])
            neck = np.mean([np.max(seg_c[:w3]), np.max(seg_c[w3:2*w3])])
            if hd < ls*0.97 and hd < rs*0.97 and abs(ls-rs)/(ls+1e-9) < 0.09 and rs > hd:
                h = neck - hd; tgt = neck + h
                st = "頸線已突破 🚀" if current > neck else f"等待突破頸線 ${neck:.2f}"
                patterns.append({
                    "name":"頭肩底 🔔","bias":"bull","bar":n-1,"category":"macro",
                    "neckline":neck,"target":tgt,
                    "urgency": 2 if current > neck else 1,
                    "desc":f"頭肩底：左肩 ${ls:.2f} / 頭 ${hd:.2f} / 右肩 ${rs:.2f}，{st}，目標 ${tgt:.2f}"
                }); break

    # 頭肩頂
    if n >= 40:
        for window in [40, 60, 80]:
            if n < window: continue
            seg_h = highs[-window:]; seg_c = closes[-window:]; w3 = window//3
            ls = np.max(seg_h[:w3]); hd = np.max(seg_h[w3:2*w3]); rs = np.max(seg_h[2*w3:])
            neck = np.mean([np.min(seg_c[:w3]), np.min(seg_c[w3:2*w3])])
            if hd > ls*1.02 and hd > rs*1.02 and abs(ls-rs)/(ls+1e-9) < 0.09 and rs < hd:
                h = hd - neck; tgt = neck - h
                st = "頸線已跌破 💀" if current < neck else f"警戒頸線 ${neck:.2f}"
                patterns.append({
                    "name":"頭肩頂 🔔","bias":"bear","bar":n-1,"category":"macro",
                    "neckline":neck,"target":tgt,
                    "urgency": 2 if current < neck else 1,
                    "desc":f"頭肩頂：左肩 ${ls:.2f} / 頭 ${hd:.2f} / 右肩 ${rs:.2f}，{st}，目標 ${tgt:.2f}"
                }); break

    # 三角收斂（最近20根）
    if n >= 20:
        sh = np.polyfit(range(20), highs[-20:], 1)[0]
        sl = np.polyfit(range(20), lows[-20:],  1)[0]
        if sh < 0 and sl > 0:
            if abs(sh+sl) < abs(sh)*0.4:
                patterns.append({"name":"對稱三角收斂 △","bias":"neutral","bar":n-1,"category":"macro",
                    "desc":"近20根對稱三角收斂：高點下降+低點上升，突破方向決定下一波主浪"})
            elif abs(sl) < abs(sh)*0.25:
                patterns.append({"name":"下降三角 △↓","bias":"bear","bar":n-1,"category":"macro",
                    "desc":"近20根下降三角：支撐持平，阻力下移，偏向向下突破"})
            elif abs(sh) < abs(sl)*0.25:
                patterns.append({"name":"上升三角 △↑","bias":"bull","bar":n-1,"category":"macro",
                    "desc":"近20根上升三角：阻力持平，支撐抬高，偏向向上突破"})

    return patterns
