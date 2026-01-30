import streamlit as st
from pyairtable import Api
from datetime import datetime, timedelta
import time
from streamlit_geolocation import streamlit_geolocation

# --- 頁面設定 ---
st.set_page_config(page_title="Decathlon Smart Clock-In", page_icon="⏱️")

# --- 1. 連接 Airtable ---
try:
    api_key = st.secrets["airtable"]["api_key"]
    base_id = st.secrets["airtable"]["base_id"]
    table_id = st.secrets["airtable"]["table_id"]
    api = Api(api_key)
    table = api.table(base_id, table_id)
except:
    st.error("⚠️ Secrets 設定未完成，請檢查 Streamlit Cloud Settings！")
    st.stop()

# --- 2. Session State 初始化 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

# --- 3. 定義登出函數 ---
def logout():
    st.session_state.authenticated = False
    st.session_state.user_email = ""
    st.rerun()

# ==========================================
#  邏輯分流：未登入 vs 已登入
# ==========================================

if not st.session_state.authenticated:
    # ------------------
    #    登入畫面
    # ------------------
    st.title("🔐 Decathlon 員工登入")
    st.markdown("請輸入你的公司電郵以進入打卡系統。")
    
    with st.form("login_form"):
        email_input = st.text_input("Email", placeholder="your.name@decathlon.com")
        submit_button = st.form_submit_button("進入系統")
        
        if submit_button:
            if email_input.strip().lower().endswith("@decathlon.com"):
                st.session_state.authenticated = True
                st.session_state.user_email = email_input.strip()
                st.success("✅ 登入成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("❌ 驗證失敗：只限 @decathlon.com 員工使用")

else:
    # ------------------
    #    主程式畫面 (已登入)
    # ------------------
    
    # --- 側邊欄：用戶資訊 & 登出 ---
    with st.sidebar:
        st.title("👤 用戶檔案")
        st.write(f"Email: **{st.session_state.user_email}**")
        st.divider()
        if st.button("👋 登出系統", type="secondary", use_container_width=True):
            logout()

    # --- 主標題 ---
    st.title("⏱️ Decathlon 智能打卡")

    # --- 獲取 GPS ---
    st.info("👇 請先點擊下方按鈕獲取位置")
    location = streamlit_geolocation()
    gps_loc = None

    if location['latitude'] is not None:
        gps_loc = f"{location['latitude']},{location['longitude']}"
        st.success(f"✅ 成功鎖定座標: {gps_loc}")
    else:
        st.caption("等待定位中...")

    is_gps_ready = gps_loc
