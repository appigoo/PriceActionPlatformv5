"""
AI 綜合分析 - HTML 輸出版
四個型態類別各自清晰分段，使用 HTML 標題，避免 Markdown 語法問題
"""


def _section(title: str, subtitle: str, items: list[str], border_color: str = "#4a7c6f") -> str:
    """生成一個帶標題的分析段落（HTML格式）"""
    items_html = "".join(
        f"<div style='margin:6px 0;padding:6px 10px;background:#f9f7f4;"
        f"border-radius:5px;font-size:.84rem;line-height:1.7;color:#1a1a1a'>{item}</div>"
        for item in items
    )
    return (
        f"<div style='margin-bottom:14px'>"
        f"<div style='font-size:.7rem;font-weight:700;letter-spacing:.1em;"
        f"color:{border_color};text-transform:uppercase;margin-bottom:5px'>"
        f"▸ {title}"
        f"<span style='font-weight:400;color:#9e9890;margin-left:8px;font-size:.65rem'>{subtitle}</span>"
        f"</div>"
        f"{items_html}"
        f"</div>"
    )


def _prose(title: str, text: str, border_color: str = "#4a7c6f") -> str:
    """生成純文字段落（HTML格式）"""
    return (
        f"<div style='margin-bottom:14px'>"
        f"<div style='font-size:.7rem;font-weight:700;letter-spacing:.1em;"
        f"color:{border_color};text-transform:uppercase;margin-bottom:5px'>"
        f"▸ {title}</div>"
        f"<div style='font-size:.86rem;line-height:1.85;color:#1a1a1a'>{text}</div>"
        f"</div>"
    )


