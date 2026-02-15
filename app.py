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

response = supabase.table("trades") \
    .select("id, symbol, trade_type, trade_date, price, quantity") \
    .order("trade_date", desc=True) \
    .execute()

if response.data:
    for row in response.data:
        col1, col2 = st.columns([5,1])

        with col1:
            st.write(
                f"{row['trade_date']} | {row['symbol']} | {row['trade_type']} | "
                f"{row['price']}円 × {row['quantity']}"
            )

        with col2:
            if st.button("削除", key=row["id"]):
                supabase.table("trades").delete().eq("id", row["id"]).execute()
                st.rerun()
else:
    st.write("データなし")
if response.data:
    total = sum(item["price"] * item["quantity"] for item in response.data)
    st.write(f"総投資額: {total} 円")
import pandas as pd

if response.data:
    df = pd.DataFrame(response.data)
    df["total"] = df["price"] * df["quantity"]

    st.subheader("銘柄ごとの売買集計")

    grouped = df.groupby(["symbol", "trade_type"])["total"].sum().reset_index()

    pivot = grouped.pivot(index="symbol", columns="trade_type", values="total").fillna(0)

    pivot["損益"] = pivot.get("sell", 0) - pivot.get("buy", 0)

    st.dataframe(pivot)
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

