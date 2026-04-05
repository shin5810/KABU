import streamlit as st
from supabase import create_client
from datetime import date
import pandas as pd

st.set_page_config(layout="wide")

# ===== Supabase設定 =====
SUPABASE_URL = "https://ofcrcrikfrgzgohzsnuo.supabase.co"
SUPABASE_KEY = "sb_publishable_j9MfY0FdNexNqzIEhxMCmQ_X9GPERlw"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===== 課税設定 =====
TAX_RATE = 0.20315
TAX_START_DATE = pd.to_datetime("2026-03-23")

# ===== 認証 =====
PASSWORD = "5810"
input_pw = st.text_input("パスワードを入力", type="password")
if input_pw != PASSWORD:
    st.warning("パスワードが違います")
    st.stop()

st.title("株取引記録ツール")

# ===== 入力 =====
symbols_res = supabase.table("trades").select("symbol").execute()
symbols = list({row["symbol"] for row in symbols_res.data}) if symbols_res.data else []

symbol_option = st.selectbox("既存銘柄", ["新規入力"] + symbols if symbols else ["新規入力"])

if symbol_option == "新規入力":
    symbol = st.text_input("銘柄コード").strip()
else:
    symbol = symbol_option

trade_type = st.selectbox("売買", ["buy", "sell"])
trade_date = st.date_input("日付", date.today())
price = st.number_input("価格", min_value=0.0)
quantity = st.number_input("株数", min_value=1)

# ★ 未来取引のみ意味ある
is_taxable = st.checkbox("課税対象にする（20.315%）", value=True)

if not symbol:
    st.warning("銘柄コードを入力")
    st.stop()

if st.button("保存"):
    supabase.table("trades").insert({
        "symbol": symbol,
        "trade_type": trade_type,
        "trade_date": str(trade_date),
        "price": price,
        "quantity": quantity,
        "is_taxable": is_taxable
    }).execute()

    st.success("保存完了")
    st.rerun()

# ===== データ取得 =====
def get_trades():
    res = supabase.table("trades") \
        .select("id,symbol,trade_type,trade_date,price,quantity,is_taxable") \
        .order("trade_date") \
        .execute()
    return res.data if res.data else []

trades = get_trades()
df = pd.DataFrame(trades) if trades else pd.DataFrame()

if not df.empty:
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["symbol", "trade_date"])

# ===== 計算 =====
realized = []
positions = []

if not df.empty:

    for symbol in df["symbol"].unique():

        sdf = df[df["symbol"] == symbol]

        qty_pos = 0
        avg_price = 0

        for _, row in sdf.iterrows():

            qty = row["quantity"]
            price = row["price"]

            if row["trade_type"] == "buy":
                total = avg_price * qty_pos + price * qty
                qty_pos += qty
                avg_price = total / qty_pos if qty_pos > 0 else 0

            elif row["trade_type"] == "sell" and qty_pos > 0:

                sell_qty = min(qty, qty_pos)
                gross = (price - avg_price) * sell_qty

                # ★ 課税判定（ここが重要）
                if row["trade_date"] >= TAX_START_DATE:
                    taxable = row.get("is_taxable", True)
                else:
                    taxable = False

                tax = gross * TAX_RATE if (taxable and gross > 0) else 0
                net = gross - tax

                realized.append({
                    "銘柄": symbol,
                    "購入価格": round(avg_price, 2),
                    "購入枚数": sell_qty,
                    "売却価格": price,
                    "売却枚数": sell_qty,
                    "実現損益": net,
                    "税額": round(tax, 0),
                    "課税": "あり" if taxable else "なし",
                    "year": row["trade_date"].year,
                    "month": row["trade_date"].to_period("M")
                })

                qty_pos -= sell_qty

        if qty_pos > 0:
            positions.append({
                "銘柄": symbol,
                "保有枚数": qty_pos,
                "平均取得単価": round(avg_price, 2),
                "取得総額": round(qty_pos * avg_price, 0)
            })

realized_df = pd.DataFrame(realized)
positions_df = pd.DataFrame(positions)

# ===== UI =====
col1, col2 = st.columns(2)

# 保有
with col1:
    st.subheader("保有ポジション")
    if not positions_df.empty:
        st.dataframe(
    positions_df.style.format({
        "平均取得単価": "{:,.0f}",
        "取得総額": "{:,.0f}"
    }),
    hide_index=True
)
    else:
        st.info("なし")

# 月別
with col2:
    st.subheader("月別損益")
    if not realized_df.empty:
        m = realized_df.groupby("month")["実現損益"].sum().reset_index()
        st.dataframe(
    m.style.format({"実現損益": "{:,.0f}"}),
    hide_index=True
)
    else:
        st.info("なし")

# 年間税額（確定申告用）
st.subheader("年間税額（確定申告）")

if not realized_df.empty:
    y = realized_df.groupby("year")["税額"].sum().reset_index()
    st.dataframe(
    y.style.format({"税額": "{:,.0f}"}),
    hide_index=True
)

    total_tax = realized_df["税額"].sum()
    st.write(f"合計税額：{total_tax:,.0f} 円")
else:
    st.info("データなし")

# 銘柄別
if not realized_df.empty:
    s = realized_df.groupby("銘柄")["実現損益"].sum().reset_index()
    st.subheader("銘柄別損益")
    st.dataframe(
    s.style.format({"実現損益": "{:,.0f}"}),
    hide_index=True
)

    st.subheader("総損益")
    st.write(f"{realized_df['実現損益'].sum():,.0f} 円")

    with st.expander("決済一覧"):
        st.dataframe(
    realized_df.drop(columns=["month"]).style.format({
        "購入価格": "{:,.0f}",
        "売却価格": "{:,.0f}",
        "実現損益": "{:,.0f}",
        "税額": "{:,.0f}"
    }),
    hide_index=True
)

# ===== 取引履歴 =====
if trades:
    with st.expander("取引履歴を見る"):
        for row in sorted(trades, key=lambda x: x["trade_date"], reverse=True):
            col1, col2 = st.columns([5, 1])

            with col1:
                st.write(
                    f"{row['trade_date']} | {row['symbol']} | {row['trade_type']} | "
                    f"{row['price']}円 × {row['quantity']} | "
                    f"課税:{'あり' if row.get('is_taxable', True) else 'なし'}"
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
