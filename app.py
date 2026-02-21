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

# ===== 銘柄コード入力（既存＋新規） =====
symbol_option = st.selectbox(
    "既存銘柄から選択",
    ["新規入力"] + symbols if symbols else ["新規入力"]
)

if symbol_option == "新規入力":
    symbol = st.text_input("銘柄コードを入力").strip()
else:
    symbol = symbol_option
trade_type = st.selectbox("売買区分", ["buy", "sell"])
trade_date = st.date_input("日付", date.today())
price = st.number_input("価格", min_value=0.0)
quantity = st.number_input("株数", min_value=1)
if not symbol:
    st.warning("銘柄コードを入力してください")
    st.stop()
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
    st.rerun()

# ===== 色付け関数 =====
def color_profit(val):
    if val > 0:
        return "color: green; font-weight: bold;"
    elif val < 0:
        return "color: red; font-weight: bold;"
    else:
        return "color: black;"

# ===== 取引履歴取得 =====
def get_trades():
    response = (
        supabase.table("trades")
        .select("id, symbol, trade_type, trade_date, price, quantity")
        .order("trade_date", desc=True)
        .execute()
    )
    return response.data if response.data else []

trades = get_trades()
df = pd.DataFrame(trades) if trades else pd.DataFrame()

if not df.empty:
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["symbol", "trade_date"])

# ===============================
# ===== 実現損益計算 ============
# ===============================

realized_trades = []
positions = []

if not df.empty:

    for symbol in df["symbol"].unique():

        symbol_df = df[df["symbol"] == symbol]

        position_qty = 0
        avg_price = 0

        for _, row in symbol_df.iterrows():

            qty = row["quantity"]
            price = row["price"]

            # BUY
            if row["trade_type"] == "buy":
                total_cost = avg_price * position_qty + price * qty
                position_qty += qty
                avg_price = total_cost / position_qty if position_qty > 0 else 0

            # SELL
            elif row["trade_type"] == "sell" and position_qty > 0:

                sell_qty = min(qty, position_qty)
                profit = (price - avg_price) * sell_qty

                realized_trades.append({
                    "銘柄": symbol,
                    "購入価格": round(avg_price, 2),
                    "購入枚数": sell_qty,
                    "売却価格": price,
                    "売却枚数": sell_qty,
                    "実現損益": profit,
                    "month": row["trade_date"].to_period("M")
                })

                position_qty -= sell_qty

        # ===== 保有ポジション =====
        if position_qty > 0:
            positions.append({
                "銘柄": symbol,
                "保有枚数": position_qty,
                "平均取得単価": round(avg_price, 2),
                "取得総額": round(position_qty * avg_price, 0)
            })

realized_df = pd.DataFrame(realized_trades)
positions_df = pd.DataFrame(positions)

# ===============================
# ===== 表示エリア ==============
# ===============================
st.set_page_config(layout="wide")
col1, col2 = st.columns(2)

# ===== 左カラム：保有ポジション =====
with col1:
    st.subheader("現在保有ポジション")

    if not positions_df.empty:
        st.dataframe(
    positions_df.style.format({
        "平均取得単価": "{:,.0f}",
        "取得総額": "{:,.0f}"
    }),
    hide_index=True
)

        total_value = positions_df["取得総額"].sum()
        st.write(f"■ 総取得額：{total_value:,.0f} 円")

    else:
        st.info("現在保有中の銘柄はありません")

# ===== 右カラム：月別実現損益 =====
with col2:
    st.subheader("月別実現損益")

    if not realized_df.empty:

        realized_df["month"] = realized_df["month"].astype(str)

        monthly_profit = (
            realized_df
            .groupby("month")["実現損益"]
            .sum()
            .reset_index()
            .rename(columns={"month": "月別"})
        )
        st.dataframe(
    monthly_profit.style
        .format({"実現損益": "{:,.0f}"})
        .map(color_profit, subset=["実現損益"]),
    hide_index=True
)
    else:
        st.info("月別実現損益はまだありません")

# ===============================
# ===== 銘柄別 & 合計 ============
# ===============================

if not realized_df.empty:

    symbol_summary = realized_df.groupby("銘柄")["実現損益"].sum().reset_index()

    st.subheader("銘柄別 実現損益合計")
    st.dataframe(
    symbol_summary.style
        .format({"実現損益": "{:,.0f}"})
        .map(color_profit, subset=["実現損益"]),
    hide_index=True
)

    total_profit = realized_df["実現損益"].sum()

    st.subheader("全体実現損益")
    st.write(f"{total_profit:,.0f} 円")

    with st.expander("決済完了取引一覧を見る"):
        st.dataframe(
    realized_df
        .drop(columns=["month"])
        .style
        .format({
            "購入価格": "{:,.0f}",
            "売却価格": "{:,.0f}",
            "実現損益": "{:,.0f}"
        })
        .map(color_profit, subset=["実現損益"]),
    hide_index=True
)

else:
    st.info("決済済み取引はありません")

# ===============================
# ===== 取引履歴（最後）==========
# ===============================

if trades:
    with st.expander("取引履歴を見る"):
        for row in trades:
            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(
                    f"{row['trade_date']} | {row['symbol']} | {row['trade_type']} | "
                    f"{row['price']}円 × {row['quantity']}"
                )

            with col2:
                delete_key = f"confirm_{row['id']}"

                if st.button("削除", key=f"del_{row['id']}"):
                    st.session_state[delete_key] = True

                if st.session_state.get(delete_key, False):
                    st.warning("本当に削除しますか？")

                    col_yes, col_no = st.columns(2)

                    with col_yes:
                        if st.button("はい", key=f"yes_{row['id']}"):
                            supabase.table("trades").delete().eq("id", row["id"]).execute()
                            st.success("削除しました")
                            st.session_state[delete_key] = False
                            st.rerun()

                    with col_no:
                        if st.button("いいえ", key=f"no_{row['id']}"):
                            st.session_state[delete_key] = False
