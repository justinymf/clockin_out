import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components

st.set_page_config(page_title="Decathlon 打卡系統", layout="centered")

# --- 2FA 模擬邏輯 ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🛡️ 員工身份驗證")
    email = st.text_input("輸入 Decathlon Email", placeholder="user@decathlon.com")
    if st.button("下一步"):
        if email.endswith("@decathlon.com"):
            st.session_state.user = email
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("只限 @decathlon.com 域名")
    st.stop()

# --- 主介面 ---
st.title("🕒 Decathlon 打卡系統")
st.write(f"當前用戶: **{st.session_state.user}**")

# GPS 獲取組件 (HTML5)
st.markdown("### 1. 獲取位置")
if st.button("📍 點擊獲取當前 GPS"):
    # 這段 JS 會在瀏覽器執行並回傳經緯度
    components.html("""
        <script>
        navigator.geolocation.getCurrentPosition(function(pos) {
            const coords = pos.coords.latitude + "," + pos.coords.longitude;
            window.parent.postMessage({type: 'streamlit:setComponentValue', value: coords}, '*');
        });
        </script>
    """, height=0)
    st.info("請允許瀏覽器定位權限...")

# 接收 JS 回傳的座標
loc = st.text_input("經緯度座標", key="gps_pos", help="自動獲取後顯示")

st.divider()

# 打卡按鈕
st.markdown("### 2. 選擇動作")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if col1.button("🎬 上班", use_container_width=True):
    st.success(f"紀錄成功: 上班 @ {now}")
if col2.button("🍱 午飯開始", use_container_width=True):
    st.success(f"紀錄成功: 午飯開始 @ {now}")
if col3.button("☕ 午飯結束", use_container_width=True):
    st.success(f"紀錄成功: 午飯結束 @ {now}")
if col4.button("🏠 下班", use_container_width=True):
    st.success(f"紀錄成功: 下班 @ {now}")

# 暫存紀錄
st.divider()
st.subheader("📝 本次作業紀錄 (暫存)")
if 'history' not in st.session_state: st.session_state.history = []
# 顯示最近紀錄 (模擬)
st.table(st.session_state.history)