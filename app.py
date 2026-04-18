import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import japanize_matplotlib
import json
import os
from datetime import datetime

# --- 1. ページ設定とデータ初期化 ---
st.set_page_config(page_title="投資学習シミュレーター", layout="wide")

# セッション状態（データの保持）の初期化
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "cash": 1000000,
        "portfolio": {},
        "history": [],
        "asset_history": []
    }

# --- 2. 補助関数 ---
def get_stock_info(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="2d")
        if len(hist) < 2: return None
        price = hist['Close'].iloc[-1]
        change = ((price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        name = t.info.get('shortName') or ticker
        return {"name": name, "price": price, "change": change}
    except:
        return None

# --- 3. サイドバー・メニュー ---
st.sidebar.title("投資アプリメニュー")
menu = st.sidebar.radio("機能を選択", ["ホーム/資産状況", "ランキング&ニュース", "株の売買", "取引履歴"])

# --- 4. メインコンテンツ ---

# A. ホーム/資産状況
if menu == "ホーム/資産状況":
    st.header("💰 現在の資産状況")
    
    # 資産計算
    current_stock_value = 0
    portfolio_data = []
    for ticker, info in st.session_state.user_data["portfolio"].items():
        if info["quantity"] > 0:
            price = yf.Ticker(ticker).history(period="1d")["Close"].iloc[-1]
            val = price * info["quantity"]
            current_stock_value += val
            portfolio_data.append({"銘柄": ticker, "数量": info["quantity"], "時価評価額": f"{val:,.0f}円"})

    total_assets = st.session_state.user_data["cash"] + current_stock_value
    
    col1, col2, col3 = st.columns(3)
    col1.metric("総資産", f"{total_assets:,.0f}円")
    col2.metric("現金残高", f"{st.session_state.user_data['cash']:,.0f}円")
    col3.metric("株式時価", f"{current_stock_value:,.0f}円")

    # 資産内訳グラフ
    if portfolio_data:
        st.subheader("資産構成")
        labels = ["現金"] + [d["銘柄"] for d in portfolio_data]
        values = [st.session_state.user_data["cash"]] + [float(d["時価評価額"].replace("円","").replace(",","")) for d in portfolio_data]
        
        fig, ax = plt.subplots()
        ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
        st.pyplot(fig)
        st.table(pd.DataFrame(portfolio_data))
    else:
        st.info("まだ株を保有していません。「株の売買」から始めてみましょう。")

# B. ランキング&ニュース
elif menu == "ランキング&ニュース":
    st.header("📈 マーケットランキング")
    check_list = ["7203.T", "9984.T", "6920.T", "AAPL", "TSLA", "NVDA"]
    
    ranks = []
    with st.spinner('データ取得中...'):
        for t in check_list:
            info = get_stock_info(t)
            if info:
                ranks.append({"コード": t, "銘柄名": info["name"], "現在値": f"{info['price']:,.1f}", "騰落率(%)": round(info['change'], 2)})
    
    df = pd.DataFrame(ranks)
    st.dataframe(df.sort_values("騰落率(%)", ascending=False), use_container_width=True)

    st.header("📰 注目ニュース")
    news_ticker = st.selectbox("ニュースを見る銘柄を選択", ["^N225", "TSLA", "AAPL"])
    for n in yf.Ticker(news_ticker).news[:5]:
        st.write(f"**[{n['publisher']}]** {n['title']}")
        st.caption(f"URL: {n['link']}")

# C. 株の売買
elif menu == "株の売買":
    st.header("🤝 株式トレード")
    
    tab1, tab2 = st.tabs(["購入", "売却"])
    
    with tab1:
        ticker_buy = st.text_input("購入する銘柄コード", "7203.T").upper()
        info = get_stock_info(ticker_buy)
        if info:
            st.write(f"**銘柄名:** {info['name']} | **価格:** {info['price']:,.1f}円")
            qty_buy = st.number_input("購入数", min_value=1, value=1, key="buy_qty")
            total_cost = info['price'] * qty_buy
            st.write(f"概算代金: {total_cost:,.0f}円")
            
            if st.button("注文確定 (購入)"):
                if st.session_state.user_data["cash"] >= total_cost:
                    st.session_state.user_data["cash"] -= total_cost
                    p = st.session_state.user_data["portfolio"].get(ticker_buy, {"quantity": 0, "avg_price": 0})
                    p["quantity"] += qty_buy
                    st.session_state.user_data["portfolio"][ticker_buy] = p
                    st.session_state.user_data["history"].append({"date": datetime.now(), "type": "購入", "ticker": ticker_buy, "qty": qty_buy})
                    st.success(f"{info['name']} を購入しました！")
                else:
                    st.error("残高が不足しています。")

    with tab2:
        holdings = [t for t, i in st.session_state.user_data["portfolio"].items() if i["quantity"] > 0]
        if holdings:
            ticker_sell = st.selectbox("売却する銘柄", holdings)
            max_qty = st.session_state.user_data["portfolio"][ticker_sell]["quantity"]
            qty_sell = st.number_input("売却数", min_value=1, max_value=max_qty, value=1)
            
            if st.button("注文確定 (売却)"):
                price = yf.Ticker(ticker_sell).history(period="1d")["Close"].iloc[-1]
                st.session_state.user_data["cash"] += price * qty_sell
                st.session_state.user_data["portfolio"][ticker_sell]["quantity"] -= qty_sell
                st.session_state.user_data["history"].append({"date": datetime.now(), "type": "売却", "ticker": ticker_sell, "qty": qty_sell})
                st.success(f"売却が完了しました。")
        else:
            st.write("保有している株はありません。")

# D. 取引履歴
elif menu == "取引履歴":
    st.header("📜 取引履歴")
    if st.session_state.user_data["history"]:
        st.table(pd.DataFrame(st.session_state.user_data["history"]))
    else:
        st.write("履歴はまだありません。")
