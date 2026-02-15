import streamlit as st
from supabase import create_client
from datetime import date
import pandas as pd

# ===== Supabase設定 =====
SUPABASE_URL = "https://ofcrcrikfrgzgohzsnuo.supabase.co"
SUPABASE_KEY = "sb_publishable_j9MfY0FdNexNqzIEhxMCmQ_X9GPERlw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== 簡易認証 =====
PASSWORD = "5810"
input_pw = st.text_input("パスワードを入力", type="password")
if input_pw != PASSWORD:
    st.warning("パスワードが違います")
    st.stop()

st.title("株取引記録ツール")

# ===== 入力フォーム =====
symbols_response = supabase.table("trades").select("symbol").execute()
symbols = list({row["symbol"] for row in symbols_response.data}) if symbols_response.data else []

symbol = st.selectbox("銘柄コード", options=symbols, index=0 if symbols else -1)
trade_type = st.selectbox("売買区分", ["buy", "sell"])
trade_date = st.date_input("日付", date.today())
price = st.number_input("価格", min_value=0.0)
quantity = st.number_input("株数", min_value=1)

if st.button("保存"):
    data = {
        "symbol": symbol,
        "trade_type": trade_type,
        "trade_date": str(trade_date),
        "price": price,
        "quantity": quantity,
    }
    supabase.table("trades").insert(data).execute()
    st.success("保存完了")
    st.experimental_rerun()

# ===== 取引履歴取得 =====
def get_trades():
    response = supabase.table("trades") \
        .select("id, symbol, trade_type, trade_date, price, quantity") \
        .order("trade_date", desc=True) \
        .execute()
    return response.data if response.data else []

trades = get_trades()

# ===== 銘柄ごとの売買集計・簡易損益 =====
if trades:
    df = pd.DataFrame(trades)
    df["total"] = df["price"] * df["quantity"]

    grouped = df.groupby(["symbol", "trade_type"])["total"].sum().reset_index()
    pivot = grouped.pivot(index="symbol", columns="trade_type", values="total").fillna(0)

    # 損益計算（列がない場合はゼロで補完）
    sell_series = pivot.get("sell", pd.Series([0]*len(pivot)))
    buy_series = pivot.get("buy", pd.Series([0]*len(pivot)))
    pivot["損益"] = sell_series - buy_series
    pivot["損益プラス"] = pivot["損益"].apply(lambda x: x if x > 0 else 0)
    pivot["損益マイナス"] = pivot["損益"].apply(lambda x: x if x < 0 else 0)

    st.subheader("銘柄ごとの売買集計")
    st.dataframe(pivot)

    # 簡易損益表示
    buy_total = df[df["trade_type"] == "buy"]["total"].sum()
    sell_total = df[df["trade_type"] == "sell"]["total"].sum()
    profit = sell_total - buy_total
    profit_plus_total = pivot["損益プラス"].sum()
    profit_minus_total = pivot["損益マイナス"].sum()

    st.subheader("簡易損益")
    st.write(f"損益合計: {profit} 円")
    st.write(f"損益プラス合計: {profit_plus_total} 円")
    st.write(f"損益マイナス合計: {profit_minus_total} 円")

# ===== 取引履歴（折りたたみ表示：最後に） =====
if trades:
    with st.expander("取引履歴を見る"):
        for row in trades:
            col1, col2 = st.columns([5,1])

            with col1:
                st.write(
                    f"{row['trade_date']} | {row['symbol']} | {row['trade_type']} | "
                    f"{row['price']}円 × {row['quantity']}"
                )

            with col2:
                delete_key = f"confirm_{row['id']}"

                # 1回目の削除ボタン
                if st.button("削除", key=f"del_{row['id']}"):
                    st.session_state[delete_key] = True

                # 確認表示
                if st.session_state.get(delete_key, False):
                    st.warning("本当に削除しますか？")

                    col_yes, col_no = st.columns(2)

                    with col_yes:
                        if st.button("はい", key=f"yes_{row['id']}"):
                            supabase.table("trades").delete().eq("id", row["id"]).execute()
                            st.success("削除しました")
                            st.session_state[delete_key] = False
                            st.experimental_rerun()

                    with col_no:
                        if st.button("いいえ", key=f"no_{row['id']}"):
                            st.session_state[delete_key] = False
