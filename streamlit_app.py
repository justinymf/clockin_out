import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
from streamlit_geolocation import streamlit_geolocation

# --- 頁面設定 ---
st.set_page_config(page_title="Decathlon Clock-In", page_icon="⏱️")
st.title("⏱️ Decathlon 員工打卡系統")

# --- 1. 身份驗證 ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.authenticated:
    st.subheader("🔐 請先登入")
    email_input = st.text_input("輸入 Decathlon Email", placeholder="your.name@decathlon.com")
    
    if st.button("進入系統"):
        if email_input.strip().lower().endswith("@decathlon.com"):
            st.session_state.authenticated = True
            st.session_state.user_email = email_input.strip()
            st.success("登入成功！")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ 只限 @decathlon.com 員工使用")
    st.stop()

# --- 2. 打卡主畫面 ---
st.write(f"👤 當前用戶: **{st.session_state.user_email}**")

st.markdown("### 📍 步驟 1: 獲取位置")
st.info("請點擊下方的 'Get Location' 按鈕")

# 使用專用插件獲取 GPS (會自帶一個按鈕)
location = streamlit_geolocation()

gps_loc = None
if location['latitude'] is not None:
    gps_loc = f"{location['latitude']},{location['longitude']}"
    st.success(f"✅ 成功鎖定座標: {gps_loc}")
else:
    st.warning("⚠️ 等待獲取位置中... (請確保已允許瀏覽器權限)")

# 檢查 GPS 是否有效
is_gps_ready = gps_loc is not None

# --- 3. Google Sheets 連接與寫入 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("⚠️ 資料庫連接錯誤，請檢查 Secrets。")
    conn = None

st.divider()
st.markdown("### 🎬 步驟 2: 選擇打卡動作")

col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

actions = {
    "上班": col1, "午飯開始": col2, "午飯結束": col3, "下班": col4
}

for action_name, col in actions.items():
    # 只有當 gps_loc 有值時，按鈕才可以用
    if col.button(f"{action_name}", use_container_width=True, disabled=not is_gps_ready):
        if conn:
            try:
                with st.spinner(f"正在紀錄 {action_name}..."):
                    # 1. 讀取
                    existing_data = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=0)
                    
                    # 2. 寫入
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    new_row = pd.DataFrame([{
                        "Email": st.session_state.user_email,
                        "Action": action_name,
                        "Time": now_time,
                        "Location": gps_loc
                    }])
                    
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    
                    st.success(f"✅ 打卡成功！{action_name} @ {now_time}")
                    st.balloons()
            except Exception as e:
                st.error(f"❌ 寫入失敗: {e}")
        else:
            st.error("系統錯誤：資料庫未連接")

# --- 4. 顯示紀錄 ---
st.divider()
st.markdown("### 📋 最近紀錄 (唯讀)")
if conn:
    try:
        df_show = conn.read(worksheet="Sheet1", usecols=list(range(4)), ttl=5)
        user_records = df_show[df_show["Email"] == st.session_state.user_email].tail(5)
        st.dataframe(user_records, use_container_width=True, hide_index=True)
    except:
        st.caption("暫時沒有紀錄")