def generate_ai_analysis(ticker, df, patterns, market_struct, volume_analysis,
                          sr_levels, smart_money, signals, scores) -> str:

    current     = df['Close'].iloc[-1]
    trend       = market_struct.get('trend', '橫盤')
    sub_trend   = market_struct.get('sub_trend', '')
    swing_desc  = market_struct.get('swing_desc', '')
    trend_str   = market_struct.get('trend_strength', 50)
    struct_break = market_struct.get('structure_break', '')
    reversal    = market_struct.get('reversal_signal', '')
    global_bear = market_struct.get('global_bear', False)
    global_bull = market_struct.get('global_bull', False)

    vol_sig   = volume_analysis.get('vol_signal', '')
    vol_ratio = volume_analysis.get('vol_ratio', 1.0)
    interp    = volume_analysis.get('interpretation', '')
    smart_vol = volume_analysis.get('smart_vol', '')
    r5        = volume_analysis.get('recent5_ratio', 1.0)
    vbias     = volume_analysis.get('vol_bias', '')
    vdiv      = volume_analysis.get('vol_divergence', '')

    behavior  = smart_money.get('behavior', '')
    sm_desc   = smart_money.get('description', '')

    sig         = signals.get('primary', 'NEUTRAL')
    buy_r       = signals.get('buy_reasons', [])
    sell_r      = signals.get('sell_reasons', [])
    conditional = signals.get('conditional_bull', False)
    trade       = signals.get('trade_setup', {})

    overall    = scores.get('overall_rating', '中性 ⟷')
    confidence = scores.get('confidence', 0)

    supports    = sr_levels.get('supports', [])
    resistances = sr_levels.get('resistances', [])

    single_k_pat = patterns.get('single_k', [])
    double_k_pat = patterns.get('double_k', [])
    triple_k_pat = patterns.get('triple_k', [])
    macro_pat    = patterns.get('macro', [])

    blocks = []

    # ══════════════════════════════════════════════════════════════════════════
    # 1. 市場結構
    # ══════════════════════════════════════════════════════════════════════════
    if trend == "多頭趨勢" and not global_bear:
        s1 = (f"{ticker} 確立 <b>{swing_desc}</b> 多頭結構，趨勢強度 {trend_str}/100。"
              f"{sub_trend}，EMA20/EMA50 多頭排列，趨勢動能強勁。")
    elif trend == "局部多頭反彈":
        s1 = (f"⚠️ {ticker} 大趨勢仍為空頭（EMA50 向下），但局部出現 <b>{swing_desc}</b> 多頭結構。"
              f"此為空頭趨勢中底部反彈甚至趨勢反轉初期最典型形態，"
              f"<b>做多比做空勝率更高</b>，但需設置嚴格止損。")
    elif trend == "空頭趨勢":
        s1 = (f"{ticker} 維持 <b>{swing_desc}</b> 空頭結構，趨勢強度僅 {trend_str}/100。"
              f"{sub_trend}，價格運行於下降 EMA 之下，空方主導市場。")
    elif "收斂" in trend:
        s1 = (f"{ticker} 進入 <b>{swing_desc}</b> 收斂整理，{sub_trend}。"
              f"突破方向決定下一波主浪。")
    else:
        s1 = f"{ticker} 目前 <b>{trend}</b>，{sub_trend}，趨勢強度 {trend_str}/100。"

    if reversal:
        s1 += f"<br><span style='color:#b07d2e'>{reversal}</span>"
    blocks.append(_prose("市場結構", s1))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. 單K型態（最新第 -1 根）
    # ══════════════════════════════════════════════════════════════════════════
    if single_k_pat:
        items = []
        for p in single_k_pat:
            color = "#3d8c5f" if p['bias']=='bull' else ("#c0392b" if p['bias']=='bear' else "#b07d2e")
            items.append(
                f"<span style='font-weight:700;color:{color}'>{p['name']}</span>"
                f"<span style='color:#6b6560;margin-left:6px'>{p.get('desc','')}</span>"
            )
        blocks.append(_section("單K型態", "最新第 -1 根", items))

    # ══════════════════════════════════════════════════════════════════════════
    # 3. 雙K型態（最新第 -2、-1 根）
    # ══════════════════════════════════════════════════════════════════════════
    if double_k_pat:
        items = []
        for p in double_k_pat:
            color = "#3d8c5f" if p['bias']=='bull' else ("#c0392b" if p['bias']=='bear' else "#b07d2e")
            items.append(
                f"<span style='font-weight:700;color:{color}'>{p['name']}</span>"
                f"<span style='color:#6b6560;margin-left:6px'>{p.get('desc','')}</span>"
            )
        blocks.append(_section("雙K型態", "最新第 -2、-1 根", items, "#3d8c5f"))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. 三K以上型態（最新 -5 ~ -1 根）
    # ══════════════════════════════════════════════════════════════════════════
    if triple_k_pat:
        items = []
        for p in triple_k_pat:
            color = "#3d8c5f" if p['bias']=='bull' else ("#c0392b" if p['bias']=='bear' else "#b07d2e")
            items.append(
                f"<span style='font-weight:700;color:{color}'>{p['name']}</span>"
                f"<span style='color:#6b6560;margin-left:6px'>{p.get('desc','')}</span>"
            )
        blocks.append(_section("三K以上型態", "最新 -5 ~ -1 根", items, "#3d8c5f"))

    # ══════════════════════════════════════════════════════════════════════════
    # 5. 型態學（全期數據長期結構）
    # ══════════════════════════════════════════════════════════════════════════
    if macro_pat:
        bull_macro = [p for p in macro_pat if p['bias'] == 'bull']
        bear_macro = [p for p in macro_pat if p['bias'] == 'bear']

        # 主導型態：bar_idx 最大（最近偵測到）的優先
        sorted_macro = sorted(macro_pat, key=lambda p: p.get('bar_idx', 0), reverse=True)
        dominant     = sorted_macro[0]
        dom_color    = "#3d8c5f" if dominant['bias']=='bull' else "#c0392b"
        dom_dir      = "多頭" if dominant['bias']=='bull' else "空頭"

        items = []
        # 矛盾型態警告
        if bull_macro and bear_macro:
            items.append(
                f"<div style='background:#fff3e0;border-radius:5px;padding:5px 8px;"
                f"font-size:.8rem;color:#b07d2e;margin-bottom:6px'>"
                f"⚠️ <b>多空型態並存</b>（多頭 {len(bull_macro)} 個 / 空頭 {len(bear_macro)} 個）"
                f"，以最近偵測到的 <b style='color:{dom_color}'>{dominant['name'].split()[0]}</b>"
                f"（{dom_dir}）為主導，其餘供參考。</div>"
            )

        for p in sorted_macro:
            color  = "#3d8c5f" if p['bias']=='bull' else ("#c0392b" if p['bias']=='bear' else "#b07d2e")
            d      = p.get('desc', '')
            is_dom = (p is sorted_macro[0])
            tag    = "<span style='background:#f0f0f0;border-radius:3px;padding:1px 5px;"                      "font-size:.68rem;margin-right:4px;color:#6b6560'>主導</span>" if is_dom else                      "<span style='background:#f9f9f9;border-radius:3px;padding:1px 5px;"                      "font-size:.68rem;margin-right:4px;color:#b8b2aa'>參考</span>"
            items.append(
                f"{tag}<span style='font-weight:700;color:{color}'>{p['name']}</span>"
                f"<span style='color:#6b6560;margin-left:6px'>{d}</span>"
            )
        blocks.append(_section("型態學", "全期數據長期結構", items, "#b07d2e"))

    # ══════════════════════════════════════════════════════════════════════════
    # 6. 成交量分析（最新5根）
    # ══════════════════════════════════════════════════════════════════════════
    if vol_ratio >= 2.0:
        vol_txt = (f"最新一根 <b>爆量</b> {vol_ratio:.1f}x 均量——{interp}，{smart_vol}。"
                   f"近5根量比 {r5:.1f}x，{vbias}，主力資金大量介入。")
    elif vol_ratio >= 1.3:
        vol_txt = (f"最新一根放量（{vol_ratio:.1f}x均量），{vol_sig}。"
                   f"近5根量比 {r5:.1f}x，{vbias}，量價配合良好。")
    elif vol_ratio < 0.7:
        vol_txt = (f"最新一根縮量（{vol_ratio:.1f}x均量），{interp}。"
                   f"近5根量比 {r5:.1f}x，{vbias}，主力未大量離場。")
    else:
        vol_txt = (f"最新一根成交量正常（{vol_ratio:.1f}x均量），{interp}。"
                   f"近5根量比 {r5:.1f}x，{vbias}。")
    if vdiv:
        vol_txt += f"<br><span style='color:#b07d2e'>{vdiv}</span>"
    blocks.append(_prose("成交量分析（最新5根）", vol_txt, "#4a7c6f"))

    # ══════════════════════════════════════════════════════════════════════════
    # 7. Smart Money 主力行為
    # ══════════════════════════════════════════════════════════════════════════
    if sm_desc:
        blocks.append(_prose("Smart Money 主力行為", sm_desc, "#b07d2e"))

    # ══════════════════════════════════════════════════════════════════════════
    # 8. 支撐與阻力
    # ══════════════════════════════════════════════════════════════════════════
    if supports and resistances:
        sup_str = " / ".join([f"<b>${s:.2f}</b>" for s in supports[:3]])
        res_str = " / ".join([f"<b>${r:.2f}</b>" for r in resistances[:3]])
        sr_txt = (f"關鍵支撐：{sup_str}，關鍵阻力：{res_str}。"
                  f"當前 ${current:.2f} 距支撐 "
                  f"{(current-supports[0])/supports[0]*100:.1f}%，"
                  f"距阻力 {(resistances[0]-current)/current*100:.1f}%。")
        if "突破阻力" in struct_break:
            sr_txt += " <b style='color:#3d8c5f'>價格已突破近期阻力 ↑</b>"
        elif "跌破支撐" in struct_break:
            sr_txt += " <b style='color:#c0392b'>⚠️ 價格已跌破近期支撐 ↓</b>"
        blocks.append(_prose("支撐與阻力", sr_txt))

    # ══════════════════════════════════════════════════════════════════════════
    # 9. 型態目標位
    # ══════════════════════════════════════════════════════════════════════════
    macro_targets = signals.get('macro_targets', [])
    if macro_targets:
        items = []
        for mt in macro_targets:
            pct = abs(mt['target'] - current) / current * 100
            items.append(
                f"<span style='color:#b07d2e;font-weight:700'>{mt['pattern'].split()[0]}</span>"
                f" 頸線 <b>${mt['neckline']:.2f}</b> → 目標 <b>${mt['target']:.2f}</b>"
                f"（潛在空間 {pct:.1f}%）"
            )
        blocks.append(_section("型態目標位", "", items, "#b07d2e"))

    # ══════════════════════════════════════════════════════════════════════════
    # 10. 綜合結論
    # ══════════════════════════════════════════════════════════════════════════
    reasons = buy_r if sig == 'BUY' else sell_r
    reason_txt = " + ".join(reasons[:5]) if reasons else "多空平衡"
    r_color = "#3d8c5f" if "看多" in overall else ("#c0392b" if "看空" in overall else "#b07d2e")

    if "強烈看多" in overall:
        conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                      f"{ticker} 多頭訊號強烈，{reason_txt} 共振，"
                      f"積極做多，嚴守止損 <b>${trade.get('stop_loss',0):.2f}</b>。")
    elif "偏多" in overall and conditional:
        conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                      f"{ticker} 大趨勢偏空但局部多頭訊號明確（{reason_txt}），"
                      f"可輕倉做多，止損嚴格設於 <b>${trade.get('stop_loss',0):.2f}</b>，"
                      f"風報比 {trade.get('rrr','N/A')}。")
    elif "偏多" in overall:
        conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                      f"{ticker} 偏向多方（{reason_txt}），"
                      f"可輕倉試多，止損 <b>${trade.get('stop_loss',0):.2f}</b>，"
                      f"風報比 {trade.get('rrr','N/A')}。")
    elif "強烈看空" in overall:
        conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                      f"{ticker} 空頭訊號強烈（{reason_txt}），不宜追多。")
    elif "偏空" in overall:
        conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                      f"{ticker} 偏向空方（{reason_txt}），持股謹慎，考慮減倉。")
    else:
        if supports and resistances:
            conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                          f"{ticker} 多空暫時平衡，觀望等待方向確認。"
                          f"突破 <b>${resistances[0]:.2f}</b> 看多，跌破 <b>${supports[0]:.2f}</b> 看空。")
        else:
            conclusion = (f"<b style='color:{r_color}'>{overall}</b>｜信心 {confidence}%<br>"
                          f"{ticker} 多空暫時平衡，等待明確訊號。")

    blocks.append(_prose("綜合結論", conclusion, r_color))

    return "".join(blocks)
