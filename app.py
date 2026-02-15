import streamlit as st
from supabase import create_client
from datetime import date

# ===== Supabase設定 =====
SUPABASE_URL = "https://ofcrcrikfrgzgohzsnuo.supabase.co"
SUPABASE_KEY = "sb_publishable_j9MfY0FdNexNqzIEhxMCmQ_X9GPERlw"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("株取引記録ツール")

# ===== 入力フォーム =====
symbol = st.text_input("銘柄コード")
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

    response = supabase.table("trades").insert(data).execute()

    st.success("保存完了")
    st.subheader("取引履歴")

response = supabase.table("trades").select("symbol, trade_type, trade_date, price, quantity").order("trade_date", desc=True).execute()

if response.data:
    st.dataframe(response.data)
else:
    st.write("まだデータがありません")
if response.data:
    total = sum(item["price"] * item["quantity"] for item in response.data)
    st.write(f"総投資額: {total} 円")
import pandas as pd
if response.data:
    df = pd.DataFrame(response.data)

    df["total"] = df["price"] * df["quantity"]

    st.subheader("銘柄ごと集計")
    grouped = df.groupby("symbol")["total"].sum().reset_index()
    st.dataframe(grouped)
if response.data:
    st.subheader("売買別集計")
    type_group = df.groupby("trade_type")["total"].sum().reset_index()
    st.dataframe(type_group)
st.subheader("データ削除")

delete_id = st.text_input("削除するIDを入力")

if st.button("削除"):
    supabase.table("trades").delete().eq("id", delete_id).execute()
    st.success("削除しました")
if response.data:
    buy_total = df[df["trade_type"] == "buy"]["total"].sum()
    sell_total = df[df["trade_type"] == "sell"]["total"].sum()

    profit = sell_total - buy_total

    st.subheader("簡易損益")
    st.write(f"損益: {profit} 円")