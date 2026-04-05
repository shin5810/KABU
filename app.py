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
